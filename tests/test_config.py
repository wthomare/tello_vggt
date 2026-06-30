"""Tests for configuration management."""

import pytest
import tempfile
from pathlib import Path

from tello_vggt.core.config import AppConfig, load_config, DeviceType, InferenceMode


def test_default_config():
    """Test default configuration creation."""
    config = AppConfig()
    
    assert config.vggt.image_resolution == 512
    assert config.inference.chunk_size == 100
    assert config.acquisition.fps == 30
    assert config.log_level == "INFO"


def test_config_to_yaml():
    """Test configuration to YAML conversion."""
    config = AppConfig()
    yaml_str = config.to_yaml()
    
    assert "vggt:" in yaml_str
    assert "inference:" in yaml_str
    assert "gaussian_splatting:" in yaml_str


def test_config_save_and_load(temp_dir):
    """Test saving and loading configuration."""
    config_file = temp_dir / "config.yaml"
    
    # Create and save config
    config1 = AppConfig(log_level="DEBUG")
    config1.save_yaml(config_file)
    
    # Load config
    config2 = AppConfig.from_yaml(config_file)
    
    assert config2.log_level == "DEBUG"
    assert config2.vggt.image_resolution == 512


def test_config_from_dict():
    """Test creating configuration from dictionary."""
    data = {
        "vggt": {"image_resolution": 768},
        "inference": {"chunk_size": 50},
    }
    
    config = AppConfig.from_dict(data)
    
    assert config.vggt.image_resolution == 768
    assert config.inference.chunk_size == 50


def test_config_paths_created(temp_dir):
    """Test that required directories are created."""
    config = AppConfig(
        missions_dir=temp_dir / "missions",
        logs_dir=temp_dir / "logs",
    )
    config.ensure_directories()
    
    assert config.missions_dir.exists()
    assert config.logs_dir.exists()


def test_device_type_enum():
    """Test device type enum."""
    config = AppConfig()
    config.vggt.device = DeviceType.CUDA
    
    assert config.vggt.device == DeviceType.CUDA


def test_inference_mode_enum():
    """Test inference mode enum."""
    config = AppConfig()
    config.vggt.mode = InferenceMode.BALANCED
    
    assert config.vggt.mode == InferenceMode.BALANCED


def test_load_config_global():
    """Test global configuration loading."""
    from tello_vggt.core.config import get_config
    
    config = load_config()
    assert get_config() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
