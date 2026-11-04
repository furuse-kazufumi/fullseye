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


# ---------------------------------------------------------------------------
# K4: フォトメトリックステレオのアルベド床が絶対 1e-8
# ---------------------------------------------------------------------------

def _ps_sphere():
    H = W = 24
    yy, xx = np.mgrid[0:H, 0:W]
    x = (xx - W / 2 + 0.5) / (W / 2.2)
    y = (yy - H / 2 + 0.5) / (H / 2.2)
    z2 = 1 - x * x - y * y
    m = z2 > 0.05
    n = np.dstack([x, y, np.sqrt(np.clip(z2, 0, 1))])
    n[~m] = (0, 0, 1)
    L = np.array([[0.3, 0.2, 1], [-0.3, 0.25, 1], [0.1, -0.35, 1], [-0.2, -0.2, 1], [0.35, -0.05, 1]], float)
    Ln = L / np.linalg.norm(L, axis=1, keepdims=True)
    I = np.stack([0.8 * np.clip(n @ l, 0, None) for l in Ln])
    m = m & (I > 1e-3).all(0)                # 全灯で照らされた画素 = 線形モデルが厳密
    return I, L, n, m


def _max_angle_deg(nn, n, m):
    d = np.clip((np.asarray(nn, float)[m] * n[m]).sum(-1), -1, 1)
    return float(np.degrees(np.arccos(d)).max())


_PS_SCALES = [1.0, 1e-6, 1e-8, 1e-9, 1e-12]


def test_k4_photometric_stereo_normals_are_scale_invariant():
    import photometric as P
    I, L, n, m = _ps_sphere()
    assert m.sum() > 300
    assert len(_PS_SCALES) == 5
    for k in _PS_SCALES:
        nn, al = P.photometric_stereo(I * k, L)
        # 真値の法線と比べる(修正前: 1e-8 倍で全法線 (0,0,1)、誤差 74.5°)
        assert _max_angle_deg(nn, n, m) < 0.05, k
        np.testing.assert_allclose(al[m], 0.8 * k, rtol=1e-3)


def test_k4_sibling_photometric_stereo_robust_is_scale_invariant():
    import specularity as S
    I, L, n, m = _ps_sphere()
    for k in _PS_SCALES:
        nr = S.photometric_stereo_robust(I * k, L, method="median")[0]
        assert not np.isnan(nr[m]).any()
        assert _max_angle_deg(nr, n, m) < 0.05, k


def test_k4_sibling_gpu_kernel_floor_is_relative_torch_cpu():
    torch = pytest.importorskip("torch")
    import accel_typed as AT
    I, L, n, m = _ps_sphere()
    Ln = L / np.linalg.norm(L, axis=1, keepdims=True)
    H, W = m.shape
    fn = AT.k_photometric(torch.device("cpu"))
    for k in (1.0, 1e-8):
        nn, _al = fn((I * k).reshape(len(L), -1), np.linalg.pinv(Ln), H, W)
        assert _max_angle_deg(nn, n, m) < 0.05, k


def test_k4_all_dark_pixels_still_default_normal():
    import photometric as P
    I, L, _n, _m = _ps_sphere()
    nn, al = P.photometric_stereo(np.zeros_like(I), L)
    assert np.all(nn == np.array([0, 0, 1], np.float32)) and np.all(al == 0)


# ---------------------------------------------------------------------------
# K5: color_pca の RGB→HSV が無彩色に H = 2/3、絶対床で小さい値の H/S が歪む
# ---------------------------------------------------------------------------

def _hsv_cases():
    rng = np.random.default_rng(1)
    x = rng.random((50, 50, 3))
    x[0, :8] = [[1, 1, 0], [1, 0, 1], [0, 1, 1], [0.5, 0.5, 0.5], [0, 0, 0], [1, 1, 1],
                [0.2, 0.7, 0.7], [0.3, 0.3, 0.1]]
    return x


def _hue_dist(a, b):
    d = np.abs(a - b)
    return np.minimum(d, 1 - d)


def test_k5_color_pca_hsv_matches_skimage_including_achromatic():
    skc = pytest.importorskip("skimage.color")
    import color_pca as C
    x = _hsv_cases()
    for out in (C.trans_from_rgb(x, "hsv"), C.apply_color_trans_lut(x, C.create_color_trans_lut("rgb_to_hsv"))):
        ref = skc.rgb2hsv(x)
        assert _hue_dist(out[..., 0], ref[..., 0]).max() < 1e-12
        assert np.abs(out[..., 1:] - ref[..., 1:]).max() < 1e-12
    # 真値: 無彩色(灰・黒・白)の H と S は 0(修正前 H = 2/3)
    out = C.trans_from_rgb(x, "hsv")
    np.testing.assert_array_equal(out[0, 3:6, :2], 0.0)


def test_k5_hsv_is_scale_invariant_for_tiny_values_against_colorsys():
    import colorsys
    import color_pca as C
    import driveworld as D
    base = np.array([2.0, 1.0, 0.5])
    h0, s0, _ = colorsys.rgb_to_hsv(*base)
    scales = [1e-1, 1e-6, 1e-13, 1e-200]
    assert len(scales) == 4
    for k in scales:
        t = (base * k).reshape(1, 1, 3)
        a = C.trans_from_rgb(t, "hsv")[0, 0]
        d = D._rgb_to_hsv(t.reshape(1, 3))[0]
        for got in (a, d):
            assert got[0] == pytest.approx(h0, abs=1e-12), (k, got)
            assert got[1] == pytest.approx(s0, abs=1e-12), (k, got)


# ---------------------------------------------------------------------------
# K6: imgmetrics.linear_to_srgb が範囲外を黙って切り詰めた
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [[1.5, 0.2, 0.5], [-0.2, 0.5, 0.5], [np.nan, 0.5, 0.5], [np.inf, 0.0, 0.0]])
def test_k6_linear_to_srgb_refuses_like_its_pair_and_its_delegate(bad):
    import gfx2d as G
    v = np.array(bad, dtype=np.float64)
    with pytest.raises(ValueError):
        M.linear_to_srgb(v)
    # 一貫性: 委譲先(gfx2d)と対(srgb_to_linear)も同じ入力を拒否する
    with pytest.raises(ValueError):
        G.linear_to_srgb(v.reshape(1, 3))
    with pytest.raises(ValueError):
        M.srgb_to_linear(v)


def test_k6_linear_to_srgb_in_range_matches_gfx2d_and_tiny_overshoot_is_clipped():
    import gfx2d as G
    x = np.linspace(0.0, 1.0, 1001)
    np.testing.assert_array_equal(M.linear_to_srgb(x), G.linear_to_srgb(x.reshape(1, -1))[0])
    np.testing.assert_array_equal(M.linear_to_srgb(np.array([1.0 + 5e-7, -5e-7, 0.5])),
                                  M.linear_to_srgb(np.array([1.0, 0.0, 0.5])))


def test_k6_lab_to_rgb_still_clips_out_of_gamut_as_documented():
    # lab_to_rgb は色域外の切り詰めを約束している(例外は出ない)
    out = M.lab_to_rgb(np.array([50.0, 120.0, -120.0]))
    assert np.all((out >= 0) & (out <= 1))
    rt = M.lab_to_rgb(M.rgb_to_lab(np.array([0.2, 0.5, 0.8])))
    np.testing.assert_allclose(rt, [0.2, 0.5, 0.8], atol=1e-6)


# ---------------------------------------------------------------------------
# K7: 幅の広い整数 dtype の拒否文が自己矛盾していた
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dt", [np.int32, np.int64, np.uint64])
def test_k7_wide_integer_dtype_refusal_names_the_reason_not_a_contradiction(dt):
    with pytest.raises(ValueError) as ei:
        M.rgb_to_lab(np.array([0, 128, 255], dt))
    msg = str(ei.value)
    # 修正前: "(or be an integer dtype)" と言いながら整数 dtype を拒否していた
    assert "or be an integer dtype" not in msg
    assert np.dtype(dt).name in msg and "uint8" in msg


@pytest.mark.parametrize("dt", [np.int32, np.int64, np.uint64])
def test_k7_wide_integer_values_already_in_unit_range_pass_as_float(dt):
    # Python の整数リスト [1, 1, 1](= int64)は白: 従来どおり通る
    np.testing.assert_allclose(M.rgb_to_lab(np.array([1, 1, 1], dt)), M.rgb_to_lab([1.0, 1.0, 1.0]))


def test_k7_table_integer_dtypes_divide_by_max_and_negative_is_refused():
    np.testing.assert_allclose(M.rgb_to_lab(np.array([0, 128, 255], np.uint8)),
                               M.rgb_to_lab(np.array([0, 128, 255]) / 255.0))
    np.testing.assert_allclose(M.rgb_to_lab(np.array([0, 64, 127], np.int8)),
                               M.rgb_to_lab(np.array([0, 64, 127]) / 127.0))
    with pytest.raises(ValueError, match="negative"):
        CT.color_transfer(np.full((4, 4, 3), -3, np.int8), np.full((4, 4, 3), 3, np.int8), "reinhard", "rgb")


# ---------------------------------------------------------------------------
# K8: annotate._luma_field の docstring が実装と違った(文書を直した)
# ---------------------------------------------------------------------------

def test_k8_luma_field_grey_equals_rgb_grey_and_wcag_linearised_value():
    import annotate as A
    v = 0.5
    grey = A._luma_field(np.full((2, 2), v))
    rgb = A._luma_field(np.full((2, 2, 3), v))
    # 真値(WCAG / IEC 61966-2-1): ((0.5 + 0.055) / 1.055) ** 2.4
    truth = ((v + 0.055) / 1.055) ** 2.4
    np.testing.assert_allclose(grey, truth, rtol=1e-12)
    np.testing.assert_allclose(rgb, truth, rtol=1e-12)
    doc = A._luma_field.__doc__
    # 文書が実装と同じことを言う: 「値そのもの」ではなく線形化
    assert "その値を輝度そのものとして扱う" not in doc
    assert "srgb_to_linear" in doc


# ---------------------------------------------------------------------------
# 未再現の疑い(再現できたので直したもの)
# ---------------------------------------------------------------------------

def test_sus_monogenic_orientation_stays_in_half_open_range():
    import quatimage as Q
    q = np.zeros((4, 4, 4))
    q[..., 0] = 1.0
    q[..., 1] = 1.0
    q[..., 2] = -1e-17          # 0° のすぐ下: np.mod(-1e-17, pi) は丸めでちょうど pi
    th = Q.monogenic_orientation(q)
    assert np.all((th >= 0) & (th < np.pi))
    # 真値: 向き -1e-17 rad は 0 と同じ(pi は 0 と同じ向きだが約束の範囲の外)
    np.testing.assert_allclose(th, 0.0, atol=1e-15)
    assert np.all(Q.monogenic_orientation(q, display=True) < 1.0)
    _amp, _ph, ori = Q.monogenic_metrics(q)
    np.testing.assert_array_equal(ori, th)


def test_sus_film_color_hue_is_nan_for_achromatic_and_never_360():
    import filmoptics as F
    # 膜が周囲(n=1)か基板と同じ屈折率 = 膜が無いのと同じ = 分散の無い基板の平坦な反射率 = 無彩色。
    # 修正前は丸め屑の向き(191°、238°…)を色相として返した。
    cases = [(1.0, 1.3), (1.0, 1.5), (1.0, 2.0), (1.5, 1.5)]
    assert len(cases) == 4
    for nf, ns in cases:
        r = F.film_color(film=nf, substrate=ns, thickness_min_nm=0.0, thickness_max_nm=500.0, n_points=3)
        assert np.all(r["chroma"] < 1e-9)
        assert np.all(np.isnan(r["hue_deg"])), (nf, ns, r["hue_deg"])
    # 色のある既定(SiO2 on Si)は [0, 360) の有限値で、独立に atan2 から求めた値と一致
    r = F.film_color(n_points=201)
    h = r["hue_deg"]
    assert np.all(np.isfinite(h)) and np.all((h >= 0) & (h < 360))
    ref = np.degrees(np.arctan2(r["lab"][:, 2], r["lab"][:, 1])) % 360.0
    np.testing.assert_allclose(h, ref, atol=1e-12)
    # 丸めで 360.0 になる入力(a* > 0、b* = -1e-17 a*: 素の式は 360.0 を返す)は 0
    assert np.degrees(np.arctan2(-1e-17, 1.0)) % 360.0 == 360.0
    assert F._hue_angle_deg(np.array([[50.0, 1.0, -1e-17]]))[0] == 0.0
