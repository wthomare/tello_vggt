"""Video reconstruction command implementation."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Optional

import cv2
import torch
from tqdm import tqdm

from tello_vggt.core.config import AppConfig
from tello_vggt.core.mission import Mission, MissionManager, MissionStatus
from tello_vggt.core.logging_config import get_logger, log_section
from tello_vggt.mission_loader import load_frames
from tello_vggt.vggt_omega_tello_inferencer import VGGTOmegaTelloInferencer
from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner
from tello_vggt.vggt_chunk_result import VGGTGlbExporter

logger = get_logger(__name__)


def _extract_frames(video_path: Path, frames_dir: Path) -> int:
    """Extract frames from video file."""
    log_section(logger, "Extracting Frames")
    
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(f"Total frames in video: {total_frames}")
    
    frame_count = 0
    pbar = tqdm(total=total_frames, desc="Extracting frames")
    
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        
        frame_path = frames_dir / f"frame_{frame_count:06d}.jpg"
        cv2.imwrite(str(frame_path), frame)
        
        frame_count += 1
        pbar.update(1)
    
    pbar.close()
    cap.release()
    
    logger.info(f"✅ Extracted {frame_count} frames to {frames_dir}")
    return frame_count


def _run_inference(
    video_path: Path,
    config: AppConfig,
    chunks_dir: Path,
) -> int:
    """Run VGGT-Omega inference on video."""
    log_section(logger, "VGGT-Omega Inference")
    
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize inferencer
    inferencer = VGGTOmegaTelloInferencer(
        checkpoint_path=str(config.vggt.checkpoint_path),
        device=config.vggt.device,
        image_resolution=config.vggt.image_resolution,
        mode=config.vggt.mode.value if hasattr(config.vggt.mode, 'value') else config.vggt.mode,
        enable_alignment=config.vggt.enable_alignment,
        input_is_bgr=True,
    )
    
    logger.info(f"VGGT-Omega loaded on {config.vggt.device}")
    
    # Video frame generator
    def video_frame_generator():
        cap = cv2.VideoCapture(str(video_path))
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
        cap.release()
    
    # Run inference with progress
    chunk_count = 0
    try:
        for result in inferencer.infer_stream(
            video_frame_generator(),
            chunk_size=config.inference.chunk_size,
            overlap=config.inference.overlap,
        ):
            chunk_file = chunks_dir / f"chunk_{chunk_count:05d}.npz"
            result.save(chunk_file)
            
            logger.info(f"💾 Saved chunk {chunk_count} to {chunk_file.name}")
            
            del result
            torch.cuda.empty_cache()
            gc.collect()
            
            chunk_count += 1
    
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise
    
    logger.info(f"✅ Inference complete: {chunk_count} chunks processed")
    return chunk_count


def _fuse_chunks(config: AppConfig, chunks_dir: Path):
    """Fuse overlapping chunks."""
    log_section(logger, "Fusing Chunks")
    
    from tello_vggt.mission_loader import MissionLoader
    
    chunks = MissionLoader.load_chunks(chunks_dir)
    if not chunks:
        raise RuntimeError(f"No chunks found in {chunks_dir}")
    
    logger.info(f"Loaded {len(chunks)} chunks for fusion")
    
    fusioner = VGGTChunkFusioner(
        min_overlap=config.inference.min_overlap_fusion,
        max_overlap=config.inference.max_overlap_fusion,
        use_allclose=config.inference.use_allclose_fusion,
    )
    
    fusioner.extend(chunks)
    fused_result = fusioner.fuse()
    
    logger.info(f"✅ Fused result: {fused_result.depth.shape[0]} frames")
    
    return fused_result


def _export_glb(
    config: AppConfig,
    fused_result,
    frames_dir: Path,
    output_path: Path,
) -> Path:
    """Export fused result to GLB."""
    log_section(logger, "Exporting GLB")
    
    logger.info("Loading frames...")
    frames = load_frames(frames_dir)
    logger.info(f"Loaded {len(frames)} frames")
    
    # Verify frame count
    if fused_result.depth.shape[0] != len(frames):
        logger.warning(
            f"Frame mismatch: {fused_result.depth.shape[0]} predictions vs {len(frames)} frames"
        )
        frames = frames[:fused_result.depth.shape[0]]
    
    logger.info("Exporting GLB...")
    exporter = VGGTGlbExporter(input_is_bgr=True)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    glb_path = exporter.export_glb(
        result=fused_result,
        out_path=output_path,
        frames=frames,
        conf_thres=config.export.confidence_threshold,
        show_cam=config.export.show_cameras,
        mask_black_bg=config.export.mask_black_background,
        mask_white_bg=config.export.mask_white_background,
    )
    
    logger.info(f"✅ GLB exported to: {glb_path}")
    return glb_path


def cmd_video(
    config: AppConfig,
    video_path: Path,
    output_dir: Optional[Path] = None,
    skip_inference: bool = False,
    skip_export: bool = False,
) -> Path:
    """Reconstruct from video file.
    
    Args:
        config: Application configuration
        video_path: Input video file path
        output_dir: Output mission directory (auto-generated if None)
        skip_inference: Skip VGGT inference
        skip_export: Skip GLB export
    
    Returns:
        Path to mission directory or GLB file
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Create mission
    mission_manager = MissionManager(config.missions_dir)
    if output_dir:
        output_dir = Path(output_dir)
        if output_dir.exists():
            raise FileExistsError(f"Mission already exists: {output_dir}")
        mission = Mission(output_dir.name, output_dir)
        mission.setup()
    else:
        mission = mission_manager.create_mission()
    
    logger.info(f"Processing video: {video_path}")
    logger.info(f"Mission directory: {mission.mission_dir}")
    
    try:
        # Extract frames
        _extract_frames(video_path, mission.frames_dir)
        
        # Run inference
        if not skip_inference:
            mission.set_status(MissionStatus.INFERENCING)
            _run_inference(video_path, config, mission.chunks_dir)
            mission.set_status(MissionStatus.INFERENCED)
        
        # Fuse chunks
        if not skip_export and mission.num_chunks > 0:
            fused_result = _fuse_chunks(config, mission.chunks_dir)
            mission.set_status(MissionStatus.FUSING)
            
            # Export GLB
            glb_path = _export_glb(
                config,
                fused_result,
                mission.frames_dir,
                mission.glb_path,
            )
            
            mission.set_status(MissionStatus.COMPLETED)
            logger.info(f"\n✨ Mission completed! GLB: {glb_path}\n")
            
            return glb_path
        else:
            mission.set_status(MissionStatus.COMPLETED)
            return mission.mission_dir
    
    except Exception as e:
        logger.error(f"❌ Mission failed: {e}", exc_info=True)
        mission.set_status(MissionStatus.FAILED)
        raise
