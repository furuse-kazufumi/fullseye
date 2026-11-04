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
