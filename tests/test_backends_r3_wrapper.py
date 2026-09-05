"""`backends_r3._make` が例外を**外へ出す**こと(fail-soft 契約の 5 族目)。

2026-09-05 の敵対レビュー(Fable)で判明: `_make` は ``except Exception: out = None``
で例外を握り潰し、外側の ``backend_safe.guard`` は何も見なかった —— strict mode でも
例外が出ず、台帳にも残らない。2026-09-02 の「24 族中 1 族しか台帳に届いていない」
監査の取りこぼし。ここでは wrapper 単体を、必ず失敗するレシピで確かめる。
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

import backend_safe as bs           # noqa: E402

r3 = pytest.importorskip("backends_r3")


def _guarded_boom():
    inner = r3._make("1/0", "feature")            # 必ず ZeroDivisionError
    return bs.guard(inner, "feature", name="t_r3_boom")


def test_strict_mode_sees_the_recipe_exception():
    g = _guarded_boom()
    with bs.strict_mode(True):
        with pytest.raises(ZeroDivisionError):
            g(np.zeros((8, 8)), 0.5, 0.5)


def test_default_mode_records_the_failure_and_returns_the_sort_fallback():
    g = _guarded_boom()
    bs.clear_fallbacks()
    m = bs.mark()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = g(np.zeros((8, 8)), 0.5, 0.5)
    ev = bs.events_since(m)
    assert len(ev) == 1 and "ZeroDivisionError" in ev[0]["error"], "台帳に残っていない"
    assert float(out) == 0.0, "feature の退避値は 0.0"


def test_a_working_recipe_is_untouched():
    inner = r3._make("float(v.mean())", "feature")
    v = np.linspace(0, 1, 64).reshape(8, 8)
    assert float(inner(v, 0.5, 0.5)) == pytest.approx(float(v.mean()))
