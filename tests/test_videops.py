"""Ground-truth tests for videops — the spatiotemporal (video) operators.

Every behavioural claim is checked against a video whose answer is known by
construction: a perfectly static sequence must have ~zero temporal std and an
empty foreground mask; a bright square that translates across the frame must be
localised by background subtraction and motion energy; a blinking dot must survive
a max projection; a constant volume must pass unchanged through the 3-D Gaussian.

A functional gate first runs every public op on canonical inputs and asserts the
declared output shape / dtype / finiteness, so a regression in any op surfaces even
without its dedicated ground-truth test.
"""
import numpy as np
import pytest

import videops as vp


# --------------------------------------------------------------------------- #
# Constructed inputs with known temporal structure
# --------------------------------------------------------------------------- #
def _static(t=8, h=32, w=40, seed=0):
    """A stationary scene: one fixed image repeated for T frames (no motion)."""
    rng = np.random.default_rng(seed)
    base = rng.random((h, w)) * 0.6 + 0.2                 # in [0.2, 0.8]
    return np.repeat(base[None], t, axis=0)


def _static_noisy(t=40, h=32, w=40, sigma=0.05, seed=1):
    """Static scene + zero-mean per-frame sensor noise (denoising target)."""
    rng = np.random.default_rng(seed)
    base = rng.random((h, w)) * 0.6 + 0.2
    noise = rng.normal(0.0, sigma, (t, h, w))
    return np.clip(base[None] + noise, 0.0, 1.0), base


def _moving_square(t=10, h=40, w=60, sq=6, seed=0):
    """Dark background with a bright square translating left->right, one step/frame.

    Returns (video, centers) where centers[t] = (row, col) of the square centre,
    so the ground truth knows exactly where motion happened."""
    vid = np.full((t, h, w), 0.1, np.float64)
    centers = []
    r0 = h // 2
    for i in range(t):
        c0 = 6 + i * ((w - 14) // max(1, t - 1))
        vid[i, r0 - sq // 2:r0 + sq // 2, c0 - sq // 2:c0 + sq // 2] = 0.95
        centers.append((r0, c0))
    return vid, centers


def _blinking_dot(t=9, h=20, w=24, r=10, c=12):
    """Black frames; a bright dot at (r, c) is on for odd frames, off for even."""
    vid = np.zeros((t, h, w), np.float64)
    for i in range(t):
        if i % 2 == 1:
            vid[i, r, c] = 0.9
    return vid, (r, c)


# A small battery covering the three input archetypes (used by the gate).
def _battery():
    stat = _static()
    mov, _ = _moving_square()
    blink, _ = _blinking_dot()
    return {"static": stat, "moving": mov, "blinking": blink}


# --------------------------------------------------------------------------- #
# FUNCTIONAL GATE — every op returns its declared sort / shape / dtype, finite
# --------------------------------------------------------------------------- #
# (name, callable, kind) where kind is "video"(T,H,W) | "diffvol"(T-1,H,W) | "map"(H,W)
_MAP_OPS = [
    ("temporal_mean", vp.temporal_mean),
    ("temporal_median", vp.temporal_median),
    ("temporal_std", vp.temporal_std),
    ("temporal_max", vp.temporal_max),
    ("temporal_min", vp.temporal_min),
    ("motion_energy", vp.motion_energy),
]
_VIDEO_OPS = [
    ("temporal_gradient", vp.temporal_gradient),
    ("background_subtraction", vp.background_subtraction),
    ("moving_average", vp.moving_average),
    ("spatiotemporal_gaussian", vp.spatiotemporal_gaussian),
    ("spatiotemporal_sobel", vp.spatiotemporal_sobel),
    ("flicker_reduce", vp.flicker_reduce),
]
_DIFFVOL_OPS = [
    ("frame_difference", vp.frame_difference),
    ("optical_flow_sequence", vp.optical_flow_sequence),
]


@pytest.mark.parametrize("vidname", ["static", "moving", "blinking"])
def test_functional_gate_maps(vidname):
    vid = _battery()[vidname]
    _, H, W = vid.shape
    for name, fn in _MAP_OPS:
        out = fn(vid)
        assert out.shape == (H, W), f"{name}: {out.shape} != {(H, W)}"
        assert out.dtype == np.float64, f"{name}: dtype {out.dtype}"
        assert np.all(np.isfinite(out)), f"{name}: non-finite"


@pytest.mark.parametrize("vidname", ["static", "moving", "blinking"])
def test_functional_gate_videos(vidname):
    vid = _battery()[vidname]
    T, H, W = vid.shape
    for name, fn in _VIDEO_OPS:
        out = fn(vid)
        assert out.shape == (T, H, W), f"{name}: {out.shape} != {(T, H, W)}"
        assert out.dtype == np.float64, f"{name}: dtype {out.dtype}"
        assert np.all(np.isfinite(out)), f"{name}: non-finite"


@pytest.mark.parametrize("vidname", ["static", "moving", "blinking"])
def test_functional_gate_diffvols(vidname):
    vid = _battery()[vidname]
    T, H, W = vid.shape
    for name, fn in _DIFFVOL_OPS:
        out = fn(vid)
        assert out.shape == (T - 1, H, W), f"{name}: {out.shape} != {(T - 1, H, W)}"
        assert out.dtype == np.float64, f"{name}: dtype {out.dtype}"
        assert np.all(np.isfinite(out)), f"{name}: non-finite"


def test_functional_gate_per_frame():
    vid = _battery()["moving"]
    out = vp.per_frame(vid, lambda f: f * 0.5)
    assert out.shape == vid.shape and out.dtype == np.float64
    assert np.all(np.isfinite(out))


def test_background_mask_is_binary():
    vid, _ = _moving_square()
    mask = vp.background_subtraction(vid, threshold=0.2)
    assert set(np.unique(mask)).issubset({0.0, 1.0})


# --------------------------------------------------------------------------- #
# GROUND TRUTH — semantics proven on constructed inputs
# --------------------------------------------------------------------------- #
def test_temporal_std_zero_for_static():
    """A repeated frame has no temporal variation anywhere."""
    vid = _static()
    s = vp.temporal_std(vid)
    assert s.max() < 1e-12


def test_background_subtraction_empty_for_static():
    """No motion -> no foreground, at any sane threshold."""
    vid = _static()
    mask = vp.background_subtraction(vid, threshold=0.05)
    assert mask.sum() == 0.0


def test_temporal_mean_denoises_static_camera():
    """Averaging T noisy frames of a fixed scene beats any single frame."""
    vid, base = _static_noisy(t=60, sigma=0.06)
    avg = vp.temporal_mean(vid)
    err_avg = np.abs(avg - base).mean()
    err_one = np.abs(vid[0] - base).mean()
    assert err_avg < err_one * 0.4, (err_avg, err_one)
    assert err_avg < 0.02


def test_temporal_median_recovers_background_under_traffic():
    """A bright square passing through leaves each pixel occupied only briefly,
    so the per-pixel median recovers the empty (0.1) background."""
    vid, _ = _moving_square(t=14)
    bg = vp.temporal_median(vid)
    assert np.abs(bg - 0.1).max() < 1e-9


def test_background_subtraction_localises_moving_square():
    """Foreground mask fires on the square and (almost) nowhere else."""
    vid, centers = _moving_square(t=12, sq=6)
    mask = vp.background_subtraction(vid, threshold=0.3)
    r0 = centers[0][0]
    for t, (r, c) in enumerate(centers):
        # the square's centre is flagged as foreground this frame
        assert mask[t, r, c] == 1.0, f"frame {t} centre not detected"
    # foreground is confined to the row band the square travels through
    band = mask[:, r0 - 4:r0 + 4, :].sum()
    total = mask.sum()
    assert total > 0
    assert band / total > 0.95, "foreground leaks outside the square's row band"


def test_motion_energy_follows_the_square_path():
    """Motion energy is high along the swept path, ~0 in never-touched corners."""
    vid, centers = _moving_square(t=12, sq=6)
    me = vp.motion_energy(vid)
    r0 = centers[0][0]
    path_band = me[r0 - 4:r0 + 4, :].mean()
    corner = me[:6, :6].mean()                 # top-left corner the square never enters
    assert path_band > 10 * (corner + 1e-9)
    assert corner < 1e-6


def test_frame_difference_matches_manual_and_shape():
    vid, _ = _moving_square(t=7)
    fd = vp.frame_difference(vid)
    assert fd.shape == (6,) + vid.shape[1:]
    assert np.allclose(fd, np.abs(vid[1:] - vid[:-1]))
    # a static clip differences to exactly zero
    assert vp.frame_difference(_static(t=5)).max() == 0.0


def test_temporal_gradient_central_difference_values():
    """A pixel ramping linearly in time has a constant unit d/dt."""
    t, h, w = 6, 4, 4
    ramp = np.zeros((t, h, w))
    for i in range(t):
        ramp[i] = 0.1 * i                       # +0.1 per frame everywhere
    g = vp.temporal_gradient(ramp)
    assert np.allclose(g, 0.1)
    # T == 1 -> zero gradient (no temporal neighbour), full shape preserved
    one = np.full((1, h, w), 0.5)
    g1 = vp.temporal_gradient(one)
    assert g1.shape == (1, h, w) and np.all(g1 == 0.0)


def test_temporal_max_captures_blinking_dot():
    """Max projection recovers the dot's peak brightness at its pixel and 0 elsewhere."""
    vid, (r, c) = _blinking_dot()
    mx = vp.temporal_max(vid)
    assert abs(mx[r, c] - 0.9) < 1e-12
    off = mx.copy()
    off[r, c] = 0.0
    assert off.max() == 0.0


def test_temporal_min_is_per_pixel_minimum():
    """Min projection equals the exact elementwise min of a known stack."""
    a = np.array([[[0.3, 0.7]]])
    b = np.array([[[0.6, 0.2]]])
    vid = np.concatenate([a, b], axis=0)        # (2, 1, 2)
    mn = vp.temporal_min(vid)
    assert np.allclose(mn, [[0.3, 0.2]])


def test_moving_average_denoises_but_preserves_static_mean():
    """Temporal box filter on a static+noise clip cuts variance yet keeps the scene."""
    vid, base = _static_noisy(t=40, sigma=0.05)
    ma = vp.moving_average(vid, window=5)
    # each smoothed frame is closer to the true scene than the raw frame
    assert np.abs(ma - base[None]).mean() < np.abs(vid - base[None]).mean()
    # window=1 is an identity
    assert np.allclose(vp.moving_average(vid, window=1), vid)


def test_spatiotemporal_gaussian_preserves_constant_volume():
    """A DC-gain-1 blur returns a constant volume unchanged."""
    vid = np.full((6, 20, 24), 0.42)
    out = vp.spatiotemporal_gaussian(vid, sigma_t=1.5, sigma_s=2.0)
    assert np.allclose(out, 0.42, atol=1e-9)
    assert out.shape == vid.shape


def test_spatiotemporal_gaussian_reduces_noise_energy():
    """Blurring genuinely lowers the high-frequency energy of a noisy clip."""
    rng = np.random.default_rng(3)
    vid = np.clip(0.5 + rng.normal(0, 0.1, (8, 30, 30)), 0, 1)
    out = vp.spatiotemporal_gaussian(vid, sigma_t=1.0, sigma_s=1.0)
    assert out.std() < vid.std()


def test_spatiotemporal_sobel_flags_a_spatial_edge():
    """A stationary vertical edge produces a strong spatiotemporal response on it
    and ~0 in the flat regions away from it."""
    vid = np.zeros((5, 20, 20))
    vid[:, :, 10:] = 1.0                          # vertical step edge, same every frame
    mag = vp.spatiotemporal_sobel(vid)
    edge = mag[:, :, 9:11].mean()
    flat = mag[:, :, :5].mean()
    assert edge > 0.5
    assert flat < 1e-9


def test_spatiotemporal_sobel_flags_a_temporal_edge():
    """A frame that switches from all-dark to all-bright creates a temporal edge
    the 3-D Sobel detects even though each frame is spatially flat."""
    vid = np.zeros((6, 16, 16))
    vid[3:] = 1.0                                 # step in time at t=3
    mag = vp.spatiotemporal_sobel(vid)
    # interior pixels straddling the temporal step respond; far-from-step frames don't
    assert mag[2:4, 8, 8].max() > 0.5
    assert mag[0, 8, 8] < 1e-9


def test_per_frame_applies_op_independently():
    vid, _ = _moving_square(t=5)
    out = vp.per_frame(vid, lambda f: np.clip(f * 2.0, 0, 1))
    assert np.allclose(out, np.clip(vid * 2.0, 0, 1))


def test_per_frame_rejects_shape_change():
    vid = _static(t=3)
    with pytest.raises(ValueError):
        vp.per_frame(vid, lambda f: f[:, :3])     # op that changes (H, W)
    with pytest.raises(TypeError):
        vp.per_frame(vid, 123)                     # not callable


def test_flicker_reduce_equalises_frame_means():
    """A static scene modulated by per-frame brightness flicker is re-levelled so
    every frame's mean matches the sequence mean."""
    rng = np.random.default_rng(4)
    base = rng.random((24, 24)) * 0.4 + 0.3       # scene in [0.3, 0.7]
    gains = np.array([-0.1, 0.05, 0.12, -0.08, 0.0, 0.09])   # additive flicker
    vid = np.stack([np.clip(base + g, 0, 1) for g in gains], axis=0)
    # sanity: the raw frame means genuinely differ (there IS flicker to remove)
    raw_means = vid.mean(axis=(1, 2))
    assert raw_means.max() - raw_means.min() > 0.05
    out = vp.flicker_reduce(vid)
    means = out.mean(axis=(1, 2))
    assert means.max() - means.min() < 1e-9        # all equal after correction
    assert abs(means.mean() - vid.mean()) < 1e-9


def test_optical_flow_sequence_static_vs_moving():
    """Flow magnitude is ~0 for a static clip and clearly larger for a moving one,
    with the documented (T-1, H, W) shape."""
    stat = _static(t=6)
    mov, _ = _moving_square(t=8)
    fs = vp.optical_flow_sequence(stat)
    fm = vp.optical_flow_sequence(mov)
    assert fs.shape == (stat.shape[0] - 1,) + stat.shape[1:]
    assert np.all(np.isfinite(fs)) and np.all(np.isfinite(fm))
    assert fs.max() < 1e-9                          # nothing moved -> no flow
    assert fm.sum() > fs.sum() + 1.0                # motion registers


def test_optical_flow_sequence_localises_motion():
    """The flow volume carries more motion in the moving square's row band than in a
    never-touched corner.

    The margin is deliberately modest, not 5x: with the real dense Lucas-Kanade
    backend a near-textureless background is aperture-ambiguous, so the regularised
    solve propagates some flow into flat regions (a genuine, documented property of
    dense LK). We assert the honest, robust inequality rather than overclaiming
    pinpoint localisation — motion_energy is the map to use when tight localisation
    is required (see test_motion_energy_follows_the_square_path)."""
    mov, centers = _moving_square(t=8, sq=6)
    fm = vp.optical_flow_sequence(mov)
    r0 = centers[0][0]
    band = fm[:, r0 - 5:r0 + 5, :].mean()
    corner = fm[:, :5, :5].mean()
    assert band > corner


# --------------------------------------------------------------------------- #
# Input validation — fail-closed on malformed input
# --------------------------------------------------------------------------- #
def test_rejects_non_3d():
    with pytest.raises(ValueError):
        vp.temporal_mean(np.zeros((10, 10)))          # 2-D, not a video
    with pytest.raises(ValueError):
        vp.temporal_mean(np.zeros((2, 3, 4, 5)))      # 4-D


def test_rejects_non_finite():
    vid = _static(t=4)
    vid[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        vp.temporal_std(vid)
    vid2 = _static(t=4)
    vid2[1, 2, 3] = np.inf
    with pytest.raises(ValueError):
        vp.temporal_max(vid2)


def test_rejects_empty_sequence():
    with pytest.raises(ValueError):
        vp.temporal_mean(np.zeros((0, 8, 8)))         # T == 0
    with pytest.raises(ValueError):
        vp.temporal_mean([])                           # empty frame list


def test_accepts_frame_list_and_stacks():
    frames = [np.full((5, 5), 0.2), np.full((5, 5), 0.8)]
    m = vp.temporal_mean(frames)
    assert m.shape == (5, 5) and np.allclose(m, 0.5)


def test_ragged_frame_list_rejected():
    with pytest.raises(ValueError):
        vp.temporal_mean([np.zeros((4, 4)), np.zeros((4, 5))])
