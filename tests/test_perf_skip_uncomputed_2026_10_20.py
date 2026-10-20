import numpy as np
from scipy import linalg, sparse

import balltrack
import emproof
import roughness
import shapestats


def _old_fit_form(a, fx, fy, order):
    A, scale = roughness._form_basis(*a.shape, fx, fy, order)
    c, *_ = np.linalg.lstsq(A, a.ravel(), rcond=None)
    return a - (A @ c).reshape(a.shape), c * scale


def test_form_projection_agrees_with_old_lstsq():
    rng = np.random.default_rng(41)
    for n in (32, 128):
        a = rng.normal(size=(n, n + 3)) + np.arange(n + 3)[None, :] * 0.01
        for order in (1, 2):
            old_r, old_c = _old_fit_form(a, 0.17, 0.23, order)
            new_r, new_c = roughness._fit_form(a, 0.17, 0.23, order)
            np.testing.assert_allclose(new_c, old_c, rtol=1e-10, atol=1e-13)
            np.testing.assert_allclose(new_r, old_r, rtol=1e-10, atol=1e-12)


def test_ball_detect_agrees_with_full_image_reference():
    image = np.zeros((80, 90))
    image[10:16, 20:27] = 3.0
    image[45:55, 60:71] = 4.0
    got = balltrack.ball_detect(image, thresh=1.0, radius_range=(1.0, 20.0))
    assert len(got) == 2
    assert [v["area"] for v in got] == [110, 42]
    np.testing.assert_allclose([[v["col"], v["row"]] for v in got],
                               [[65.0, 49.5], [23.0, 12.5]])


def test_sparse_labels_do_not_allocate_by_maximum_id():
    labels = np.zeros((32, 32), np.int64)
    labels[:16] = 1
    labels[16:] = 100_000_000
    out = emproof.seg_inject_merge(labels, min_area=100, seed=0)
    assert set(np.unique(out)).issubset({1, 100_000_000})


def test_generalized_procrustes_matches_old_loop():
    x = shapestats.shape_synth_family(5, 20, seed=8)
    old = x.copy()
    ref = x[0]
    prev = None
    for _ in range(100):
        for i in range(len(x)):
            old[i] = shapestats.procrustes_align(x[i], ref)
        mean = shapestats.procrustes_align(old.mean(0), x[0])
        if prev is not None and np.sqrt(np.mean(np.sum((mean - prev) ** 2, axis=1))) <= 1e-10:
            ref = mean
            break
        prev, ref = mean, mean
    for i in range(len(x)):
        old[i] = shapestats.procrustes_align(x[i], ref)
    np.testing.assert_allclose(shapestats.generalized_procrustes(x), old,
                               rtol=1e-12, atol=1e-12)


def test_symmetric_spline_band_matches_general_solver():
    n = 80
    w = np.linspace(0.2, 1.0, n)
    d = sparse.diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(n - 2, n))
    p = (d.T @ d).tocsr()
    band = np.zeros((5, n))
    for k in range(-2, 3):
        dg = p.diagonal(k)
        band[2 - k, k:] = dg if k >= 0 else band[2 - k, k:]
        if k < 0:
            band[2 - k, :n + k] = dg
    band[2] += w
    rhs = w * np.sin(np.arange(n) / 7)
    old = linalg.solve_banded((2, 2), band, rhs)
    new = linalg.solveh_banded(band[:3], rhs)
    np.testing.assert_allclose(new, old, rtol=1e-10, atol=1e-12)
