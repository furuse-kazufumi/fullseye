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


# genuinely local ops with NO trailing global normalization -> bit-exact under tiling
@pytest.mark.parametrize("name,halo", [
    ("gaussian", 24), ("gerode", 8), ("gdilate", 8), ("mean_box", 8), ("median", 8),
])
def test_tiled_matches_whole_for_local_ops(name, halo):
    err = scale.tiling_error(ops.RT[name], _img(), a=0.4, b=0.5, tile=64, halo=halo)
    assert err < 1e-6, f"{name}: tiled result differs from whole-image by {err}"


def test_globally_normalized_op_tiles_spatially_but_not_in_scale():
    """sobel_mag ends in a global _norm, so tiling is structurally right but not
    bit-identical — documents the scale.py caveat rather than pretending otherwise."""
    err = scale.tiling_error(ops.RT["sobel_mag"], _img(), a=0.4, b=0.5, tile=64, halo=8)
    assert err > 0.0   # differs (per-tile normalization) — expected, not a tile-safe op


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


# --- the tile-safe classification is measured, not guessed -------------------- #
# A category-only classifier called 141 non-local ops "tile_safe" (region skeleton /
# distance / shape, gray histogram, edge magnitude / corner / DoG, multiscale
# texture, TV / diffusion / transform smoothers). scale._NOT_TILE_SAFE lists them.
# These two tests keep that list honest against the actual haloed tiler, so the
# classifier can never again silently promise a tiling that gives a wrong answer.

def _probes():
    """Structured (non-random) images with a bright feature parked in ONE tile, so a
    whole-image normalization or a global region op diverges from the tiled result."""
    yy, xx = np.mgrid[:192, :192]
    a = (0.3 + 0.5 * xx / 192).astype(np.float64)
    a[20:60, 20:120] = 0.9; a[120:170, 60:150] = 0.1; a[:8, :8] = 1.0
    b = np.zeros((160, 160)); b[40:120, 40:120] = 1.0; b[70:90, 70:90] = 0.3; b[:6, -6:] = 0.8
    c = np.sin(np.mgrid[:176, :176][1] / 9.0) * 0.4 + 0.5; c[10:30, 10:30] = 1.0
    return [a, b, c]


def _worst_tiling_error(op):
    """Max tiling_error over the probes x two param settings (-1.0 if it never ran)."""
    mx, ran = 0.0, False
    for im in _probes():
        for a, b in ((0.5, 0.5), (0.3, 0.7)):
            try:
                e = scale.tiling_error(op.fn, im, a, b, tile=64, halo=16)
            except Exception:                                # noqa: BLE001 - optional backend / shape
                continue
            if np.isfinite(e):
                mx, ran = max(mx, e), True
    return mx if ran else -1.0


def test_no_tile_safe_op_actually_breaks_under_tiling():
    """Completeness: every op scale_class marks tile_safe is bit-interior-identical
    under haloed tiling (the whole point of the class). Generous 1e-3 margin keeps
    the handful of borderline iterative smoothers — which ARE listed non-tileable —
    from making this flaky.
    """
    bad = []
    for op in ops.REGISTRY:
        if not scale.scale_class(op).get("tile_safe"):
            continue
        err = _worst_tiling_error(op)
        if err > 1e-3:
            bad.append((op.name, getattr(op, "category", ""), round(err, 4)))
    assert not bad, ("ops marked tile_safe that measurably break under tiling: %s\n"
                     "add them to scale._NOT_TILE_SAFE (with the right category "
                     "reason) or fix the op." % sorted(bad, key=lambda t: -t[2]))


def test_not_tile_safe_list_is_not_stale():
    """Staleness: every op in _NOT_TILE_SAFE really does diverge under tiling
    (> 1e-9). If an op became genuinely local, drop it from the set so the class
    stops under-reporting. Threshold is far below the completeness margin, so the
    two never contradict on a borderline op.
    """
    by = {o.name: o for o in ops.REGISTRY}
    stale = []
    for name in scale._NOT_TILE_SAFE:
        op = by.get(name)
        if op is None:
            continue                                         # optional backend absent
        err = _worst_tiling_error(op)
        if err >= 0.0 and err <= 1e-9:
            stale.append((name, err))
    assert not stale, ("_NOT_TILE_SAFE entries that are actually tileable now "
                       "(remove them): %s" % stale)


def test_reclassified_ops_report_actionable_class():
    """The measured non-tileable ops carry a real reason, not the tile_safe default."""
    by = {o.name: o for o in ops.REGISTRY}
    for name, cls in [("sobel_mag", "global_reduce"), ("sk_skeleton", "global"),
                      ("clahe", "global"), ("dist_transform", "global")]:
        if name in by:
            sc = scale.scale_class(by[name])
            assert sc["tile_safe"] is False and sc["class"] == cls, (name, sc)
