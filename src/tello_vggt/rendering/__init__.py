"""Rendering module for advanced 3D reconstruction outputs."""

from tello_vggt.rendering.gaussian_splatting import (
    GaussianSplattingTrainer,
    GaussianSplattingRenderer,
    GaussianSplattingResult,
)
from tello_vggt.rendering.deep_anything_v3 import (
    DepthAnything3Estimator,
    DepthAnything3Result,
    DeepAnythingV3Segmenter,
    DeepAnythingV3Processor,
    depth_to_point_cloud,
    export_point_cloud_ply,
    gaussian_from_point_cloud,
    save_depth_pngs,
)

__all__ = [
    "GaussianSplattingTrainer",
    "GaussianSplattingRenderer",
    "GaussianSplattingResult",
    "DepthAnything3Estimator",
    "DepthAnything3Result",
    "DeepAnythingV3Segmenter",
    "DeepAnythingV3Processor",
    "depth_to_point_cloud",
    "export_point_cloud_ply",
    "gaussian_from_point_cloud",
    "save_depth_pngs",
]
