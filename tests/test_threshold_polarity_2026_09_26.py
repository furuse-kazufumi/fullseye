# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""しきい値 op の**極性** —— region になるのは明るい側(2026-09-26)。

`otsu` の直しで使った「雑音を載せない板」を族全体に当てたところ、SimpleITK 由来の
3 本(`xsitk_huang_thresh` / `xsitk_maxentropy_thresh` / `xsitk_moments_thresh`)が
**兄弟 op の補集合**を返していた —— 明部 400 px の板で 3,696 px(= 4096 - 400)。
例外も警告も無く、`region_area` に渡せば 9 倍の面積が「もっともらしく」返る。

原因は ITK の規約: ``insideValue`` は**しきい値以下**の側(暗い方)に付く。
recipe が ``(img, 1, 0, bins)`` と書いていたので、暗い側が 1 になっていた。
SimpleITK 自身の ``OtsuThreshold`` も同じ規約なので、これは SimpleITK の不具合では
なく**こちらの呼び方**の誤り(2026-09-26 に一次情報で確認)。

この試験が守るのは「どの方法を使っても、region になるのは明るい側」という
**族としての約束**。方法ごとにしきい値が違うのは構わないが、**向きが違うのは困る**
—— パイプラインの次の段は向きを知らないからである。
"""
from __future__ import annotations

import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ops  # noqa: E402

_SIDE, _BOX, _FG = 64, 20, 400

#: しきい値「方法」の名前。★op 名から拾うので、**新しく足した方法も自動で門に入る**
#: (免除台帳に名前を書かない限り)。綴りで探す門は綴りが違うものを見逃すので、
#: 説明文も一緒に見る。
_METHOD = re.compile(
    r"otsu|huang|triangle|isodata|yen|(?:^|_)li(?:_|$)|minimum_thresh|binary_threshold"
    r"|auto_threshold|sauvola|niblack|bernsen|mean_thresh|multiotsu|kapur"
    r"|entropy_thresh|moments_thresh", re.I)

#: ★**暗い側が答えで正しい op**。理由つきで名指しする —— 台帳が黙って腐らないよう、
#: 下の試験が「本当にまだ暗い側なのか」を確かめる。
_DARK_BY_DESIGN: dict = {}


def _plate(bg=0.0, fg=1.0):
    im = np.full((_SIDE, _SIDE), float(bg))
    im[22:22 + _BOX, 22:22 + _BOX] = float(fg)
    return im


_BOX_MASK = np.zeros((_SIDE, _SIDE), bool)
_BOX_MASK[22:22 + _BOX, 22:22 + _BOX] = True


def _threshold_ops():
    return sorted(o.name for o in ops._BY_NAME.values()
                  if o.in_sort == "image" and o.out_sort == "region"
                  and _METHOD.search(o.name))


def _region_of(name, im):
    return np.asarray(ops.RT[name](im.copy(), 0.5, 0.5), np.float64) > 0.5


def _rates(name, im=None):
    r = _region_of(name, _plate() if im is None else im)
    return float(r[_BOX_MASK].mean()), float(r[~_BOX_MASK].mean())


def test_the_family_is_not_empty_and_covers_the_known_methods():
    """門が何も見ていない状態で緑になるのを防ぐ。"""
    names = _threshold_ops()
    assert len(names) >= 12, "しきい値 op が %d 本しか見つからない: %s" % (len(names), names)
    for must in ("otsu", "sk_otsu", "cv_otsu", "xsitk_huang_thresh",
                 "xsitk_maxentropy_thresh", "xsitk_moments_thresh"):
        assert must in names, "%r が族から漏れている" % must


@pytest.mark.parametrize("name", _threshold_ops())
def test_the_region_is_the_bright_side(name):
    """★族としての約束: 明るい箱の方が region になる。

    方法ごとにしきい値が違うのは構わない(だから被覆率で見る)。**向き**が違うと、
    次の段が黙って別のものを測る。
    """
    if name in _DARK_BY_DESIGN:
        pytest.skip(_DARK_BY_DESIGN[name])
    inside, outside = _rates(name)
    assert inside > outside + 0.4, (
        "%s: 箱の中 %.1f%% / 外 %.1f%% —— 暗い側を region にしている疑い"
        % (name, 100 * inside, 100 * outside))


#: 大域の自動しきい値は、値が 2 種類しかない板で**ちょうど箱**を返すべきである
#: (局所適応のものは窓の中で決めるので、平らな面では外れてよい)。
_EXACT = ["otsu", "sk_otsu", "cv_otsu", "sk_yen", "sk_li", "binary_threshold",
          "auto_threshold", "xsitk_huang_thresh", "xsitk_maxentropy_thresh",
          "xsitk_moments_thresh"]


@pytest.mark.parametrize("name", _EXACT)
def test_a_global_automatic_threshold_gets_the_box_exactly(name):
    if name not in ops.RT:
        pytest.skip("%s はこの版に無い" % name)
    got = int(_region_of(name, _plate()).sum())
    assert got == _FG, "%s が %d px(期待 %d)" % (name, got, _FG)


@pytest.mark.parametrize("name", _EXACT)
def test_they_all_agree_with_each_other(name):
    """★兄弟が真値になる。方法が違っても、この板では答えが割れる余地が無い。"""
    if name not in ops.RT:
        pytest.skip("%s はこの版に無い" % name)
    assert np.array_equal(_region_of(name, _plate()), _region_of("otsu", _plate())), \
        "%s と otsu が同じ板で違う region を返した" % name


def test_the_complement_is_what_the_gate_catches():
    """★門を壊して確かめる —— 補集合を返す実装がこの門を通らないこと。

    落ちない門は「直した」の証拠にならない。直す前の 3 本はちょうどこれだった。
    """
    r = _region_of("otsu", _plate())
    flipped = ~r
    inside, outside = float(flipped[_BOX_MASK].mean()), float(flipped[~_BOX_MASK].mean())
    assert not (inside > outside + 0.4), "補集合が極性の門を通ってしまう"
    assert int(flipped.sum()) == _SIDE * _SIDE - _FG == 3696


def test_the_dark_side_ledger_names_ops_that_really_are_dark():
    """免除は「本当にまだ暗い側なのか」を確かめてから許す(台帳を腐らせない)。"""
    stale = []
    for name in _DARK_BY_DESIGN:
        if name not in ops.RT:
            stale.append((name, "op が無い"))
            continue
        inside, outside = _rates(name)
        if inside > outside + 0.4:
            stale.append((name, "もう明るい側を返している —— 免除から外すこと"))
    assert not stale, "免除台帳が古い: %s" % stale


def test_the_itk_convention_is_the_one_we_had_wrong():
    """★一次情報を門に固定する: ITK の ``insideValue`` は**しきい値以下**の側。

    この 1 行を知らないと、`(img, 1, 0, bins)` は「前景を 1 にした」と読める。
    SimpleITK が手元に無い環境では skip(結論は上の族の門が守る)。
    """
    sitk = pytest.importorskip("SimpleITK", reason="一次情報の確認")
    f = sitk.OtsuThresholdImageFilter()
    f.SetInsideValue(1)
    f.SetOutsideValue(0)
    out = np.asarray(sitk.GetArrayFromImage(
        f.Execute(sitk.GetImageFromArray(_plate().astype("float32")))))
    assert int((out == 1).sum()) == _SIDE * _SIDE - _FG, (
        "ITK の insideValue が明るい側に付いている —— 規約が変わったなら "
        "backends_r3.py の recipe の 0,1 を見直すこと")
