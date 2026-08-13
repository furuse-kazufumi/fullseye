"""Ground-truth tests for dense optical flow.

The motion is known by construction: ``nxt`` is ``prev`` shifted by a fixed
(sub-)pixel vector, so the recovered flow is checked against the exact answer,
not merely for plausibility. Warping ``prev`` by the estimated flow must also
reconstruct ``nxt`` (the standard consistency check)."""
import numpy as np
import pytest
from scipy import ndimage

import flow
import imgio


def _textured(h=112, w=144, seed=0):
    """Smooth random texture -> locally unique, band-limited gradients."""
    rng = np.random.default_rng(seed)
    return np.clip(ndimage.gaussian_filter(rng.random((h, w)), 1.3), 0, 1)


def _shift(img, u0, v0):
    """nxt[y, x] = prev[y - v0, x - u0]: a feature at (x, y) moves to (x+u0, y+v0)."""
    return ndimage.shift(img, (v0, u0), order=1, mode="nearest")


def _interior(a, m=22):
    return a[m:-m, m:-m]


@pytest.mark.parametrize("u0,v0", [(3.0, 2.0), (4.0, -3.0), (-2.0, 4.0)])
def test_lk_recovers_known_translation(u0, v0):
    prev = _textured()
    nxt = _shift(prev, u0, v0)
    u, v = flow.optical_flow_lk(prev, nxt, window=15, levels=3, iters=5)
    cu, cv = _interior(u), _interior(v)
    assert abs(np.median(cu) - u0) < 0.6, f"u median {np.median(cu)} != {u0}"
    assert abs(np.median(cv) - v0) < 0.6, f"v median {np.median(cv)} != {v0}"
    within = ((np.abs(cu - u0) <= 1.0) & (np.abs(cv - v0) <= 1.0)).mean()
    assert within > 0.7, f"only {within:.2f} of interior within 1px of ({u0},{v0})"


def test_hs_recovers_small_translation():
    prev = _textured(seed=2)
    nxt = _shift(prev, 1.0, 1.0)
    u, v = flow.optical_flow_hs(prev, nxt, alpha=0.5, iters=300)
    assert abs(np.median(_interior(u)) - 1.0) < 0.5
    assert abs(np.median(_interior(v)) - 1.0) < 0.5


def test_warp_by_flow_reconstructs_next():
    prev = _textured(seed=3)
    u0, v0 = 3.0, -2.0
    nxt = _shift(prev, u0, v0)
    # exact flow -> warp reproduces nxt in the interior
    exact = flow.warp_by_flow(prev, np.full_like(prev, u0), np.full_like(prev, v0))
    assert np.abs(_interior(exact) - _interior(nxt)).mean() < 0.02
    # estimated flow -> residual is much smaller than doing nothing
    u, v = flow.optical_flow_lk(prev, nxt, window=15, levels=3, iters=5)
    rec = flow.warp_by_flow(prev, u, v)
    r_warp = np.abs(_interior(rec) - _interior(nxt)).mean()
    r_none = np.abs(_interior(prev) - _interior(nxt)).mean()
    assert r_warp < 0.5 * r_none, f"warp residual {r_warp} not < half of {r_none}"


def test_zero_motion_gives_zero_flow():
    prev = _textured(seed=4)
    for u, v in (flow.optical_flow_lk(prev, prev.copy()),
                 flow.optical_flow_hs(prev, prev.copy(), iters=50)):
        assert np.abs(u).max() < 1e-9 and np.abs(v).max() < 1e-9


def test_flow_magnitude_and_angle_exact():
    u = np.array([[3.0, 0.0], [-1.0, 0.0]])
    v = np.array([[4.0, 0.0], [0.0, -2.0]])
    mag = flow.flow_magnitude(u, v)
    assert np.isclose(mag[0, 0], 5.0) and np.isclose(mag[0, 1], 0.0)
    ang = flow.flow_angle(u, v)
    assert np.isclose(ang[0, 0], np.arctan2(4.0, 3.0))
    assert np.isclose(ang[1, 1], np.arctan2(-2.0, 0.0))   # straight down -> -pi/2


def test_colorize_flow_contract():
    u = np.array([[0.0, 2.0], [-3.0, 0.0]])
    v = np.array([[0.0, -1.0], [1.0, 0.0]])
    rgb = imgio.colorize_flow(u, v)
    assert rgb.shape == (2, 2, 3)
    assert np.isfinite(rgb).all() and rgb.min() >= 0.0 and rgb.max() <= 1.0
    assert np.allclose(rgb[0, 0], 0.0)          # zero motion -> black


def test_lk_is_contrast_invariant():
    # brightness constancy is scale-invariant; scaling both frames must not change
    # the recovered flow (regression: a constant regulariser over-damped [0,1] input)
    prev = _textured(seed=11)
    nxt = _shift(prev, 3.0, 2.0)
    meds = []
    for c in (1.0, 0.25, 255.0):
        u, v = flow.optical_flow_lk(prev * c, nxt * c, iters=5)
        meds.append((np.median(_interior(u)), np.median(_interior(v))))
    for mu, mv in meds:
        assert abs(mu - 3.0) < 0.3 and abs(mv - 2.0) < 0.3
    assert max(m[0] for m in meds) - min(m[0] for m in meds) < 0.05   # ~identical across scale


def test_lk_does_not_diverge_with_many_iterations():
    # the fixed-template iteration must not blow up as iters grows (regression:
    # unbounded divergence past ~10 iterations)
    prev = _textured(seed=12)
    nxt = _shift(prev, 3.0, 2.0)
    for it in (5, 20, 80):
        u, v = flow.optical_flow_lk(prev, nxt, iters=it)
        assert abs(np.median(_interior(u)) - 3.0) < 0.4
        assert np.abs(u).max() < 20.0            # no runaway (was 225px at iters=80)


def test_lk_border_flow_stays_bounded():
    prev = _textured(seed=13)
    nxt = _shift(prev, 3.0, 2.0)
    u, v = flow.optical_flow_lk(prev, nxt)       # all defaults
    assert flow.flow_magnitude(u, v).max() < 10.0   # border spikes bounded (was ~14.5)


def test_hs_alpha_zero_is_finite():
    # alpha=0 on a flat region must not produce 0/0 = NaN (codex review)
    z = np.zeros((8, 8))
    u, v = flow.optical_flow_hs(z, z, alpha=0.0)
    assert np.isfinite(u).all() and np.isfinite(v).all()


def test_flow_rejects_degenerate_shape():
    import pytest
    for fn in (flow.optical_flow_lk, flow.optical_flow_hs):
        with pytest.raises(ValueError):
            fn(np.zeros((1, 3)), np.zeros((1, 3)))     # too thin for a gradient


def test_flow_reachable_through_facade():
    import fullseye as fs
    prev = _textured(seed=5)
    nxt = _shift(prev, 2.0, 1.0)
    u, v = fs.optical_flow_lk(prev, nxt, levels=3)
    assert u.shape == prev.shape
    assert abs(np.median(_interior(u)) - 2.0) < 0.7
    rgb = fs.colorize_flow(u, v)
    assert rgb.shape == prev.shape + (3,)
    rec = fs.warp_by_flow(prev, u, v)
    assert rec.shape == prev.shape
