"""External audit regressions for v0.9.0 (2026-11-04, nine findings F1-F9).

Each class reproduces one finding from the reviewer's numbers, re-derived here
independently (true values from closed forms, not from the implementation), and
then sweeps the same shape of bug in the sibling code paths.
"""

import math

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

import api
import backend_safe as bs


class TestF1PartialTupleStage:
    """``("op", a)`` must take the omitted ``b`` from the shared ``b``, not from ``a``."""

    def test_normalise_fills_each_missing_knob_from_its_own_default(self):
        got = api._normalise_stages(np.zeros((2, 2)),
                                    [("scale_clip",), ("scale_clip", 0.2), ("scale_clip", 0.2, 0.3),
                                     ("scale_clip", {"a": 0.2}), {"op": "scale_clip", "a": 0.2},
                                     "scale_clip"], 0.7, 0.9)
        assert [(a, b) for _, a, b in got] == [(0.7, 0.9), (0.2, 0.9), (0.2, 0.3),
                                              (0.2, 0.9), (0.2, 0.9), (0.7, 0.9)]

    def test_tuple_and_dict_forms_give_the_same_pipeline_result(self):
        x = np.full((2, 2), 0.25)
        forms = [("scale_clip", 0.2), {"op": "scale_clip", "a": 0.2}, ("scale_clip", {"a": 0.2}),
                 ("scale_clip", 0.2, 0.9)]
        outs = [float(api.run_pipeline(x, [s], a=0.7, b=0.9, on_error="raise")[0, 0]) for s in forms]
        assert outs == [outs[-1]] * len(forms)

    def test_engine_constructor_agrees_with_run_pipeline(self):
        import engine
        e = engine.FullseyeEngine([("scale_clip", 0.2)])
        assert e.stages == [["scale_clip", 0.2, 0.5]]      # engine's own default b is 0.5


class TestF2NaryDtypeContract:
    """The n-ary tier (``apply([x1, x2], ...)``) follows the same float64 [0,1] dtype contract as one input."""

    U = np.full((2, 2), 32, np.uint8)

    def test_strict_mode_refuses_integer_images(self):
        with pytest.raises(ValueError, match="float64 in \\[0,1\\]"):
            api.apply([self.U, self.U], "add_image", on_error="raise")

    def test_fallback_converts_like_the_single_input_path_and_records_it(self):
        bs.clear_fallbacks()
        out = api.apply([self.U, self.U], "add_image")
        assert float(out[0, 0]) == pytest.approx(64 / 255, abs=1e-15)
        ev = [e for e in bs.fallbacks() if "dtype_converted" in e["error"]]
        assert len(ev) == 2 and all(e["name"] == "add_image" for e in ev)
        ref = api.apply([self.U / 255.0, self.U / 255.0], "add_image", on_error="raise")
        assert np.array_equal(out, ref)

    def test_float32_inputs_are_promoted_without_a_record(self):
        bs.clear_fallbacks()
        x = np.full((2, 2), 0.25, np.float32)
        out = api.apply([x, x], "add_image", on_error="raise")
        assert out.dtype == np.float64 and float(out[0, 0]) == 0.5
        assert bs.fallbacks() == []

    def test_region_inputs_are_not_rescaled(self):
        m = np.array([[0, 1], [1, 0]], np.int64)
        out = api.apply([m, m], "union2", on_error="raise")
        assert np.array_equal(np.asarray(out, float), m.astype(float))

    def test_integer_convolution_kernel_is_a_weight_table_not_an_image(self):
        img = np.random.default_rng(0).random((20, 20))
        k_int = np.array([[0, 0, 0], [0, 1, 2], [0, 0, 0]], np.int64)
        got = api.apply([img, k_int], "convol_image", on_error="raise")
        ref = api.apply([img, k_int.astype(np.float64)], "convol_image", on_error="raise")
        assert np.array_equal(got, ref)


SCALES = [1e-9, 1e-6, 1e-3, 1.0, 1e3, 1e6]


def _similar_pair(k, scale=2.0, th=0.3):
    s = k * np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    return s, scale * s @ R.T + k * np.array([0.5, -0.25]), R


class TestF3ScaleFreeSimilarity:
    """A fit whose answer is scale-free must not depend on the unit of the coordinates."""

    @pytest.mark.parametrize("k", SCALES)
    def test_vector_to_similarity_recovers_exact_scale_at_every_unit(self, k):
        import fit_transform
        s, d, R = _similar_pair(k)
        M = fit_transform.vector_to_similarity(s, d)
        np.testing.assert_allclose(M[:2, :2], 2.0 * R, rtol=0, atol=1e-12)
        np.testing.assert_allclose(M[:2, 2] / k, [0.5, -0.25], rtol=0, atol=1e-9)

    def test_reviewer_numbers(self):
        import opscalib
        for k in (1.0, 1e-6):
            s = k * np.array([[0.0, 0.0], [1, 0], [0, 1], [1, 1]])
            assert float(opscalib.call("vector_to_similarity", s, 2 * s)[0, 0]) == pytest.approx(2.0, abs=1e-12)

    @pytest.mark.parametrize("k", SCALES)
    def test_featmatch_minimal_sample_fits_are_unit_free(self, k):
        import featmatch
        s, d, R = _similar_pair(k)
        H = featmatch._similarity_fit(s[:2], d[:2])
        np.testing.assert_allclose(H[:2, :2], 2.0 * R, rtol=0, atol=1e-12)
        assert not featmatch._degenerate_pair(s[:2], d[:2])
        assert not featmatch._degenerate_affine(s[:3], d[:3])
        assert not featmatch._degenerate_h(s[:4], d[:4])

    @pytest.mark.parametrize("k", SCALES)
    def test_featmatch_degeneracy_still_caught_at_every_unit(self, k):
        import featmatch
        line = k * np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
        same = k * np.array([[1.0, 2.0], [1.0, 2.0]])
        assert featmatch._degenerate_pair(same, same)
        assert featmatch._degenerate_affine(line[:3], line[:3])
        assert featmatch._degenerate_h(line, line)
        with pytest.raises(ValueError):
            featmatch._similarity_fit(same, same)

    @pytest.mark.parametrize("k", SCALES)
    def test_odometry_umeyama_scale_is_unit_free(self, k):
        import odometry
        P = k * np.random.default_rng(0).normal(size=(10, 3))
        s, R, t = odometry.umeyama_align(P, 2.0 * P, with_scale=True)
        assert s == pytest.approx(2.0, rel=1e-12)
        np.testing.assert_allclose(R, np.eye(3), atol=1e-12)

    def test_umeyama_coincident_points_keep_unit_scale(self):
        import odometry
        P = np.ones((5, 3))
        s, _R, _t = odometry.umeyama_align(P, P + 1.0, with_scale=True)
        assert s == 1.0

    @pytest.mark.parametrize("k", [1e-14, 1e-9, 1.0, 1e9])
    def test_projective_fit_maps_points_at_every_unit(self, k):
        import fit_transform
        s = k * np.array([[0.0, 0.0], [1, 0], [0, 1], [1, 1], [0.3, 0.7]])
        Ht = np.array([[1.1, 0.1, 0.2 * k], [-0.05, 0.9, 0.1 * k], [0.01 / k, -0.02 / k, 1.0]])
        h = np.c_[s, np.ones(len(s))] @ Ht.T
        d = h[:, :2] / h[:, 2:]
        H = fit_transform.hom_vector_to_proj_hom_mat2d(s, d)
        g = np.c_[s, np.ones(len(s))] @ H.T
        np.testing.assert_allclose(g[:, :2] / g[:, 2:] / k, d / k, atol=1e-9)


NAN, INF = float("nan"), float("inf")


class TestF4NonFiniteLeaves:
    """Every numeric leaf is scanned: scalars in dicts / lists / tuples, object arrays, deep nesting."""

    @pytest.mark.parametrize("value", [
        {"x": NAN},
        {"x": np.float64(INF)},
        {"x": complex(NAN, 0.0)},
        [np.zeros(2), INF],
        (np.zeros(2), {"k": NAN}),
        {"a": {"b": {"c": {"d": np.array([NAN])}}}},
        {"a": [[[[[[1.0, NAN]]]]]]},
        np.array([1.0, NAN], dtype=object),
        {"x": np.float32(NAN)},
    ], ids=["dict-float", "dict-np-inf", "dict-complex", "list-scalar", "tuple-dict", "deep-dict",
            "deep-list", "object-array", "float32-scalar"])
    def test_leaf_is_found(self, value):
        assert api._nonfinite_leaf(value) is not None

    @pytest.mark.parametrize("value", [
        {"x": 1.0, "n": 3, "flag": True, "s": "text", "none": None},
        [np.zeros(2), 1.5, (2, 3)],
        {"a": {"b": {"c": {"d": np.array([1.0])}}}},
        np.array([1.0, "a"], dtype=object),
        {"z": complex(1.0, -2.0)},
    ])
    def test_finite_values_pass(self, value):
        assert api._nonfinite_leaf(value) is None

    @pytest.mark.parametrize("policy", ["raise", "fallback", "warn"])
    def test_identity_refuses_nan_in_a_dict_whatever_the_policy(self, policy):
        with pytest.raises(ValueError, match="NaN or infinity"):
            api.apply({"x": NAN}, "identity", on_error=policy)

    def test_escape_hatch_still_hands_the_value_through(self):
        out = api.apply({"x": NAN}, "identity", allow_nonfinite=True)
        assert math.isnan(out["x"])


def _hand_eye_case(rels, X_rotvec=(0.3, -0.2, 0.15), X_t=(12.0, -5.0, 30.0), step_t=(2.0, 3.0, 4.0)):
    """Poses A (and B = X⁻¹ A X) built from relative rotations *rels*; X is the known truth."""
    X = np.eye(4)
    X[:3, :3] = Rotation.from_rotvec(X_rotvec).as_matrix()
    X[:3, 3] = X_t
    A = [np.eye(4)]
    for R in rels:
        M = np.eye(4)
        M[:3, :3] = R
        M[:3, 3] = step_t
        A.append(A[-1] @ M)
    B = [np.linalg.inv(X) @ p @ X for p in A]
    return A, B, X


HALF_X = np.diag([1.0, -1.0, -1.0])
HALF_Y = np.diag([-1.0, 1.0, -1.0])
HALF_Z = np.diag([-1.0, -1.0, 1.0])
HALF_XY = Rotation.from_rotvec(np.pi * np.array([1.0, 1.0, 0.0]) / math.sqrt(2.0)).as_matrix()
HALF_XYZ = Rotation.from_rotvec(np.pi * np.ones(3) / math.sqrt(3.0)).as_matrix()
GENERAL = Rotation.from_rotvec([0.2, 0.3, 0.4]).as_matrix()


class TestF5HandEyeHalfTurns:
    """Exact 180° relative motions are valid hand-eye data; the rotation log must handle them."""

    @pytest.mark.parametrize("rels", [
        [HALF_X, HALF_Y, GENERAL],                      # the reviewer's sequence
        [HALF_X, GENERAL],                              # one half-turn + one general motion
        [HALF_X, HALF_Y, HALF_XYZ],                     # three half-turns, no common normal
        [GENERAL, HALF_XY, Rotation.from_rotvec([-0.5, 0.1, 0.2]).as_matrix()],
    ], ids=["reviewer", "half-plus-general", "three-half-turns", "mixed"])
    def test_recovers_known_X(self, rels):
        import calib
        A, B, X = _hand_eye_case(rels)
        got = calib.hand_eye_calibration(A, B)
        np.testing.assert_allclose(got[:3, :3], X[:3, :3], atol=1e-9)
        np.testing.assert_allclose(got[:3, 3], X[:3, 3], atol=1e-7)

    def test_reviewer_call_through_opscalib(self):
        import opscalib
        A, B, X = _hand_eye_case([HALF_X, HALF_Y, GENERAL])
        np.testing.assert_allclose(opscalib.call("hand_eye_calibration", A, B), X, atol=1e-7)

    @pytest.mark.parametrize("rels", [[HALF_X, HALF_Y], [HALF_X, HALF_Z, HALF_XY]],
                             ids=["two-half-turns", "half-turns-sharing-a-normal"])
    def test_half_turns_alone_are_ambiguous_and_refused(self, rels):
        # Q = 180 deg about the common normal n maps every half-turn axis a to -a (same half-turn),
        # so Q·Rx explains the data as well as Rx: the data do not determine X.
        import calib
        A, B, _ = _hand_eye_case(rels)
        assert all(np.allclose(HALF_Z @ R @ HALF_Z.T, R) for R in rels)   # the ambiguity is real
        with pytest.raises(ValueError, match="half-turns"):
            calib.hand_eye_calibration(A, B)

    def test_half_turn_data_with_small_noise_stays_close(self):
        import calib
        A, B, X = _hand_eye_case([HALF_X, HALF_Y, GENERAL])
        rng = np.random.default_rng(3)
        Bn = []
        for p in B:
            q = p.copy()
            q[:3, :3] = Rotation.from_rotvec(1e-6 * rng.normal(size=3)).as_matrix() @ q[:3, :3]
            Bn.append(q)
        got = calib.hand_eye_calibration(A, Bn)
        ang = np.linalg.norm(Rotation.from_matrix(got[:3, :3] @ X[:3, :3].T).as_rotvec())
        assert ang < 1e-4

    def test_single_axis_half_turns_are_still_refused(self):
        import calib
        A, B, _ = _hand_eye_case([HALF_X, HALF_X, Rotation.from_rotvec([0.4, 0, 0]).as_matrix()])
        with pytest.raises(ValueError, match="single axis|not determined"):
            calib.hand_eye_calibration(A, B)

    @pytest.mark.parametrize("theta", [np.pi, np.pi - 1e-9, np.pi - 1e-6, np.pi - 1e-3, 3.0, 1.0, 1e-4])
    def test_rotation_logs_match_scipy_near_and_at_pi(self, theta):
        import calib
        import camera
        axis = np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])
        R = Rotation.from_rotvec(theta * axis).as_matrix()
        for f in (calib._rot_to_axis, camera.rotation_log):
            w = f(R)
            # at exactly π the sign of the axis is a free choice: compare as rotations
            np.testing.assert_allclose(Rotation.from_rotvec(w).as_matrix(), R, atol=1e-12)
            assert abs(np.linalg.norm(w) - theta) < 1e-9
            if theta < np.pi - 1e-12:
                np.testing.assert_allclose(w, theta * axis, atol=1e-9)

    def test_balltrack_spin_half_turn_is_finite(self):
        import balltrack
        R = Rotation.from_rotvec(np.pi * np.array([0.0, 0.6, 0.8])).as_matrix()
        d0 = np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0], [0.6, 0.0, 0.8]])
        out = balltrack.spin_from_markers(d0, d0 @ R.T, dt=1.0)
        assert np.isfinite(out["omega"]).all()
        assert abs(abs(float(out["axis"] @ [0.0, 0.6, 0.8])) - 1.0) < 1e-9
        np.testing.assert_allclose(out["R"], R, atol=1e-9)


class TestF6RansacFinalConsensus:
    """The returned model must itself have >= min_inliers inliers (after the final refit)."""

    Q = np.array([[.956, -.667], [-1.216, .292], [.621, .143], [-.141, -.144], [1.163, -.200],
                  [.779, -.276], [-.342, -.285], [-1.048, -.804], [1.321, .294], [1.378, .323]])

    def _matches(self, p, q):
        return dict(kind="feature_matches", pts1=p, pts2=q, image_shape1=(16, 16), image_shape2=(16, 16))

    def test_reviewer_case_keeps_the_promised_consensus(self):
        import featmatch
        r = featmatch.ransac_homography(self._matches(np.zeros((10, 2)), self.Q), model="translation",
                                        thresh=1, min_inliers=7, seed=0, local_optimization=False)
        assert r["n_inliers"] >= 7
        # the reported inliers are exactly the points within thresh of the returned model
        res = np.linalg.norm(self.Q - r["H"][:2, 2], axis=1)
        assert np.array_equal(r["inliers"], res < 1.0)

    @pytest.mark.parametrize("model", ["translation", "similarity", "affine", "projective"])
    @pytest.mark.parametrize("seed", range(12))
    def test_every_model_and_seed_honours_min_inliers(self, model, seed):
        import featmatch
        rng = np.random.default_rng(seed)
        p = rng.uniform(0, 20, (14, 2))
        q = p + rng.normal(0, 0.6, (14, 2))          # noise of the order of thresh: refits move the set
        mn = 7
        try:
            r = featmatch.ransac_homography(self._matches(p, q), model=model, thresh=1.0, min_inliers=mn,
                                            seed=seed, local_optimization=bool(seed % 2))
        except ValueError:
            return                                    # honest "no consensus" is allowed
        assert r["n_inliers"] >= mn and int(r["inliers"].sum()) == r["n_inliers"]

    @pytest.mark.parametrize("seed", range(8))
    def test_fundamental_honours_min_inliers(self, seed):
        import featmatch
        rng = np.random.default_rng(100 + seed)
        X = np.c_[rng.uniform(-1, 1, (30, 2)), rng.uniform(4, 8, 30)]
        p = X[:, :2] / X[:, 2:] * 100 + 50
        Xb = X + np.array([0.3, 0.0, 0.0])
        q = Xb[:, :2] / Xb[:, 2:] * 100 + 50 + rng.normal(0, 0.8, (30, 2))
        try:
            r = featmatch.ransac_fundamental(self._matches(p, q), thresh=0.8, min_inliers=20, seed=seed)
        except ValueError:
            return
        assert r["n_inliers"] >= 20 and int(r["inliers"].sum()) == r["n_inliers"]
