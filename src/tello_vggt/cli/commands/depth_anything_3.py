"""Depth Anything 3 command."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from tqdm import tqdm

from tello_vggt.core.config import AppConfig
from tello_vggt.core.logging_config import get_logger, log_section
from tello_vggt.core.mission import Mission
from tello_vggt.mission_loader import load_frames
from tello_vggt.rendering.deep_anything_v3 import (
    DepthAnything3Estimator,
    depth_to_point_cloud,
    export_point_cloud_ply,
    gaussian_from_point_cloud,
    save_depth_pngs,
)

logger = get_logger(__name__)


def _resolve_input_path(config: AppConfig, input_path: Path) -> Path:
    input_path = Path(input_path).expanduser()
    if input_path.exists():
        return input_path

    mission_path = config.missions_dir / input_path
    if mission_path.exists():
        return mission_path

    raise FileNotFoundError(f"Input video or mission not found: {input_path}")


def _load_video_frames(video_path: Path, frame_stride: int, max_frames: Optional[int]) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frames: list[np.ndarray] = []
    frame_index = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    pbar = tqdm(total=total_frames or None, desc="Loading video frames")

    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break

            if frame_index % frame_stride == 0:
                frames.append(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                if max_frames is not None and len(frames) >= max_frames:
                    break

            frame_index += 1
            pbar.update(1)
    finally:
        pbar.close()
        cap.release()

    return frames


def _load_input_frames(
    config: AppConfig,
    input_path: Path,
    frame_stride: int,
    max_frames: Optional[int],
) -> tuple[str, list[np.ndarray], Path]:
    resolved = _resolve_input_path(config, input_path)

    if resolved.is_dir():
        mission = Mission.load(resolved)
        frames_bgr = load_frames(mission.frames_dir)
        frames_rgb = [
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            for index, frame in enumerate(frames_bgr)
            if index % frame_stride == 0
        ]
        if max_frames is not None:
            frames_rgb = frames_rgb[:max_frames]
        return mission.mission_id, frames_rgb, mission.output_dir / "depth_anything_3"

    mission_id = resolved.stem
    frames_rgb = _load_video_frames(resolved, frame_stride=frame_stride, max_frames=max_frames)
    return mission_id, frames_rgb, config.missions_dir / mission_id / "depth_anything_3"


def cmd_depth_anything_3(
    config: AppConfig,
    input_path: Path,
    output: Optional[Path] = None,
    model_id: Optional[str] = None,
    checkpoint: Optional[Path] = None,
    model_import: Optional[str] = None,
) -> Path:
    """Run Depth Anything 3 on a video or mission and export depth/PLY/Gaussians."""
    da3_config = config.depth_anything_3
    mission_id, frames, default_output = _load_input_frames(
        config=config,
        input_path=input_path,
        frame_stride=da3_config.frame_stride,
        max_frames=da3_config.max_frames,
    )

    if not frames:
        raise RuntimeError(f"No frames found in {input_path}")

    output_dir = Path(output) if output else default_output
    output_dir.mkdir(parents=True, exist_ok=True)

    log_section(logger, "Depth Anything 3")
    estimator = DepthAnything3Estimator(
        model_id=model_id or da3_config.model_id,
        checkpoint_path=checkpoint or da3_config.checkpoint_path,
        model_import=model_import or da3_config.model_import,
        device=config.vggt.device,
        input_size=da3_config.input_size,
        metric_scale=da3_config.metric_scale,
    )

    logger.info(f"Running Depth Anything 3 on {len(frames)} frames")
    result = estimator.predict_batch(frames)

    depth_npz = output_dir / f"{mission_id}_depth_anything_3_depths.npz"
    result.save(depth_npz)
    logger.info(f"Saved depths to {depth_npz}")

    depth_png_dir = output_dir / "depth_png"
    save_depth_pngs(result.depths, depth_png_dir)
    logger.info(f"Saved normalized depth PNGs to {depth_png_dir}")

    points, colors = depth_to_point_cloud(
        result.depths,
        images=result.images,
        stride=da3_config.point_stride,
        max_points=da3_config.max_points,
        focal_length_px=da3_config.focal_length_px,
    )
    if len(points) == 0:
        raise RuntimeError("Depth Anything 3 produced no valid 3D points")

    ply_path = output_dir / f"{mission_id}_depth_anything_3_pointcloud.ply"
    export_point_cloud_ply(points, ply_path, colors=colors)
    logger.info(f"Saved point cloud to {ply_path}")

    gaussians = gaussian_from_point_cloud(
        points,
        sh_degree=config.gaussian_splatting.sh_degree,
    )
    gaussians_path = output_dir / f"{mission_id}_depth_anything_3_gaussians.npz"
    gaussians.save(gaussians_path)
    logger.info(f"Saved Gaussian initialization to {gaussians_path}")

    logger.info(f"\n✨ Depth Anything 3 output ready at: {output_dir}\n")
    return output_dir
