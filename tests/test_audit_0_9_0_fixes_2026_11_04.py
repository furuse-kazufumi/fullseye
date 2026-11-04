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
