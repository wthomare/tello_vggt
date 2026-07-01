"""Record command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from datetime import datetime

from tello_vggt.core.config import AppConfig
from tello_vggt.core.mission import Mission, MissionManager, MissionStatus
from tello_vggt.core.logging_config import get_logger

logger = get_logger(__name__)


def cmd_record(
    config: AppConfig,
    duration: Optional[int] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Record from Tello drone.
    
    Args:
        config: Application configuration
        duration: Recording duration in seconds (None = until interrupt)
        output_dir: Output mission directory (auto-generated if None)
    
    Returns:
        Path to mission directory
    """
    try:
        from djitellopy import Tello
    except ImportError:
        logger.error("djitellopy not installed. Install with: pip install djitellopy")
        raise
    
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
    
    logger.info(f"Starting recording to: {mission.mission_dir}")
    
    # Connect to Tello
    tello = Tello()
    logger.info("Connecting to Tello...")
    tello.connect()
    
    battery = tello.get_battery()
    logger.info(f"🔋 Battery: {battery}%")
    
    if battery < config.acquisition.tello_battery_warning:
        logger.warning(f"⚠️ Battery low ({battery}%)")
    
    # Start streaming
    tello.streamon()
    frame_reader = tello.get_frame_read()
    
    logger.info("🎬 Recording started. Press Ctrl+C to stop.")
    
    # Recording loop
    try:
        frame_count = 0
        start_time = datetime.now()
        
        mission.set_status(MissionStatus.RECORDING)
        
        while True:
            frame = frame_reader.frame
            
            if frame is None:
                continue
            
            # Save frame
            frame_path = mission.frames_dir / f"frame_{frame_count:07d}.jpg"
            import cv2
            cv2.imwrite(str(frame_path), frame)
            
            frame_count += 1
            
            # Check duration limit
            if duration:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= duration:
                    break
            
            if frame_count % 30 == 0:
                logger.info(f"Recorded {frame_count} frames")
        
        logger.info(f"✅ Recording complete: {frame_count} frames")
        mission.set_status(MissionStatus.RECORDED)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Recording interrupted by user")
        mission.set_status(MissionStatus.RECORDED)
    
    finally:
        tello.streamoff()
    
    return mission.mission_dir
