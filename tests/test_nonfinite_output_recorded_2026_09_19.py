# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""非有限の出力は黙って置き換えない(#14)/ n-ary op は op_find から見える(N2)—— GenSpark 第 3・4 報(2026-09-19)。

中央 1 画素だけ NaN の画像を gaussian / median_image / mean_image / sobel_amp に通すと、出力は全画素が有限で
警告も台帳の記録も無かった(``on_error="raise"`` でも止まらない)。``backend_safe._finite`` が非有限を sort の
既定値で埋めていたから。直し = 置き換える**前に**件数を数えて記録(source ``"output"``)、strict では ValueError。
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

import backend_safe  # noqa: E402
import fullseye as fs  # noqa: E402


def _nan_image():
    x = np.random.default_rng(0).random((9, 9))
    x[4, 4] = np.nan
    return x


@pytest.mark.parametrize("name", ["gaussian", "median_image", "mean_image", "sobel_amp"])
def test_partial_nan_input_is_recorded_as_a_nonfinite_output_under_the_default_policy(name):
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(_nan_image(), name)
    assert np.isfinite(out).all()                          # 置き換え自体は従来どおり(有限で sort として妥当)
    recs = [e for e in fs.fallbacks() if e["name"] == name and e["source"] == "output"]
    assert recs and "non_finite_output" in recs[0]["error"], fs.fallbacks()
    assert "input itself has 1 non-finite" in recs[0]["error"], recs[0]["error"]


def test_partial_nan_input_stops_under_raise():
    with pytest.raises(ValueError, match="non_finite_output"):
        fs.apply(_nan_image(), "gaussian", on_error="raise")


def test_finite_output_is_not_recorded():
    fs.clear_fallbacks()
    fs.apply(np.random.default_rng(1).random((9, 9)), "gaussian", on_error="raise")
    assert not fs.fallbacks()


def test_nan_handling_ops_that_return_finite_results_are_untouched():
    # otsu は NaN を無視して有限の region を返す —— 出力が有限なら記録も例外も無い
    fs.clear_fallbacks()
    out = fs.apply(_nan_image(), "otsu", on_error="raise")
    assert set(np.unique(out)) <= {0.0, 1.0} and not fs.fallbacks()


def test_note_nonfinite_counts_scalars_too():
    fs.clear_fallbacks()
    backend_safe._note_nonfinite(float("nan"), np.zeros((2, 2)), "feature", "demo_scalar")
    recs = [e for e in fs.fallbacks() if e["name"] == "demo_scalar"]
    assert recs and "1 of 1" in recs[0]["error"]
    fs.clear_fallbacks()
    backend_safe._note_nonfinite(np.ones(3), np.zeros(3), "image", "demo_ok")   # 有限: 何もしない
    assert not fs.fallbacks()


def test_nary_ops_are_found_by_op_find_and_explained_as_list_calls():
    hits = fs.op_find("add_image")
    top = [h["op"] for h in hits[:3]]
    assert "add_image" in top, top
    h = next(h for h in hits if h["op"] == "add_image")
    assert h["ledger"] == "nary" and h["call"].startswith("apply([x0, x1]")
    assert "add_image" not in fs.op_names()                 # 1 入力のレジストリには載らない(文書どおり)
    assert "nary" in (fs.op_names.__doc__ or "")


def test_documented_nan_ops_are_exempt_from_the_note():
    # fly_tau_from_expansion は「膨張していない標本は NaN」を仕様として書いている op。
    # レジストリ版は有限契約で埋めるが、それを fallback として数えない(記録も例外も無い)。
    assert "tb_fly_tau_from_expansion" in backend_safe.NONFINITE_BY_DESIGN
    fs.clear_fallbacks()
    out = fs.apply(np.full(16, 0.5), "tb_fly_tau_from_expansion", on_error="raise")   # 定数角 = 膨張なし
    assert np.all(np.isfinite(np.asarray(out, dtype=float))) and not fs.fallbacks()
