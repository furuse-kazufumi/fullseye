# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""退化入力(空 / 極小 / 1-D / RGB)の門と注記の回帰(2026-09-19、全 op 走査から)。

image/region 入力 681 op × 7 種の退化入力を ``on_error="raise"`` で回した結果:
空配列 (0,0) は 271 op が 49 種類の生エラー、極小 (1,1)/(2,2) は 9〜19 群の生エラー(kornia の padding、
numpy gradient、skimage coordinates …)。1-D と RGB は既存の門が断っていた。直し = 空は門で 1 文、
生エラーには op 名と入力の形を注記(``BaseException.add_note``、型も文も変えない)。
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api  # noqa: E402
import engine  # noqa: E402
import fullseye as fs  # noqa: E402

EMPTY = np.zeros((0, 0))


@pytest.mark.parametrize("name", ["gaussian", "sobel_amp", "otsu", "tophat", "fft_image", "lowpass", "reg_erode"])
def test_empty_input_is_one_clean_sentence_under_raise(name):
    with pytest.raises(ValueError, match="empty input") as ei:
        fs.apply(EMPTY, name, on_error="raise")
    assert name in str(ei.value) and "upstream" in str(ei.value)


def test_empty_input_is_recorded_and_falls_back_under_the_default_policy():
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(EMPTY, "gaussian")
    assert isinstance(out, np.ndarray)
    assert any(e["name"] == "gaussian" and "empty input" in e["error"] for e in fs.fallbacks())


def test_empty_input_in_a_pipeline_names_the_first_stage():
    with pytest.raises(ValueError, match="'gaussian'.*empty input"):
        fs.run_pipeline(EMPTY, "gaussian,otsu", on_error="raise")


def test_non_raster_sorts_are_not_touched_by_the_empty_check():
    # feature / 1-D signal など、空が正当でありうる sort には空の門を掛けない
    class _Op:
        in_sort, name = "signal", "demo"
    assert api._check_input_empty(np.zeros(0), _Op()) is None
    assert api._check_input_empty(np.zeros((0, 0)), _Op()) is None


def test_raw_error_from_inside_an_op_gets_an_op_and_shape_note():
    if not hasattr(BaseException, "add_note"):
        pytest.skip("add_note needs Python 3.11+")
    # numpy.gradient needs at least 2 samples per axis: a 1x1 image makes the op raise numpy's own ValueError
    with pytest.raises(ValueError) as ei:
        fs.apply(np.full((1, 1), 0.5), "structure_tensor_orientation", on_error="raise")
    notes = getattr(ei.value, "__notes__", [])
    assert any("structure_tensor_orientation" in n and "(1, 1)" in n for n in notes), (str(ei.value), notes)


def test_clean_errors_are_not_annotated_twice():
    if not hasattr(BaseException, "add_note"):
        pytest.skip("add_note needs Python 3.11+")
    with pytest.raises(ValueError) as ei:
        fs.apply(np.full((8, 8), np.nan), "otsu", on_error="raise")     # 文に op 名が既にある
    assert not getattr(ei.value, "__notes__", [])


def test_annotate_never_replaces_the_original_error():
    e = ValueError("boom")
    api._annotate_raw(e, "some_op", np.zeros((3, 3)))
    assert str(e) == "boom"
    api._annotate_raw(e, "some_op", "not an array")                     # non-array input: still no crash
    assert str(e) == "boom"


def test_one_d_and_rgb_inputs_to_a_2d_op_are_still_refused_cleanly():
    with pytest.raises(ValueError, match="expects a image"):
        fs.apply(np.zeros(32), "gaussian", on_error="raise")


def test_pipeline_validate_explains_a_missing_backend(monkeypatch):
    fake = {"fake_missing_op": {"name": "fake_missing_op", "tier": "registry", "module": "backends_ski2",
                                "requires": ["skimage", "definitely_missing_mod_xyz"]}}
    monkeypatch.setattr(api, "_SHIPPED_INDEX_CACHE", fake)
    problems = engine.diagnose_stages(["gaussian", "fake_missing_op"])
    errs = [p for p in problems if p["severity"] == "error"]
    assert errs and "pip install" in errs[0]["message"] and "definitely_missing_mod_xyz" in errs[0]["message"]
    problems = engine.diagnose_stages(["gaussian", "no_such_op_xyz"])
    errs = [p for p in problems if p["severity"] == "error"]
    assert errs and "unknown operator 'no_such_op_xyz'" in errs[0]["message"]
