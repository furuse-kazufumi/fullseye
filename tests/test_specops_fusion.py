"""Ground-truth tests for the specops **fusion** additions.

Covers the three purely additive functions:

* :func:`specops.spec_pansharpen`          — Brovey / generalised IHS / PC1 substitution
* :func:`specops.spec_decorrelation_stretch` — Gillespie et al. 1986 decorrelation stretch
* :func:`specops.spec_fuse`                — pixel-level PCA / average / choose-max fusion

Every check recomputes the named algorithm's defining property **independently**
(band ratios, the intensity identity, the output covariance, the PCA weights) rather
than merely running the function: a Brovey fusion that did not preserve band ratios,
an IHS fusion whose band mean is not the pan band, a decorrelation stretch whose
output is not white, or a PCA fusion with different weights all fail here.

The file also pins the additive-only promise: the module still imports, the
pre-existing ``spec_*`` functions still exist and still return their documented
analytic answers, and the new names are advertised in ``__all__`` / ``SPECTRALOPS``.
"""
import inspect

import numpy as np
import pytest

import specops as sp


# --------------------------------------------------------------------------- #
# deterministic inputs                                                        #
# --------------------------------------------------------------------------- #
def _cube(H=12, W=15, B=6, seed=7):
    """A positive, non-degenerate (H, W, B) cube (B != 3, so it is a valid cube)."""
    rng = np.random.default_rng(seed)
    return 0.2 + 0.8 * rng.random((H, W, B))


def _pan(H=12, W=15, seed=11):
    rng = np.random.default_rng(seed)
    return 0.1 + 0.9 * rng.random((H, W))


def _correlated_cube(H=16, W=20, B=5, seed=3):
    """Strongly (but not perfectly) correlated bands: a shared brightness term plus
    a small independent per-band term — full rank, and heavily off-diagonal."""
    rng = np.random.default_rng(seed)
    base = rng.random((H, W))
    return np.stack([base + 0.05 * (i + 1) * rng.random((H, W)) for i in range(B)], -1)


def _max_offdiag_corr(stack3d):
    """Largest |correlation| between two distinct channels of an (H, W, K) stack."""
    X = stack3d.reshape(-1, stack3d.shape[2])
    C = np.corrcoef(X.T)
    K = C.shape[0]
    return float(np.max(np.abs(C[~np.eye(K, dtype=bool)])))


# --------------------------------------------------------------------------- #
# additive-only promise: module imports, old surface intact, new names present #
# --------------------------------------------------------------------------- #
_PRE_EXISTING = (
    "BandMeta", "read_envi", "write_envi", "spec_band", "spec_rgb_composite",
    "spec_nearest_band", "spec_band_ratio", "spec_index", "spec_angle_mapper",
    "spec_pca", "spec_mnf", "spec_unmix", "spec_endmembers_ppi",
    "spec_continuum_removal", "SPECTRALOPS", "MAX_VOXELS", "MAX_FILE_BYTES",
    "MAX_BANDS",
)
_NEW = ("spec_pansharpen", "spec_decorrelation_stretch", "spec_fuse")


def test_specops_still_imports_with_its_whole_prior_surface():
    for name in _PRE_EXISTING:
        assert hasattr(sp, name), "specops lost %s" % name
        assert name in sp.__all__, "%s dropped out of specops.__all__" % name


def test_new_fusion_names_are_advertised():
    for name in _NEW:
        assert callable(getattr(sp, name)), name
        assert name in sp.__all__, "%s missing from specops.__all__" % name
        assert name in sp.SPECTRALOPS, "%s missing from specops.SPECTRALOPS" % name
    # the introspection contract the existing suite relies on still holds
    for name in sp.SPECTRALOPS:
        assert callable(getattr(sp, name)), name


def test_existing_functions_still_return_their_analytic_answers():
    """A couple of pre-existing ops, re-anchored — proof the edit was additive."""
    b0 = np.full((5, 5), 0.25)
    b1 = np.full((5, 5), 0.75)
    cube = np.stack([b0, b1], -1)                        # a valid 2-band cube
    assert np.allclose(sp.spec_index(cube, 1, 0), (0.75 - 0.25) / (0.75 + 0.25))
    assert np.allclose(sp.spec_band_ratio(cube, 1, 0), 3.0)
    assert np.array_equal(sp.spec_band(cube, 0), b0)
    # SAM: a pixel parallel to the reference has angle 0, an orthogonal one pi/2
    c4 = np.zeros((2, 2, 4))
    c4[0, 0] = [1.0, 0.0, 0.0, 0.0]
    c4[0, 1] = [0.0, 1.0, 0.0, 0.0]
    ang = sp.spec_angle_mapper(c4, np.array([2.0, 0.0, 0.0, 0.0]))
    assert np.isclose(ang[0, 0], 0.0)
    assert np.isclose(ang[0, 1], np.pi / 2)


def test_new_functions_contain_no_rng_anywhere():
    """Determinism at the source level: none of the new code may touch an RNG."""
    for name in _NEW + ("_as_pan", "_as_stack", "_pca_basis", "_canonical_signs",
                        "_match_ranks_to", "_select_bands", "_finite_or_raise"):
        src = inspect.getsource(getattr(sp, name))
        assert "random" not in src, "%s reaches for an RNG" % name
        assert "shuffle" not in src and "permutation" not in src, name


# --------------------------------------------------------------------------- #
# spec_pansharpen — Brovey                                                    #
# --------------------------------------------------------------------------- #
def test_brovey_matches_the_published_formula_and_shape():
    cube, pan = _cube(), _pan()
    fused = sp.spec_pansharpen(cube, pan, method="brovey")
    assert fused.shape == cube.shape
    assert fused.dtype == np.float64
    # independent recomputation of fused_i = cube_i * pan / mean_over_bands(cube)
    ref = cube * (pan / cube.mean(axis=2))[:, :, None]
    assert np.allclose(fused, ref, rtol=1e-12, atol=0.0)
    assert np.isfinite(fused).all()


def test_brovey_preserves_every_band_ratio():
    """The defining property of the chromaticity/Brovey transform: all bands are
    scaled by the *same* per-pixel factor, so fused_i/fused_j == cube_i/cube_j."""
    cube, pan = _cube(B=6), _pan()
    fused = sp.spec_pansharpen(cube, pan, method="brovey")
    B = cube.shape[2]
    for i in range(B):
        for j in range(B):
            if i == j:
                continue
            assert np.allclose(fused[:, :, i] / fused[:, :, j],
                               cube[:, :, i] / cube[:, :, j],
                               rtol=1e-12, atol=0.0), (i, j)
    # ... and the fusion genuinely injected the pan detail (it is not a no-op)
    assert not np.allclose(fused, cube)


def test_brovey_is_deterministic():
    cube, pan = _cube(), _pan()
    a = sp.spec_pansharpen(cube, pan, method="brovey")
    b = sp.spec_pansharpen(cube, pan, method="brovey")
    assert np.array_equal(a, b)                          # bit-identical


def test_brovey_survives_a_zero_band_mean():
    """A pixel whose bands sum to zero must not produce inf/NaN (guarded denominator)."""
    cube = np.zeros((4, 4, 5))
    cube[1, 1] = [1.0, -1.0, 0.5, -0.5, 0.0]             # mean exactly 0
    fused = sp.spec_pansharpen(cube, np.ones((4, 4)), method="brovey")
    assert np.isfinite(fused).all()


# --------------------------------------------------------------------------- #
# spec_pansharpen — generalised IHS                                            #
# --------------------------------------------------------------------------- #
def test_ihs_replaces_the_intensity_with_the_pan_band():
    """Tu et al. 2001: with I = mean over bands, the fused intensity *is* the pan."""
    cube, pan = _cube(B=5), _pan()
    fused = sp.spec_pansharpen(cube, pan, method="ihs")
    assert fused.shape == cube.shape
    assert np.allclose(fused.mean(axis=2), pan, rtol=0.0, atol=1e-12)
    # independent recomputation of the additive form
    ref = cube + (pan - cube.mean(axis=2))[:, :, None]
    assert np.allclose(fused, ref, rtol=1e-12, atol=0.0)


def test_ihs_preserves_every_band_difference():
    """The injection is additive and identical across bands, so band *differences*
    (the complement of the ratio property Brovey has) are untouched."""
    cube, pan = _cube(B=4), _pan()
    fused = sp.spec_pansharpen(cube, pan, method="ihs")
    for i in range(4):
        for j in range(4):
            assert np.allclose(fused[:, :, i] - fused[:, :, j],
                               cube[:, :, i] - cube[:, :, j], atol=1e-12), (i, j)


def test_ihs_is_deterministic():
    cube, pan = _cube(), _pan()
    assert np.array_equal(sp.spec_pansharpen(cube, pan, method="ihs"),
                          sp.spec_pansharpen(cube, pan, method="ihs"))


# --------------------------------------------------------------------------- #
# spec_pansharpen — PC1 substitution                                           #
# --------------------------------------------------------------------------- #
def _pca_frame(cube):
    """Independent PCA of the cube: (mean, V columns ordered by descending eigenvalue).

    The eigenvector signs are whatever LAPACK returns here — every assertion below
    is written to be invariant to that choice.
    """
    X = cube.reshape(-1, cube.shape[2])
    mean = X.mean(axis=0)
    cov = np.cov(X.T, ddof=1)
    evals, V = np.linalg.eigh(cov)
    order = np.argsort(evals)[::-1]
    return mean, V[:, order]


def test_pca_pansharpen_replaces_pc1_only():
    cube, pan = _correlated_cube(), _pan(16, 20, seed=5)
    fused = sp.spec_pansharpen(cube, pan, method="pca")
    assert fused.shape == cube.shape

    mean, V = _pca_frame(cube)
    B = cube.shape[2]
    o = (cube.reshape(-1, B) - mean) @ V                 # original scores
    f = (fused.reshape(-1, B) - mean) @ V                # fused scores, same frame

    # components 2..B pass through *exactly* (sign-invariant: both use the same V)
    for k in range(1, B):
        assert np.allclose(f[:, k], o[:, k], atol=1e-9), "PC%d was disturbed" % (k + 1)
    # PC1 was actually replaced
    assert not np.allclose(f[:, 0], o[:, 0])


def test_pca_pansharpen_pc1_is_the_pan_histogram_matched_to_pc1():
    cube, pan = _correlated_cube(), _pan(16, 20, seed=5)
    fused = sp.spec_pansharpen(cube, pan, method="pca")
    mean, V = _pca_frame(cube)
    B = cube.shape[2]
    o1 = ((cube.reshape(-1, B) - mean) @ V)[:, 0]
    f1 = ((fused.reshape(-1, B) - mean) @ V)[:, 0]

    # (a) the injected component carries PC1's own radiometry: identical histogram
    assert np.allclose(np.sort(f1), np.sort(o1), atol=1e-9)
    # (b) ... and the pan band's spatial ordering (up to the eigenvector's sign,
    #     which reverses every rank)
    r_f = np.argsort(np.argsort(f1, kind="stable"), kind="stable")
    r_p = np.argsort(np.argsort(pan.reshape(-1), kind="stable"), kind="stable")
    n = r_p.size
    assert np.array_equal(r_f, r_p) or np.array_equal(r_f, n - 1 - r_p)


def test_pca_pansharpen_preserves_the_scene_mean_and_is_deterministic():
    cube, pan = _correlated_cube(), _pan(16, 20, seed=5)
    fused = sp.spec_pansharpen(cube, pan, method="pca")
    # histogram matching permutes PC1's values, so the per-band means are unchanged
    assert np.allclose(fused.reshape(-1, cube.shape[2]).mean(axis=0),
                       cube.reshape(-1, cube.shape[2]).mean(axis=0), atol=1e-9)
    assert np.array_equal(fused, sp.spec_pansharpen(cube, pan, method="pca"))


# --------------------------------------------------------------------------- #
# spec_pansharpen — fail-closed                                                #
# --------------------------------------------------------------------------- #
def test_pansharpen_is_fail_closed():
    cube, pan = _cube(), _pan()
    with pytest.raises(ValueError, match="not one of"):
        sp.spec_pansharpen(cube, pan, method="nope")
    with pytest.raises(ValueError, match="common grid"):
        sp.spec_pansharpen(cube, np.zeros((5, 5)))
    with pytest.raises(ValueError, match="2-D"):
        sp.spec_pansharpen(cube, np.zeros(cube.shape))
    bad = _pan(); bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        sp.spec_pansharpen(cube, bad)
    with pytest.raises(ValueError, match="color"):        # 3 channels is RGB, not a cube
        sp.spec_pansharpen(np.zeros((12, 15, 3)), pan)


# --------------------------------------------------------------------------- #
# spec_decorrelation_stretch                                                   #
# --------------------------------------------------------------------------- #
def test_dcs_whitens_the_band_covariance():
    """Gillespie 1986: rotate to the principal axes, give every axis the same
    standard deviation, rotate back. The output covariance must therefore be
    *exactly* ``target_std**2 * I`` — recomputed here from scratch."""
    cube = _correlated_cube()
    k = cube.shape[2]
    X = cube.reshape(-1, k)
    s_ref = float(np.mean(np.std(X, axis=0, ddof=1)))    # the documented default target

    out = sp.spec_decorrelation_stretch(cube)
    assert out.shape == cube.shape
    assert np.isfinite(out).all()

    C = np.cov(out.reshape(-1, k).T, ddof=1)
    assert np.allclose(C, (s_ref ** 2) * np.eye(k), atol=1e-9), C
    # per-axis variance really is the target, not an accident of scaling
    assert np.allclose(np.sqrt(np.diag(C)), s_ref, rtol=1e-9)


def test_dcs_reduces_the_worst_band_correlation():
    cube = _correlated_cube()
    before = _max_offdiag_corr(cube)
    after = _max_offdiag_corr(sp.spec_decorrelation_stretch(cube))
    assert before > 0.5, before                          # the input really is correlated
    assert after < before                                # ... and the stretch decorrelates
    assert after < 1e-6, after                           # to numerical zero, in fact


def test_dcs_preserves_the_band_means():
    cube = _correlated_cube()
    out = sp.spec_decorrelation_stretch(cube)
    assert np.allclose(out.reshape(-1, cube.shape[2]).mean(axis=0),
                       cube.reshape(-1, cube.shape[2]).mean(axis=0), atol=1e-9)


def test_dcs_honours_an_explicit_target_std():
    cube = _correlated_cube()
    out = sp.spec_decorrelation_stretch(cube, target_std=0.25)
    C = np.cov(out.reshape(-1, cube.shape[2]).T, ddof=1)
    assert np.allclose(C, 0.0625 * np.eye(cube.shape[2]), atol=1e-9)


def test_dcs_handles_a_fully_correlated_cube_without_nan():
    """All bands identical => the covariance is rank 1 and every other eigenvalue is
    numerically zero. The degenerate directions must be zeroed, not divided by ~0."""
    base = np.linspace(0.0, 1.0, 16 * 20).reshape(16, 20)
    cube = np.stack([base] * 5, axis=-1)                 # zero off-diagonal *variance*
    out = sp.spec_decorrelation_stretch(cube)
    assert out.shape == cube.shape
    assert np.isfinite(out).all()
    assert not np.isnan(out).any()
    assert np.array_equal(out, sp.spec_decorrelation_stretch(cube))   # deterministic
    # the one real axis is still stretched to the target std
    s_ref = float(np.mean(np.std(cube.reshape(-1, 5), axis=0, ddof=1)))
    assert np.isclose(float(np.std(out[:, :, 0], ddof=1)), s_ref, rtol=1e-9)


def test_dcs_on_a_constant_cube_is_finite():
    cube = np.full((6, 6, 4), 0.42)
    out = sp.spec_decorrelation_stretch(cube)
    assert np.isfinite(out).all()
    assert np.allclose(out, 0.42)                        # nothing to stretch


def test_dcs_is_deterministic():
    cube = _correlated_cube()
    assert np.array_equal(sp.spec_decorrelation_stretch(cube),
                          sp.spec_decorrelation_stretch(cube))


def test_dcs_band_subset_leaves_the_other_bands_bit_identical():
    cube = _correlated_cube(B=6)
    out = sp.spec_decorrelation_stretch(cube, bands=[0, 2, 4])
    assert out.shape == cube.shape
    for j in (1, 3, 5):
        assert np.array_equal(out[:, :, j], cube[:, :, j]), j
    for j in (0, 2, 4):
        assert not np.allclose(out[:, :, j], cube[:, :, j]), j
    # the selected sub-cube is whitened among itself
    sub = out[:, :, [0, 2, 4]]
    C = np.cov(sub.reshape(-1, 3).T, ddof=1)
    off = C[~np.eye(3, dtype=bool)]
    assert np.allclose(off, 0.0, atol=1e-9)


def test_dcs_is_fail_closed():
    cube = _correlated_cube()
    with pytest.raises(ValueError, match="at least 2 bands"):
        sp.spec_decorrelation_stretch(cube, bands=[1])
    with pytest.raises(ValueError, match="repeats"):
        sp.spec_decorrelation_stretch(cube, bands=[1, 1, 2])
    with pytest.raises(ValueError, match="out of range"):
        sp.spec_decorrelation_stretch(cube, bands=[0, 99])
    with pytest.raises(ValueError, match="target_std"):
        sp.spec_decorrelation_stretch(cube, target_std=0.0)
    with pytest.raises(ValueError, match="color"):
        sp.spec_decorrelation_stretch(np.zeros((8, 8, 3)))


# --------------------------------------------------------------------------- #
# spec_fuse                                                                    #
# --------------------------------------------------------------------------- #
def _sources(seed=21):
    rng = np.random.default_rng(seed)
    base = rng.random((14, 18))
    return [base, base + 0.1 * rng.random((14, 18)), base * 0.8 + 0.2]


@pytest.mark.parametrize("method", ["pca", "average", "max_abs_detail"])
def test_fuse_of_identical_copies_returns_that_image(method):
    """The invariance every fusion rule owes: nothing to choose between two identical
    sources, so the fused image *is* the source."""
    rng = np.random.default_rng(4)
    img = 0.2 + 0.6 * rng.random((14, 18))
    fused = sp.spec_fuse([img, img.copy()], method=method)
    assert fused.shape == img.shape
    assert fused.dtype == np.float64
    if method == "average":
        assert np.array_equal(fused, img)                # exact, bit for bit
    else:
        assert np.allclose(fused, img, rtol=1e-9, atol=1e-12)


@pytest.mark.parametrize("method", ["pca", "average", "max_abs_detail"])
def test_fuse_shape_and_determinism(method):
    srcs = _sources()
    a = sp.spec_fuse(srcs, method=method)
    b = sp.spec_fuse(srcs, method=method)
    assert a.shape == (14, 18)
    assert np.array_equal(a, b)                          # bit-identical
    assert np.isfinite(a).all()
    # the (H, W, K) array form must agree with the list form
    assert np.array_equal(a, sp.spec_fuse(np.stack(srcs, -1), method=method))


def test_fuse_average_is_the_arithmetic_mean():
    srcs = _sources()
    assert np.allclose(sp.spec_fuse(srcs, method="average"),
                       (srcs[0] + srcs[1] + srcs[2]) / 3.0, rtol=0.0, atol=1e-15)


def test_fuse_pca_weights_match_an_independent_pc1_computation():
    """Recompute the PC1 loadings of the source covariance from scratch and rebuild
    the weighted sum: the sum-to-one normalisation makes the weights independent of
    the eigenvector sign, so this is an exact cross-check."""
    srcs = _sources()
    S = np.stack(srcs, -1)
    X = S.reshape(-1, S.shape[2])
    evals, V = np.linalg.eigh(np.cov(X.T, ddof=1))
    v = V[:, int(np.argmax(evals))]
    w = v / v.sum()
    ref = (S * w).sum(axis=2)
    assert np.allclose(sp.spec_fuse(srcs, method="pca"), ref, rtol=1e-12, atol=1e-15)
    assert np.isclose(w.sum(), 1.0)


def test_fuse_pca_differs_from_the_flat_average_on_unequal_sources():
    srcs = _sources()
    assert not np.allclose(sp.spec_fuse(srcs, method="pca"),
                           sp.spec_fuse(srcs, method="average"))


def test_fuse_max_abs_detail_picks_the_locally_sharper_source():
    """Multi-focus ground truth: two frames of the same ramp, each sharp in a
    different quadrant. The fused image must take each patch from the frame that is
    in focus there, and must *select* (never blend) everywhere."""
    n = 32
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    base = 0.2 + 0.3 * xx / (n - 1)                      # smooth: no high-pass detail
    checker = ((xx.astype(int) + yy.astype(int)) % 2) * 0.2
    a = base.copy(); a[6:15, 6:15] += checker[6:15, 6:15]     # sharp top-left
    b = base.copy(); b[18:27, 18:27] += checker[18:27, 18:27]  # sharp bottom-right

    fused = sp.spec_fuse([a, b], method="max_abs_detail")
    assert fused.shape == (n, n)
    # inside each sharp patch (eroded by the filter half-width) the sharp frame wins
    assert np.array_equal(fused[8:13, 8:13], a[8:13, 8:13])
    assert np.array_equal(fused[20:25, 20:25], b[20:25, 20:25])
    # far from both patches the frames agree, and the fusion is the common value
    assert np.array_equal(fused[0:4, 20:24], base[0:4, 20:24])
    # a selection rule never invents a value
    assert np.all((fused == a) | (fused == b))


def test_fuse_max_abs_detail_window_is_validated():
    srcs = _sources()
    with pytest.raises(ValueError, match="odd integer"):
        sp.spec_fuse(srcs, method="max_abs_detail", detail_size=4)
    with pytest.raises(ValueError, match="odd integer"):
        sp.spec_fuse(srcs, method="max_abs_detail", detail_size=1)
    out = sp.spec_fuse(srcs, method="max_abs_detail", detail_size=5)
    assert out.shape == (14, 18) and np.isfinite(out).all()


def test_fuse_single_source_is_the_identity():
    rng = np.random.default_rng(9)
    img = rng.random((7, 9))
    for method in ("pca", "average", "max_abs_detail"):
        assert np.allclose(sp.spec_fuse([img], method=method), img, atol=1e-12), method


def test_fuse_accepts_an_hwk_array_including_three_sources():
    """(H, W, 3) is refused as a *cube* but is a legal 3-source stack here — the
    parameter is a stack of co-registered images, not a spectral cube."""
    S = np.stack(_sources(), -1)
    assert S.shape[2] == 3
    fused = sp.spec_fuse(S, method="average")
    assert np.allclose(fused, S.mean(axis=2))
    with pytest.raises(ValueError):                      # ... while a cube still refuses it
        sp._as_cube(S)


def test_fuse_is_fail_closed():
    with pytest.raises(ValueError, match="empty"):
        sp.spec_fuse([])
    with pytest.raises(ValueError, match="co-registered"):
        sp.spec_fuse([np.zeros((4, 4)), np.zeros((5, 4))])
    with pytest.raises(ValueError, match="2-D"):
        sp.spec_fuse([np.zeros((4, 4, 2))])
    with pytest.raises(ValueError, match=r"\(H, W, K\)"):
        sp.spec_fuse(np.zeros((4, 4)))
    with pytest.raises(ValueError, match="non-finite"):
        sp.spec_fuse([np.zeros((4, 4)), np.full((4, 4), np.nan)])
    with pytest.raises(ValueError, match="not one of"):
        sp.spec_fuse(_sources(), method="wavelet")
