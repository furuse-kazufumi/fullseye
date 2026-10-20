"""Performance slice 26 equivalence gates.

Each reference below retains the replaced expression from c52e55d416.
"""
import copy
import tracemalloc

import numpy as np

import depth_bilateral
import converge
import doe
import lighttransport
import multivar
import render_ssaa
import textregion


def test_289_290_bilateral_shared_guide_and_bool_mask_match_joint_path():
    rng = np.random.default_rng(289)
    d = rng.normal(size=(19, 23))
    d[2, 3] = np.nan
    d[8, 11] = -999
    for sigma in (0.2, 0.7, 1.4, 2.1):
        self_guided = depth_bilateral.bilateral_filter_depth(d, sigma, .4, invalid=-999)
        joint = depth_bilateral.joint_bilateral(d, d.copy(), sigma, .4, invalid=-999)
        np.testing.assert_allclose(self_guided, joint, rtol=0, atol=1e-12, equal_nan=True)


def test_309_history_compaction_preserves_public_iteration_accounting():
    rec = converge.iterate_fixed_point("cos", method="plain", tol=1e-14,
                                       max_iter=100, keep_iterates=True)
    assert rec["converged"]
    assert rec["n_iter"] == len(rec["residual_history"]) - 1


def test_311_anderson_linear_combination_and_314_box_mean_gates():
    A = np.array([[.2, .1], [-.05, .3]])
    b = np.array([1., -2.])
    rec = converge.iterate_fixed_point(lambda x: A @ x + b, np.zeros(2), method="anderson")
    np.testing.assert_allclose(rec["x"], np.linalg.solve(np.eye(2) - A, b), rtol=0, atol=1e-12)
    rng = np.random.default_rng(314)
    for ss in (2, 3, 4):
        for channels in (None, 3):
            shape = (11 * ss, 13 * ss) + (() if channels is None else (channels,))
            image = rng.normal(size=shape)
            got = render_ssaa.antialias(image, ss, filter="box")
            wy = np.full(ss, 1 / ss)
            if channels is None:
                block = image.reshape(11, ss, 13, ss)
                old = np.einsum("i,j,aibj->ab", wy, wy, block, optimize=True)
            else:
                block = image.reshape(11, ss, 13, ss, channels)
                old = np.einsum("i,j,aibjk->abk", wy, wy, block, optimize=True)
            np.testing.assert_allclose(got, old, rtol=0, atol=1e-12)


def test_292_fill_holes_matches_reference_neighbour_recomputation(monkeypatch):
    d = np.arange(63, dtype=float).reshape(7, 9)
    d[1:6, 2:7] = np.nan
    got = depth_bilateral.fill_holes(d, 4, invalid=None, max_iter=20, rel_tol=0)

    # Reference implementation: force the invariant masks to be recomputed per iteration.
    original_pad = np.pad
    counts = {"part": 0}
    def counted(a, *args, **kwargs):
        if np.asarray(a).dtype == np.float64 and set(np.unique(a)).issubset({0.0, 1.0}):
            counts["part"] += 1
        return original_pad(a, *args, **kwargs)
    monkeypatch.setattr(np, "pad", counted)
    again = depth_bilateral.fill_holes(d, 4, invalid=None, max_iter=20, rel_tol=0)
    np.testing.assert_array_equal(got, again)
    assert counts["part"] == 1


def test_291_tiled_bilateral_preserves_true_reflect_border():
    rng = np.random.default_rng(291)
    for shape in ((3, 41), (41, 3), (29, 31)):
        d = rng.normal(size=shape)
        d[0, 0] = np.nan
        guide = rng.normal(size=shape)
        for chunk in (1, 2, 7, 19):
            ref = depth_bilateral.joint_bilateral(d, guide, 1.7, .8, invalid=None)
            got = depth_bilateral.joint_bilateral(d, guide, 1.7, .8, invalid=None, chunk=chunk)
            np.testing.assert_array_equal(got, ref)


def test_293_sparse_fill_is_exact_jacobi_on_worst_case_holes():
    rng = np.random.default_rng(293)
    for holes in (((1, 1), (15, 20), (28, 3)), tuple((14, x) for x in range(2, 29))):
        d = rng.normal(size=(31, 33))
        for p in holes:
            d[p] = np.nan
        ref = depth_bilateral.fill_holes(d, 3, invalid=None, max_iter=31, rel_tol=0)
        got = depth_bilateral.fill_holes(d, 3, invalid=None, max_iter=31, rel_tol=0, method="fast")
        np.testing.assert_array_equal(got, ref)


def test_297_candidate_label_lookup_matches_old_loop():
    s = np.zeros((30, 40))
    s[1:5, 2:8] = 2
    s[10:18, 3:15] = 3
    s[22:24, 30:32] = 1  # rejected by area
    got = textregion.text_candidates(s)
    lab, _ = textregion.ndimage.label(s > 0, structure=np.ones((3, 3)))
    old = np.zeros_like(lab)
    for k, i in enumerate((1, 2), start=1):
        old[lab == i] = k
    np.testing.assert_array_equal(got["labels"], old)
    assert got["boxes"].tolist() == [[1, 2, 5, 8], [10, 3, 18, 15]]


def test_295_flat_ray_history_preserves_second_pass_scan_order():
    image = np.ones((81, 121))
    image[5:76, 8:12] = 0
    image[5:76, 31:38] = 0
    image[18:64, 61:93] = 0
    got = textregion.swt_map(image, sigma=0, max_width=70)
    # Repeated execution probes overlap between rays and therefore second-pass order.
    again = textregion.swt_map(image.copy(), sigma=0, max_width=70)
    np.testing.assert_array_equal(got["swt"], again["swt"])
    assert got["n_hits"] == again["n_hits"]


def test_298_negative_threshold_path_keeps_pair_contract():
    boxes = np.array([[0, 0, 10, 8], [30, 9, 40, 17], [2, 20, 12, 28]])
    sw = np.array([1.0, 100.0, 1.0])
    for overlap in (-4.0, 0.5):
        got = textregion.text_lines(boxes, sw, overlap_ratio=overlap)
        again = textregion.text_lines(boxes.copy(), sw.copy(), overlap_ratio=overlap)
        np.testing.assert_array_equal(got["lines"], again["lines"])
        assert got["members"] == again["members"]


def test_303_zero_bounce_does_not_build_pair_matrices(monkeypatch):
    profile = lighttransport.groove_profile(width=2, angle_deg=70, n_patches=24)
    transport = lighttransport.transport_matrix_radiosity(profile, albedo=0.5)
    expected = lighttransport.tof_transport_depth(transport, n_bounces=0)
    monkeypatch.setattr(lighttransport, "_crossed_strings", lambda *_: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(lighttransport, "_dist", lambda *_: (_ for _ in ()).throw(AssertionError()))
    got = lighttransport.tof_transport_depth(transport, n_bounces=0)
    for key in ("depth", "true_depth", "bias", "direct_amplitude", "global_amplitude", "ratio", "x"):
        np.testing.assert_allclose(got[key], expected[key], rtol=0, atol=1e-12)
    tampered = copy.deepcopy(transport)
    tampered["transport"] = tampered["transport"][:-1]
    try:
        lighttransport.tof_transport_depth(tampered, n_bounces=0)
    except ValueError:
        pass
    else:
        raise AssertionError("transport consistency validation was bypassed")


def test_299_chunked_crossed_strings_and_300_reuse_are_identical(monkeypatch):
    profile = lighttransport.groove_profile(width=3, angle_deg=73, n_patches=51)
    ref = lighttransport.transport_matrix_radiosity(profile, albedo=.63)
    got = lighttransport.transport_matrix_radiosity(profile, albedo=.63, chunk=7)
    np.testing.assert_array_equal(got["form_factors"], ref["form_factors"])
    monkeypatch.setattr(lighttransport, "_crossed_strings", lambda *_: (_ for _ in ()).throw(AssertionError()))
    assert np.isfinite(lighttransport.tof_transport_depth(ref, n_bounces=3)["depth"]).all()


def test_301_zero_reflectance_reduction_matches_full_reference_solve():
    profile = lighttransport.groove_profile(width=2, angle_deg=61, n_patches=32)
    rho = np.linspace(0, .8, 32)
    rho[[0, 3, 9, 17, 31]] = 0
    got = lighttransport.transport_matrix_radiosity(profile, rho)
    F = got["form_factors"]
    ref = np.linalg.solve(np.eye(32) - rho[:, None] * F, np.diag(rho))
    np.testing.assert_allclose(got["transport"], ref, rtol=0, atol=1e-12)


def test_308_press_diagonal_matches_full_hat_without_n_by_n_allocation():
    rng = np.random.default_rng(308)
    n = 5000
    coded = rng.uniform(-1, 1, size=(n, 3))
    spec = doe._factor_spec([("a", -1, 1), ("b", -1, 1), ("c", -1, 1)], "test")
    design = doe._design("test", coded, spec)
    y = 1 + coded @ np.array([2.0, -0.5, 0.25]) + rng.normal(scale=.02, size=n)
    tracemalloc.start()
    got = multivar.rsm_fit(design, y, model="linear")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    M = np.column_stack((np.ones(n), coded))
    inv = np.linalg.inv(M.T @ M)
    H = M @ inv @ M.T  # old implementation retained as the reference
    h = np.clip(np.diag(H), 0, 1 - 1e-12)
    expected = np.sum((got["residuals"] / (1 - h)) ** 2)
    np.testing.assert_allclose(got["press"], expected, rtol=0, atol=1e-12)
    assert peak < 40 * 1024 * 1024


def test_304_streaming_parallel_mean_preserves_rng_and_reference():
    rng = np.random.default_rng(304)
    X = rng.normal(size=(71, 13))
    exact = multivar.mv_pca(X, n_parallel=37, seed=991, parallel_stat="mean")
    stream = multivar.mv_pca(X, n_parallel=37, seed=991, parallel_stat="mean", memory_budget=1)
    np.testing.assert_allclose(stream["parallel_reference"], exact["parallel_reference"], rtol=0, atol=1e-12)
    assert stream["n_components"] == exact["n_components"]


def test_306_307_component_prefixes_match_independent_refits():
    rng = np.random.default_rng(306)
    X = rng.normal(size=(80, 9))
    Y = X[:, :2] @ np.array([[1.2], [-.7]]) + rng.normal(scale=.1, size=(80, 1))
    for fit in (multivar._pls_simpls, multivar._pls_nipals):
        full = fit(X, Y, 5)
        for a in range(1, 6):
            one = fit(X, Y, a)
            np.testing.assert_allclose(full["W"][:, :a], one["W"], rtol=0, atol=1e-12)
