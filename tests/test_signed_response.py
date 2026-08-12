"""Signed filter responses must honour out_sort=image ([0,1]) WITHOUT losing
their negative half.

Before the fix these ops used `_norm` (→[-1,1]); the pipeline's [0,1] clip then
discarded every negative pixel. Now they map through `signed01` (0 → 0.5), so the
output stays in [0,1] AND both signs survive.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

# ops whose raw response is genuinely bipolar (Laplacian / Harris R / phase / morph-laplace)
SIGNED_OPS = [
    "highpass", "corner_response", "laplace_of_gauss", "dots_image", "tan_image",
    "sk_shape_index", "sk_hessian_det", "sk_corner_harris", "cv_corner_harris",
    "xkor_harris", "xsk2_corner_kr", "xsp_morph_laplace", "xsk_unwrap_phase",
    "points_harris_binomial",
]


def _corner_rich(n=64):
    """Squares on a field -> corners (Harris R>0) and edges (R<0): both signs."""
    img = np.full((n, n), 0.2)
    for (r, c) in [(12, 12), (12, 40), (40, 12), (40, 40)]:
        img[r:r + 12, c:c + 12] = 0.9
    return np.clip(img + np.random.default_rng(0).normal(0, 0.02, img.shape), 0, 1)


@pytest.mark.parametrize("name", SIGNED_OPS)
def test_signed_op_stays_in_unit_range(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered")
    out = np.asarray(fn(_corner_rich(), 0.5, 0.5), np.float64)
    assert np.all(np.isfinite(out))
    assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (
        f"{name} out of [0,1]: min={out.min()} max={out.max()}")


@pytest.mark.parametrize("name", SIGNED_OPS)
def test_signed_op_preserves_negative_half(name):
    """A signed response must keep values on BOTH sides of 0.5 — the old code
    clipped the whole negative half to 0."""
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered")
    out = np.asarray(fn(_corner_rich(), 0.5, 0.5), np.float64)
    has_neg = (out < 0.5 - 1e-3).any()
    has_pos = (out > 0.5 + 1e-3).any()
    assert has_neg and has_pos, (
        f"{name} collapsed to one side of 0.5 (sign lost): "
        f"min={out.min():.3f} max={out.max():.3f}")
