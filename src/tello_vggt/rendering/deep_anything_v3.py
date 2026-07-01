"""Depth Anything 3 integration.

The public Depth Anything 3 API is not stable across installs, so this module supports
three loading strategies:

- a Hugging Face depth-estimation pipeline via ``model_id``;
- a local Python factory via ``model_import="package.module:factory"``;
- a TorchScript or callable PyTorch checkpoint via ``checkpoint_path``.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
from PIL import Image

from tello_vggt.core.logging_config import get_logger
from tello_vggt.rendering.gaussian_splatting import GaussianSplattingResult

logger = get_logger(__name__)


@dataclass
class DepthAnything3Result:
    """Depth Anything 3 inference output."""

    depths: np.ndarray
    images: Optional[np.ndarray] = None

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, np.ndarray] = {"depths": self.depths}
        if self.images is not None:
            payload["images"] = self.images
        np.savez_compressed(path, **payload)

    @classmethod
    def load(cls, path: str | Path) -> "DepthAnything3Result":
        data = np.load(path, allow_pickle=False)
        images = data["images"] if "images" in data.files else None
        return cls(depths=data["depths"], images=images)


class DepthAnything3Estimator:
    """Load and run a Depth Anything 3 compatible depth estimator."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        checkpoint_path: Optional[str | Path] = None,
        model_import: Optional[str] = None,
        device: str = "cuda",
        input_size: Optional[int] = None,
        metric_scale: float = 1.0,
        **model_kwargs: Any,
    ) -> None:
        self.model_id = model_id
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.model_import = model_import
        self.device = self._resolve_device(device)
        self.input_size = input_size
        self.metric_scale = metric_scale
        self.model_kwargs = model_kwargs
        self.model: Any = None
        self.pipeline: Any = None

        self._load_model()

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device.startswith("cuda"):
            try:
                import torch

                if not torch.cuda.is_available():
                    logger.warning("CUDA requested but unavailable. Falling back to CPU.")
                    return "cpu"
            except ImportError:
                return "cpu"
        return device

    def _load_model(self) -> None:
        if self.model_import:
            self.model = self._load_from_import(self.model_import)
            return

        if self.checkpoint_path and self.checkpoint_path.suffix in {".pt", ".pth", ".jit"}:
            self.model = self._load_from_torch_checkpoint(self.checkpoint_path)
            return

        if self.model_id or self.checkpoint_path:
            self.pipeline = self._load_transformers_pipeline()
            return

        raise ValueError(
            "Depth Anything 3 needs one of: model_id, checkpoint_path, or model_import."
        )

    def _load_from_import(self, import_path: str) -> Any:
        if ":" not in import_path:
            raise ValueError("model_import must use the form 'module.submodule:factory'.")

        module_name, factory_name = import_path.split(":", 1)
        module = importlib.import_module(module_name)
        factory = getattr(module, factory_name)

        kwargs = dict(self.model_kwargs)
        kwargs.setdefault("checkpoint_path", self.checkpoint_path)
        kwargs.setdefault("model_id", self.model_id)
        kwargs.setdefault("device", self.device)

        try:
            model = factory(**kwargs)
        except TypeError:
            if self.checkpoint_path is not None:
                try:
                    model = factory(str(self.checkpoint_path))
                except TypeError:
                    model = factory()
            else:
                model = factory()
        if hasattr(model, "to"):
            model = model.to(self.device)
        if hasattr(model, "eval"):
            model.eval()
        return model

    def _load_from_torch_checkpoint(self, checkpoint_path: Path) -> Any:
        try:
            import torch
        except ImportError as exc:
            raise ImportError("PyTorch is required to load Depth Anything 3 checkpoints.") from exc

        try:
            model = torch.jit.load(str(checkpoint_path), map_location=self.device)
        except Exception:
            model = torch.load(str(checkpoint_path), map_location=self.device)

        if isinstance(model, dict) and "model" in model:
            model = model["model"]
        if not callable(model) and not hasattr(model, "predict"):
            raise TypeError(
                f"Checkpoint {checkpoint_path} did not contain a callable model. "
                "Use depth_anything_3.model_import to provide a local factory."
            )
        if hasattr(model, "to"):
            model = model.to(self.device)
        if hasattr(model, "eval"):
            model.eval()
        return model

    def _load_transformers_pipeline(self) -> Any:
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ImportError(
                "Install transformers or use depth_anything_3.model_import for a local model."
            ) from exc

        model_ref = str(self.checkpoint_path) if self.checkpoint_path else self.model_id
        device_index = 0 if self.device.startswith("cuda") else -1
        return pipeline("depth-estimation", model=model_ref, device=device_index)

    def predict_image(self, image: np.ndarray) -> np.ndarray:
        """Predict a single depth map from an RGB or BGR uint8 image."""
        rgb = self._ensure_rgb_uint8(image)

        if self.pipeline is not None:
            raw_depth = self._predict_with_pipeline(rgb)
        else:
            raw_depth = self._predict_with_model(rgb)

        depth = self._coerce_depth(raw_depth, rgb.shape[:2])
        return depth.astype(np.float32) * float(self.metric_scale)

    def predict_batch(self, images: Sequence[np.ndarray] | np.ndarray) -> DepthAnything3Result:
        rgb_images = [self._ensure_rgb_uint8(image) for image in images]
        depths = [self.predict_image(image) for image in rgb_images]
        return DepthAnything3Result(
            depths=np.stack(depths, axis=0),
            images=np.stack(rgb_images, axis=0),
        )

    def segment_batch(
        self,
        images: Sequence[np.ndarray] | np.ndarray,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> list[dict[str, np.ndarray]]:
        """Backward-compatible pseudo-segmentation from valid DA3 depth."""
        result = self.predict_batch(images)
        outputs: list[dict[str, np.ndarray]] = []
        for depth in result.depths:
            mask = (np.isfinite(depth) & (depth > 0)).astype(np.int32)
            outputs.append(
                {
                    "segmentation": mask,
                    "classes": np.array(["valid_depth"]),
                    "confidences": np.array([1.0], dtype=np.float32),
                    "depth": depth,
                }
            )
        return outputs

    def process_vggt_result(
        self,
        vggt_result: Any,
        images: Sequence[np.ndarray] | np.ndarray,
        segmentation_prompt: str = "valid depth",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Backward-compatible processor used by older CLI paths."""
        result = self.predict_batch(images)
        segmentations = (np.isfinite(result.depths) & (result.depths > 0)).astype(np.int32)
        points, _colors = depth_to_point_cloud(
            result.depths,
            images=result.images,
            stride=int(kwargs.get("point_stride", 4)),
            max_points=int(kwargs.get("max_points", 500_000)),
        )
        return {
            "vggt_result": vggt_result,
            "depth_anything_3": result,
            "segmentations": segmentations,
            "semantic_depth": result.depths,
            "class_point_clouds": {1: points} if len(points) else {},
            "segmentation_results": self.segment_batch(images, prompt=segmentation_prompt),
        }

    def _predict_with_pipeline(self, rgb: np.ndarray) -> Any:
        result = self.pipeline(Image.fromarray(rgb))
        if isinstance(result, dict):
            return result.get("predicted_depth", result.get("depth"))
        return result

    def _predict_with_model(self, rgb: np.ndarray) -> Any:
        for method_name in ("infer_image", "infer", "predict"):
            method = getattr(self.model, method_name, None)
            if method is not None:
                return method(rgb)

        try:
            return self.model(rgb)
        except Exception:
            return self._predict_with_tensor(rgb)

    def _predict_with_tensor(self, rgb: np.ndarray) -> Any:
        try:
            import torch
            import torch.nn.functional as functional
        except ImportError as exc:
            raise ImportError("PyTorch is required for callable Depth Anything 3 models.") from exc

        tensor = torch.from_numpy(rgb).float().permute(2, 0, 1).unsqueeze(0) / 255.0
        tensor = tensor.to(self.device)

        if self.input_size:
            tensor = functional.interpolate(
                tensor,
                size=(self.input_size, self.input_size),
                mode="bilinear",
                align_corners=False,
            )

        with torch.inference_mode():
            return self.model(tensor)

    @staticmethod
    def _ensure_rgb_uint8(image: np.ndarray) -> np.ndarray:
        arr = np.asarray(image)
        if arr.ndim != 3 or arr.shape[2] not in (3, 4):
            raise ValueError(f"Expected HxWx3/4 image, got {arr.shape}")
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        return arr

    @staticmethod
    def _coerce_depth(raw_depth: Any, target_hw: tuple[int, int]) -> np.ndarray:
        if isinstance(raw_depth, Image.Image):
            depth = np.asarray(raw_depth)
        else:
            try:
                import torch

                if torch.is_tensor(raw_depth):
                    depth = raw_depth.detach().float().cpu().numpy()
                else:
                    depth = raw_depth
            except ImportError:
                depth = raw_depth

            if isinstance(depth, dict):
                for key in ("depth", "predicted_depth", "metric_depth", "disp"):
                    if key in depth:
                        depth = depth[key]
                        break

            if isinstance(depth, (list, tuple)):
                depth = depth[0]

            depth = np.asarray(depth)

        depth = np.squeeze(depth).astype(np.float32)
        if depth.ndim != 2:
            raise ValueError(f"Depth Anything 3 output must be 2D after squeeze, got {depth.shape}")

        if depth.shape != target_hw:
            import cv2

            depth = cv2.resize(depth, (target_hw[1], target_hw[0]), interpolation=cv2.INTER_CUBIC)
        return depth


def save_depth_pngs(depths: np.ndarray, output_dir: str | Path) -> list[Path]:
    """Save depth maps as 16-bit normalized PNG images."""
    import cv2

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for index, depth in enumerate(depths):
        valid = np.isfinite(depth)
        if valid.any():
            d_min = float(depth[valid].min())
            d_max = float(depth[valid].max())
            norm = (depth - d_min) / max(d_max - d_min, 1e-8)
        else:
            norm = np.zeros_like(depth, dtype=np.float32)

        path = output_dir / f"depth_{index:06d}.png"
        cv2.imwrite(str(path), np.clip(norm * 65535.0, 0, 65535).astype(np.uint16))
        paths.append(path)

    return paths


def depth_to_point_cloud(
    depths: np.ndarray,
    images: Optional[np.ndarray] = None,
    stride: int = 4,
    max_points: int = 500_000,
    focal_length_px: Optional[float] = None,
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Back-project depth maps with a simple centered pinhole camera model."""
    if depths.ndim != 3:
        raise ValueError(f"Expected depths with shape (N,H,W), got {depths.shape}")

    all_points: list[np.ndarray] = []
    all_colors: list[np.ndarray] = []

    for frame_index, depth in enumerate(depths):
        h, w = depth.shape
        fx = fy = float(focal_length_px or max(h, w))
        cx = (w - 1) / 2.0
        cy = (h - 1) / 2.0

        y, x = np.mgrid[0:h:stride, 0:w:stride]
        z = depth[0:h:stride, 0:w:stride]
        valid = np.isfinite(z) & (z > 0)
        if not valid.any():
            continue

        x3 = (x[valid].astype(np.float32) - cx) * z[valid] / fx
        y3 = (y[valid].astype(np.float32) - cy) * z[valid] / fy
        z3 = z[valid].astype(np.float32)
        points = np.column_stack([x3, y3, z3])
        all_points.append(points)

        if images is not None:
            colors = images[frame_index, 0:h:stride, 0:w:stride][valid]
            all_colors.append(colors.astype(np.uint8))

    if not all_points:
        return np.empty((0, 3), dtype=np.float32), None

    points_out = np.vstack(all_points).astype(np.float32)
    colors_out = np.vstack(all_colors).astype(np.uint8) if all_colors else None

    if len(points_out) > max_points:
        indices = np.linspace(0, len(points_out) - 1, max_points).astype(np.int64)
        points_out = points_out[indices]
        if colors_out is not None:
            colors_out = colors_out[indices]

    return points_out, colors_out


def export_point_cloud_ply(
    points: np.ndarray,
    output_path: str | Path,
    colors: Optional[np.ndarray] = None,
) -> Path:
    """Export a colored or uncolored point cloud as PLY."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from plyfile import PlyData, PlyElement
    except ImportError:
        _export_ascii_ply(points, output_path, colors=colors)
        return output_path

    if colors is not None:
        vertex = np.zeros(
            len(points),
            dtype=[
                ("x", "f4"),
                ("y", "f4"),
                ("z", "f4"),
                ("red", "u1"),
                ("green", "u1"),
                ("blue", "u1"),
            ],
        )
        vertex["red"] = colors[:, 0]
        vertex["green"] = colors[:, 1]
        vertex["blue"] = colors[:, 2]
    else:
        vertex = np.zeros(len(points), dtype=[("x", "f4"), ("y", "f4"), ("z", "f4")])

    vertex["x"] = points[:, 0]
    vertex["y"] = points[:, 1]
    vertex["z"] = points[:, 2]

    PlyData([PlyElement.describe(vertex, "vertex")]).write(output_path)
    return output_path


def _export_ascii_ply(
    points: np.ndarray,
    output_path: Path,
    colors: Optional[np.ndarray] = None,
) -> None:
    has_colors = colors is not None
    with open(output_path, "w") as handle:
        handle.write("ply\n")
        handle.write("format ascii 1.0\n")
        handle.write(f"element vertex {len(points)}\n")
        handle.write("property float x\n")
        handle.write("property float y\n")
        handle.write("property float z\n")
        if has_colors:
            handle.write("property uchar red\n")
            handle.write("property uchar green\n")
            handle.write("property uchar blue\n")
        handle.write("end_header\n")

        for index, point in enumerate(points):
            if has_colors:
                color = colors[index]
                handle.write(
                    f"{point[0]} {point[1]} {point[2]} "
                    f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
                )
            else:
                handle.write(f"{point[0]} {point[1]} {point[2]}\n")


def gaussian_from_point_cloud(points: np.ndarray, sh_degree: int = 3) -> GaussianSplattingResult:
    """Create a simple Gaussian initialization from a point cloud."""
    num_points = len(points)
    num_sh_components = (sh_degree + 1) ** 2
    return GaussianSplattingResult(
        means=points.astype(np.float32),
        scales=np.full((num_points, 3), 0.01, dtype=np.float32),
        rotations=np.tile(
            np.array([[0.0, 0.0, 0.0, 1.0]], dtype=np.float32),
            (num_points, 1),
        ),
        sh_coefficients=np.zeros((num_points, num_sh_components, 3), dtype=np.float32),
        opacity=np.ones(num_points, dtype=np.float32),
        point_cloud=points.astype(np.float32),
    )


DeepAnythingV3Processor = DepthAnything3Estimator
DeepAnythingV3Segmenter = DepthAnything3Estimator
