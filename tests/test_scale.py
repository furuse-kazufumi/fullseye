"""Large-image tiling (scale.py): local ops are bit-interior-identical under
haloed tiling, and scale_class flags the ops that need an algorithm change.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops
import scale


def _img(n=200):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return np.clip(0.5 + 0.3 * np.sin(xx / 9.0) * np.cos(yy / 7.0), 0, 1)


@pytest.mark.parametrize("name,halo", [
    ("gaussian", 24), ("sobel_mag", 8), ("gerode", 8), ("mean_box", 8), ("median", 8),
])
def test_tiled_matches_whole_for_local_ops(name, halo):
    err = scale.tiling_error(ops.RT[name], _img(), a=0.4, b=0.5, tile=64, halo=halo)
    assert err < 1e-6, f"{name}: tiled result differs from whole-image by {err}"


def test_process_tiled_handles_non_multiple_size():
    img = _img(150)                                   # 150 not a multiple of tile=64
    out = scale.process_tiled(ops.RT["gaussian"], img, a=0.5, tile=64, halo=16)
    assert out.shape == img.shape and np.all(np.isfinite(out))


def test_scale_class_flags_known_cases():
    by = {o.name: o for o in ops.REGISTRY}
    assert scale.scale_class(by["gaussian"])["tile_safe"] is True
    assert scale.scale_class(by["lowpass"])["class"] == "memory_bound"        # FFT
    assert scale.scale_class(by["polar_trans_image"])["class"] == "cv2_limited"
    assert scale.scale_class(by["otsu"])["tile_safe"] is False                # global threshold
