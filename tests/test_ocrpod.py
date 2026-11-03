# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""OCR の可読性の POD(symbolpod.ocr_read_trials)の門。

  * 真値 = 描いた文字列。成功 / 誤読 / 不能の 3 通りが排他で、誤読は「別の字を読んだ」ときだけ
  * 誤読の判定は ocr_score の内訳(置換・「?」でない挿入)と一致する
  * 字高(大きいほど良い)とデフォーカス(大きいほど悪い)で POD の向きが逆になる
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ocrclassic as O  # noqa: E402
import symbolpod as P  # noqa: E402


@pytest.fixture(scope="module")
def model():
    return O.ocr_train("dot5x7")


def test_outcomes_are_exclusive_and_match_the_score(model):
    tr = P.ocr_read_trials("LOT2611A", "defocus_px", [1.0, 9.0, 11.0, 13.0], model=model,
                           trials=6, seed=3)
    assert np.all(tr["hit"] + tr["misread"] + tr["noread"] == 1)
    assert tr["hit"][tr["level"] == 1.0].all()                  # くっきりは全部読める
    assert len(tr["text"]) == 24
    for got, mis, sub in zip(tr["text"], tr["misread"], tr["substituted_chars"]):
        sc = O.ocr_score(got, "LOT2611A")
        ins_real = sum(c != "?" for c in got) - sc["correct"] - sc["substituted"]
        assert bool(mis) == (got != "LOT2611A" and (sc["substituted"] > 0 or ins_real > 0))
        assert sub == sc["substituted"]


def test_character_height_pod_is_better_when_larger(model):
    tr = P.ocr_read_trials("4711", "char_height_px", np.linspace(6.0, 14.0, 5), model=model,
                           trials=8, capture={"gauss_px": 1.2}, level_jitter=0.05, seed=1)
    assert tr["worse_when_larger"] is False
    rates = [tr["hit"][tr["level"] == v].mean() for v in np.unique(tr["level"])]
    assert rates[-1] >= rates[0]
    r = P.symbol_read_pod(tr)                                   # 同じ表の形で POD に掛かる
    assert r["factor"] == "char_height_px" and r["worse_when_larger"] is False


def test_fail_closed(model):
    with pytest.raises(ValueError):
        P.ocr_read_trials("", "defocus_px", [1, 2, 3], model=model)
    with pytest.raises(ValueError):
        P.ocr_read_trials("abc", "defocus_px", [1, 2, 3], model=model)   # 字種の外(小文字)
    with pytest.raises(ValueError):
        P.ocr_read_trials("A1", "rotation", [1, 2, 3], model=model)
    with pytest.raises(ValueError):
        P.ocr_read_trials("A1", "defocus_px", [1, 2, 3], model={"x": 1})
    with pytest.raises(ValueError):
        P.ocr_read_trials("A1", "ink_gain", [0.1, 0.2, 0.3], model=model, render={"ink_gain": 0.1})
