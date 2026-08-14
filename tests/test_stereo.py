"""Ground-truth tests for the stereo depth building blocks.

The disparity is known by construction (the right image is the left image shifted
by a fixed number of columns), so the recovered disparity/depth can be checked
against an exact answer, not merely for plausibility."""
import numpy as np
import pytest

import stereo


def _textured(h=96, w=128, seed=0):
    rng = np.random.default_rng(seed)
    # smooth random texture -> locally unique matches, still band-limited
    from scipy import ndimage
    return np.clip(ndimage.gaussian_filter(rng.random((h, w)), 1.2), 0, 1)


def _shift_left_by(img, d0):
    """right[y, x] = left[y, x + d0]  (a feature at left col c appears at right c-d0)."""
    r = np.empty_like(img)
    r[:, : img.shape[1] - d0] = img[:, d0:]
    r[:, img.shape[1] - d0 :] = img[:, -1:]
    return r


@pytest.mark.parametrize("method", ["sad", "ssd", "ncc"])
def test_disparity_recovers_known_constant_shift(method):
    d0 = 6
    left = _textured()
    right = _shift_left_by(left, d0)
    disp = stereo.disparity_map(left, right, max_disp=16, block=9, method=method)
    # check the interior (away from the left search border and image edges)
    core = disp[20:-20, 30:-10]
    assert np.median(core) == d0, f"{method}: median disparity {np.median(core)} != {d0}"
    assert (np.abs(core - d0) <= 1).mean() > 0.9, f"{method}: <90% of interior within 1px of {d0}"


def test_disparity_is_discriminative_two_planes():
    # left region shifted by 4, right region by 10 -> a disparity edge in the middle
    left = _textured(seed=1)
    H, W = left.shape
    right = np.empty_like(left)
    right[:, : W // 2] = _shift_left_by(left, 4)[:, : W // 2]
    right[:, W // 2 :] = _shift_left_by(left, 10)[:, W // 2 :]
    disp = stereo.disparity_map(left, right, max_disp=16, block=9)
    near = np.median(disp[20:-20, 30 : W // 2 - 10])
    far = np.median(disp[20:-20, W // 2 + 10 : -10])
    assert near == 4 and far == 10


def test_depth_from_disparity_is_inverse_law():
    disp = np.array([[2.0, 4.0], [8.0, 0.0]])
    z = stereo.depth_from_disparity(disp, focal=100.0, baseline=0.5)
    assert np.isclose(z[0, 0], 100.0 * 0.5 / 2.0)     # 25
    assert np.isclose(z[0, 1], 100.0 * 0.5 / 4.0)     # 12.5
    assert np.isclose(z[1, 0], 100.0 * 0.5 / 8.0)     # 6.25
    assert np.isinf(z[1, 1])                           # zero disparity -> unknown/far


def test_reproject_to_points_shape_and_finiteness():
    depth = np.full((10, 12), 5.0)
    depth[0, 0] = np.inf                               # one unmatched pixel dropped
    pts = stereo.reproject_to_points(depth, fx=50.0, fy=50.0)
    assert pts.shape == (10 * 12 - 1, 3)
    assert np.all(np.isfinite(pts))
    assert np.allclose(pts[:, 2], 5.0)                 # all at the constant plane depth


def _shift_subpixel(img, d0):
    """Fractional-disparity right image: right[y, x] = left[y, x + d0]."""
    from scipy import ndimage
    return ndimage.shift(img, (0.0, -d0), order=1, mode="nearest")


def test_subpixel_recovers_fractional_disparity():
    d0 = 5.4
    left = _textured(seed=7)
    right = _shift_subpixel(left, d0)
    sub = stereo.disparity_subpixel(left, right, max_disp=16, block=9, method="ssd")
    core = sub[20:-20, 30:-10]
    assert abs(np.median(core) - d0) < 0.3, f"subpixel median {np.median(core)} != {d0}"
    # and it beats the integer matcher's rounding error on this fractional shift
    integer = stereo.disparity_map(left, right, max_disp=16, block=9, method="ssd")
    err_sub = abs(np.median(core) - d0)
    err_int = abs(np.median(integer[20:-20, 30:-10]) - d0)
    assert err_sub <= err_int + 1e-9


def test_lr_consistency_accepts_clean_and_flags_corruption():
    d0 = 6
    left = _textured(seed=8)
    right = _shift_left_by(left, d0)
    dL = stereo.disparity_map(left, right, max_disp=16, block=9, reference="left")
    dR = stereo.disparity_map(left, right, max_disp=16, block=9, reference="right")
    ok = stereo.lr_consistency(dL, dR, max_diff=1.0)
    assert ok[20:-20, 30:-10].mean() > 0.9            # clean interior is consistent
    # corrupt a block of the right map -> those left pixels become inconsistent
    dR_bad = dR.copy()
    dR_bad[40:60, 40:60] = 0.0
    ok_bad = stereo.lr_consistency(dL, dR_bad, max_diff=1.0)
    assert ok_bad[45:55, 50:60].mean() < 0.5


def test_lr_consistency_rejects_no_overlap_margin():
    # left columns whose match falls at x - dL < 0 have no right correspondence and
    # must be marked untrustworthy, not clamped to column 0 and fabricated as valid
    ok = stereo.lr_consistency(np.full((1, 10), 6.0), np.full((1, 10), 6.0), max_diff=1.0)
    assert not ok[0, :6].any()          # columns 0..5 map to right cols -6..-1 -> invalid
    assert ok[0, 6:].all()              # columns 6..9 have real matches at cols 0..3


# --- census / SGM / post-processing ----------------------------------------- #
def test_census_is_illumination_invariant():
    img = _textured(seed=11)
    a = stereo.census_transform(img, window=5)
    b = stereo.census_transform(2.0 * img + 0.3, window=5)   # monotonic gain+offset
    assert np.array_equal(a, b)                              # ordering preserved -> same code


def test_census_disparity_robust_to_gain():
    d0 = 6
    left = _textured(seed=12)
    right = _shift_left_by(1.7 * left + 0.15, d0)            # brightened + shifted
    disp = stereo.disparity_census(left, right, max_disp=16, window=5)
    core = disp[20:-20, 30:-10]
    assert np.median(core) == d0
    assert (np.abs(core - d0) <= 1).mean() > 0.9


def test_sgm_recovers_shift_and_is_smoother():
    d0 = 7
    rng = np.random.default_rng(13)
    left = _textured(seed=13)
    right = _shift_left_by(left, d0) + rng.normal(0, 0.05, left.shape)   # noisy right
    wta = stereo.disparity_census(left, right, max_disp=16, window=5)
    sgm = stereo.disparity_sgm(left, right, max_disp=16, window=5, paths=4)
    assert np.median(sgm[20:-20, 30:-10]) == d0

    def tv(a):
        return np.abs(np.diff(a, axis=0)).mean() + np.abs(np.diff(a, axis=1)).mean()

    assert tv(sgm) < tv(wta)                                 # smoothness prior -> fewer specks


def test_speckle_filter_removes_small_blob():
    disp = np.full((60, 60), 6.0)
    disp[10:13, 10:13] = 0.0                                 # 9-px speckle, differs by 6
    clean, valid = stereo.speckle_filter(disp, max_diff=1.0, min_size=50)
    assert np.isnan(clean[10:13, 10:13]).all()               # small region invalidated
    assert valid[10:13, 10:13].sum() == 0
    assert np.isfinite(clean[30:, 30:]).all()                # large region kept


def test_fill_disparity_background_bias():
    disp = np.array([[5.0, 5.0, np.nan, np.nan, 3.0, 3.0],
                     [4.0, np.nan, np.nan, np.nan, np.nan, 4.0]])
    filled = stereo.fill_disparity(disp)
    assert filled[0, 2] == 3.0 and filled[0, 3] == 3.0       # min(left 5, right 3) = 3
    assert np.allclose(filled[1], 4.0)                        # both neighbours 4
    assert filled[0, 0] == 5.0                                # valid pixels untouched


def test_fill_disparity_keeps_measured_zero():
    # a legitimately-measured 0 disparity (far background) must NOT be treated as a
    # hole and overwritten; only NaN is a hole under the default mask.
    disp = np.array([[0.0, 5.0, np.nan, 5.0]])
    filled = stereo.fill_disparity(disp)
    assert filled[0, 0] == 0.0                          # measured zero preserved
    assert filled[0, 2] == 5.0                          # the NaN hole is filled


def test_confidence_high_on_texture_low_on_flat():
    d0 = 5
    left = _textured(seed=14)
    left[:, :40] = 0.5                                        # left block: flat / ambiguous
    right = _shift_left_by(left, d0)
    conf = stereo.disparity_confidence(left, right, max_disp=16, block=9, method="ssd")
    flat = conf[20:-20, 10:30].mean()
    textured = conf[20:-20, 60:-10].mean()
    assert textured > flat + 0.2                             # texture is more trustworthy
