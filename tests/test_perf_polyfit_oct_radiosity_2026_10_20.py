"""Performance slice 16: exactness gates against the former implementations."""
import warnings

import numpy as np
import pytest

import mathops as M
import octscan as O
import radiosity3d as R


def _old_poly(x, y, degree):
    xs, ys = M._require_nodes(x, y, "poly_fit", 1)
    V = np.vander(xs, degree + 1)
    sv = np.linalg.svd(V, compute_uv=False)
    cond = float("inf") if float(sv[-1]) <= 0 else float(sv[0] / sv[-1])
    if cond > M.POLY_COND_WARN:
        warnings.warn("ill conditioned", RuntimeWarning, stacklevel=2)
    coeffs = np.linalg.lstsq(V, ys, rcond=None)[0]
    return coeffs, cond


@pytest.mark.parametrize("degree", range(9))
def test_poly_fit_one_decomposition_and_old_agreement(monkeypatch, degree):
    x = np.linspace(-1.3, 2.1, 24)
    y = np.sin(x) + 0.01 * x
    old_c, old_cond = _old_poly(x, y, degree)
    calls = 0
    original = np.linalg.lstsq

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(np.linalg, "lstsq", counted)
    got = M.poly_fit(x, y, degree)
    assert calls == 1
    np.testing.assert_allclose(got["coeffs"], old_c, rtol=1e-10, atol=1e-13)
    assert got["cond"] == pytest.approx(old_cond, rel=1e-10)


def test_poly_fit_duplicate_x_rejection_and_warning_match_old():
    x = np.ones(12)
    y = np.arange(12.0)
    with pytest.raises(ValueError, match="strictly increasing"):
        _old_poly(x, y, 3)
    with pytest.raises(ValueError, match="strictly increasing"):
        M.poly_fit(x, y, 3)
    x = np.linspace(1e6, 1e6 + 1, 20)
    y = np.arange(20.0)
    with pytest.warns(RuntimeWarning):
        old_c, old_cond = _old_poly(x, y, 8)
    with pytest.warns(RuntimeWarning):
        got = M.poly_fit(x, y, 8)
    np.testing.assert_allclose(got["coeffs"], old_c, rtol=1e-10, atol=1e-13)
    assert got["cond"] == pytest.approx(old_cond, rel=1e-10)


def _old_jump(prev, J, penalty):
    n = len(prev)
    best, arg = np.full(n, np.inf), np.zeros(n, np.int32)
    idx = np.arange(n)
    for d in range(-J, J + 1):
        src = idx - d
        ok = (src >= 0) & (src < n)
        v = np.full(n, np.inf)
        v[ok] = prev[src[ok]] + penalty * abs(d)
        take = v < best
        best[take], arg[take] = v[take], src[take]
    return best, arg


@pytest.mark.parametrize("J", [2, 8, 32, 128])
@pytest.mark.parametrize("penalty", [0.0, 0.37])
def test_oct_linear_transition_is_bit_identical_including_plateau_ties(J, penalty):
    prev = np.r_[np.full(40, 3.0), np.arange(80) % 7, np.full(40, -2.0)]
    expected = _old_jump(prev, J, penalty)
    actual = O._jump_min_linear(prev, J, penalty)
    np.testing.assert_allclose(actual[0], expected[0], rtol=1e-14, atol=1e-14)
    np.testing.assert_array_equal(actual[1], expected[1])


@pytest.mark.parametrize("J", [8, 32, 128])
@pytest.mark.parametrize("reference", [False, True])
def test_oct_boundary_paths_match_old_with_plateaus(monkeypatch, J, reference):
    image = np.zeros((160, 48), float)
    image[45:48] = 5.0
    image[90:93] = 4.0
    kw = dict(n_boundaries=1, max_jump_px=J, jump_penalty=0.37, smooth_sigma=0)
    if reference:
        kw.update(reference_rows=np.full(48, 40.0), offset_px=(0, 80))
    actual = O.oct_bscan_boundaries(image, **kw)
    monkeypatch.setattr(O, "_jump_min_linear", _old_jump)
    expected = O.oct_bscan_boundaries(image, **kw)
    np.testing.assert_array_equal(actual["rows"], expected["rows"])


def test_radiosity_block_candidates_and_matrix_match_old():
    polys = np.array([
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        [[0, 1, 1], [1, 1, 1], [1, 0, 1], [0, 0, 1]],
        [[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]],
    ], float)
    patches = R.radiosity_patches(polygons=polys)
    p = patches
    old_candidates = R._candidates(p["polygons"], p["normals"], 1e-12)
    old_ff = R._candidates
    try:
        # Reconstruct the former matrix path by forcing the full candidate array.
        def full(*args):
            return old_candidates
        R._candidates = full
        expected = _old_ff_matrix(p, old_candidates)
    finally:
        R._candidates = old_ff
    actual = R.form_factor_matrix(p, n_quad=2, symmetric=False, far_ratio=None)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(actual.sum(1), expected.sum(1), rtol=0, atol=1e-14)


def _old_ff_matrix(p, candidates):
    polys, normals, areas, centers = (p[k] for k in ("polygons", "normals", "areas", "centers"))
    I, J = np.nonzero(candidates)
    F = np.zeros((len(polys), len(polys)))
    xq, wq = R._quad_points(polys, 2)
    eps = 1e-12 * max(1.0, float(np.abs(polys).max()))
    F[I, J] = R._ff_pairs(xq[I], normals[I], wq[I], areas[I], polys[J], centers[J], normals[J], None, eps)
    return F
