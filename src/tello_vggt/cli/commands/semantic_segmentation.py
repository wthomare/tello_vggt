"""Semantic segmentation command with Deep Anything V3."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import cv2

from tello_vggt.core.config import AppConfig
from tello_vggt.core.mission import Mission
from tello_vggt.core.logging_config import get_logger, log_section
from tello_vggt.mission_loader import MissionLoader, load_frames

logger = get_logger(__name__)


def cmd_semantic_segmentation(
    config: AppConfig,
    mission_path: Path,
    output: Optional[Path] = None,
) -> Path:
    """Generate semantic segmentation with Deep Anything V3.
    
    Args:
        config: Application configuration
        mission_path: Mission directory or mission ID
        output: Output directory
    
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
    
    # Load chunks and frames
    log_section(logger, "Loading Mission Data")
    
    chunks = MissionLoader.load_chunks(mission.chunks_dir)
    if not chunks:
        raise RuntimeError(f"No chunks found in {mission.chunks_dir}")
    
    logger.info(f"Loaded {len(chunks)} chunks")
    
    # Fuse chunks
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
    output_dir = Path(output) if output else mission.output_dir / "semantic_segmentation"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process with Deep Anything V3
    log_section(logger, "Semantic Segmentation")
    
    from tello_vggt.rendering.deep_anything_v3 import DeepAnythingV3Processor
    
    processor = DeepAnythingV3Processor(
        checkpoint_path=config.gaussian_splatting.deep_anything_v3_checkpoint,
        device=config.vggt.device,
    )
    
    # Process VGGT result
    frames_array = np.stack([cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in frames])
    
    da_result = processor.process_vggt_result(
        vggt_result,
        images=frames_array,
        segmentation_prompt="all objects",
    )
    
    logger.info(f"✅ Segmentation complete")
    logger.info(f"   Detected {len(da_result['class_point_clouds'])} semantic classes")
    
    # Save results
    seg_path = output_dir / f"{mission.mission_id}_segmentation.npz"
    np.savez_compressed(
        seg_path,
        segmentations=da_result["segmentations"],
        semantic_depth=da_result["semantic_depth"],
    )
    logger.info(f"💾 Segmentation saved to {seg_path}")
    
    # Export class point clouds as separate PLY files
    try:
        from plyfile import PlyData, PlyElement
        
        for class_id, points in da_result["class_point_clouds"].items():
            ply_path = output_dir / f"{mission.mission_id}_class_{class_id}.ply"
            
            vertex = np.zeros(len(points), dtype=[("x", "f4"), ("y", "f4"), ("z", "f4")])
            vertex["x"] = points[:, 0]
            vertex["y"] = points[:, 1]
            vertex["z"] = points[:, 2]
            
            ply_element = PlyElement.describe(vertex, "vertex")
            ply_data = PlyData([ply_element])
            ply_data.write(ply_path)
            
            logger.info(f"   Exported class {class_id}: {ply_path}")
    
    except ImportError:
        logger.warning("plyfile not installed. Skipping PLY export.")
    
    logger.info(f"\n✨ Semantic segmentation output ready at: {output_dir}\n")
    
    return output_dir
