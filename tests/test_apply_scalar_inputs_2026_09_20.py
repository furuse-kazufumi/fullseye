# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""apply の image が配列でない(GenSpark 第 26 報 N97)、data_range_of の空呼び出し(第 23 報 N92)、
torch_lazy の ImportError の理由(第 24・25 報 N94)、list_ops の未知 sort(第 24 報 N95)。2026-09-20。
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

import fullseye as fs  # noqa: E402
import imgmetrics  # noqa: E402
import torch_lazy  # noqa: E402


@pytest.mark.parametrize("bad", ["abc", b"ab", 5, 0.3, {"a": 1}, np.float64(0.3), np.array(0.3)])
@pytest.mark.parametrize("policy", ["fallback", "warn", "raise"])
def test_non_array_images_are_type_errors_regardless_of_policy(bad, policy):
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TypeError, match="gaussian"):
            fs.apply(bad, "gaussian", on_error=policy)
    assert not [e for e in fs.fallbacks() if e["name"] == "gaussian"]      # 落とし先が無いので台帳にも書かない


def test_nested_numeric_lists_are_still_arrays():
    img = np.random.default_rng(0).random((8, 8))
    out = fs.apply(img.tolist(), "gaussian", on_error="raise")
    assert np.asarray(out).shape == (8, 8)


def test_dict_inputs_are_still_accepted_where_the_sort_is_a_dict():
    contour = fs.apply(np.random.default_rng(0).random((16, 16)) > 0.5, "gen_contour_region_xld", on_error="raise")
    if not isinstance(contour, dict):
        pytest.skip("contour op returned %s" % type(contour).__name__)
    rows = [r for r in fs.list_ops() if r["in_sort"] == "contour"]
    assert rows                                                            # contour を取る op は dict を受ける
    fs.apply(contour, rows[0]["name"], on_error="raise")


def test_data_range_of_without_arrays_is_a_contract_error():
    with pytest.raises(imgmetrics.MetricContractError, match="at least one array"):
        imgmetrics.data_range_of()
    assert imgmetrics.data_range_of(data_range=2.0) == 2.0
    assert imgmetrics.data_range_of(np.zeros((4, 4), np.uint8)) == 255.0


def test_lazy_torch_import_error_says_whether_torch_is_installed(monkeypatch):
    lazy = torch_lazy._LazyModule("no_such_module_xyz_fullseye")
    with pytest.raises(ImportError, match="is not installed"):
        _ = lazy.zeros
    lazy2 = torch_lazy._LazyModule("json")
    import importlib

    def boom(name):
        raise RuntimeError("simulated broken build")
    monkeypatch.setattr(importlib, "import_module", boom)
    with pytest.raises(ImportError, match="is installed but importing it failed: RuntimeError: simulated broken build"):
        _ = lazy2.dumps


def test_list_ops_unknown_sort_is_refused_and_lists_the_known_ones():
    with pytest.raises(ValueError, match="unknown sort 'nonsense'.*image"):
        fs.list_ops(sort="nonsense")
    assert len(fs.list_ops(sort="")) == len(fs.list_ops())
    assert fs.list_ops(sort="region")
