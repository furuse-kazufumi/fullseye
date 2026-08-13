"""Ground-truth tests for flow-based motion analysis.

The flow fields are built by construction (a known constant / affine field, or a
static background plus one moving patch), so the fitted global motion, the
residual, and the segmented moving regions all have exact expected answers."""
import numpy as np

import motion


def _const(u0, v0, h=96, w=120):
    return np.full((h, w), float(u0)), np.full((h, w), float(v0))


def test_frame_motion_energy_is_rms_speed():
    u, v = _const(3.0, 4.0)
    assert np.isclose(motion.frame_motion_energy(u, v), 5.0)
    assert motion.frame_motion_energy(*_const(0.0, 0.0)) == 0.0


def test_dominant_motion_recovers_translation_and_affine():
    u, v = _const(2.5, -1.5)
    M = motion.dominant_motion(u, v)
    assert np.allclose(M[0], [2.5, 0, 0], atol=1e-6)
    assert np.allclose(M[1], [-1.5, 0, 0], atol=1e-6)
    # a genuine affine field: u = 2 + 0.1 x, v = 1 - 0.05 y
    H, W = 96, 120
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    ua, va = 2 + 0.1 * xx, 1 - 0.05 * yy
    Ma = motion.dominant_motion(ua, va)
    assert np.allclose(Ma[0], [2, 0.1, 0], atol=1e-6)
    assert np.allclose(Ma[1], [1, 0, -0.05], atol=1e-6)


def test_residual_motion_zero_for_pure_global():
    H, W = 64, 80
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    u, v = 1 + 0.03 * xx, -0.5 + 0.02 * yy
    ru, rv = motion.residual_motion(u, v)
    assert np.abs(ru).max() < 1e-6 and np.abs(rv).max() < 1e-6


def _bg_plus_patch(bg=(2.0, 1.0), patch=(2.0, -6.0), h=96, w=120):
    u, v = _const(bg[0], bg[1], h, w)
    u[38:58, 48:72] = patch[0]
    v[38:58, 48:72] = patch[1]
    return u, v


def test_motion_segments_finds_the_moving_patch():
    u, v = _bg_plus_patch()
    mask, segs = motion.motion_segments(u, v, threshold=2.0, min_area=25)
    assert len(segs) == 1, f"expected one moving region, got {len(segs)}"
    cy, cx = segs[0]["centroid"]
    assert abs(cy - 47.5) < 4 and abs(cx - 59.5) < 4      # centred on the patch
    assert mask[48, 60] and not mask[5, 5]                # patch set, background clear


def test_dominant_motion_robust_to_a_moving_object():
    # background (2,1); a centred 15%-area object moving at (10,10)
    u, v = _const(2.0, 1.0)
    u[30:66, 42:78] = 10.0
    v[30:66, 42:78] = 10.0
    M_rob = motion.dominant_motion(u, v, robust=True, trim=0.25)
    M_raw = motion.dominant_motion(u, v, robust=False)
    assert abs(M_rob[0, 0] - 2.0) < 0.15 and abs(M_rob[1, 0] - 1.0) < 0.15
    assert abs(M_raw[0, 0] - 2.0) > 0.3                  # plain LS is dragged by the object


def test_dominant_motion_handles_nan_without_failing_open():
    # a single NaN flow sample must not collapse the model to a fake zero (which
    # would report the whole frame as independently moving)
    u, v = _const(4.0, 0.0)
    u[0, 0] = np.nan
    M = motion.dominant_motion(u, v)             # robust default
    assert abs(M[0, 0] - 4.0) < 1e-6 and abs(M[1, 0]) < 1e-6
    # too few finite samples -> visible NaN model, not a silent zero
    allnan = np.full((8, 8), np.nan)
    assert np.isnan(motion.dominant_motion(allnan, allnan)).all()


def test_robust_one_iteration_actually_trims():
    # robust=True, iters=1 must differ from the plain least-squares fit
    u, v = _const(2.0, 1.0)
    u[30:66, 42:78] = 10.0
    v[30:66, 42:78] = 10.0
    m1 = motion.dominant_motion(u, v, robust=True, iters=1)
    mr = motion.dominant_motion(u, v, robust=False)
    assert not np.allclose(m1, mr)
    assert abs(m1[0, 0] - 2.0) < 0.15            # one robust pass already rejects the object


def test_motion_segments_measures_unblurred_field():
    # area and mean_speed must come from the true speed, not a blurred one
    u = np.zeros((64, 64))
    v = np.zeros((64, 64))
    u[30:36, 30:36] = 10.0                        # a 6x6 block moving at exactly 10
    _, segs = motion.motion_segments(u, v, threshold=2.0, min_area=25, subtract_dominant=False)
    assert len(segs) == 1
    assert segs[0]["area"] == 36                  # exact, no smoothing dilation
    assert abs(segs[0]["mean_speed"] - 10.0) < 1e-6


def _seq_static_then_shift(n=8, move_at=4, seed=20):
    from scipy import ndimage
    rng = np.random.default_rng(seed)
    b = np.clip(ndimage.gaussian_filter(rng.random((64, 80)), 1.3), 0, 1)
    return [ndimage.shift(b, (0.0, 0.0) if i < move_at else (2.0, 3.0),
                          order=1, mode="nearest")
            for i in range(n)]


def test_motion_energy_series_and_detect_events():
    frames = _seq_static_then_shift(n=8, move_at=4)
    series = motion.motion_energy_series(frames, window=15, levels=2, iters=5)
    assert series.shape == (7,)
    assert int(series.argmax()) == 3              # the one static->moved transition (pair 3->4)
    events = motion.detect_events(series)
    assert 3 in events.tolist()


def test_motion_reachable_through_facade():
    import fullseye as fs
    u, v = _bg_plus_patch()
    assert np.isclose(fs.frame_motion_energy(*_const(3.0, 4.0)), 5.0)
    mask, segs = fs.motion_segments(u, v, threshold=2.0)
    assert len(segs) == 1
