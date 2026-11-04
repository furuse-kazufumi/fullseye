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
