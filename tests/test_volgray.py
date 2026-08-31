"""Ground-truth tests for the 3-D volume intensity transforms (volgray.py).

Each test builds a *known* synthetic volume — three fixed HU values, a uniform
random field, a bimodal mixture, exact-percentile ramps — and asserts the
operator produces the value that arithmetic guarantees, plus the fail-closed
contracts (3-D only, finite only, voxel cap). The volume frame is the one
:mod:`volio` / :mod:`volops` use: ``(D, H, W)`` float64 indexed ``[z, y, x]``.
"""
import numpy as np
import pytest

import volgray


def _rng(seed=0):
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------- #
# vol_window_level — hand-computed linear map with clipping                    #
# --------------------------------------------------------------------------- #
def test_window_level_known_values_map_exactly():
    """Window C=40, W=400 -> [-160, 240]. Below maps to 0, centre to 0.5,
    above to 1 — each checked against the hand-computed value."""
    v = np.zeros((2, 2, 3), np.float64)
    v[0, 0, 0] = -1000.0        # far below the window  -> 0.0 (clipped)
    v[0, 0, 1] = 40.0           # exactly the centre    -> 0.5
    v[0, 0, 2] = 700.0          # far above the window  -> 1.0 (clipped)
    v[1, 1, 0] = -160.0         # window low edge       -> 0.0 (exact)
    v[1, 1, 1] = 240.0          # window high edge      -> 1.0 (exact)
    v[1, 1, 2] = 140.0          # (140 + 160) / 400     -> 0.75
    out = volgray.vol_window_level(v, center=40.0, width=400.0)
    assert out.shape == v.shape and out.dtype == np.float64
    assert out[0, 0, 0] == 0.0
    assert out[0, 0, 1] == pytest.approx(0.5)
    assert out[0, 0, 2] == 1.0
    assert out[1, 1, 0] == pytest.approx(0.0)
    assert out[1, 1, 1] == pytest.approx(1.0)
    assert out[1, 1, 2] == pytest.approx(0.75)


def test_window_level_negative_center_hu_style():
    """A lung-style window C=-600, W=1500 -> [-1350, 150]: negative centres
    (real Hounsfield practice) work identically."""
    v = np.array([[[-1350.0, -600.0, 150.0, -2000.0, 500.0]]])
    out = volgray.vol_window_level(v, center=-600.0, width=1500.0)
    assert out[0, 0, 0] == pytest.approx(0.0)
    assert out[0, 0, 1] == pytest.approx(0.5)
    assert out[0, 0, 2] == pytest.approx(1.0)
    assert out[0, 0, 3] == 0.0                        # clipped below
    assert out[0, 0, 4] == 1.0                        # clipped above


def test_window_level_custom_out_range():
    v = np.full((2, 2, 2), 40.0)
    out = volgray.vol_window_level(v, center=40.0, width=400.0, out_range=(0.0, 255.0))
    assert np.allclose(out, 127.5)                    # centre -> midpoint of [0, 255]


def test_window_level_rejects_bad_width_and_out_range():
    v = np.zeros((2, 2, 2))
    with pytest.raises(ValueError, match="width"):
        volgray.vol_window_level(v, center=0.0, width=0.0)
    with pytest.raises(ValueError, match="width"):
        volgray.vol_window_level(v, center=0.0, width=-10.0)
    with pytest.raises(ValueError, match="out_range"):
        volgray.vol_window_level(v, center=0.0, width=1.0, out_range=(1.0, 0.0))
    with pytest.raises(ValueError, match="out_range"):
        volgray.vol_window_level(v, center=0.0, width=1.0, out_range=(0.0, np.inf))


# --------------------------------------------------------------------------- #
# vol_equalize — CDF flattening, verified at the quantiles                     #
# --------------------------------------------------------------------------- #
def test_equalize_uniform_is_roughly_identity():
    """A uniform [0, 1] field already has a flat histogram: equalisation must
    leave it (approximately — nbins discretisation) unchanged."""
    v = _rng(1).uniform(0.0, 1.0, size=(12, 14, 16))
    out = volgray.vol_equalize(v, nbins=256)
    assert out.shape == v.shape
    assert out.min() >= 0.0 and out.max() <= 1.0
    # per-voxel: each value moves by at most a few bin widths
    assert np.abs(out - v).max() < 0.05
    assert np.abs(out - v).mean() < 0.01


def test_equalize_bimodal_flattens_cdf():
    """A bimodal mixture (two tight clusters at 0.2 and 0.8) has a badly
    non-uniform CDF. After equalisation the empirical quantiles must sit close
    to the ideal flat-histogram quantiles q (machine-checked at 9 deciles)."""
    r = _rng(2)
    a = r.normal(0.2, 0.02, size=4000)
    b = r.normal(0.8, 0.02, size=4000)
    v = np.concatenate([a, b]).reshape(20, 20, 20)
    out = volgray.vol_equalize(v, nbins=256)
    qs = np.linspace(0.1, 0.9, 9)
    emp = np.quantile(out, qs)
    # before: the same quantiles of the raw volume are nowhere near flat
    raw = np.quantile((v - v.min()) / (v.max() - v.min()), qs)
    err_after = np.abs(emp - qs).max()
    err_before = np.abs(raw - qs).max()
    assert err_after < 0.05, (emp, qs)
    assert err_before > 0.2                           # the test is not vacuous
    # monotone: ordering preserved
    flat_v, flat_o = v.ravel(), out.ravel()
    order = np.argsort(flat_v)
    assert (np.diff(flat_o[order]) >= 0.0).all()


def test_equalize_constant_passthrough():
    v = np.full((6, 7, 8), 3.25)
    out = volgray.vol_equalize(v)
    assert np.array_equal(out, v)
    assert out is not v                               # a copy, not the input object


def test_equalize_mask_uses_masked_histogram_only():
    """Changing *only* voxels outside the mask must not change the LUT: the
    masked region's output stays identical (up to the shared [min, max] binning
    range, held fixed here by pinning the volume extremes inside the mask)."""
    r = _rng(3)
    v1 = r.uniform(0.0, 1.0, size=(10, 10, 10))
    mask = np.zeros_like(v1)
    mask[:, :, :5] = 1.0                              # left half is the domain
    # pin the global extremes inside the mask so the binning range is identical
    v1[0, 0, 0] = 0.0
    v1[0, 0, 1] = 1.0
    v2 = v1.copy()
    outside = mask <= 0.5
    v2[outside] = np.clip(v2[outside] * 0.3 + 0.2, 0.0, 1.0)  # perturb outside only
    out1 = volgray.vol_equalize(v1, mask=mask)
    out2 = volgray.vol_equalize(v2, mask=mask)
    inside = mask > 0.5
    assert np.allclose(out1[inside], out2[inside])
    # and the mask genuinely matters: no-mask equalisation of v2 differs inside
    out2_nomask = volgray.vol_equalize(v2)
    assert not np.allclose(out2_nomask[inside], out2[inside])


def test_equalize_mask_validation():
    v = _rng(4).uniform(size=(4, 4, 4))
    with pytest.raises(ValueError, match="mask"):
        volgray.vol_equalize(v, mask=np.zeros((4, 4, 5)))     # shape mismatch
    with pytest.raises(ValueError, match="mask"):
        volgray.vol_equalize(v, mask=np.zeros((4, 4, 4)))     # empty domain
    with pytest.raises(ValueError, match="nbins"):
        volgray.vol_equalize(v, nbins=1)


# --------------------------------------------------------------------------- #
# vol_gamma — identity, darkening, monotonicity                                #
# --------------------------------------------------------------------------- #
def test_gamma_one_is_identity():
    v = _rng(5).uniform(-50.0, 300.0, size=(8, 9, 10))
    out = volgray.vol_gamma(v, 1.0)
    assert np.allclose(out, v)


def test_gamma_two_darkens_midtones_and_fixes_extremes():
    """On [0, 1], gamma=2 sends 0.5 -> 0.25 exactly; 0 and 1 are fixed points."""
    v = np.zeros((2, 2, 2), np.float64)
    v[0, 0, 0] = 0.0
    v[0, 0, 1] = 0.5
    v[0, 1, 0] = 1.0
    out = volgray.vol_gamma(v, 2.0)
    assert out[0, 0, 0] == pytest.approx(0.0)
    assert out[0, 0, 1] == pytest.approx(0.25)        # darker than 0.5
    assert out[0, 1, 0] == pytest.approx(1.0)
    # on a shifted range [100, 300], the midpoint 200 -> 100 + 0.25*200 = 150
    w = np.zeros((2, 2, 2), np.float64) + 100.0
    w[0, 0, 1] = 200.0
    w[0, 1, 0] = 300.0
    outw = volgray.vol_gamma(w, 2.0)
    assert outw[0, 0, 1] == pytest.approx(150.0)


def test_gamma_preserves_monotonic_order():
    v = _rng(6).uniform(0.0, 1.0, size=(6, 6, 6))
    for g in (0.4, 2.5):
        out = volgray.vol_gamma(v, g)
        order = np.argsort(v.ravel())
        assert (np.diff(out.ravel()[order]) >= 0.0).all()
        # range endpoints preserved
        assert out.min() == pytest.approx(v.min())
        assert out.max() == pytest.approx(v.max())


def test_gamma_constant_passthrough_and_bad_gamma():
    v = np.full((3, 3, 3), -7.5)
    assert np.array_equal(volgray.vol_gamma(v, 2.0), v)
    with pytest.raises(ValueError, match="gamma"):
        volgray.vol_gamma(v, 0.0)
    with pytest.raises(ValueError, match="gamma"):
        volgray.vol_gamma(v, -1.0)


# --------------------------------------------------------------------------- #
# vol_stretch — exact percentile mapping on constructed data                   #
# --------------------------------------------------------------------------- #
def test_stretch_known_percentiles_map_exactly():
    """The 101 values 0..100: with linear interpolation the p-th percentile is
    exactly p, so stretch(10, 90) maps 10 -> 0, 50 -> 0.5, 90 -> 1, and clips
    0 and 100."""
    v = np.arange(101, dtype=np.float64).reshape(1, 1, 101)
    lo, hi = np.percentile(v, [10.0, 90.0])
    assert lo == pytest.approx(10.0) and hi == pytest.approx(90.0)
    out = volgray.vol_stretch(v, p_low=10.0, p_high=90.0)
    # exact mapping of hand-picked values
    pick = lambda val: out[v == val]
    assert np.allclose(pick(10.0), 0.0)
    assert np.allclose(pick(50.0), 0.5)
    assert np.allclose(pick(90.0), 1.0)
    assert np.allclose(pick(0.0), 0.0)                # clipped below
    assert np.allclose(pick(100.0), 1.0)              # clipped above
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_stretch_outliers_are_clipped_not_dominant():
    """A single hot voxel must not compress the rest of the range (the whole
    point of a percentile stretch vs min/max normalisation)."""
    v = _rng(7).uniform(0.0, 1.0, size=(10, 10, 10))
    v[0, 0, 0] = 1e6                                  # metal-artefact voxel
    out = volgray.vol_stretch(v, p_low=1.0, p_high=99.0)
    assert out[0, 0, 0] == 1.0                        # clipped
    # the bulk still spans (almost) the full [0, 1]
    assert np.quantile(out, 0.5) == pytest.approx(0.5, abs=0.1)


def test_stretch_constant_passthrough_and_bad_percentiles():
    v = np.full((3, 3, 3), 42.0)
    assert np.array_equal(volgray.vol_stretch(v), v)
    w = np.zeros((3, 3, 3))
    with pytest.raises(ValueError, match="p_low"):
        volgray.vol_stretch(w, p_low=90.0, p_high=10.0)
    with pytest.raises(ValueError, match="p_low"):
        volgray.vol_stretch(w, p_low=50.0, p_high=50.0)
    with pytest.raises(ValueError, match="percentiles"):
        volgray.vol_stretch(w, p_low=-1.0, p_high=99.0)
    with pytest.raises(ValueError, match="percentiles"):
        volgray.vol_stretch(w, p_low=1.0, p_high=101.0)


# --------------------------------------------------------------------------- #
# shared fail-closed contracts                                                 #
# --------------------------------------------------------------------------- #
_ALL_OPS = [
    lambda v: volgray.vol_window_level(v, 0.0, 1.0),
    lambda v: volgray.vol_equalize(v),
    lambda v: volgray.vol_gamma(v, 2.0),
    lambda v: volgray.vol_stretch(v),
]


@pytest.mark.parametrize("op", _ALL_OPS)
def test_all_ops_reject_nan(op):
    v = np.zeros((4, 4, 4))
    v[1, 2, 3] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        op(v)


@pytest.mark.parametrize("op", _ALL_OPS)
def test_all_ops_reject_2d(op):
    with pytest.raises(ValueError, match="3-D"):
        op(np.zeros((8, 8)))


@pytest.mark.parametrize("op", _ALL_OPS)
def test_voxel_cap_is_enforced(op, monkeypatch):
    monkeypatch.setattr(volgray, "MAX_VOXELS", 10)
    with pytest.raises(ValueError, match="MAX_VOXELS"):
        op(np.zeros((3, 3, 3)))                       # 27 voxels > 10


def test_volgray_introspection_list_matches_module():
    for name in volgray.VOLGRAY_OPS:
        assert hasattr(volgray, name), name
        assert callable(getattr(volgray, name))
