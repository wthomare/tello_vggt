"""Configuration management for tello_vggt using Pydantic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class DeviceType(str, Enum):
    """Supported compute devices."""
    CUDA = "cuda"
    CPU = "cpu"
    MPS = "mps"  # Metal Performance Shaders for Apple


class InferenceMode(str, Enum):
    """VGGT-Omega inference modes."""
    BALANCED = "balanced"
    MAX_SIZE = "max_size"


class GaussianSplattingBackend(str, Enum):
    """Gaussian Splatting rendering backends."""
    GAUSSIAN_SPLATTING = "gaussian_splatting"  # 3D Gaussian Splatting
    DEEP_ANYTHING_V3 = "deep_anything_v3"      # Deep Anything V3


# ============================================================================
# Configuration Models
# ============================================================================


class VGGTConfig(BaseModel):
    """VGGT-Omega model configuration."""
    
    checkpoint_path: Path = Field(
        default=Path("checkpoints/VGGT-Omega.pt"),
        description="Path to VGGT-Omega checkpoint"
    )
    image_resolution: int = Field(
        default=512,
        ge=256,
        le=2048,
        description="Input image resolution (width)"
    )
    mode: InferenceMode = Field(
        default=InferenceMode.BALANCED,
        description="Inference mode (balanced or max_size)"
    )
    enable_alignment: bool = Field(
        default=False,
        description="Enable camera alignment"
    )
    device: DeviceType = Field(
        default=DeviceType.CUDA,
        description="Compute device (cuda, cpu, mps)"
    )
    half_precision: bool = Field(
        default=False,
        description="Use FP16 precision for faster inference"
    )

    @field_validator("checkpoint_path", mode="before")
    @classmethod
    def convert_path(cls, v: Any) -> Path:
        return Path(v) if v is not None else Path("checkpoints/VGGT-Omega.pt")

    model_config = {"use_enum_values": True}


class InferenceConfig(BaseModel):
    """Inference processing configuration."""
    
    chunk_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of frames per chunk"
    )
    overlap: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Overlap between chunks for seamless fusion"
    )
    batch_size: int = Field(
        default=16,
        ge=1,
        le=128,
        description="Batch size for inference"
    )
    min_overlap_fusion: int = Field(
        default=1,
        description="Minimum overlap frames to detect for fusion"
    )
    max_overlap_fusion: int = Field(
        default=20,
        description="Maximum overlap frames to search for fusion"
    )
    use_allclose_fusion: bool = Field(
        default=False,
        description="Use allclose() for fuzzy overlap detection"
    )

    @field_validator("overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        if "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("overlap must be < chunk_size")
        return v


class AcquisitionConfig(BaseModel):
    """Video acquisition configuration."""
    
    fps: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Target frames per second"
    )
    frame_size: Optional[tuple[int, int]] = Field(
        default=None,
        description="Output frame size (width, height). None = auto-detect"
    )
    fourcc: str = Field(
        default="mp4v",
        description="Video codec (mp4v, MJPG, etc.)"
    )
    tello_battery_warning: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Battery percentage to warn user"
    )


class ExportConfig(BaseModel):
    """Export configuration for GLB and other formats."""
    
    confidence_threshold: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Confidence threshold for point cloud filtering"
    )
    show_cameras: bool = Field(
        default=True,
        description="Include camera frustums in output"
    )
    mask_black_background: bool = Field(
        default=False,
        description="Mask black background pixels"
    )
    mask_white_background: bool = Field(
        default=False,
        description="Mask white background pixels"
    )
    mask_sky: bool = Field(
        default=False,
        description="Attempt to mask sky regions"
    )


class GaussianSplattingConfig(BaseModel):
    """Gaussian Splatting configuration."""
    
    enabled: bool = Field(
        default=False,
        description="Enable Gaussian Splatting rendering"
    )
    backend: GaussianSplattingBackend = Field(
        default=GaussianSplattingBackend.GAUSSIAN_SPLATTING,
        description="Gaussian Splatting backend to use"
    )
    sh_degree: int = Field(
        default=3,
        ge=0,
        le=4,
        description="Spherical harmonics degree for color"
    )
    densification_interval: int = Field(
        default=100,
        description="Densification interval for training"
    )
    iterations: int = Field(
        default=7000,
        description="Training iterations for Gaussian Splatting"
    )
    deep_anything_v3_checkpoint: Optional[Path] = Field(
        default=None,
        description="Path to Deep Anything V3 checkpoint for segmentation"
    )

    model_config = {"use_enum_values": True}


class AppConfig(BaseModel):
    """Main application configuration."""
    
    # Core configurations
    vggt: VGGTConfig = Field(default_factory=VGGTConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    acquisition: AcquisitionConfig = Field(default_factory=AcquisitionConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    gaussian_splatting: GaussianSplattingConfig = Field(default_factory=GaussianSplattingConfig)
    
    # Paths
    missions_dir: Path = Field(
        default=Path("missions"),
        description="Directory to store missions"
    )
    checkpoints_dir: Path = Field(
        default=Path("checkpoints"),
        description="Directory containing model checkpoints"
    )
    logs_dir: Path = Field(
        default=Path("logs"),
        description="Directory for application logs"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_to_file: bool = Field(
        default=True,
        description="Log to file in addition to console"
    )
    
    # Performance
    gpu_memory_fraction: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="GPU memory fraction to allocate (None = auto)"
    )
    num_workers: int = Field(
        default=4,
        ge=0,
        le=16,
        description="Number of data loading workers"
    )

    @field_validator("missions_dir", "checkpoints_dir", "logs_dir", mode="before")
    @classmethod
    def convert_paths(cls, v: Any) -> Path:
        return Path(v) if v is not None else Path(".")

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [self.missions_dir, self.checkpoints_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump()

    def to_yaml(self) -> str:
        """Convert config to YAML string."""
        return yaml.dump(self.model_dump(), default_flow_style=False, sort_keys=False)

    def save_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_yaml())

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppConfig:
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        return cls(**data or {})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        """Load configuration from dictionary."""
        return cls(**data)


# ============================================================================
# Global Configuration Instance
# ============================================================================

_global_config: Optional[AppConfig] = None


def load_config(config_path: Optional[str | Path] = None) -> AppConfig:
    """
    Load configuration from file or create default.
    
    Args:
        config_path: Path to YAML config file. If None, uses defaults.
    
    Returns:
        AppConfig instance
    """
    global _global_config
    
    if config_path:
        _global_config = AppConfig.from_yaml(config_path)
    else:
        _global_config = AppConfig()
    
    _global_config.ensure_directories()
    return _global_config


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = AppConfig()
        _global_config.ensure_directories()
    return _global_config


def set_config(config: AppConfig) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config
