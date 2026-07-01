"""Rebuild command implementation."""

from __future__ import annotations

from pathlib import Path

from tello_vggt.core.config import AppConfig
from tello_vggt.core.mission import Mission, MissionStatus
from tello_vggt.core.logging_config import get_logger, log_section
from tello_vggt.mission_loader import MissionLoader, load_frames
from tello_vggt.vggt_chunk_fusioner import VGGTChunkFusioner
from tello_vggt.vggt_chunk_result import VGGTGlbExporter

logger = get_logger(__name__)


def cmd_rebuild(
    config: AppConfig,
    mission_path: Path,
    re_export: bool = False,
) -> Path:
    """Rebuild GLB from existing mission chunks.
    
    Args:
        config: Application configuration
        mission_path: Mission directory or mission ID
        re_export: Force re-export even if GLB exists
    
    Returns:
        Path to GLB file
    """
    mission_path = Path(mission_path)
    
    # Resolve mission path
    if not mission_path.is_absolute():
        # Try as mission ID
        resolved_path = config.missions_dir / mission_path
        if resolved_path.exists():
            mission_path = resolved_path
    
    if not mission_path.exists():
        raise FileNotFoundError(f"Mission not found: {mission_path}")
    
    # Load mission
    mission = Mission.load(mission_path)
    
    logger.info(f"📂 Loaded mission: {mission.mission_id}")
    logger.info(f"   Status: {mission.get_status().value}")
    logger.info(f"   Frames: {mission.num_frames}")
    logger.info(f"   Chunks: {mission.num_chunks}")
    
    # Check if GLB already exists
    if mission.glb_path.exists() and not re_export:
        logger.info(f"✅ GLB already exists: {mission.glb_path}")
        return mission.glb_path
    
    if mission.num_chunks == 0:
        raise RuntimeError(f"No chunks found in {mission.chunks_dir}")
    
    # Load and fuse chunks
    log_section(logger, "Loading Chunks")
    
    chunks = MissionLoader.load_chunks(mission.chunks_dir)
    logger.info(f"✅ Loaded {len(chunks)} chunks")
    
    log_section(logger, "Fusing Chunks")
    
    fusioner = VGGTChunkFusioner(
        min_overlap=config.inference.min_overlap_fusion,
        max_overlap=config.inference.max_overlap_fusion,
        use_allclose=config.inference.use_allclose_fusion,
    )
    
    fusioner.extend(chunks)
    fused_result = fusioner.fuse()
    
    logger.info(f"✅ Fused result: {fused_result.depth.shape[0]} frames")
    
    # Load frames
    log_section(logger, "Loading Frames")
    
    frames = load_frames(mission.frames_dir)
    logger.info(f"✅ Loaded {len(frames)} frames")
    
    # Verify frame count
    if fused_result.depth.shape[0] != len(frames):
        logger.warning(
            f"Frame mismatch: {fused_result.depth.shape[0]} predictions vs {len(frames)} frames"
        )
        frames = frames[:fused_result.depth.shape[0]]
    
    # Export GLB
    log_section(logger, "Exporting GLB")
    
    exporter = VGGTGlbExporter(input_is_bgr=True)
    
    glb_path = exporter.export_glb(
        result=fused_result,
        out_path=mission.glb_path,
        frames=frames,
        conf_thres=config.export.confidence_threshold,
        show_cam=config.export.show_cameras,
        mask_black_bg=config.export.mask_black_background,
        mask_white_bg=config.export.mask_white_background,
    )
    
    mission.set_status(MissionStatus.COMPLETED)
    
    logger.info(f"\n✨ Rebuild complete! GLB: {glb_path}\n")
    return glb_path
