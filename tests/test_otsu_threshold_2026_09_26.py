# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""大津のしきい値を argmax ビンの**上端**で取ることの門(2026-09-26)。

`docs/hardening/otsu-threshold-at-the-bin-midpoint.md` の直しに対応する回帰。

**なぜ 30 年物の門が全部通していたか**: 試験の入力に必ず雑音が載っていた。
雑音があると背景が多数のビンに散らばるので、argmax ビンの中点が背景の大半より
上に来て「だいたい合う」(902 対 900)。ここでは **雑音を載せない平らな板**を
使う —— `feedback_random_test_data_hides_structural_defects` の型そのもので、
構造のある入力を 1 本混ぜていれば出ていた欠陥だった。

門は 4 面すべてに置く: 中核 op (`ops._otsu`) / GPU 逐語移植 (`accel._otsu`) /
`segment_objects` が使う `detect._otsu_mask` / FScript の組み込み
(`fscript._b_binary_threshold`)。4 つとも同じ式を**別々に**書いていて、実際に
4 つとも同じ欠陥を持っていた —— 1 面だけ直すと、直したつもりのまま穴が 3 つ残る
([[feedback_a_fix_leaves_the_twin_surface_open]])。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import detect  # noqa: E402
import fscript  # noqa: E402
import ops  # noqa: E402

#: 板の形。20x20 の明部を 64x64 の背景に置く = 前景はちょうど 400 px。
_SIDE, _BOX, _FG_PIXELS = 64, 20, 400


def _plate(bg: float, fg: float) -> np.ndarray:
    """**雑音を載せない**二値の板。値は 2 種類しか無い。"""
    im = np.full((_SIDE, _SIDE), float(bg))
    im[22:22 + _BOX, 22:22 + _BOX] = float(fg)
    return im


#: 同じ板をアフィン変換したもの。大津のしきい値はアフィン変換に**等変**である
#: べきなので、どれでも答えは 400 px でなければならない。中点で切る実装は
#: ``(0.30, 0.90)`` だけ 4,096 px を返していた —— つまり「値が 2 種類だから」
#: ではなく、**背景の値がビンの境界のどちら側に落ちるか**で答えが変わっていた。
_PLATES = [(0.00, 1.00), (0.30, 0.90), (0.10, 0.60), (0.25, 0.75),
           (0.20, 0.80), (0.01, 0.99), (0.45, 0.55)]


@pytest.mark.parametrize("bg,fg", _PLATES)
def test_a_flat_plate_gives_exactly_the_bright_box(bg, fg):
    reg = ops._otsu(_plate(bg, fg), 0.0, 0.0)
    assert int(reg.sum()) == _FG_PIXELS, (
        "otsu が平らな板で %d px を前景にした(期待 %d)。しきい値が argmax ビンの"
        "内側にあると、そのビンに居る背景画素が前景へ漏れる"
        % (int(reg.sum()), _FG_PIXELS))


@pytest.mark.parametrize("bg,fg", _PLATES)
def test_the_three_implementations_of_otsu_agree(bg, fg):
    """同じ式を 3 か所に書いてある。1 つだけ直すと静かに割れる。"""
    im = _plate(bg, fg)
    core = ops._otsu(im, 0.0, 0.0).astype(bool)
    mask = detect._otsu_mask(im)
    assert np.array_equal(core, mask), "ops._otsu と detect._otsu_mask が割れた"


@pytest.mark.parametrize("bg,fg", _PLATES)
def test_the_fscript_builtin_agrees_with_the_core_op(bg, fg):
    """FScript の `binary_threshold` —— **4 面目**。

    ここだけ式の書き方が違う((k + 0.5)/256)ので、`mids[` を探しただけでは
    見つからない。綴りでなく**同じ問いに答える入口**を数えること。
    """
    im = _plate(bg, fg)
    got = int(fscript._b_binary_threshold(None, fscript._as_fimage(im)).area())
    assert got == _FG_PIXELS, "FScript の binary_threshold が %d px(期待 %d)" % (got, _FG_PIXELS)


def test_the_fscript_builtin_keeps_the_constant_frame_contract():
    assert int(fscript._b_binary_threshold(None, fscript._as_fimage(np.zeros((8, 8)))).area()) == 0
    assert int(fscript._b_binary_threshold(
        None, fscript._as_fimage(np.full((8, 8), 0.5))).area()) == 64


@pytest.mark.parametrize("bg,fg", _PLATES)
def test_the_gpu_port_agrees_with_the_core_op(bg, fg):
    torch = pytest.importorskip("torch", reason="accel._otsu は torch の経路")
    import accel  # noqa: WPS433 - torch がある時だけ import できる

    im = _plate(bg, fg)
    got = accel._otsu(torch.as_tensor(im[None], dtype=torch.float32), 0.0, 0.0, "cpu")
    assert np.array_equal(np.asarray(got[0], np.float64).astype(bool),
                          ops._otsu(im, 0.0, 0.0).astype(bool)), \
        "GPU 逐語移植が CPU と別の答えを出した"


def test_the_threshold_is_equivariant_under_an_affine_map():
    """``otsu(s*v + t)`` は ``otsu(v)`` と同じ region でなければならない。

    ★これが元の欠陥を一文で言い当てる: {0,1} の板を {0.3,0.9} にアフィン変換
    しただけで答えが 400 から 4,096 に変わっていた。
    """
    base = _plate(0.0, 1.0)
    want = ops._otsu(base, 0.0, 0.0)
    for scale, offset in ((0.6, 0.3), (0.5, 0.25), (0.98, 0.01), (0.1, 0.45)):
        got = ops._otsu(base * scale + offset, 0.0, 0.0)
        assert np.array_equal(got, want), \
            "s=%.2f t=%.2f のアフィン変換で region が変わった" % (scale, offset)


@pytest.mark.parametrize("bg,fg", _PLATES)
def test_skimage_gets_the_same_count(bg, fg):
    filters = pytest.importorskip("skimage.filters", reason="独立実装との突き合わせ")
    im = _plate(bg, fg)
    theirs = int((im > filters.threshold_otsu(im)).sum())
    assert int(ops._otsu(im, 0.0, 0.0).sum()) == theirs


@pytest.mark.parametrize("bg,fg", _PLATES)
def test_opencv_gets_the_same_count(bg, fg):
    cv2 = pytest.importorskip("cv2", reason="2 つ目の独立実装との突き合わせ")
    im = _plate(bg, fg)
    u8 = np.round(np.clip(im, 0, 1) * 255).astype(np.uint8)
    _t, m = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    assert int(ops._otsu(im, 0.0, 0.0).sum()) == int((m > 0).sum())


def test_the_midpoint_spelling_is_what_the_gate_catches():
    """★門を壊して確かめる —— 直す前の式に戻すと、上の板の門が落ちること。

    落ちない門は「直した」の証拠にならない。
    """
    im = _plate(0.30, 0.90)
    x = np.clip(np.asarray(im, np.float64), 0, 1)
    hist, edges = np.histogram(x, 256, (0.0, 1.0))
    p = hist.astype(np.float64) / max(1, hist.sum())
    omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2
    mu = np.cumsum(p * mids)
    den = omega * (1 - omega)
    sb = np.where(den > 1e-12, (mu[-1] * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    k = int(np.argmax(sb))
    old = int((x > mids[k]).sum())
    assert old == _SIDE * _SIDE, "中点で切る式が全画素を前景にしない = 探針が板でない"
    assert int((x >= edges[k + 1]).sum()) == _FG_PIXELS


def test_the_argmax_bin_belongs_to_the_background():
    """欠陥の**理由**を固定する: argmax が指すのは背景の山を含むビン。

    だから「そのビンの中」で切ると背景画素が前景に混ざる。上端で切れば
    argmax ビンの画素は全部背景側に落ちる。
    """
    im = _plate(0.30, 0.90)
    hist, edges = np.histogram(im, 256, (0.0, 1.0))
    p = hist.astype(np.float64) / hist.sum()
    omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2
    mu = np.cumsum(p * mids)
    den = omega * (1 - omega)
    sb = np.where(den > 1e-12, (mu[-1] * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    k = int(np.argmax(sb))
    assert hist[k] == _SIDE * _SIDE - _FG_PIXELS, "argmax ビンに背景画素が丸ごと居る"
    assert edges[k] <= 0.30 < edges[k + 1]


def test_a_constant_image_keeps_its_documented_answer():
    """定数画像は分ける山が無い。docstring の約束(0 なら背景、正なら前景)を保つ。

    ★ビン格子で決めさせない: しきい値をビン上端にすると ``[0,1]`` の外の定数
    (例 5.0)が背景に落ちてしまい、約束が範囲によって変わっていた。
    """
    for value, want in ((0.0, 0.0), (0.002, 1.0), (0.5, 1.0), (1.0, 1.0),
                        (5.0, 1.0), (255.0, 1.0)):
        got = ops._otsu(np.full((8, 8), value), 0.0, 0.0)
        assert float(got.min()) == float(got.max()) == want, \
            "定数 %g の答えが %g(期待 %g)" % (value, float(got.max()), want)
    neg = ops._otsu(np.full((8, 8), -3.0), 0.0, 0.0)
    assert float(neg.max()) == 0.0, "負の定数は前景にならない"


def test_a_plate_outside_the_unit_range_still_finds_the_box():
    """0..255 の板(8 bit 相当)でも 400 px。既存の注記の主張を板でも固定する。"""
    assert int(ops._otsu(_plate(0.30, 0.90) * 255.0, 0.0, 0.0).sum()) == _FG_PIXELS


def test_segment_objects_sees_one_box_not_one_frame():
    """★利用者が最初に踏む面: `segment_objects` が板で「1 個の対象」を返していた。

    中点で切ると画像全体が 1 つの連結成分になり、面積 4,096・重心が画像中心の
    「もっともらしい」記録が 1 件返る —— 例外も警告も出ない。
    """
    objs = detect.segment_objects(_plate(0.30, 0.90), min_area=4)
    assert len(objs) == 1
    area = objs[0]["area"] if isinstance(objs[0], dict) else objs[0].area
    assert int(area) == _FG_PIXELS, "面積が %s(期待 %d)" % (area, _FG_PIXELS)
