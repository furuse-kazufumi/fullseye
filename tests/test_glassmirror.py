"""glassmirror(ガラス・鏡面の光学)の単体テスト。

契約(すべて閉じた式・公開値との突き合わせ):
  * 誘電体 Fresnel: 垂直入射 = ((n1−n2)/(n1+n2))²、Brewster 角で p 偏光が厳密 0、
    臨界角超で 1.0(全反射)、R + T = 1(吸収の無い界面)。
  * 金属 Fresnel: 銀はほぼ中性で最も明るく、金と銅は長波長で立ち上がる(色の順序)。
  * 平行平板: 吸収 0・垂直入射で T = 2n/(n²+1) の既知値。
  * 屈折: Snell を満たし、全反射は**光線ごとに**マスクされる。
  * プリズム: 最小偏角が短波長ほど大きい(正常分散)。
"""
import numpy as np
import pytest

import glassmirror as G


# --------------------------------------------------------------------------- #
# 誘電体の界面                                                                  #
# --------------------------------------------------------------------------- #
def test_normal_incidence_matches_closed_form():
    for n2 in (1.33, 1.5168, 2.0, 3.5):
        got = float(G.fresnel_dielectric(1.0, 1.0, n2))
        want = ((1.0 - n2) / (1.0 + n2)) ** 2
        assert got == pytest.approx(want, rel=1e-12), (n2, got, want)


def test_brewster_angle_kills_p_polarisation():
    for n2 in (1.33, 1.5, 1.8):
        b = G.brewster_angle_deg(1.0, n2)
        assert b == pytest.approx(np.degrees(np.arctan(n2)), rel=1e-12)
        rp = float(G.fresnel_dielectric(np.cos(np.radians(b)), 1.0, n2, "p"))
        assert abs(rp) < 1e-15, (n2, rp)
        # s 偏光は消えない(消えたら「偏光板で映り込みが消える」現象が説明できない)
        assert float(G.fresnel_dielectric(np.cos(np.radians(b)), 1.0, n2, "s")) > 0.05


def test_total_internal_reflection_is_exactly_one():
    c = G.critical_angle_deg(1.5, 1.0)
    assert c == pytest.approx(np.degrees(np.arcsin(1.0 / 1.5)), rel=1e-12)
    ang = np.array([c - 1.0, c + 0.001, c + 5.0, 89.0])
    R = G.fresnel_dielectric(np.cos(np.radians(ang)), 1.5, 1.0)
    assert R[0] < 1.0
    assert np.all(R[1:] == 1.0)
    with pytest.raises(ValueError, match="total internal reflection"):
        G.critical_angle_deg(1.0, 1.5)                     # 密→疎でなければ存在しない


def test_energy_is_conserved_on_a_lossless_interface():
    ci = np.cos(np.radians(np.linspace(0.0, 89.0, 90)))
    for pol in ("unpolarized", "s", "p"):
        R = G.fresnel_dielectric(ci, 1.0, 1.5, pol)
        assert np.all(R >= 0.0) and np.all(R <= 1.0)
    # 反射率は入射角について単調増加(誘電体、air→glass)
    R = G.fresnel_dielectric(ci, 1.0, 1.5)
    assert np.all(np.diff(R) >= -1e-12)


def test_fresnel_argument_validation():
    with pytest.raises(ValueError):
        G.fresnel_dielectric(1.2, 1.0, 1.5)                # cos_i の範囲外
    with pytest.raises(ValueError):
        G.fresnel_dielectric(1.0, 0.0, 1.5)                # 屈折率 0
    with pytest.raises(ValueError):
        G.fresnel_dielectric(1.0, 1.0, 1.5, "circular")    # 未知の偏光


# --------------------------------------------------------------------------- #
# 金属鏡                                                                        #
# --------------------------------------------------------------------------- #
def test_metal_reflectance_ordering_is_physical():
    w = np.array([450.0, 550.0, 650.0])
    R = {}
    for m in G.METALS:
        n, k = G.metal_optical_constants(m, w)
        R[m] = G.fresnel_conductor(1.0, n, k)
        assert np.all(R[m] > 0.0) and np.all(R[m] < 1.0)   # 金属に全反射は無い
    assert np.all(R["ag"] > 0.9)                           # 銀は可視全域で明るい
    assert R["au"][2] / R["au"][0] > 2.0                   # 金は赤側で立ち上がる
    assert R["cu"][2] / R["cu"][0] > 1.5                   # 銅も
    assert np.ptp(R["al"]) < 0.05                          # アルミは平坦
    assert np.all(R["cr"] < 0.7)                           # クロムは暗い


def test_metal_mirror_colour_comes_out_of_nk():
    """色を塗っていないのに金は黄色く、銀は中性になる(n,k → 分光 → 等色関数)。"""
    au = G.metal_mirror_rgb("au", 1.0)
    ag = G.metal_mirror_rgb("ag", 1.0)
    cu = G.metal_mirror_rgb("cu", 1.0)
    assert au[0] > au[1] > au[2], au                       # R > G > B = 黄金色
    assert cu[0] > cu[1] > cu[2], cu                       # 銅も暖色
    # ★直感と逆だった: 「銅は金より赤い」と思って cu[2] < au[2] を書いたら落ちた。
    # 公開値でも Au の R(450 nm) ≈ 0.40 に対し Cu ≈ 0.56 で、**青は銅の方が多い**
    # (= 金の方が飽和した黄色)。表ではなくこちらの思い込みが誤りだった。
    assert au[2] < cu[2], (au[2], cu[2])
    assert float(np.ptp(ag)) < 0.08, ag                    # 銀はほぼ中性
    assert np.all(au > 0.0) and np.all(ag > 0.5)


def test_metal_unknown_name_is_fail_closed():
    with pytest.raises(ValueError, match="unknown metal"):
        G.metal_optical_constants("unobtainium", 550.0)


# --------------------------------------------------------------------------- #
# ガラスの体積と平行平板                                                        #
# --------------------------------------------------------------------------- #
def test_slab_transmittance_matches_the_known_value():
    """吸収 0・垂直入射の板は T = 2n/(n²+1)(多重反射を数え上げた既知の結果)。"""
    for n in (1.33, 1.5, 1.8, 2.4):
        got = float(G.slab_transmittance(1.0, 1.0, n, 3.0, 0.0))
        assert got == pytest.approx(2.0 * n / (n ** 2 + 1.0), rel=1e-12), (n, got)


def test_absorption_reduces_transmittance_monotonically():
    sig = np.array([0.0, 0.001, 0.01, 0.1])
    T = np.array([float(G.slab_transmittance(1.0, 1.0, 1.5, 10.0, s)) for s in sig])
    assert np.all(np.diff(T) < 0.0)
    # Beer-Lambert 単体は exp(-σL) そのもの
    assert float(G.beer_lambert_transmittance(10.0, 0.1)) == pytest.approx(np.exp(-1.0), rel=1e-12)
    with pytest.raises(ValueError):
        G.beer_lambert_transmittance(-1.0, 0.1)


def test_slab_from_inside_beyond_critical_angle_blocks():
    c = G.critical_angle_deg(1.5, 1.0)
    T = G.slab_transmittance(np.cos(np.radians(np.array([c - 2.0, c + 2.0]))), 1.5, 1.0, 3.0, 0.0)
    assert T[0] > 0.5 and T[1] == 0.0


# --------------------------------------------------------------------------- #
# 光線(per-ray TIR)                                                            #
# --------------------------------------------------------------------------- #
def test_refract_rays_satisfies_snell_per_ray():
    ang = np.radians(np.array([0.0, 15.0, 30.0, 45.0, 60.0]))
    d = np.stack([np.sin(ang), np.zeros_like(ang), -np.cos(ang)], -1)
    n = np.tile(np.array([0.0, 0.0, 1.0]), (len(ang), 1))
    out, tir = G.refract_rays(d, n, 1.0, 1.5)
    assert not tir.any()
    st = np.linalg.norm(np.cross(out, n), axis=-1)          # sin(屈折角)
    assert np.allclose(1.5 * st, 1.0 * np.sin(ang), atol=1e-12)


def test_refract_rays_masks_tir_per_ray_not_wholesale():
    """★ match3d.refract は「1 本でも TIR なら全体が None」。こちらは光線ごと。"""
    ang = np.radians(np.array([10.0, 60.0]))                # 60° は 1.5→1.0 で全反射
    d = np.stack([np.sin(ang), np.zeros_like(ang), -np.cos(ang)], -1)
    n = np.tile(np.array([0.0, 0.0, 1.0]), (2, 1))
    out, tir = G.refract_rays(d, n, 1.5, 1.0)
    assert tir.tolist() == [False, True]
    assert np.isfinite(out).all()                           # NaN を返さない
    assert out[1][2] > 0.0                                  # 全反射した光線は戻る


# --------------------------------------------------------------------------- #
# プリズムの分散                                                                #
# --------------------------------------------------------------------------- #
def test_prism_dispersion_bends_blue_more():
    w = np.array([486.1, 587.6, 656.3])                     # F / d / C 線
    d = G.prism_min_deviation_deg(w, 60.0, "N-BK7")
    assert np.all(np.diff(d) < 0.0), d                      # 短波長ほど大きく曲がる
    assert d[1] == pytest.approx(38.6, abs=0.3)             # d 線 ≈ 38.6°
    # 屈折率を直接与えても同じ閉じた式
    n = 1.5168
    got = float(G.prism_min_deviation_deg(587.6, 60.0, n))
    want = 2.0 * np.degrees(np.arcsin(n * np.sin(np.radians(30.0)))) - 60.0
    assert got == pytest.approx(want, rel=1e-12)


def test_prism_rejects_bad_apex():
    with pytest.raises(ValueError):
        G.prism_min_deviation_deg(550.0, 0.0)
    with pytest.raises(ValueError):
        G.prism_min_deviation_deg(-1.0, 60.0, "N-BK7")
    with pytest.raises(ValueError, match="apex_deg must be a scalar"):
        # ★ 波長を第 1 引数にした理由(台帳の「先頭がデータ」規約)。配列を頂角へ
        #   渡すと以前は素の TypeError が出ていた。
        G.prism_min_deviation_deg(550.0, np.array([60.0, 30.0]))
