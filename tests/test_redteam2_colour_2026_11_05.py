# -*- coding: utf-8 -*-
"""敵対的検証 2026-11-05 第 2 巡(colour)K1〜K8 の回帰テスト。

各テストは報告の再現を、真値・不変量・独立実装と突き合わせる形にしてある。
"""
from __future__ import annotations

import numpy as np
import pytest

import colortransport as CT
import imgmetrics as M


# ---------------------------------------------------------------------------
# K1: color_transfer の「一定のチャネル」の床が絶対値だった
# ---------------------------------------------------------------------------

def _achromatic_gradient():
    g = np.linspace(0.05, 0.95, 64)
    return np.repeat(np.repeat(g[None, :, None], 16, 0), 3, 2)


def _colourful_ref():
    rng = np.random.default_rng(0)
    return np.clip(rng.normal([0.6, 0.4, 0.3], 0.15, (32, 32, 3)), 0, 1)


def test_k1_achromatic_src_lab_chroma_is_only_rounding_residue():
    # 前提: 無彩色の Lab a*/b* は数学的に 0。残るのは丸め屑だけ(L の広がりの 1e-6 未満)。
    lab = M.rgb_to_lab(_achromatic_gradient()).reshape(-1, 3)
    assert lab[:, 0].std() > 10.0
    assert lab[:, 1:].std(axis=0).max() < 1e-4


def test_k1_reinhard_lab_refuses_constant_chroma_of_grey_src():
    # 修正前: 屑(std 3.9e-6)を数百万倍して a* -24..61 の偽の色を返した。
    with pytest.raises(ValueError, match="constant"):
        CT.color_transfer(_achromatic_gradient(), _colourful_ref(), "reinhard", "lab")


def test_k1_histogram_lab_maps_constant_chroma_like_exact_constant():
    # 不変量: 一定のチャネルは参照の平均 1 点へ写る(ties="average" で厳密に一定な
    # 入力が写る先と同じ)。修正前は a* が -45..58 に散った。
    src, ref = _achromatic_gradient(), _colourful_ref()
    out = CT.color_transfer(src, ref, "histogram", "lab")
    lo = M.rgb_to_lab(out).reshape(-1, 3)
    assert np.ptp(lo[:, 1]) < 1e-6 and np.ptp(lo[:, 2]) < 1e-6
    # 独立に: 厳密に一定な a* を histogram_match に通した結果(参照 a* の平均)
    rv = M.rgb_to_lab(ref).reshape(-1, 3)
    exact = CT.histogram_match(np.zeros(src.shape[0] * src.shape[1]), rv[:, 1])
    assert np.ptp(exact) == 0.0
    # L は単調に保たれる(階調は運ばれている)
    L = M.rgb_to_lab(out)[0, :, 0]
    assert np.all(np.diff(L) >= -1e-9)


def test_k1_reinhard_refuses_flat_patch_with_float_noise():
    rng = np.random.default_rng(0)
    src = 0.5 + 1e-9 * rng.standard_normal((32, 32, 3))
    with pytest.raises(ValueError, match="constant"):
        CT.color_transfer(src, _colourful_ref(), "reinhard", "rgb")


def test_k1_rgb_space_grey_gradient_still_transfers():
    # 過剰な拒否をしない: rgb 空間では無彩色の勾配も各チャネルに広がりがある。
    out = CT.color_transfer(_achromatic_gradient(), _colourful_ref(), "reinhard", "rgb")
    assert np.all(np.isfinite(out)) and out.shape == (16, 64, 3)
