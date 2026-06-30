"""Tests for mission management."""

import pytest
from pathlib import Path
from datetime import datetime

from tello_vggt.core.mission import Mission, MissionManager, MissionStatus


def test_mission_creation(temp_dir):
    """Test mission creation."""
    mission = Mission.create(temp_dir / "missions", "test_mission")
    
    assert mission.mission_id == "test_mission"
    assert mission.mission_dir.exists()
    assert mission.chunks_dir.exists()
    assert mission.frames_dir.exists()
    assert mission.output_dir.exists()
    assert mission.logs_dir.exists()


def test_mission_metadata():
    """Test mission metadata."""
    mission = Mission("test", Path("/tmp/test"))
    
    assert mission.metadata.mission_id == "test"
    assert mission.metadata.status == MissionStatus.INITIALIZED


def test_mission_status_changes(temp_dir):
    """Test mission status transitions."""
    mission = Mission.create(temp_dir / "missions", "test_mission")
    
    mission.set_status(MissionStatus.RECORDING)
    assert mission.get_status() == MissionStatus.RECORDING
    
    mission.set_status(MissionStatus.INFERENCING)
    assert mission.get_status() == MissionStatus.INFERENCING
    
    mission.set_status(MissionStatus.COMPLETED)
    assert mission.get_status() == MissionStatus.COMPLETED


def test_mission_save_load(temp_dir):
    """Test saving and loading mission metadata."""
    mission_dir = temp_dir / "missions" / "test_mission"
    
    # Create mission
    mission1 = Mission.create(temp_dir / "missions", "test_mission")
    mission1.set_status(MissionStatus.FUSED)
    
    # Load mission
    mission2 = Mission.load(mission_dir)
    
    assert mission2.mission_id == "test_mission"
    assert mission2.get_status() == MissionStatus.FUSED


def test_mission_stats(temp_dir):
    """Test mission statistics."""
    mission = Mission.create(temp_dir / "missions", "test_mission")
    
    assert mission.num_frames == 0
    assert mission.num_chunks == 0
    assert mission.glb_path.name == "test_mission_reconstruction.glb"


def test_mission_manager(temp_dir):
    """Test mission manager."""
    manager = MissionManager(temp_dir / "missions")
    
    # Create missions
    mission1 = manager.create_mission("mission_001")
    mission2 = manager.create_mission("mission_002")
    
    # List missions
    missions = manager.list_missions()
    
    assert len(missions) == 2
    assert any(m.mission_id == "mission_001" for m in missions)
    assert any(m.mission_id == "mission_002" for m in missions)


def test_mission_duplicate_error(temp_dir):
    """Test that duplicate mission creation raises error."""
    missions_dir = temp_dir / "missions"
    
    Mission.create(missions_dir, "duplicate")
    
    with pytest.raises(FileExistsError):
        Mission.create(missions_dir, "duplicate")


def test_mission_not_found(temp_dir):
    """Test that loading non-existent mission raises error."""
    with pytest.raises(FileNotFoundError):
        Mission.load(temp_dir / "missions" / "nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
