# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""段の正規化は 1 本(2026-09-20、GenSpark 第 53 報 N179 / N181、設計パターン提案 ②)。

同じ段 ``{"op": "otsu"}`` が、run_pipeline では走り、engine では走り、diagnose_stages では「unknown operator
{'op': 'otsu'}」、unified.Pipeline では ``unhashable type: 'dict'`` だった。名前の取り出しを
``engine.stage_name`` の 1 本にし、4 つの入口が同じ段を同じ名前に読むことを問う。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import engine  # noqa: E402
import fullseye as fs  # noqa: E402

X = np.random.default_rng(0).random((32, 32))
FORMS = ["gaussian", ("sobel_amp", 0.3), ("median", {"a": 0.4}), {"op": "invert"}, {"name": "gaussian", "a": 0.2}, ["otsu", 0.5, 0.5]]


def test_four_entry_points_read_the_same_stage_names():
    names = [engine.stage_name(s) for s in FORMS]
    assert names == ["gaussian", "sobel_amp", "median", "invert", "gaussian", "otsu"]
    assert engine.FullseyeEngine(FORMS).op_names() == names
    assert [n for n, _, _ in api._normalise_stages(X, FORMS, 0.5, 0.5)] == names
    assert engine.diagnose_stages(FORMS) == []                       # 以前は dict 段が unknown operator
    assert fs.run_pipeline(X, FORMS).shape == X.shape


def test_diagnose_stages_reports_a_broken_stage_instead_of_raising():
    probs = engine.diagnose_stages(["gaussian", {"a": 0.3}, 7, {"op": "no_such_op_xyz"}])
    assert [p["index"] for p in probs] == [1, 2, 3] and all(p["severity"] == "error" for p in probs)
    assert "'op'" in probs[0]["message"] and "non-empty name" in probs[1]["message"]
    assert probs[2]["op"] == "no_such_op_xyz" and "unknown operator 'no_such_op_xyz'" in probs[2]["message"]


def test_engine_rejects_a_malformed_stage_with_the_shared_sentence():
    for bad in ([{"a": 0.3}], [7], [("", 0.5)], [(3, 0.5)]):
        with pytest.raises(ValueError, match="stage 0: "):
            engine.FullseyeEngine(bad)
    with pytest.raises(TypeError, match="non-empty name"):
        engine.stage_name(None)


def test_unified_pipeline_accepts_list_and_dict_stages():
    img = np.random.default_rng(0).random((48, 60))
    ref = fs.Pipeline(["median", ("sobel_amp", {}), "invert"]).run(img)
    for stages in ([["median", {}], {"op": "sobel_amp"}, {"name": "invert"}],
                   [("median", {}), ["sobel_amp"], "invert"]):
        assert np.allclose(np.asarray(fs.Pipeline(stages).run(img)), np.asarray(ref))
    assert fs.Pipeline([{"op": "median"}]).steps == [("median", {})]
    with pytest.raises(TypeError, match="'op'"):
        fs.Pipeline([{"a": 1}])
    with pytest.raises(TypeError, match="op name"):
        fs.Pipeline([3])
    with pytest.raises(TypeError, match=r"\(op, \{kwargs\}\)"):
        fs.Pipeline([("median", 3)])
