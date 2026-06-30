"""Gaussian Splatting rendering support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

import numpy as np

from tello_vggt.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class GaussianSplattingResult:
    """Result of Gaussian Splatting training."""
    
    means: np.ndarray          # (N, 3) - Gaussian centers
    scales: np.ndarray         # (N, 3) - Gaussian scales
    rotations: np.ndarray      # (N, 4) - Gaussian rotations (quaternions)
    sh_coefficients: np.ndarray  # (N, num_components, 3) - SH coefficients
    opacity: np.ndarray        # (N,) - Opacity values
    point_cloud: Optional[np.ndarray] = None  # (N, 3) - Optional point cloud
    
    def save(self, path: str | Path) -> None:
        """Save to NPZ file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        np.savez_compressed(
            path,
            means=self.means,
            scales=self.scales,
            rotations=self.rotations,
            sh_coefficients=self.sh_coefficients,
            opacity=self.opacity,
            point_cloud=self.point_cloud if self.point_cloud is not None else np.array([]),
        )
        logger.info(f"Saved Gaussian Splatting result to {path}")
    
    @classmethod
    def load(cls, path: str | Path) -> GaussianSplattingResult:
        """Load from NPZ file."""
        path = Path(path)
        data = np.load(path, allow_pickle=False)
        
        return cls(
            means=data["means"],
            scales=data["scales"],
            rotations=data["rotations"],
            sh_coefficients=data["sh_coefficients"],
            opacity=data["opacity"],
            point_cloud=data["point_cloud"] if data["point_cloud"].size > 0 else None,
        )


class GaussianSplattingTrainer:
    """Train Gaussian Splatting from VGGT-Omega results."""
    
    def __init__(
        self,
        sh_degree: int = 3,
        densification_interval: int = 100,
        iterations: int = 7000,
        device: str = "cuda",
    ):
        """Initialize trainer.
        
        Args:
            sh_degree: Spherical Harmonics degree (0-4)
            densification_interval: Interval for densification
            iterations: Training iterations
            device: Compute device
        """
        self.sh_degree = sh_degree
        self.densification_interval = densification_interval
        self.iterations = iterations
        self.device = device
        
        logger.info(
            f"Initialized Gaussian Splatting Trainer "
            f"(SH degree: {sh_degree}, iterations: {iterations})"
        )
    
    def train_from_vggt(
        self,
        vggt_result,  # VGGTChunkResult
        camera_poses: np.ndarray,
        camera_intrinsics: np.ndarray,
        images: np.ndarray,
        **kwargs: Any,
    ) -> GaussianSplattingResult:
        """Train Gaussian Splatting from VGGT-Omega result.
        
        Args:
            vggt_result: VGGTChunkResult from inference
            camera_poses: Camera extrinsics (N, 4, 4)
            camera_intrinsics: Camera intrinsics (N, 3, 3)
            images: Input images (N, H, W, 3)
            **kwargs: Additional training parameters
        
        Returns:
            GaussianSplattingResult
        
        Note:
            This is a placeholder for the actual Gaussian Splatting training.
            Full implementation requires:
            - diff-gaussian-rasterization
            - simple-knn
            - Optimization loop
        """
        try:
            import torch
        except ImportError:
            raise ImportError("PyTorch is required for Gaussian Splatting")
        
        logger.info("Starting Gaussian Splatting training...")
        logger.warning(
            "Full Gaussian Splatting implementation requires additional setup. "
            "Using simplified initialization from point cloud."
        )
        
        # Extract point cloud from depth maps
        point_cloud = self._extract_point_cloud_from_depth(vggt_result)
        
        # Initialize Gaussians from point cloud
        num_points = point_cloud.shape[0]
        
        # Simple initialization
        means = torch.from_numpy(point_cloud).float().to(self.device)
        scales = torch.ones((num_points, 3), device=self.device) * 0.01
        rotations = torch.tensor(
            [[0, 0, 0, 1]] * num_points,  # Identity quaternions
            dtype=torch.float32,
            device=self.device,
        )
        opacity = torch.ones((num_points, 1), device=self.device)
        
        # SH coefficients initialization
        num_sh_components = (self.sh_degree + 1) ** 2
        sh_coefficients = torch.randn(
            (num_points, num_sh_components, 3),
            device=self.device,
        ) * 0.1
        
        logger.info(f"Initialized {num_points} Gaussians")
        logger.info(
            "Note: Full training loop not implemented. "
            "Use third-party GS implementation for complete training."
        )
        
        # Convert back to numpy for storage
        result = GaussianSplattingResult(
            means=means.cpu().numpy(),
            scales=scales.cpu().numpy(),
            rotations=rotations.cpu().numpy(),
            sh_coefficients=sh_coefficients.cpu().numpy(),
            opacity=opacity.squeeze(-1).cpu().numpy(),
            point_cloud=point_cloud,
        )
        
        logger.info("✅ Gaussian Splatting result ready for rendering")
        
        return result
    
    @staticmethod
    def _extract_point_cloud_from_depth(vggt_result) -> np.ndarray:
        """Extract point cloud from VGGT depth maps.
        
        Args:
            vggt_result: VGGTChunkResult with depth maps
        
        Returns:
            Point cloud (N, 3)
        """
        try:
            from vggt.utils.geometry import unproject_depth_map_to_point_map
        except ImportError:
            logger.warning(
                "vggt.utils.geometry not available. "
                "Using simplified point cloud extraction."
            )
            # Fallback: simple extraction
            depth = vggt_result.depth.squeeze(-1)  # (S, H, W)
            h, w = depth.shape[-2:]
            
            points = []
            for d in depth:
                y, x = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
                valid = d > 0
                points_img = np.column_stack([
                    x[valid],
                    y[valid],
                    d[valid]
                ])
                points.append(points_img)
            
            return np.vstack(points) if points else np.array([])
        
        # Use VGGT's unproject function
        point_cloud = unproject_depth_map_to_point_map(
            vggt_result.depth,
            vggt_result.extrinsics,
            vggt_result.intrinsics,
        )
        
        return point_cloud.reshape(-1, 3)


class GaussianSplattingRenderer:
    """Render Gaussian Splatting results."""
    
    def __init__(self, device: str = "cuda"):
        """Initialize renderer.
        
        Args:
            device: Compute device
        """
        self.device = device
        logger.info(f"Initialized Gaussian Splatting Renderer on {device}")
    
    def render(
        self,
        gs_result: GaussianSplattingResult,
        height: int,
        width: int,
        camera_pose: Optional[np.ndarray] = None,
        camera_intrinsics: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Render Gaussian Splatting result.
        
        Args:
            gs_result: Gaussian Splatting result
            height: Output height
            width: Output width
            camera_pose: Camera extrinsic (4, 4)
            camera_intrinsics: Camera intrinsic (3, 3)
        
        Returns:
            Rendered image (height, width, 3)
        
        Note:
            This is a placeholder. Full rendering requires:
            - diff-gaussian-rasterization CUDA kernels
            - Proper camera parameter setup
        """
        logger.warning(
            "Full Gaussian Splatting rendering requires diff-gaussian-rasterization. "
            "Returning placeholder image."
        )
        
        # Placeholder: return random image
        image = np.random.rand(height, width, 3) * 255
        return image.astype(np.uint8)
    
    def export_ply(self, gs_result: GaussianSplattingResult, output_path: str | Path) -> None:
        """Export Gaussian Splatting as PLY point cloud.
        
        Args:
            gs_result: Gaussian Splatting result
            output_path: Output PLY file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            from plyfile import PlyData, PlyElement
        except ImportError:
            logger.error("plyfile not installed. Cannot export PLY.")
            return
        
        # Create vertex array
        vertex = np.zeros(
            len(gs_result.means),
            dtype=[
                ("x", "f4"),
                ("y", "f4"),
                ("z", "f4"),
                ("opacity", "f4"),
            ],
        )
        
        vertex["x"] = gs_result.means[:, 0]
        vertex["y"] = gs_result.means[:, 1]
        vertex["z"] = gs_result.means[:, 2]
        vertex["opacity"] = gs_result.opacity
        
        # Create PLY
        ply_element = PlyElement.describe(vertex, "vertex")
        ply_data = PlyData([ply_element])
        
        ply_data.write(output_path)
        logger.info(f"Exported Gaussian Splatting to PLY: {output_path}")
