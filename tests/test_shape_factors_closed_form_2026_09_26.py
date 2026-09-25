# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""形状特徴を閉形式で採点する門(2026-09-26)。

`docs/hardening/compactness-saturated-at-one.md` の直しに対応する回帰と、
`docs/KNOWN_ISSUES.md` §50 に書いた**測定値が本当にそうか**の確認。

★後者が要る理由: §50 は「解像度を上げても消えないバイアス」を表で主張している。
数字を書いた回の実行から離れると、説明文だけが古いまま残る
([[feedback_captions_drift_from_the_run_that_made_them]])。
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


def _rect(h, w, n=160, top=20, left=20):
    reg = np.zeros((n, n))
    reg[top:top + h, left:left + w] = 1.0
    return reg


def _disc(r, n=None):
    n = int(2 * r + 8) if n is None else n
    yy, xx = np.mgrid[:n, :n]
    c = n / 2.0
    return (((yy - c) ** 2 + (xx - c) ** 2) <= r * r).astype(np.float64)


def _feat(name, reg):
    return float(np.ravel(np.asarray(ops.RT[name](reg.copy(), 0.5, 0.5), np.float64))[0])


# --------------------------------------------------------------------------- #
# 閉形式で厳密に採れるもの
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("h,w", [(24, 16), (40, 40), (8, 60), (2, 100)])
def test_area_and_rectangularity_are_exact(h, w):
    n = 160
    reg = _rect(h, w, n)
    assert abs(_feat("area_frac", reg) - h * w / (n * n)) < 1e-12
    assert abs(_feat("rectangularity", reg) - 1.0) < 1e-12


# --------------------------------------------------------------------------- #
# 頭打ちの回帰
# --------------------------------------------------------------------------- #
def test_compactness_does_not_saturate_on_long_scratches():
    """★幅 2 px の傷を伸ばすと、数も伸び続けること。

    直す前は ``min(1.0, C/10)`` で、長さ 80 以上が**全部 1.0** だった ——
    傷や割れという、いちばん見たい領域で形が区別できていなかった。
    """
    prev = 0.0
    for length in (10, 40, 80, 110, 140):
        got = _feat("compactness", _rect(2, length, 200))
        assert got > prev + 0.5, (
            "長さ %d で compactness が伸びていない(%g -> %g)—— 頭打ちが戻っている"
            % (length, prev, got))
        prev = got
    assert prev > 20.0, "いちばん細長い傷でも %g しか出ていない" % prev


def test_compactness_matches_the_closed_form_shape():
    """op が返すのは ``周囲長²/(4π·面積)`` そのもの(スケールも切りも無い)。"""
    skm = pytest.importorskip("skimage.measure")
    for h, w in ((24, 16), (8, 60), (2, 100)):
        reg = _rect(h, w, 200)
        pr = skm.regionprops(reg.astype(int))[0]
        want = (pr.perimeter ** 2) / (4 * np.pi * max(pr.area, 1))
        assert abs(_feat("compactness", reg) - want) < 1e-9, \
            "%dx%d で式と一致しない" % (h, w)


def test_the_old_squash_is_what_the_gate_catches():
    """★門を壊して確かめる —— 旧式に戻すと上の門が落ちること。"""
    skm = pytest.importorskip("skimage.measure")
    vals = []
    for length in (80, 110, 140):
        reg = _rect(2, length, 200)
        pr = skm.regionprops(reg.astype(int))[0]
        raw = (pr.perimeter ** 2) / (4 * np.pi * max(pr.area, 1))
        vals.append(min(1.0, raw / 10))
    assert vals == [1.0, 1.0, 1.0], "旧式が頭打ちしない = 探針が細すぎる"
    assert len(set(vals)) == 1, "旧式では 3 つの別の形が同じ数になる"


def test_a_feature_is_not_required_to_stay_in_the_unit_range():
    """潰す理由が無かったことの根拠を門に残す(兄弟が既に 1 を超えている)。"""
    long_bar = _rect(2, 110, 128)
    over = []
    for name in ("elliptic_axis", "r3_region_features", "r2_runlength_features"):
        if name not in ops.RT:
            continue
        v = np.ravel(np.asarray(ops.RT[name](long_bar.copy(), 0.5, 0.5), np.float64))
        if v.size and float(v.max()) > 1.0:
            over.append(name)
    assert over, "region->feature で 1 を超える op が 1 つも無い —— 前提が変わった"


def test_the_two_compactness_entry_points_are_both_unbounded():
    """★同じ量に入口が 2 つある。**両方**が頭打ちしないこと。

    直す前は `r3_region_features` だけが素の値を返し、`compactness` が潰していた。
    """
    if "r3_region_features" not in ops.RT:
        pytest.skip("r3_region_features がこの版に無い")
    bar = _rect(2, 110, 200)
    a = _feat("compactness", bar)
    b = float(np.max(np.ravel(np.asarray(
        ops.RT["r3_region_features"](bar.copy(), 0.9, 0.0), np.float64))))
    assert a > 10.0 and b > 10.0, "片方が潰れている: compactness=%g / r3=%g" % (a, b)


# --------------------------------------------------------------------------- #
# KNOWN_ISSUES §50 に書いた測定が、いまも本当にそうか
# --------------------------------------------------------------------------- #
def test_the_perimeter_bias_is_still_what_the_doc_says():
    """★説明文の数字を、実行と突き合わせる。

    §50 は「2 つの推定量が逆の形で外し、解像度を上げても消えない」と主張する。
    主張が古くなったら(skimage が直したら)ここが落ちて、文書を直せと言う。
    """
    skm = pytest.importorskip("skimage.measure")
    d = _disc(96).astype(np.uint8)
    true_p = 2 * np.pi * 96
    assert skm.perimeter(d) / true_p > 1.04, "円で perimeter のバイアスが消えた"
    assert abs(skm.perimeter_crofton(d) / true_p - 1.0) < 0.01, "円で crofton が外れた"

    n = 128
    sq = np.zeros((n + 8, n + 8), np.uint8)
    sq[4:4 + n, 4:4 + n] = 1
    true_p = 4.0 * n
    assert abs(skm.perimeter(sq) / true_p - 1.0) < 0.01, "正方形で perimeter が外れた"
    assert skm.perimeter_crofton(sq) / true_p < 0.96, "正方形で crofton のバイアスが消えた"


def test_the_doc_records_the_open_decision():
    """§50 が「記録のみ・判断待ち」であることを文書側にも固定する。"""
    txt = open(os.path.join(ROOT, "docs", "KNOWN_ISSUES.md"), encoding="utf-8").read()
    assert "§50" in txt
    assert "perimeter_crofton" in txt
    assert "決めていないこと" in txt, "判断待ちであることが書かれていない"
