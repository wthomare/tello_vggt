"""Mission management and lifecycle."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any

from tello_vggt.core.logging_config import get_logger

logger = get_logger(__name__)


class MissionStatus(str, Enum):
    """Mission execution status."""
    INITIALIZED = "initialized"
    RECORDING = "recording"
    RECORDED = "recorded"
    INFERENCING = "inferencing"
    INFERENCED = "inferenced"
    FUSING = "fusing"
    FUSED = "fused"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MissionMetadata:
    """Mission metadata."""
    mission_id: str
    status: MissionStatus
    created_at: str
    updated_at: str
    config_path: Optional[str] = None
    checkpoint_path: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissionMetadata:
        """Create from dictionary."""
        data = dict(data)
        if "status" in data and isinstance(data["status"], str):
            data["status"] = MissionStatus(data["status"])
        return cls(**data)


class Mission:
    """Manages mission lifecycle and directories."""
    
    def __init__(self, mission_id: str, mission_dir: Path):
        """Initialize mission.
        
        Args:
            mission_id: Unique mission identifier
            mission_dir: Root directory for mission
        """
        self.mission_id = mission_id
        self.mission_dir = Path(mission_dir)
        
        # Create subdirectories
        self.chunks_dir = self.mission_dir / "chunks"
        self.frames_dir = self.mission_dir / "frames"
        self.output_dir = self.mission_dir / "output"
        self.logs_dir = self.mission_dir / "logs"
        self.checkpoint_dir = self.mission_dir / "checkpoints"
        
        # Create metadata
        now = datetime.now().isoformat()
        self.metadata = MissionMetadata(
            mission_id=mission_id,
            status=MissionStatus.INITIALIZED,
            created_at=now,
            updated_at=now,
        )
    
    def setup(self) -> None:
        """Create necessary directories and metadata file."""
        for directory in [self.chunks_dir, self.frames_dir, self.output_dir, 
                         self.logs_dir, self.checkpoint_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.save_metadata()
        logger.info(f"Mission {self.mission_id} initialized at {self.mission_dir}")
    
    def get_status(self) -> MissionStatus:
        """Get mission status."""
        return self.metadata.status
    
    def set_status(self, status: MissionStatus | str) -> None:
        """Update mission status."""
        if isinstance(status, str):
            status = MissionStatus(status)
        self.metadata.status = status
        self.metadata.updated_at = datetime.now().isoformat()
        self.save_metadata()
        logger.info(f"Mission {self.mission_id} status: {status.value}")
    
    def save_metadata(self) -> None:
        """Save metadata to JSON file."""
        metadata_file = self.mission_dir / "mission.json"
        with open(metadata_file, "w") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)
    
    def load_metadata(self) -> None:
        """Load metadata from JSON file."""
        metadata_file = self.mission_dir / "mission.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                data = json.load(f)
            self.metadata = MissionMetadata.from_dict(data)
    
    @property
    def num_frames(self) -> int:
        """Get number of recorded frames."""
        return len(list(self.frames_dir.glob("frame_*.jpg"))) + \
               len(list(self.frames_dir.glob("frame_*.png")))
    
    @property
    def num_chunks(self) -> int:
        """Get number of inference chunks."""
        return len(list(self.chunks_dir.glob("chunk_*.npz")))
    
    @property
    def glb_path(self) -> Path:
        """Get path to output GLB file."""
        return self.output_dir / f"{self.mission_id}_reconstruction.glb"
    
    @classmethod
    def create(cls, missions_dir: Path, mission_id: Optional[str] = None) -> Mission:
        """Create a new mission with auto-generated ID if needed.
        
        Args:
            missions_dir: Root missions directory
            mission_id: Optional mission ID. If None, generates from timestamp.
        
        Returns:
            Mission instance
        """
        if mission_id is None:
            mission_id = f"mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        mission_dir = missions_dir / mission_id
        if mission_dir.exists():
            raise FileExistsError(f"Mission already exists: {mission_dir}")
        
        mission = cls(mission_id, mission_dir)
        mission.setup()
        return mission
    
    @classmethod
    def load(cls, mission_dir: Path) -> Mission:
        """Load existing mission from directory.
        
        Args:
            mission_dir: Mission directory path
        
        Returns:
            Mission instance
        """
        mission_dir = Path(mission_dir)
        if not mission_dir.exists():
            raise FileNotFoundError(f"Mission directory not found: {mission_dir}")
        
        mission_id = mission_dir.name
        mission = cls(mission_id, mission_dir)
        mission.load_metadata()
        return mission


class MissionManager:
    """Manages multiple missions."""
    
    def __init__(self, missions_dir: Path):
        """Initialize mission manager.
        
        Args:
            missions_dir: Root directory for all missions
        """
        self.missions_dir = Path(missions_dir)
        self.missions_dir.mkdir(parents=True, exist_ok=True)
    
    def list_missions(self) -> list[Mission]:
        """List all available missions.
        
        Returns:
            List of Mission instances
        """
        missions = []
        for mission_dir in self.missions_dir.iterdir():
            if mission_dir.is_dir() and (mission_dir / "mission.json").exists():
                try:
                    mission = Mission.load(mission_dir)
                    missions.append(mission)
                except Exception as e:
                    logger.warning(f"Failed to load mission {mission_dir}: {e}")
        
        return sorted(missions, key=lambda m: m.metadata.created_at, reverse=True)
    
    def get_mission(self, mission_id: str) -> Mission:
        """Get mission by ID.
        
        Args:
            mission_id: Mission identifier
        
        Returns:
            Mission instance
        
        Raises:
            FileNotFoundError: If mission not found
        """
        mission_dir = self.missions_dir / mission_id
        return Mission.load(mission_dir)
    
    def create_mission(self, mission_id: Optional[str] = None) -> Mission:
        """Create new mission.
        
        Args:
            mission_id: Optional mission ID
        
        Returns:
            Mission instance
        """
        return Mission.create(self.missions_dir, mission_id)
    
    def delete_mission(self, mission_id: str, force: bool = False) -> None:
        """Delete mission (with safety checks).
        
        Args:
            mission_id: Mission to delete
            force: Skip status checks
        """
        mission = self.get_mission(mission_id)
        
        if not force and mission.get_status() != MissionStatus.COMPLETED:
            raise RuntimeError(
                f"Cannot delete mission in {mission.get_status().value} status. "
                "Use force=True to override."
            )
        
        import shutil
        shutil.rmtree(mission.mission_dir)
        logger.info(f"Deleted mission {mission_id}")
