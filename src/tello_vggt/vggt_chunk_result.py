from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence, TYPE_CHECKING

import numpy as np
import pickle

if TYPE_CHECKING:
    import trimesh

try:
    from visual_util import predictions_to_glb
except ImportError:
    predictions_to_glb = None

try:
    from vggt.utils.geometry import unproject_depth_map_to_point_map
except ImportError:
    unproject_depth_map_to_point_map = None


@dataclass
class VGGTChunkResult:
    extrinsics: np.ndarray   # (S, 3, 4) ou (S, 4, 4)
    intrinsics: np.ndarray   # (S, 3, 3) ou compatible avec unproject_depth_map_to_point_map
    depth: np.ndarray        # (S, H, W, 1) idéalement
    depth_conf: np.ndarray   # (S, H, W) ou (S, H, W, 1)
    raw: dict[str, Any]

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        np.savez_compressed(
            path,
            extrinsics=self.extrinsics,
            intrinsics=self.intrinsics,
            depth=self.depth,
            depth_conf=self.depth_conf,
            raw=np.frombuffer(
                pickle.dumps(self.raw),
                dtype=np.uint8
            ),
        )

    @classmethod
    def load(cls, path: str | Path) -> "VGGTChunkResult":

        data = np.load(path, allow_pickle=False)

        raw = pickle.loads(
            data["raw"].tobytes()
        )

        return cls(
            extrinsics=data["extrinsics"],
            intrinsics=data["intrinsics"],
            depth=data["depth"],
            depth_conf=data["depth_conf"],
            raw=raw,
        )


class VGGTGlbExporter:
    def __init__(self, input_is_bgr: bool = True) -> None:
        self.input_is_bgr = input_is_bgr

    @staticmethod
    def _to_float_rgb(frames: Sequence[np.ndarray], input_is_bgr: bool = True) -> np.ndarray:
        rgb_frames = []
        for frame in frames:
            arr = np.asarray(frame)

            if arr.ndim != 3 or arr.shape[2] not in (3, 4):
                raise ValueError(f"Frame invalide: shape={arr.shape}")

            if arr.shape[2] == 4:
                arr = arr[:, :, :3]

            if arr.dtype != np.uint8:
                arr = np.clip(arr, 0, 255).astype(np.uint8)

            if input_is_bgr:
                arr = arr[:, :, ::-1]  # BGR -> RGB

            rgb_frames.append(arr.astype(np.float32) / 255.0)

        return np.stack(rgb_frames, axis=0)

    @staticmethod
    def _ensure_extrinsic_3x4(extrinsics: np.ndarray) -> np.ndarray:
        extrinsics = np.asarray(extrinsics)

        if extrinsics.ndim == 2 and extrinsics.shape == (4, 4):
            extrinsics = extrinsics[None, ...]
        elif extrinsics.ndim == 2 and extrinsics.shape == (3, 4):
            extrinsics = extrinsics[None, ...]

        if extrinsics.ndim != 3:
            raise ValueError(f"Extrinsics invalides: shape={extrinsics.shape}")

        if extrinsics.shape[-2:] == (4, 4):
            extrinsics = extrinsics[:, :3, :4]
        elif extrinsics.shape[-2:] != (3, 4):
            raise ValueError(f"Extrinsics invalides: shape={extrinsics.shape}")

        return extrinsics

    @staticmethod
    def _ensure_depth_4d(depth: np.ndarray) -> np.ndarray:
        depth = np.asarray(depth)
        if depth.ndim == 3:
            depth = depth[..., None]
        if depth.ndim != 4 or depth.shape[-1] != 1:
            raise ValueError(f"Depth invalide: shape={depth.shape}, attendu (S,H,W,1)")
        return depth

    @staticmethod
    def _ensure_conf_3d(conf: np.ndarray) -> np.ndarray:
        conf = np.asarray(conf)
        if conf.ndim == 4 and conf.shape[-1] == 1:
            conf = conf[..., 0]
        if conf.ndim != 3:
            raise ValueError(f"Confidence invalide: shape={conf.shape}, attendu (S,H,W)")
        return conf

    def build_predictions(
        self,
        result: VGGTChunkResult,
        frames: Optional[Sequence[np.ndarray]] = None,
    ) -> dict[str, Any]:
        if unproject_depth_map_to_point_map is None:
            raise ImportError(
                "La dépendance 'vggt.utils.geometry' n'est pas disponible. "
                "Installez vggt_omega avec: pip install vggt_omega"
            )
        
        extrinsic = self._ensure_extrinsic_3x4(result.extrinsics)
        depth = self._ensure_depth_4d(result.depth)
        depth_conf = self._ensure_conf_3d(result.depth_conf)

        if frames is not None:
            images = self._to_float_rgb(frames, input_is_bgr=self.input_is_bgr)
        elif "images" in result.raw:
            images = np.asarray(result.raw["images"])
            if images.dtype != np.float32 and images.dtype != np.float64:
                images = images.astype(np.float32)
            if images.max() > 1.5:
                images = images / 255.0
        else:
            raise ValueError("Il faut fournir `frames` ou avoir `raw['images']` dans le résultat.")

        # Le demo officiel reconstruit les points monde depuis la depth map avec ces matrices.
        world_points = unproject_depth_map_to_point_map(depth, extrinsic, result.intrinsics)

        predictions = {
            "images": images,
            "extrinsic": extrinsic,
            "intrinsic": result.intrinsics,
            "depth": depth,
            "depth_conf": depth_conf,
            "world_points": world_points,
            "world_points_conf": depth_conf,
            "world_points_from_depth": world_points,
        }

        return predictions

    def export_glb(
        self,
        result: VGGTChunkResult,
        out_path: str | Path,
        frames: Optional[Sequence[np.ndarray]] = None,
        conf_thres: float = 50.0,
        show_cam: bool = True,
        mask_black_bg: bool = False,
        mask_white_bg: bool = False,
    ) -> Path:
        """
        Exporte un GLB à partir d'un VGGTChunkResult.
        """
        if predictions_to_glb is None:
            raise ImportError(
                "La dépendance 'visual_util' n'est pas disponible. "
                "Vérifiez que le module est installé et accessible."
            )
        
        predictions = self.build_predictions(result, frames=frames)

        scene = predictions_to_glb(
            predictions,
            conf_thres=conf_thres,
            filter_by_frames="all",
            mask_black_bg=mask_black_bg,
            mask_white_bg=mask_white_bg,
            show_cam=show_cam,
            mask_sky=False,
            target_dir=None,
            prediction_mode="Predicted Pointmap",
        )

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        scene.export(file_obj=str(out_path))
        return out_path
    
"""
exporter = VGGTGlbExporter(input_is_bgr=True)

glb_path = exporter.export_glb(
    result=chunk_result,
    out_path="outputs/reconstruction.glb",
    frames=tello_frames,   # liste de frames BGR OpenCV
    conf_thres=50.0,
    show_cam=True,
)

print("GLB écrit ici :", glb_path)
"""
