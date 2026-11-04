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


# ---------------------------------------------------------------------------
# K2: トーンマップが有限の大きな放射輝度で NaN を返した
# ---------------------------------------------------------------------------

_HUGE = [1e10, 1e154, 1e155, 1e200, 1e307, 1e308]


def test_k2_tonemap_aces_is_one_for_huge_finite_radiance():
    import render_tonemap as RT
    assert len(_HUGE) == 6
    for v in _HUGE:
        out = RT.tonemap_aces(np.full((2, 2), v))
        # 真値: f(x) >= 1 for x >= 7.24 → クリップで 1.0(docstring の [0, 1] の約束)
        assert np.all(out == 1.0), (v, out)


@pytest.mark.parametrize("kw", [{}, {"exposure": 10.0}, {"white": 2.0}, {"white": 1e200},
                                {"white": 1e-200, "exposure": 10.0}])
def test_k2_tonemap_reinhard_is_finite_in_unit_range_for_huge_input(kw):
    import render_tonemap as RT
    for v in _HUGE:
        out = RT.tonemap_reinhard(np.full((2, 2, 3), v), **kw)
        assert np.all(np.isfinite(out)) and np.all((out >= 0) & (out <= 1)), (v, kw, out)
        assert np.all(out > 0.99), (v, kw, out)


def test_k2_tonemap_values_in_normal_range_unchanged_against_closed_form():
    # 頭打ちは「1 に写る点より上」だけ: 通常域では閉じた式と一致する。
    import render_tonemap as RT
    x = np.linspace(0.0, 20.0, 2001).reshape(1, -1)
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    np.testing.assert_array_equal(RT.tonemap_aces(x), np.clip(x * (a * x + b) / (x * (c * x + d) + e), 0, 1))
    np.testing.assert_array_equal(RT.tonemap_reinhard(x), x / (1 + x))
    w = 3.0
    np.testing.assert_array_equal(RT.tonemap_reinhard(x, white=w),
                                  np.clip(x * (1 + x / (w * w)) / (1 + x), 0, 1))


def test_k2_sibling_driveenv_tone_map_huge_and_nonfinite():
    import driveenv as DE
    for v in (1e200, 1e307, 1e308):
        out = DE.tone_map(np.array([[v, v / 2, 0.0]]), 10.0)
        # 真値: 明るい画素は最大チャンネルを 1 に割る = 色の比 (1, 0.5, 0)
        np.testing.assert_allclose(out, [[1.0, 0.5, 0.0]], rtol=1e-12, atol=0)
    with pytest.raises(ValueError, match="finite"):
        DE.tone_map(np.array([[np.inf, 1.0, 0.0]]), 1.0)
    with pytest.raises(ValueError, match="finite"):
        DE.tone_map(np.array([[np.nan, 1.0, 0.0]]), 1.0)


# ---------------------------------------------------------------------------
# K3: Stokes の実現可能性検査に絶対床 +1e-12
# ---------------------------------------------------------------------------

# 1e-200 / 1e200: 2 乗の和が下溢れ・溢れる桁(兄弟: pol の計算)
_SCALES = [1.0, 1e-6, 1e-9, 1e-12, 1e-13, 1e-200, 1e200]


def test_k3_unphysical_stokes_refused_at_every_intensity_scale():
    import optics as O
    M = O.mueller_element("polarizer", 0.0)
    assert len(_SCALES) == 7
    for k in _SCALES:
        s = np.array([1.0, 2.0, 0.0, 0.0]) * k          # DoP = 2 はどの桁でも非物理
        with pytest.raises(ValueError, match="realisable"):
            O.stokes_analyze(s)
        with pytest.raises(ValueError, match="realisable"):
            O.mueller_apply(M, s)
        with pytest.raises(ValueError, match="unphysical"):
            O.mueller_apply(M, np.tile(s, (2, 2, 1)))


def test_k3_physical_stokes_accepted_at_every_intensity_scale():
    import optics as O
    M = O.mueller_element("polarizer", 0.0)
    for k in _SCALES:
        s = np.array([1.0, 1.0, 0.0, 0.0]) * k          # DoP = 1(境界)は受理
        assert O.stokes_analyze(s)["dop"] == pytest.approx(1.0, abs=1e-12)
        np.testing.assert_allclose(O.mueller_apply(M, s), s, rtol=1e-12, atol=0)
        np.testing.assert_allclose(O.mueller_apply(M, np.tile(s, (2, 2, 1)))[0, 0], s, rtol=1e-12, atol=0)


def test_k3_field_accepts_rounding_dust_in_dark_pixel_of_bright_field():
    # 屑の許容は場の明るさに対する相対量: 明るい場の中の暗い画素の屑は通す。
    import optics as O
    M = O.mueller_element("polarizer", 0.0)
    field = np.array([[[1.0, 0.5, 0.0, 0.0], [0.0, 1e-17, 0.0, 0.0]]])
    out = O.mueller_apply(M, field)
    assert np.all(np.isfinite(out))


def test_k3_polar_gpu_torch_cpu_matches_optics_rule():
    torch = pytest.importorskip("torch")
    import optics as O
    import polar_gpu as PG
    M = torch.tensor(O.mueller_element("polarizer", 0.0))
    for k in _SCALES:
        bad = torch.tensor(np.tile(np.array([1.0, 2.0, 0.0, 0.0]) * k, (3, 1)))
        with pytest.raises(ValueError, match="unphysical"):
            PG.mueller_apply_batch(M, bad)
        with pytest.raises(ValueError, match="unphysical"):
            PG.stokes_analyze_batch(bad)
        good = torch.tensor(np.tile(np.array([1.0, 1.0, 0.0, 0.0]) * k, (3, 1)))
        PG.mueller_apply_batch(M, good)
        assert float(PG.stokes_analyze_batch(good)["dop"][0]) == pytest.approx(1.0, abs=1e-12)
