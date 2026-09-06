# -*- coding: utf-8 -*-
"""``[0,1]`` の外の入力を clip して**静かに壊す** op を捕まえる門。

2026-09-06、植生被覆率の PoC が「同じ画像を 4095 倍しただけで大津の判定が
13 pp ずれる」と報告してきたのを追ったら、原因は 1 行でした ——
``np.clip(v, 0, 1)``。

* ``ops._otsu`` は ``[0,1]`` の 256 ビン固定でヒストグラムを張っていた。
  0..255 の float(8 bit 相当。**まったく普通の入力**)を渡すと全画素が 1 に
  飽和し、しきい値が意味を失って「全画素が前景」を返す。正解との IoU が
  **1.0000 -> 0.2578**。警告も例外も出ない。
* ``ops._equalize`` も同じ形で、CDF が全部 1 になり平坦化が恒等に化けていた。
* ``backends._u8`` も同じ 1 行。この関数は backends.py だけで **23 op** が
  通るので、``cv_otsu`` を筆頭に同じ穴が横に並んでいた。

大津のしきい値は**アフィン変換に等変**であるべきなので、これは仕様ではなく
穴です。直し方は「範囲外のときだけ実データの範囲を使う」——
``[0,1]`` に収まっている入力の結果は 1 ビットも変えていません。

この門が見るのは「値域を変えただけで答えが変わらないこと」だけです。
op ごとの正しさではなく、**入力の単位系に対する不変性**を見ています。
"""
from __future__ import annotations

import numpy as np
import pytest

import backends
import fullseye as fs


def _bimodal():
    """二山の構造データ。乱数だけの絵は「対称性の破れ」を隠すので使わない。"""
    rng = np.random.default_rng(0)
    img = np.full((64, 64), 0.20)
    img[20:44, 10:54] = 0.70
    img += rng.normal(0, 0.03, img.shape)
    truth = np.zeros((64, 64), bool)
    truth[20:44, 10:54] = True
    return img, truth


def _iou(mask, truth):
    return float((mask & truth).sum()) / max(int((mask | truth).sum()), 1)


def _as_mask(out):
    a = np.asarray(out, np.float64)
    return a > (a.max() / 2 if a.max() > 1 else 0.5)


#: 大津は 3 実装ある。**同じアルゴリズムを名乗るなら同じ答えを返すべき**で、
#: 少なくとも「入力を定数倍しただけで答えが変わらない」ことは共通の要求。
_OTSU_OPS = ["otsu", "sk_otsu", "cv_otsu"]


@pytest.mark.parametrize("name", _OTSU_OPS)
def test_otsu_is_equivariant_under_scaling(name):
    """入力を 1 / 4 / 255 / 4095 倍しても判定が動かないこと。"""
    img, truth = _bimodal()
    base = _iou(_as_mask(fs.apply(img, name)), truth)
    assert base > 0.9, "%s: そもそも [0,1] で当たっていない (IoU %.4f)" % (name, base)
    for k in (4.0, 255.0, 4095.0):
        got = _iou(_as_mask(fs.apply(img * k, name)), truth)
        assert abs(got - base) < 0.02, (
            "%s: 入力を %g 倍しただけで IoU が %.4f -> %.4f に動いた。"
            "大津のしきい値はアフィン変換に等変であるべき。" % (name, k, base, got)
        )


def test_equalize_does_not_collapse_outside_unit_range():
    """``equalize`` が 8 bit 相当の入力で恒等に化けないこと。"""
    img, _ = _bimodal()
    out = np.asarray(fs.apply(img * 255.0, "equalize"), np.float64)
    assert out.max() - out.min() > 0.5, (
        "equalize が定数を返した(範囲 %.4f..%.4f)。CDF が全部 1 に飽和している。"
        % (out.min(), out.max())
    )


def test_u8_helper_stretches_instead_of_saturating():
    """``backends._u8`` が範囲外を潰さないこと —— 23 op が通る 1 か所。"""
    ramp = np.linspace(0.0, 255.0, 256).reshape(16, 16)
    got = backends._u8(ramp)
    assert got.min() == 0 and got.max() == 255, (
        "0..255 の float が %d..%d に潰れた" % (got.min(), got.max()))
    assert len(np.unique(got)) > 200, (
        "階調が %d 段しか残っていない(飽和している)" % len(np.unique(got)))


def test_u8_helper_is_bit_identical_inside_unit_range():
    """**[0,1] の中では 1 ビットも変えていない**こと(直し方の約束)。"""
    rng = np.random.default_rng(1)
    v = rng.random((32, 32))
    assert np.array_equal(backends._u8(v), (np.clip(v, 0, 1) * 255).astype(np.uint8))


def test_u8_helper_handles_constant_and_empty():
    """定数画像で 0 除算しないこと(範囲が 0 の場合)。"""
    assert np.all(backends._u8(np.full((4, 4), 7.0)) == 0)
    assert backends._u8(np.zeros((0, 0))).shape == (0, 0)
