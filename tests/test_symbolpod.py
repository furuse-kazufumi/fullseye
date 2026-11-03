# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""読み取りの POD(symbolpod)の門。

  * 写像の正しさ: 劣化が「大きいほど悪い」因子は x = −水準で当て、答えを戻す
    → :func:`pod.pod_hitmiss_fit` を直接呼んだ結果と 1e-12 で一致(符号の取り違えの門)
  * 向き: 大きいほど悪い因子では level90_95 < level90 < level50、大きいほど良い因子
    (モジュールの大きさ)では level50 < level90 < level90_95
  * 完全分離(決定的な読み取り)は傾きの無い POD を作らず、全数成功の実証(29/29)を返す
  * 誤読は当たりに数えない・別に上限を付ける
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import barcode1d as B  # noqa: E402
import pod  # noqa: E402
import symbolpod as P  # noqa: E402


@pytest.fixture(scope="module")
def defocus_trials():
    enc = B.encode_barcode1d("4901234567894", "ean13")
    return P.symbol_read_trials(enc, "defocus_px", np.linspace(6.0, 7.8, 7), trials=14,
                                module_px=3.0, level_jitter=0.05, seed=1)


def test_mapping_matches_a_direct_hitmiss_fit(defocus_trials):
    tr = defocus_trials
    r = P.symbol_read_pod(tr)
    assert r["method"] == "hitmiss_glm"
    fit = pod.pod_hitmiss_fit({"a": -tr["level"], "hit": tr["hit"]}, size="a", hit="hit")
    assert abs(r["level90"] - (-fit["a90"])) < 1e-12
    assert abs(r["level90_95"] - (-fit["a90_95"])) < 1e-12
    assert r["level90_95"] < r["level90"] < r["level50"]          # 大きいほど悪い → 保守側は小さい
    lo, hi = tr["level"].min(), tr["level"].max()
    assert lo < r["level90"] < hi


def test_outcomes_are_split_and_counted(defocus_trials):
    tr = defocus_trials
    assert np.all(tr["hit"] + tr["misread"] + tr["noread"] == 1)
    r = P.symbol_read_pod(tr)
    assert sum(p["n"] for p in r["per_level"]) == tr["level"].size
    assert r["misread_total"] == int(tr["misread"].sum())
    n = r["decoded_total"]
    if r["misread_total"] == 0:
        # 0 件の誤読の片側上限 = 1 − (1 − 0.95)^(1/n)(Clopper-Pearson の閉形式)
        assert abs(r["misread_rate_upper"] - (1.0 - 0.05 ** (1.0 / n))) < 1e-9
    rates = [p["read_rate"] for p in r["per_level"]]
    assert rates[0] >= 0.9 and rates[-1] <= 0.2                   # 両端は読める / 読めない


def test_better_when_larger_factor_orders_the_other_way():
    enc = B.encode_barcode1d("FULLSEYE", "code128")
    tr = P.symbol_read_trials(enc, "module_px", np.linspace(1.35, 1.65, 6), trials=12,
                              capture={"gauss_px": 0.8}, level_jitter=0.05, seed=2)
    r = P.symbol_read_pod(tr)
    assert r["method"] == "hitmiss_glm" and r["worse_when_larger"] is False
    assert r["level50"] < r["level90"] < r["level90_95"]          # 保守側は「より大きいモジュール」


def test_complete_separation_returns_the_all_success_demonstration():
    """雑音も揺らぎも無い描画は劣化量だけで読めるかが決まる → 29/29 の論法で返す。"""
    enc = B.encode_barcode1d("4901234567894", "ean13")
    tr = P.symbol_read_trials(enc, "defocus_px", [5.0, 6.0, 9.0, 10.0], trials=29, module_px=3.0,
                              capture={"full_well_e": None, "read_noise_e": 0.0},
                              rotate=0.0, seed=0)
    assert set(np.unique(tr["hit"][tr["level"] <= 6.0])) == {1}
    assert set(np.unique(tr["hit"][tr["level"] >= 9.0])) == {0}
    r = P.symbol_read_pod(tr)
    assert r["method"] == "all_success_demonstration"
    assert r["trials_needed"] == pod.trials_for_all_success(0.90) == 29
    assert r["separation_bracket"] == (6.0, 9.0)
    assert r["level90_95"] == 6.0 and r["level90"] is None


def test_zxing_reader_runs_on_the_same_captures():
    pytest.importorskip("zxingcpp")
    enc = B.encode_barcode1d("4901234567894", "ean13")
    tr = P.symbol_read_trials(enc, "defocus_px", [1.0, 2.0, 12.0], trials=3, module_px=3.0,
                              reader="zxing", seed=0)
    assert tr["reader"] == "zxing"
    assert tr["hit"][tr["level"] == 1.0].all() and not tr["hit"][tr["level"] == 12.0].any()


def test_fail_closed():
    enc = B.encode_barcode1d("12345678", "itf")
    with pytest.raises(ValueError):
        P.symbol_read_trials(enc, "brightness", [1, 2, 3])
    with pytest.raises(ValueError):
        P.symbol_read_trials(enc, "defocus_px", [1, 2])
    with pytest.raises(ValueError):
        P.symbol_read_trials(enc, "defocus_px", [1, 1, 2])
    with pytest.raises(ValueError):
        P.symbol_read_trials(enc, "defocus_px", [1, 2, 3], trials=0)
    with pytest.raises(ValueError):
        P.symbol_read_trials(enc, "ink_gain", [0.1, 0.2, 0.3], render={"ink_gain": 0.1})
    with pytest.raises(ValueError):
        P.symbol_read_trials(enc, "defocus_px", [1, 2, 3], level_jitter=0.9)
    with pytest.raises(ValueError):
        P.symbol_read_pod({"level": []})
    all_read = P.symbol_read_trials(enc, "defocus_px", [0.0, 0.5, 1.0], trials=2)
    with pytest.raises(ValueError):
        P.symbol_read_pod(all_read)                               # 全部読めた = 曲線が立たない
    with pytest.raises(ValueError):
        P.symbol_read(np.ones((10, 10)), reader="ocr")
