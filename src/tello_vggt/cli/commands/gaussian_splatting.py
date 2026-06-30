"""Gaussian Splatting rendering command."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from tello_vggt.core.config import AppConfig
from tello_vggt.core.mission import Mission
from tello_vggt.core.logging_config import get_logger, log_section
from tello_vggt.mission_loader import MissionLoader, load_frames
from tello_vggt.rendering.gaussian_splatting import GaussianSplattingTrainer, GaussianSplattingRenderer

logger = get_logger(__name__)


def cmd_gaussian_splatting(
    config: AppConfig,
    mission_path: Path,
    output: Optional[Path] = None,
    skip_training: bool = False,
) -> Path:
    """Render Gaussian Splatting from mission.
    
    Args:
        config: Application configuration
        mission_path: Mission directory or mission ID
        output: Output directory for renderings
        skip_training: Skip training, only render
    
    Returns:
        Path to output directory
    """
    mission_path = Path(mission_path)
    
    # Resolve mission path
    if not mission_path.is_absolute():
        resolved_path = config.missions_dir / mission_path
        if resolved_path.exists():
            mission_path = resolved_path
    
    if not mission_path.exists():
        raise FileNotFoundError(f"Mission not found: {mission_path}")
    
    # Load mission
    mission = Mission.load(mission_path)
    
    logger.info(f"📂 Loaded mission: {mission.mission_id}")
    
    # Check if Gaussian Splatting is enabled
    if not config.gaussian_splatting.enabled:
        logger.warning("Gaussian Splatting is disabled in config")
        return None
    
    # Load chunks
    log_section(logger, "Loading Mission Data")
    
    chunks = MissionLoader.load_chunks(mission.chunks_dir)
    if not chunks:
        raise RuntimeError(f"No chunks found in {mission.chunks_dir}")
    
    logger.info(f"Loaded {len(chunks)} chunks")
    
    # Combine chunks
    from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner
    
    fusioner = VGGTChunkFusioner(
        min_overlap=config.inference.min_overlap_fusion,
        max_overlap=config.inference.max_overlap_fusion,
    )
    fusioner.extend(chunks)
    vggt_result = fusioner.fuse()
    
    logger.info(f"Fused result: {vggt_result.depth.shape[0]} frames")
    
    # Load frames
    frames = load_frames(mission.frames_dir)
    logger.info(f"Loaded {len(frames)} frames")
    
    # Setup output directory
    output_dir = Path(output) if output else mission.output_dir / "gaussian_splatting"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Train Gaussian Splatting
    if not skip_training:
        log_section(logger, "Training Gaussian Splatting")
        
        trainer = GaussianSplattingTrainer(
            sh_degree=config.gaussian_splatting.sh_degree,
            densification_interval=config.gaussian_splatting.densification_interval,
            iterations=config.gaussian_splatting.iterations,
            device=config.vggt.device,
        )
        
        # Ensure frames format (H, W, 3)
        frames_array = np.stack(frames)  # (N, H, W, 3)
        
        gs_result = trainer.train_from_vggt(
            vggt_result,
            camera_poses=vggt_result.extrinsics,
            camera_intrinsics=vggt_result.intrinsics,
            images=frames_array,
        )
        
        # Save Gaussian Splatting result
        gs_path = output_dir / f"{mission.mission_id}_gaussians.npz"
        gs_result.save(gs_path)
        
        logger.info(f"✅ Gaussian Splatting result saved to {gs_path}")
        
        # Export PLY
        ply_path = output_dir / f"{mission.mission_id}_gaussians.ply"
        renderer = GaussianSplattingRenderer(device=config.vggt.device)
        renderer.export_ply(gs_result, ply_path)
        
        logger.info(f"✅ Exported PLY to {ply_path}")
    
    # Process with Deep Anything V3 if available
    if config.gaussian_splatting.backend == "deep_anything_v3":
        log_section(logger, "Processing with Deep Anything V3")
        
        from tello_vggt.rendering.deep_anything_v3 import DeepAnythingV3Processor
        
        processor = DeepAnythingV3Processor(
            checkpoint_path=config.gaussian_splatting.deep_anything_v3_checkpoint,
            device=config.vggt.device,
        )
        
        # Process VGGT result
        frames_array = np.stack(frames)
        
        da_result = processor.process_vggt_result(
            vggt_result,
            images=frames_array,
            segmentation_prompt="all objects",
        )
        
        logger.info(f"✅ Deep Anything V3 segmentation complete")
        logger.info(f"   Detected {len(da_result['class_point_clouds'])} semantic classes")
    
    logger.info(f"\n✨ Gaussian Splatting output ready at: {output_dir}\n")
    
    return output_dir
