"""Tests for Depth Anything 3 helpers."""

import numpy as np

from tello_vggt.rendering.deep_anything_v3 import (
    DepthAnything3Result,
    depth_to_point_cloud,
    gaussian_from_point_cloud,
)


def test_depth_anything_3_result_save_load(temp_dir):
    depths = np.ones((2, 4, 4), dtype=np.float32)
    images = np.zeros((2, 4, 4, 3), dtype=np.uint8)
    result = DepthAnything3Result(depths=depths, images=images)

    path = temp_dir / "depths.npz"
    result.save(path)
    loaded = DepthAnything3Result.load(path)

    assert loaded.depths.shape == (2, 4, 4)
    assert loaded.images.shape == (2, 4, 4, 3)


def test_depth_to_point_cloud_and_gaussians():
    depths = np.ones((1, 4, 4), dtype=np.float32)
    images = np.full((1, 4, 4, 3), 128, dtype=np.uint8)

    points, colors = depth_to_point_cloud(depths, images=images, stride=2)
    gaussians = gaussian_from_point_cloud(points, sh_degree=1)

    assert points.shape[1] == 3
    assert colors.shape[1] == 3
    assert gaussians.means.shape == points.shape
    assert gaussians.sh_coefficients.shape[1] == 4
