# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""特徴 op は、入力を変えたら出力も変わること(2026-09-26)。

★この型は**1 枚の探針では原理的に出ない**。値域([0,1])も有限性も決定性も、
潰れた出力はすべて満たす —— むしろ「きれいに収まっている」ように見える。
潰れを見つけるには「入力を変えたら出力も変わるか」を問う必要があり、そのためには
形を 1 つでなく**列**で渡さねばならない([[feedback_one_probe_input_is_not_coverage]])。

この門が実際に見つけたもの(2026-09-26):

| op | 症状 |
|---|---|
| `height_width_ratio` | `min(1, H/W)` で**縦長の対象が全部 1.0**(60x20 -> 1.0、真値 3.0) |
| `moments_region_2nd` ほか 6 本 | `min(1, ...)` で細長い形が全部 1.0 |
| `moments_xld` | 同上(輪郭版にも同じ欠陥) |

★**判定は「どれか 1 つの族で動けば合格」**。特徴があらゆる変形に応答する必要は
無い —— 対称な矩形では奇数次モーメントが厳密に 0 になるのは**正しい**。最初は
「全族で動くこと」を求めて 31 本落としたが、その大半は**探針が対称すぎた**だけ
だった。非対称な族(三角・L 字)と穴の族を足すと、免除は 1 本まで減った。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ops  # noqa: E402

_N = 200


def _rect(h, w):
    reg = np.zeros((_N, _N))
    reg[_N // 2 - h // 2:_N // 2 + h // 2, _N // 2 - w // 2:_N // 2 + w // 2] = 1.0
    return reg


def _triangle(k):
    """直角三角形。``k`` が大きいほど鈍る(**非対称**なので奇数次モーメントが動く)。"""
    reg = np.zeros((_N, _N))
    for i in range(80):
        reg[60 + i, 60:60 + max(1, int((80 - i) * k / 10))] = 1.0
    return reg


def _ell(arm):
    """L 字。``arm`` が腕の長さ(凸性・矩形度が動く)。"""
    reg = np.zeros((_N, _N))
    reg[60:140, 60:80] = 1.0
    reg[120:140, 60:60 + arm] = 1.0
    return reg


def _blobs(k):
    """離れた塊を ``k`` 個置く(連結成分を数える op が動く)。"""
    reg = np.zeros((_N, _N))
    for i in range(k):
        r0 = 30 + (i % 5) * 32
        c0 = 30 + (i // 5) * 32
        reg[r0:r0 + 18, c0:c0 + 18] = 1.0
    return reg


def _holes(k):
    """穴を ``k`` 個あけた板(オイラー数・穴の面積が動く)。"""
    reg = np.zeros((_N, _N))
    reg[50:150, 50:150] = 1.0
    for i in range(k):
        r0 = 60 + (i % 4) * 22
        c0 = 60 + (i // 4) * 22
        reg[r0:r0 + 10, c0:c0 + 10] = 0.0
    return reg


#: ★族は**6 つ**。対称な矩形だけだと、対称性で消える特徴(奇数次モーメント)や
#: 穴を数える特徴(オイラー数)が原理的に動かず、「潰れている」と区別できない。
_FAMILIES = {
    "横長": [_rect(4, length) for length in (10, 20, 40, 80, 120, 160)],
    "縦長": [_rect(length, 4) for length in (10, 20, 40, 80, 120, 160)],
    "三角": [_triangle(k) for k in (2, 4, 6, 8, 10, 12)],
    "L字": [_ell(arm) for arm in (25, 45, 65, 85, 105, 125)],
    "穴": [_holes(k) for k in (1, 2, 4, 6, 8, 12)],
    "個数": [_blobs(k) for k in (1, 2, 4, 7, 11, 15)],
}

#: ★**どの族でも一定で、それが正しい op**。理由つきで名指しし、下の試験が
#: 「本当にまだ一定か」を確かめる —— 動くようになったら外させられる。
_CONSTANT_BY_DESIGN = {
    "hx_distance_sc": "2 つの輪郭の距離を測る op。単独の輪郭では常に 0 に退化する",
    "hx_test_closed_xld": "ここで作る輪郭は常に閉じている",
    "hx_test_self_intersect": "単純な形の輪郭は自己交差しない",
    "hx_full_domain": "定義上、常に画像全体",
    "hx_get_domain": "同上",
}


def _value(name, x):
    v = np.ravel(np.asarray(ops.RT[name](x, 0.5, 0.5), np.float64))
    return float(v[0]) if v.size else float("nan")


def _series(name, family, to_contour=False):
    out = []
    for reg in family:
        x = reg.copy()
        if to_contour:
            x = ops.RT["gen_contour_region_xld"](x, 0.5, 0.5)
        out.append(_value(name, x))
    return out


def _moves(vals):
    """末尾 3 つが完全に同じなら「止まっている」。"""
    if not vals or any(not np.isfinite(v) for v in vals):
        return None                       # 判定しない(この族を受け取れない)
    return len({round(v, 12) for v in vals[-3:]}) > 1


def _feature_ops(in_sort):
    return sorted(o.name for o in ops._BY_NAME.values()
                  if o.in_sort == in_sort and o.out_sort == "feature")


def _scan(name, to_contour):
    """(動いた族, 止まった族)。"""
    moved, stuck = [], []
    for key, family in _FAMILIES.items():
        try:
            vals = _series(name, family, to_contour=to_contour)
        except Exception:                                    # noqa: BLE001
            continue
        verdict = _moves(vals)
        if verdict is None:
            continue
        (moved if verdict else stuck).append((key, vals))
    return moved, stuck


@pytest.mark.parametrize("name", _feature_ops("region"))
def test_a_region_feature_responds_to_at_least_one_deformation(name):
    if name in _CONSTANT_BY_DESIGN:
        pytest.skip(_CONSTANT_BY_DESIGN[name])
    moved, stuck = _scan(name, to_contour=False)
    if not moved and not stuck:
        pytest.skip("%s はどの族も受け取れない" % name)
    assert moved, (
        "%s がどの族でも止まっている —— 形が違うのに同じ数を返している: %s"
        % (name, {k: [round(v, 4) for v in vals] for k, vals in stuck}))


@pytest.mark.parametrize("name", _feature_ops("contour"))
def test_a_contour_feature_responds_to_at_least_one_deformation(name):
    if name in _CONSTANT_BY_DESIGN:
        pytest.skip(_CONSTANT_BY_DESIGN[name])
    if "gen_contour_region_xld" not in ops.RT:
        pytest.skip("輪郭への変換 op が無い")
    moved, stuck = _scan(name, to_contour=True)
    if not moved and not stuck:
        pytest.skip("%s はどの族も受け取れない" % name)
    assert moved, (
        "%s がどの族でも止まっている: %s"
        % (name, {k: [round(v, 4) for v in vals] for k, vals in stuck}))


def test_the_constant_ledger_names_ops_that_really_are_constant():
    """★免除台帳が腐らないこと —— 動くようになったら外させる。"""
    stale = []
    for name in _CONSTANT_BY_DESIGN:
        if name not in ops.RT:
            continue
        to_c = ops._BY_NAME[name].in_sort == "contour"
        moved, _stuck = _scan(name, to_contour=to_c)
        if moved:
            stale.append((name, moved[0][0]))
    assert not stale, "もう一定ではない: %s —— 免除台帳から外すこと" % stale


def test_the_probe_would_catch_a_squashed_feature():
    """★門を壊して確かめる —— ``min(1, ...)`` を掛けた値はこの門を通らないこと。"""
    raw = [float((_rect(4, length) > 0.5).sum()) / 200.0
           for length in (10, 20, 40, 80, 120, 160)]
    squashed = [min(1.0, v) for v in raw]
    assert _moves(raw), "素の値が止まっている = 探針が弱い"
    assert not _moves(squashed), "潰した値を門が見逃す(%s)" % squashed


def test_height_width_ratio_reports_tall_objects_honestly():
    """★この門が最初に見つけたもの。縦長の比は 1 を超える。"""
    for h, w, want in ((20, 60, 1 / 3), (60, 20, 3.0), (160, 4, 40.0)):
        got = _value("height_width_ratio", _rect(h, w))
        assert abs(got - want) < 0.05 * max(want, 1.0), \
            "%dx%d の比が %.4f(真値 %.4f)" % (h, w, got, want)


def test_the_moment_features_keep_growing_on_long_shapes():
    """★moments 族の頭打ち回帰。"""
    for name in ("moments_region_2nd", "moments_region_central", "moments_xld"):
        if name not in ops.RT:
            continue
        to_c = ops._BY_NAME[name].in_sort == "contour"
        vals = _series(name, _FAMILIES["横長"], to_contour=to_c)
        assert vals[-1] > vals[2] + 0.5, "%s が伸びていない: %s" % (name, vals)
