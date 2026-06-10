from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

import numpy as np
import torch
from PIL import Image

from vggt_omega.models import VGGTOmega
from vggt_omega.utils.load_fn import load_and_preprocess_images
from vggt_omega.utils.pose_enc import encoding_to_camera


@dataclass
class VGGTChunkResult:
    """
    Résultat d'inférence pour un batch de frames.
    Les tenseurs sont convertis en numpy pour être plus simples à manipuler.
    """
    extrinsics: np.ndarray
    intrinsics: np.ndarray
    depth: np.ndarray
    depth_conf: np.ndarray
    raw: Dict[str, Any]


class VGGTOmegaTelloInferencer:
    """
    Charge VGGT-Omega et infère sur des batches de frames provenant d'un flux vidéo
    (par exemple un drone Tello).

    Hypothèses:
    - les frames d'entrée sont des tableaux numpy HxWx3
    - format OpenCV par défaut : BGR
    - on écrit temporairement les frames sur disque pour réutiliser
      le loader officiel de VGGT-Omega
    """

    def __init__(
        self,
        checkpoint_path: str,
        device: str = "cuda",
        image_resolution: int = 512,
        mode: str = "balanced",   # "balanced" ou "max_size"
        enable_alignment: bool = False,
        input_is_bgr: bool = True,
    ) -> None:
        if device.startswith("cuda") and not torch.cuda.is_available():
            device = "cpu"

        self.device = torch.device(device)
        self.image_resolution = image_resolution
        self.mode = mode
        self.input_is_bgr = input_is_bgr

        self.model = VGGTOmega(enable_alignment=enable_alignment).to(self.device).eval()

        state = torch.load(checkpoint_path, map_location="cpu")
        self.model.load_state_dict(state)

    @staticmethod
    def _ensure_uint8_rgb(frame: np.ndarray, input_is_bgr: bool = True) -> np.ndarray:
        arr = np.asarray(frame)

        if arr.ndim != 3 or arr.shape[2] not in (3, 4):
            raise ValueError(f"Frame invalide, shape attendue HxWx3/4, reçu {arr.shape}")

        if arr.shape[2] == 4:
            arr = arr[:, :, :3]

        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)

        # OpenCV / Tello donnent souvent du BGR
        if input_is_bgr:
            arr = arr[:, :, ::-1].copy()

        return arr

    def _save_frames_to_tempdir(self, frames: Sequence[np.ndarray], temp_dir: Path) -> List[str]:
        temp_dir.mkdir(parents=True, exist_ok=True)

        image_paths: List[str] = []
        for i, frame in enumerate(frames):
            rgb = self._ensure_uint8_rgb(frame, input_is_bgr=self.input_is_bgr)
            image = Image.fromarray(rgb)

            path = temp_dir / f"{i:06d}.png"
            image.save(path)
            image_paths.append(str(path))

        return image_paths

    def infer_frames(self, frames: Sequence[np.ndarray]) -> VGGTChunkResult:
        """
        Lance VGGT-Omega sur une séquence de frames déjà collectées.
        """
        if len(frames) == 0:
            raise ValueError("Aucune frame fournie.")

        with tempfile.TemporaryDirectory(prefix="vggt_omega_") as tmp:
            tmp_dir = Path(tmp)
            image_paths = self._save_frames_to_tempdir(frames, tmp_dir)

            images = load_and_preprocess_images(
                image_paths,
                mode=self.mode,
                image_resolution=self.image_resolution,
            ).to(self.device)

            with torch.inference_mode():
                predictions = self.model(images)

            extrinsics, intrinsics = encoding_to_camera(
                predictions["pose_enc"],
                predictions["images"].shape[-2:],
            )

            def to_numpy(x: Any) -> Any:
                if torch.is_tensor(x):
                    return x.detach().float().cpu().numpy()
                return x

            raw_np: Dict[str, Any] = {k: to_numpy(v) for k, v in predictions.items()}
            extrinsics_np = to_numpy(extrinsics)
            intrinsics_np = to_numpy(intrinsics)

            depth = raw_np.get("depth")
            depth_conf = raw_np.get("depth_conf")

            if depth is None:
                raise KeyError("La sortie du modèle ne contient pas 'depth'.")
            if depth_conf is None:
                raise KeyError("La sortie du modèle ne contient pas 'depth_conf'.")

            return VGGTChunkResult(
                extrinsics=extrinsics_np,
                intrinsics=intrinsics_np,
                depth=depth,
                depth_conf=depth_conf,
                raw=raw_np,
            )

    def infer_stream(
        self,
        frame_iter: Iterable[np.ndarray],
        chunk_size: int = 100,
        overlap: int = 5,
    ) -> Iterator[VGGTChunkResult]:
        """
        Infère sur un flux potentiellement long.

        Exemple:
            inferencer.infer_stream(tello_frames(), chunk_size=100, overlap=5)
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size doit être > 0")
        if overlap < 0:
            raise ValueError("overlap doit être >= 0")
        if overlap >= chunk_size:
            raise ValueError("overlap doit être strictement inférieur à chunk_size")

        buffer: List[np.ndarray] = []

        for frame in frame_iter:
            buffer.append(frame)

            if len(buffer) >= chunk_size:
                yield self.infer_frames(buffer[:chunk_size])
                buffer = buffer[chunk_size - overlap :]

        if buffer:
            yield self.infer_frames(buffer)


def tello_frame_generator(tello_capture) -> Iterator[np.ndarray]:
    """
    Adaptateur minimal pour un objet Tello qui expose une méthode `read()` style OpenCV.
    On suppose que read() renvoie (ok, frame).
    """
    while True:
        ok, frame = tello_capture.read()
        if not ok:
            break
        yield frame

"""
inferencer = VGGTOmegaTelloInferencer(
    checkpoint_path="checkpoints/VGGT-Omega-1B-512/model.pt",
    device="cuda",
    image_resolution=512,
    mode="balanced",
    input_is_bgr=True,
)

for result in inferencer.infer_stream(
    tello_frame_generator(tello_capture),
    chunk_size=100,
    overlap=5,
):
    print("depth:", result.depth.shape)
    print("extrinsics:", result.extrinsics.shape)
    print("intrinsics:", result.intrinsics.shape)
"""