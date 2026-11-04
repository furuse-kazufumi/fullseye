# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05(担当 stats)の回帰テスト。

各テストは報告の再現を「真値・不変量・独立実装」と比べる形にしてある。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

# ---- S7: fullseye.judge の非有限な限界値 ----------------------------------

_NONFINITE_SPECS = [
    {"width_mm": {"min": 3.0, "max": float("nan")}},
    {"width_mm": {"nominal": 3.0, "tol": float("nan")}},
    {"width_mm": {"nominal": float("nan"), "tol": 0.1}},
    {"area": {"min": float("nan"), "max": float("nan")}},
    {"width_mm": {"max": float("inf")}},
    {"width_mm": {"min": -math.inf}},
    {"width_mm": {"nominal": 3.0, "tol": math.inf}},
    {"width_mm": {"eq": float("nan")}},
    {"width_mm": {"in": [1.0, float("nan")]}},
]


@pytest.mark.parametrize("spec", _NONFINITE_SPECS)
def test_s7_judge_refuses_nonfinite_rule_limits(spec):
    """NaN/inf の限界値は比較が全部 False になり「常に ok」になる → ValueError。"""
    from fullseye.judge import judge
    meas = {"width_mm": 99.0, "area": -5.0}
    with pytest.raises(ValueError, match="finite"):
        judge(meas, spec)


def test_s7_judge_finite_limits_still_judge():
    """有限な規則は従来どおり: 99 mm は max 3.5 を破って ng。"""
    from fullseye.judge import judge
    v = judge({"width_mm": 99.0}, {"width_mm": {"min": 3.0, "max": 3.5}})
    assert v.status == "ng"
    v = judge({"width_mm": 3.2}, {"width_mm": {"min": 3.0, "max": 3.5}})
    assert v.status == "ok"
