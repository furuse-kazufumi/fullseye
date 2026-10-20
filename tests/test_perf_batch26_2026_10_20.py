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
