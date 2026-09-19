# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.judge — 計測 dict を仕様に照らして根拠つき Verdict にする(検査ワークフロー層 #2)。

恒等式で固定する: 仕様内→ok / 超過→ng+violations / 欠損→error / NaN→error /
境界 inclusive / eq・in / 仕様の誤字は ValueError / signal_verdict にそのまま渡せる。
"""
import math

import numpy as np
import pytest

import fullseye
from fullseye.judge import judge
from fsruntime import Verdict, _VERDICTS


def test_within_spec_is_ok_with_no_violations():
    v = judge({"area": 12.5, "width_mm": 3.02, "label": "OK"},
              {"area": {"min": 10, "max": 15}, "width_mm": {"nominal": 3.0, "tol": 0.05},
               "label": {"eq": "OK"}})
    assert isinstance(v, Verdict) and v.status == "ok"
    assert v.result["violations"] == [] and v.result["checked"] == 3
    assert v.detail.startswith("ok: 3/3")


def test_one_violation_is_ng_and_names_key_and_limit():
    v = judge({"area": 17.0, "label": "OK"}, {"area": {"min": 10, "max": 15}, "label": {"eq": "OK"}})
    assert v.status == "ng"
    assert v.result["violations"] == [{"key": "area", "value": 17.0, "rule": "max", "limit": 15.0}]
    assert "area=17" in v.detail and "max 15" in v.detail


def test_missing_key_is_error_when_strict_and_skipped_otherwise():
    spec = {"area": {"min": 10, "max": 15}, "width_mm": {"nominal": 3.0, "tol": 0.05}}
    strict = judge({"area": 12.0}, spec)
    assert strict.status == "error" and "width_mm" in strict.detail
    loose = judge({"area": 12.0}, spec, strict=False)
    assert loose.status == "ok" and loose.result["missing"] == ["width_mm"]
    assert loose.result["checked"] == 1 and "skipped 1 missing" in loose.detail


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, np.float64("nan")])
def test_non_finite_is_error_not_ok_or_ng(bad):
    v = judge({"area": bad}, {"area": {"min": 0, "max": 100}})
    assert v.status == "error" and "not finite" in v.detail


def test_non_numeric_against_numeric_rule_is_error():
    v = judge({"area": "12"}, {"area": {"min": 0, "max": 100}})
    assert v.status == "error" and "not a number" in v.detail


def test_boundaries_are_inclusive():
    spec = {"w": {"nominal": 3.0, "tol": 0.05}, "a": {"min": 10, "max": 15}}
    for w, a in ((3.05, 10), (2.95, 15)):
        assert judge({"w": w, "a": a}, spec).status == "ok"
    assert judge({"w": 3.0500001, "a": 12}, spec).status == "ng"
    assert judge({"w": 3.0, "a": 15.0000001}, spec).status == "ng"


def test_eq_and_in_rules_compare_strings_and_numbers():
    assert judge({"grade": "A", "n": 3}, {"grade": {"in": ["A", "B"]}, "n": {"eq": 3.0}}).status == "ok"
    v = judge({"grade": "C", "n": 4}, {"grade": {"in": ["A", "B"]}, "n": {"eq": 3}})
    assert v.status == "ng"
    assert {x["key"] for x in v.result["violations"]} == {"grade", "n"}
    assert v.result["violations"][0]["limit"] == ["A", "B"]


def test_measurements_not_in_spec_are_ignored():
    v = judge({"area": 12.0, "extra": "whatever", "other": math.nan}, {"area": {"min": 10, "max": 15}})
    assert v.status == "ok" and v.result["checked"] == 1


@pytest.mark.parametrize("spec", [
    {"area": {"mx": 15}},                       # 誤字の規則が「検査しない」に化けない
    {"area": {}},
    {"area": {"nominal": 3.0}},                  # tol 無し
    {"area": {"tol": 0.1}},                      # nominal 無し
    {"area": {"min": 15, "max": 10}},
    {"area": {"min": "10"}},
    {"area": {"in": "AB"}},                      # 文字列は集合でない
    {},
    "not a dict",
])
def test_broken_spec_is_rejected_before_any_judgement(spec):
    with pytest.raises(ValueError):
        judge({"area": 12.0}, spec)


def test_verdict_vocabulary_matches_the_plc_exit():
    """status は fsruntime._VERDICTS の語彙 —— signal_verdict がそのまま受け取り、one-hot で出す。"""
    import device
    io = device.DigitalIO(backend="memory")
    for m, want in (({"a": 1.0}, "ok"), ({"a": 9.0}, "ng"), ({"b": 1.0}, "error")):
        v = judge(m, {"a": {"min": 0, "max": 5}})
        assert v.status == want and v.status in _VERDICTS
        assert device.signal_verdict(io, v) == want


def test_facade_exposes_judge():
    assert fullseye.judge is judge and "judge" in fullseye.__all__
