"""Regression guard for the np.roll wrap-around defect (audit finding #70).

`_bilateral`, `_roberts_mag` (ops.py) and the `roberts` edge kind
(backends_auto._sh_edge) built their neighbourhood with `np.roll`, which is
CIRCULAR: the pixels of the first column/row were filtered with values taken
from the OPPOSITE border. That destroys the edge-preserving guarantee of the
bilateral filter and injects a spurious full-scale Roberts edge at the wrap
seam. The neighbourhood must be edge-clamped (border replication) so a pixel
only ever sees in-image neighbours.

Ground truth used here:
  * a bilateral filter is a normalised weighted average of neighbour values, so
    on a locally CONSTANT patch it must reproduce that constant exactly;
  * Roberts cross magnitude on a single vertical step edge is non-zero on
    exactly one column (the step column) and zero everywhere else in-image.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

N = 16


def _step_h():
    """16x16: left half 0.0, right half 1.0 (vertical edge between col 7 and 8)."""
    v = np.zeros((N, N), np.float64)
    v[:, N // 2:] = 1.0
    return v


def _step_v():
    """16x16: top half 0.0, bottom half 1.0 (horizontal edge between row 7 and 8)."""
    v = np.zeros((N, N), np.float64)
    v[N // 2:, :] = 1.0
    return v


# --- Bug I-a: bilateral wrapped, so the left border averaged in the bright ---- #
#              right border (and vice versa).                                    #
def test_bilateral_flat_border_is_not_contaminated_by_opposite_edge():
    v = _step_h()
    out = np.asarray(ops.RT["bilateral"](v.copy(), 0.0, 1.0), np.float64)
    # radius is 2, so cols 0..5 (and 10..15) see only their own flat half
    assert np.allclose(out[:, 0:6], 0.0, atol=1e-9), (
        "bilateral bled the bright far edge into the dark border "
        f"(max={np.abs(out[:, 0:6]).max():.6f}, expected 0)")
    assert np.allclose(out[:, 10:16], 1.0, atol=1e-9), (
        "bilateral bled the dark far edge into the bright border "
        f"(max dev={np.abs(out[:, 10:16] - 1).max():.6f}, expected 0)")


def test_bilateral_flat_border_is_not_contaminated_vertically():
    v = _step_v()
    out = np.asarray(ops.RT["bilateral"](v.copy(), 0.0, 1.0), np.float64)
    assert np.allclose(out[0:6, :], 0.0, atol=1e-9), "bilateral wrapped across the top border"
    assert np.allclose(out[10:16, :], 1.0, atol=1e-9), "bilateral wrapped across the bottom border"


def test_bilateral_still_preserves_the_real_edge():
    """The fix must not smear the genuine step: the two plateaus stay separated."""
    v = _step_h()
    out = np.asarray(ops.RT["bilateral"](v.copy(), 0.0, 1.0), np.float64)
    assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9
    assert out[8, 8] - out[8, 7] > 0.9, "bilateral no longer preserves the step edge"


# --- Bug I-b: roberts wrapped, producing a full-scale phantom edge at the ----- #
#              last column / last row.                                            #
@pytest.mark.parametrize("name", ["roberts_mag", "roberts"])
def test_roberts_has_no_phantom_edge_at_the_wrap_seam(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered")
    v = _step_h()
    out = np.asarray(fn(v.copy(), 0.5, 0.5), np.float64)
    # ground truth: a single vertical step -> response on exactly the step column
    assert out[8, N // 2 - 1] > 0.99, "the genuine step edge was lost"
    assert np.allclose(out[:, N - 1], 0.0, atol=1e-9), (
        f"{name} reported a phantom edge at the wrap seam (last column): "
        f"max={out[:, N - 1].max():.4f}, expected 0")
    nonzero_cols = sorted(np.flatnonzero(out.max(axis=0) > 1e-9).tolist())
    assert nonzero_cols == [N // 2 - 1], (
        f"{name} responded on columns {nonzero_cols}, expected only [{N // 2 - 1}]")


@pytest.mark.parametrize("name", ["roberts_mag", "roberts"])
def test_roberts_has_no_phantom_edge_at_the_bottom_row(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered")
    v = _step_v()
    out = np.asarray(fn(v.copy(), 0.5, 0.5), np.float64)
    assert out[N // 2 - 1, 8] > 0.99, "the genuine step edge was lost"
    assert np.allclose(out[N - 1, :], 0.0, atol=1e-9), (
        f"{name} reported a phantom edge at the wrap seam (last row): "
        f"max={out[N - 1, :].max():.4f}, expected 0")
