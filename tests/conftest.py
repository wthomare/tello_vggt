"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from tello_vggt.core.config import AppConfig
from tello_vggt.core.mission import Mission, MissionManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    config = AppConfig(
        missions_dir=temp_dir / "missions",
        logs_dir=temp_dir / "logs",
        checkpoints_dir=temp_dir / "checkpoints",
    )
    config.ensure_directories()
    return config


@pytest.fixture
def test_mission(temp_dir):
    """Create a test mission."""
    mission = Mission.create(temp_dir / "missions", "test_mission")
    return mission
