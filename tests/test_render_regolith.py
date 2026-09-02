# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""惑星測光レンダ(Lommel-Seeliger / Hapke / 太陽視直径のレイキャスト影 / 地形レリーフ)の閉形式検証。

2026-09-03、記事のイトカワ画像への指摘「影が不自然」「表面がなめらかすぎてジャガイモ」
を受けて足した op 群を、論文の式・幾何・統計で固定する:

  * Lommel-Seeliger は μ0 = μ で r = w/(8π)、縁(μ→0)で暗くならない。
  * Hapke は多重散乱を切ると Lommel-Seeliger × (1+B(g)) P(g) に厳密に戻り、θ̄=0 で
    粗さ補正が恒等になる。
  * 半影の幅は「遮蔽物までの距離 × tan(視直径/2)」に比例する(平面 + 浮いた板)。
  * レイキャスト影: 球が平面に落とす影の面積は解析楕円 πab(a = r/cos θ)に 1 % で一致。
  * 影の底は環境光と一致する(一回反射を切ったとき)。
  * fBm 変位は振幅を超えない / 岩の個数は Poisson 誤差内でべき則の期待値に一致 /
    同じ seed は同じ出力、違う seed は違う出力。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render3d  # noqa: E402
import render_beauty as rb  # noqa: E402
import render_shade as rs  # noqa: E402
import render_shadow as sh  # noqa: E402


def _plane(n, half, z):
    xs = np.linspace(-half, half, n + 1)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    V = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], axis=1)
    F = []
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            F.append([a, a + 1, a + n + 2])
            F.append([a, a + n + 2, a + n + 1])
    return V, np.asarray(F, np.int64)


def _sphere(radius, centre, subdiv=3):
    V, F = render3d._unit_ellipsoid(subdiv)
    return V * radius + np.asarray(centre, float), F


# --------------------------------------------------------------------------- #
# 反射則の閉形式                                                                #
# --------------------------------------------------------------------------- #
def test_lommel_seeliger_closed_form_and_bright_limb():
    for w in (0.1, 0.42, 1.0):
        assert rs.lommel_seeliger_reflectance(0.3, 0.3, w) == pytest.approx(w / (8 * np.pi))
    # 縁(μ→0)でも μ0 に比例して明るいまま(Lambert なら μ に無関係に暗くならないのが特徴)
    r_limb = rs.lommel_seeliger_reflectance(0.5, 1e-3, 0.42)
    r_centre = rs.lommel_seeliger_reflectance(0.5, 0.5, 0.42)
    assert r_limb > r_centre                      # μ0/(μ0+μ) は μ→0 で 1 に増える
    assert rs.lommel_seeliger_reflectance(0.0, 0.5, 0.42) == 0.0
    with pytest.raises(ValueError):
        rs.lommel_seeliger_reflectance(0.5, 0.5, 1.5)


def test_hapke_reduces_to_lommel_seeliger_times_phase_terms_without_multiple_scattering():
    w, xi, B0, h = 0.42, -0.35, 0.87, 0.01
    for g_deg in (0.0, 8.8, 30.0, 90.0):
        g = np.deg2rad(g_deg)
        B = B0 / (1.0 + np.tan(g / 2) / h)
        P = (1 - xi * xi) / (1 + 2 * xi * np.cos(g) + xi * xi) ** 1.5
        got = rs.hapke_reflectance(0.7, 0.6, g, w=w, g=xi, B0=B0, h=h, roughness_deg=0.0,
                                   multiple_scattering=False)
        assert got == pytest.approx(rs.lommel_seeliger_reflectance(0.7, 0.6, w) * (1 + B) * P, rel=1e-12)
    # 対向効果: g=0 で B=B0、g が大きいと B→0(明るさは位相角とともに単調減少)
    r0 = rs.hapke_reflectance(0.9, 0.9, 0.0, multiple_scattering=False)
    r1 = rs.hapke_reflectance(0.9, 0.9, np.deg2rad(20.0), multiple_scattering=False)
    assert r0 > 1.5 * r1


def test_hapke_roughness_zero_is_identity_and_roughness_darkens_grazing_geometry():
    g = np.deg2rad(8.8)
    mu0 = np.array([0.9, 0.5, 0.2, 0.05])
    mu = np.array([0.9, 0.6, 0.15, 0.05])
    smooth = rs.hapke_reflectance(mu0, mu, g, roughness_deg=0.0)
    tiny = rs.hapke_reflectance(mu0, mu, g, roughness_deg=1e-6)
    assert np.allclose(smooth, tiny, rtol=1e-4)
    rough = rs.hapke_reflectance(mu0, mu, g, roughness_deg=26.0)
    assert np.all(np.isfinite(rough)) and np.all(rough >= 0.0)
    assert rough[-1] < 0.8 * smooth[-1]          # 掠め角では粗さの影で暗くなる
    assert rough[0] > 0.9 * smooth[0]            # 正面ではほぼ変わらない


def test_brdf_shade_image_semantics_and_ops():
    n = np.zeros((4, 4, 3))
    n[1:3, 1:3] = [0.0, 0.0, 1.0]
    L = np.array([0.0, 0.0, 1.0])
    ls = rs.brdf_lommel_seeliger(n, light=L, view=(0, 0, 1), w=0.42)
    assert ls[0, 0] == 0.0 and ls[1, 1] == pytest.approx(np.pi * 0.42 / (8 * np.pi))
    hk = rs.brdf_hapke(n, light=L, view=(0, 0, 1))
    assert hk[1, 1] > 0.0 and hk[0, 0] == 0.0
    lam = rs.brdf_shade(n, light=L, view=(0, 0, 1), model="lambert", w=0.42)
    assert lam[1, 1] == pytest.approx(0.42)
    with pytest.raises(ValueError):
        rs.brdf_shade(n, model="ggx")
    with pytest.raises(ValueError):
        rs.brdf_hapke(n, g=1.5)


# --------------------------------------------------------------------------- #
# レイキャスト影の幾何                                                          #
# --------------------------------------------------------------------------- #
def _topdown(size, half):
    pose = render3d.look_at([0.0, 0.0, 30.0], [0.0, 0.0, 0.0], up=(0.0, 1.0, 0.0))
    fov = 2 * np.degrees(np.arctan(half / 30.0))
    K = render3d.intrinsics_from_fov(fov, size, size)
    return pose, K


def test_penumbra_width_scales_with_occluder_distance_times_tan_half_angle():
    """浮いた板の影の半影幅 ∝ 高さ × tan(視直径/2)(距離 2 倍 → 幅 2 倍、角 2 倍 → 幅 2 倍)。"""
    size = 200
    Vg, Fg = _plane(4, 4.0, 0.0)
    pix = 8.0 / size                                  # 画素の世界幅(枠 = ±4)
    a = np.deg2rad(45.0)                              # 光の仰角 45°(影が板の真下から外れ、カメラに見える)
    light = (np.sin(a), 0.0, np.cos(a))

    def width(height, diam_deg, samples=128):
        """影の左縁(x 小)の可視性プロファイルで 5 %→95 % に上がる距離(世界単位)。"""
        Vb, Fb = _plane(1, 0.5, height)               # 半幅 0.5 の板を高さ height に浮かべる
        V = np.vstack([Vg, Vb])
        F = np.vstack([Fg, Fb + len(Vg)])
        pose, K = _topdown(size, 4.0)
        vis = sh.shadow_raycast(V, F, light, pose=pose, intrinsics=K, width=size,
                                height=size, angular_diameter_deg=diam_deg, samples=samples)
        row = vis[size // 2]
        umbra = int(np.argmin(row))                   # 影の中
        left = row[:umbra][::-1]                      # 影中心から左へ(明るくなる向き)
        x = np.arange(left.size) * pix

        def cross(level):
            k = int(np.argmax(left >= level))
            if k == 0:
                return 0.0
            f = (level - left[k - 1]) / max(left[k] - left[k - 1], 1e-12)
            return x[k - 1] + f * pix

        return cross(0.95) - cross(0.05)

    def expect(height, diam_deg):
        # 円盤光源の角半径 ρ、仰角 a: 地面での半影の全幅 = h [tan(a+ρ) − tan(a−ρ)]。
        # 円盤を直線の縁が横切るとき、遮蔽率が 5 % / 95 % になるのは端から全幅の 0.19 の
        # 位置(円弧の切片面積 = 0.05 π)なので 5→95 % の距離は全幅 × 0.62。
        rho = np.deg2rad(diam_deg / 2.0)
        return 0.62 * height * (np.tan(a + rho) - np.tan(a - rho))

    w1 = width(1.0, 8.0)
    w2 = width(2.0, 8.0)
    w3 = width(1.0, 16.0)
    assert w1 == pytest.approx(expect(1.0, 8.0), rel=0.2)
    assert w2 == pytest.approx(expect(2.0, 8.0), rel=0.2)
    assert w3 == pytest.approx(expect(1.0, 16.0), rel=0.2)
    assert w2 / w1 == pytest.approx(2.0, rel=0.2)      # 距離 2 倍 → 半影 2 倍
    # 太陽(0.53°)・高さ 1: 半影の全幅は 0.019 世界単位 = 0.5 画素 → 事実上ハード影
    assert expect(1.0, 0.53) / 0.62 < pix
    assert width(1.0, 0.53, samples=16) <= 2.0 * pix


def test_raycast_sphere_shadow_area_matches_analytic_ellipse():
    """半径 r の球が傾き θ の平行光で平面に落とす影 = 楕円 π r² / cos θ(1 % 以内)。"""
    size = 400
    r = 1.0
    Vg, Fg = _plane(4, 4.0, 0.0)
    Vs, Fs = _sphere(r, (0.0, 0.0, 2.5), subdiv=4)
    V = np.vstack([Vg, Vs])
    F = np.vstack([Fg, Fs + len(Vg)])
    pose, K = _topdown(size, 4.0)
    theta = np.deg2rad(30.0)
    light = (np.sin(theta), 0.0, np.cos(theta))
    vis = sh.shadow_raycast(V, F, light, pose=pose, intrinsics=K, width=size, height=size)
    # 地面画素だけ数える(球自身の自己陰を除く): 球の投影円の外
    depth = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=size, height=size)["depth"]
    Pw = sh.unproject_to_world(depth, pose, K)
    ground = np.isfinite(Pw[..., 2]) & (np.abs(Pw[..., 2]) < 1e-6)
    pix_area = (8.0 / size) ** 2
    shadow_area = float(((vis < 0.5) & ground).sum()) * pix_area
    ellipse = np.pi * r * r / np.cos(theta)
    # 球の真下の楕円のうち球の投影(半径 r の円)に隠れる部分は地面画素として見えない
    hidden = _hidden_overlap(r, theta, size)
    assert shadow_area == pytest.approx(ellipse - hidden, rel=0.01)


def _hidden_overlap(r, theta, n=2000):
    """楕円影(中心 (-2.5 tanθ, 0)、半軸 r/cosθ, r)と球の投影円(中心 0、半径 r)の重なり面積(数値)。"""
    xs = np.linspace(-4, 4, n)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    cx = -2.5 * np.tan(theta)
    inside_e = ((X - cx) * np.cos(theta) / r) ** 2 + (Y / r) ** 2 <= 1.0
    inside_c = X * X + Y * Y <= r * r
    return float((inside_e & inside_c).sum()) * (8.0 / n) ** 2


def test_raycast_matches_shadow_map_where_map_is_unambiguous():
    Vg, Fg = _plane(4, 4.0, 0.0)
    Vb, Fb = _plane(1, 1.0, 1.5)
    V = np.vstack([Vg, Vb])
    F = np.vstack([Fg, Fb + len(Vg)])
    pose, K = _topdown(160, 4.0)
    rc = sh.shadow_raycast(V, F, (0.2, 0.1, 1.0), pose=pose, intrinsics=K, width=160, height=160)
    sm = sh.cast_shadow(V, F, (0.2, 0.1, 1.0), pose=pose, intrinsics=K, width=160, height=160,
                        shadow_res=1024)
    agree = ((rc < 0.5) == (sm < 0.5)).mean()
    assert agree > 0.98
    with pytest.raises(ValueError):
        sh.shadow_raycast(V, F, (0, 0, 1), width=160, height=160, angular_diameter_deg=-1)


# --------------------------------------------------------------------------- #
# render_beauty の物理オプション                                                 #
# --------------------------------------------------------------------------- #
def test_defaults_unchanged_and_shadow_floor_equals_ambient_without_bounce():
    Vs, Fs = _sphere(1.0, (0.0, 0.0, 1.0), subdiv=2)
    base = dict(size=64, ss=1, ao=False, ground_shadow=False, tonemap="none",
                material="plastic", albedo=(0.5, 0.5, 0.5), light=(1.0, 0.0, 0.0))
    a = rb.render_beauty(Vs, Fs, **base)
    b = rb.render_beauty(Vs, Fs, **base, brdf="phong", shadow_method="map",
                         self_illumination=0.0, albedo_variation=0.0)
    assert np.array_equal(a, b)                    # 新引数の既定値は従来出力を変えない
    # 環境光 ka・一回反射なし・Lommel-Seeliger: 影(光に背く側)の底は ka × albedo に一致
    img = rb.render_beauty(Vs, Fs, size=64, ss=1, ao=False, ground_shadow=False, tonemap="none",
                           albedo=(0.5, 0.5, 0.5), light=(1.0, 0.0, 0.0), ambient=0.2,
                           brdf="lommel_seeliger", brdf_params={"w": 0.42},
                           shadow_method="raycast", background=(0, 0, 0))
    obj = img.max(axis=2) > 0
    floor = img[..., 0][obj].min()
    assert floor == pytest.approx(0.2 * 1.0, abs=1e-6)   # albedo は平均 1 に正規化 → ka
    dark = rb.render_beauty(Vs, Fs, size=64, ss=1, ao=False, ground_shadow=False, tonemap="none",
                            albedo=(0.5, 0.5, 0.5), light=(1.0, 0.0, 0.0), ambient=0.0,
                            brdf="hapke", shadow_method="raycast", background=(0, 0, 0))
    assert dark[..., 0][obj].min() == 0.0           # 宇宙: 環境光 0 → 影は真っ黒
    with pytest.raises(ValueError):
        rb.render_beauty(Vs, Fs, size=32, brdf="ggx")


def test_render_regolith_is_deterministic_and_bounce_lifts_shadow_floor():
    V, F = _sphere(1.0, (0.0, 0.0, 0.0), subdiv=2)
    V, F = render3d.mesh_scatter_boulders(V, F, density=3.0, d_min=0.15, seed=2)
    kw = dict(size=64, ss=1, sun=(1.0, 0.3, 0.5), ao_samples=16, shadow_samples=1)
    a = rb.render_regolith(V, F, **kw)
    b = rb.render_regolith(V, F, **kw)
    assert a.shape == (64, 64, 3) and np.array_equal(a, b)
    assert a.max() == pytest.approx(0.95, abs=0.05)          # 露出自動
    nob = rb.render_regolith(V, F, self_illumination=0.0, **kw)
    assert a.sum() >= nob.sum()                              # 一回反射は明るさを足すだけ
    with pytest.raises(ValueError):
        rb.render_regolith(V, F, exposure=-1.0, **kw)


# --------------------------------------------------------------------------- #
# 地形レリーフ                                                                  #
# --------------------------------------------------------------------------- #
def test_fbm_displacement_bounded_and_seeded():
    V, F = _sphere(1.0, (0.0, 0.0, 0.0), subdiv=3)
    for amp in (0.01, 0.05):
        Vd, Fd = render3d.mesh_displace_fbm(V, F, amp, seed=7)
        d = np.linalg.norm(Vd - V, axis=1)
        assert d.max() <= amp + 1e-12 and d.max() > 0.3 * amp
        assert np.array_equal(Fd, F)
    V1, _ = render3d.mesh_displace_fbm(V, F, 0.02, seed=7)
    V2, _ = render3d.mesh_displace_fbm(V, F, 0.02, seed=7)
    V3, _ = render3d.mesh_displace_fbm(V, F, 0.02, seed=8)
    assert np.array_equal(V1, V2) and not np.array_equal(V1, V3)
    V0, _ = render3d.mesh_displace_fbm(V, F, 0.0)
    assert np.array_equal(V0, V)
    with pytest.raises(ValueError):
        render3d.mesh_displace_fbm(V, F, -1.0)


def test_boulder_count_and_size_distribution_follow_the_power_law():
    V, F = _sphere(1.0, (0.0, 0.0, 0.0), subdiv=3)
    area = 4 * np.pi
    dens, dmin, ex = 200.0, 0.02, 3.1
    s = render3d.sample_boulders(V, F, density=dens, d_min=dmin, d_max=10 * dmin, exponent=ex, seed=11)
    n = s["diameter"].size
    lam = dens * area
    assert s["expected"] == pytest.approx(lam, rel=1e-3)   # 面積 = 4π(icosphere 近似)
    assert abs(n - lam) < 4 * np.sqrt(lam)                  # Poisson 4σ
    # N(>2 d_min)/N(>d_min) = (2^-3.1 - 10^-3.1)/(1 - 10^-3.1)(切断べき則)
    frac = (s["diameter"] > 2 * dmin).mean()
    expect = (2 ** -ex - 10 ** -ex) / (1 - 10 ** -ex)
    assert abs(frac - expect) < 4 * np.sqrt(expect * (1 - expect) / n)
    assert s["diameter"].min() >= dmin and s["diameter"].max() <= 10 * dmin
    # 海(weight 0)には岩が置かれない
    wts = render3d.terrain_region_mask(V, F, smooth_fraction=0.5, method="noise", seed=1)
    assert abs((wts == 0).mean() - 0.5) < 0.05
    s2 = render3d.sample_boulders(V, F, density=dens, d_min=dmin, seed=11, region_weights=wts)
    assert s2["expected"] == pytest.approx(0.5 * lam, rel=0.1)
    Vb, Fb = render3d.mesh_scatter_boulders(V, F, density=dens, d_min=dmin, seed=11, region_weights=wts)
    assert Fb.shape[0] == F.shape[0] + 80 * s2["diameter"].size
    Vb2, _ = render3d.mesh_scatter_boulders(V, F, density=dens, d_min=dmin, seed=11, region_weights=wts)
    assert np.array_equal(Vb, Vb2)
    with pytest.raises(ValueError):
        render3d.mesh_scatter_boulders(V, F, density=1.0, d_min=0.0)


def test_terrain_region_mask_neck_is_a_band_around_the_narrowest_section():
    # ピーナツ: 2 球が重なって首を作る → 首のまわりの帯が海(weight 0)
    V1, F1 = _sphere(1.0, (-0.9, 0.0, 0.0), subdiv=3)
    V2, F2 = _sphere(0.8, (0.9, 0.0, 0.0), subdiv=3)
    V = np.vstack([V1, V2])
    F = np.vstack([F1, F2 + len(V1)])
    w = render3d.terrain_region_mask(V, F, smooth_fraction=0.2, method="neck")
    fc = V[F].mean(axis=1)
    assert 0.0 < (w == 0).mean() < 0.5
    assert abs(fc[w == 0, 0]).mean() < abs(fc[w == 1, 0]).mean()   # 海は首(|x| 小)側
    assert np.median(abs(fc[w == 0, 0])) < 0.8
    assert render3d.terrain_region_mask(V, F, smooth_fraction=0.0).min() == 1.0
    with pytest.raises(ValueError):
        render3d.terrain_region_mask(V, F, method="ocean")
