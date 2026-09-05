"""``fullseye.apply`` の**呼び出し規約**(引数の型・順・値域)。

2026-09-05 に自分で踏んだ: `apply(name, image)` と順を逆にしたら numpy の
「truth value of an array is ambiguous」が出て、原因に辿り着けなかった。
測り直すと `a="big"` / `a=None` は**利用者の入力がそのまま結果として返り**、
`a=nan` は台帳にも残らず、`image=None` はスカラーが返った。
呼び出し側の誤りは実行時の劣化ではないので、fail-soft の対象から外して即座に拒否する。
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

import backend_safe as bs   # noqa: E402
import fullseye as F        # noqa: E402

OP = "gauss_image"
IMG = np.linspace(0, 1, 32 * 32).reshape(32, 32)


def test_swapped_arguments_say_so():
    with pytest.raises(TypeError, match="swapped"):
        F.apply(OP, IMG, 0.5, 0.5)


def test_non_string_name_is_a_type_error_not_a_numpy_riddle():
    with pytest.raises(TypeError, match="name must be str"):
        F.apply(IMG, 3, 0.5, 0.5)
    with pytest.raises(TypeError, match="name must be str"):
        F.apply(IMG, None, 0.5, 0.5)


def test_none_image_is_refused():
    with pytest.raises(TypeError, match="image is None"):
        F.apply(None, OP, 0.5, 0.5)


@pytest.mark.parametrize("bad", ["big", None, [0.5], object()])
def test_non_numeric_knob_is_refused_whatever_the_policy(bad):
    for pol in ("fallback", "warn", "raise"):
        with pytest.raises(TypeError, match="must be a number"):
            F.apply(IMG, OP, bad, 0.5, on_error=pol)
        with pytest.raises(TypeError, match="must be a number"):
            F.apply(IMG, OP, 0.5, bad, on_error=pol)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_knob_is_refused_whatever_the_policy(bad):
    for pol in ("fallback", "warn", "raise"):
        with pytest.raises(ValueError, match="non-finite"):
            F.apply(IMG, OP, bad, 0.5, on_error=pol)


def test_out_of_range_knob_is_clamped_and_recorded_or_refused():
    bs.clear_fallbacks()
    m = bs.mark()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = F.apply(IMG, OP, 5.0, 0.5)
    ref = F.apply(IMG, OP, 1.0, 0.5)
    assert np.array_equal(np.asarray(out), np.asarray(ref)), "5.0 は 1.0 に切り詰められるはず"
    ev = bs.events_since(m)
    assert ev and ev[0]["source"] == "input" and "outside 0..1" in ev[0]["error"], "記録されていない"
    with pytest.raises(ValueError, match="outside 0..1"):
        F.apply(IMG, OP, 5.0, 0.5, on_error="raise")


def test_bool_and_int_knobs_are_accepted_as_numbers():
    a = F.apply(IMG, OP, True, 0.5)
    b = F.apply(IMG, OP, 1, 0.5)
    c = F.apply(IMG, OP, 1.0, 0.5)
    assert np.array_equal(np.asarray(a), np.asarray(c)) and np.array_equal(np.asarray(b), np.asarray(c))


def test_the_normal_call_is_untouched():
    """規約検査は正しい呼び出しの結果を 1 ビットも変えない。"""
    x = F.apply(IMG, OP, 0.3, 0.7)
    y = F.apply(IMG, OP, 0.3, 0.7)
    assert np.array_equal(np.asarray(x), np.asarray(y))
    assert np.asarray(x).shape == IMG.shape


def test_nary_path_also_validates_knobs():
    """n-ary 層(`add_image` 等、入力がリスト)も同じ入口を通る。"""
    import api
    assert "add_image" in api._nary_by_name(), "n-ary の代表 op が無い(検査の前提が違う)"
    with pytest.raises(TypeError, match="must be a number"):
        F.apply([IMG, IMG], "add_image", "big", 0.5)
    with pytest.raises(ValueError, match="non-finite"):
        F.apply([IMG, IMG], "add_image", float("nan"), 0.5)
    out = F.apply([IMG, IMG], "add_image", 0.5, 0.5)          # 正常経路は通る
    assert np.asarray(out).shape == IMG.shape
