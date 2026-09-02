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

2026-09-03(2 回目の指摘「粗すぎる/凹凸が見えない/粗密の使い分けが無い」)で足した op:
  * mesh_subdivide: 一様 = 面 ×4・面積/体積厳密保存(点は元のファセット上)。適応 = 目標
    辺長へのテッセレーション(最大辺 ≤ 1.5×target、辺の valence 2 = 適合、幾何不変)。
  * displacement_band_weights / mesh_displace_spectrum: 2×局所辺長より短い波長は重み 0
    (粗いパッチで短波長オクターブのエネルギーが厳密に 0)、変位は Σ振幅以内。
  * bump_normals_fbm: 単位長、平均が幾何法線に戻る、振幅 0 で恒等、補集合ゲート。
  * mesh_scatter_boulders(shape='hull'): べき則の個数、max_count は d_min を法則どおり
    引き上げる、埋没率は幾何で検証(要求値と一致)、ランダム姿勢でも決定的。
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
        # 円盤を直線の縁が横切るとき、遮蔽率が 5 % / 95 % になるのは端から直径の 0.098 の
        # 位置(円の切片面積 acos(1−H) − (1−H)√(1−(1−H)²) = 0.05π ⇒ H = 0.195 半径)
        # なので 5→95 % の距離は全幅 × 0.80。
        rho = np.deg2rad(diam_deg / 2.0)
        return 0.80 * height * (np.tan(a + rho) - np.tan(a - rho))

    w1 = width(1.0, 8.0)
    w2 = width(2.0, 8.0)
    w3 = width(1.0, 16.0)
    assert w1 == pytest.approx(expect(1.0, 8.0), rel=0.2)
    assert w2 == pytest.approx(expect(2.0, 8.0), rel=0.2)
    assert w3 == pytest.approx(expect(1.0, 16.0), rel=0.2)
    assert w2 / w1 == pytest.approx(2.0, rel=0.2)      # 距離 2 倍 → 半影 2 倍
    # 太陽(0.53°)・高さ 1: 半影の全幅は 0.019 世界単位 = 0.5 画素 → 事実上ハード影
    assert expect(1.0, 0.53) / 0.80 < pix
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
    # 見えている地面画素の上で、解析楕円(中心 (-2.5 tanθ, 0)、半軸 r/cosθ, r)の内側の
    # 画素数と、レイキャストで影になった画素数を比べる(球に隠れた地面は両方から外れる)。
    cx = -2.5 * np.tan(theta)
    X, Y = Pw[..., 0], Pw[..., 1]
    with np.errstate(invalid="ignore"):
        inside = ground & (((X - cx) * np.cos(theta) / r) ** 2 + (Y / r) ** 2 <= 1.0)
    n_shadow = int(((vis < 0.5) & ground).sum())
    n_ellipse = int(inside.sum())
    pix_area = (8.0 / size) ** 2
    assert n_ellipse * pix_area > 0.5 * np.pi * r * r / np.cos(theta)   # 楕円の大半が見えている
    assert n_shadow == pytest.approx(n_ellipse, rel=0.01)


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
    assert 0.85 <= a.max() <= 1.0                            # 露出自動(99.5 % 点 → 0.95、最大は clip)
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
    tri = V[F]
    area = float(0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum())
    assert area == pytest.approx(4 * np.pi, rel=0.01)       # icosphere ≈ 球
    dens, dmin, ex = 200.0, 0.02, 3.1
    s = render3d.sample_boulders(V, F, density=dens, d_min=dmin, d_max=10 * dmin, exponent=ex, seed=11)
    n = s["diameter"].size
    lam = dens * area
    assert s["expected"] == pytest.approx(lam, rel=1e-9)   # 期待個数 = 密度 × メッシュ面積
    assert np.all(s["face"] >= 0) and np.all(s["face"] < F.shape[0])
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


# --------------------------------------------------------------------------- #
# 解像度: 適応テッセレーション / 帯域ゲート / bump / 角張った岩(2026-09-03)      #
# --------------------------------------------------------------------------- #
def _area_volume(V, F):
    t = V[F]
    c = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    return 0.5 * float(np.linalg.norm(c, axis=1).sum()), float(np.einsum("ij,ij->i", t[:, 0], c).sum() / 6.0)


def _edge_valence(F):
    e = np.sort(np.stack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 1), axis=2).reshape(-1, 2)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return cnt


def test_uniform_subdivision_quadruples_faces_and_preserves_area_and_volume():
    V, F = _sphere(1.3, (0.2, -0.1, 0.4), subdiv=2)
    a0, v0 = _area_volume(V, F)
    V1, F1 = render3d.mesh_subdivide(V, F, levels=1)
    V2, F2 = render3d.mesh_subdivide(V, F, levels=2)
    assert F1.shape[0] == 4 * F.shape[0] and F2.shape[0] == 16 * F.shape[0]
    for Vx, Fx in ((V1, F1), (V2, F2)):
        a, v = _area_volume(Vx, Fx)
        assert a == pytest.approx(a0, rel=1e-12) and v == pytest.approx(v0, rel=1e-12)
        assert np.all(_edge_valence(Fx) == 2)                # 閉じた適合メッシュのまま
    V0, F0 = render3d.mesh_subdivide(V, F, levels=0)
    assert np.array_equal(V0, V) and np.array_equal(F0, F)
    with pytest.raises(ValueError):
        render3d.mesh_subdivide(V, F, levels=-1)
    with pytest.raises(ValueError):
        render3d.mesh_subdivide(V, F, levels=3, max_faces=1000)


def _graded_plane(seed=3):
    """辺長が 0.5 → 4.5 と 9 倍変わる(粗密が混ざった)平面メッシュ(Delaunay)。"""
    from scipy.spatial import Delaunay
    rng = np.random.default_rng(seed)
    pts = []
    x = 0.0
    while x < 40.0:
        h = 0.5 + x / 10.0
        for y in np.arange(0.0, 20.0, h):
            pts.append([x + rng.random() * 0.2 * h, y + rng.random() * 0.2 * h])
        x += h * 0.87
    P = np.asarray(pts)
    F = Delaunay(P).simplices.astype(np.int64)
    return np.column_stack([P, np.zeros(len(P))]), F


def test_adaptive_tessellation_makes_facets_uniform_in_metres_and_keeps_geometry():
    """粗密の混ざった平面: 目標辺長 0.5 で最大辺 ≤ 0.75、中央値 ≈ 0.5、p95/p5 が 7.4 → ≤ 2.5、
    面積不変、辺は適合(内部辺の valence 2 / 境界 1)。

    honest: 元の面の形(最長/最短辺 比)は per-face の適合細分では変えられないので、
    p95/p5 は 1.5 には届かない(イトカワ実測 2.38、この平面 2.39)。1.5 未満が要るなら
    連結を変える等方リメッシュ(meshres)が必要で、それは間引き=学術用途では避ける方針。"""
    V, F = _graded_plane()
    e0 = render3d.mesh_edge_lengths(V, F, per="edge")
    r0 = np.percentile(e0, 95) / np.percentile(e0, 5)
    assert r0 > 6.0
    Vt, Ft = render3d.mesh_subdivide(V, F, target_edge=0.5)
    e1 = render3d.mesh_edge_lengths(Vt, Ft, per="edge")
    r1 = np.percentile(e1, 95) / np.percentile(e1, 5)
    assert e1.max() <= 0.5 * 2.0 + 1e-9                    # 辺上 ≤ 1.5×、面内接続 < 2×
    assert abs(np.median(e1) - 0.5) < 0.05
    assert r1 <= 2.5 and r1 < 0.4 * r0
    a0, _ = _area_volume(V, F)
    a1, _ = _area_volume(Vt, Ft)
    assert a1 == pytest.approx(a0, rel=1e-12)
    val = _edge_valence(Ft)
    assert set(np.unique(val).tolist()) <= {1, 2}
    assert np.all(Vt[:, 2] == 0.0)                          # 点は元の面上
    # per-vertex / per-face の局所辺長
    ev = render3d.mesh_edge_lengths(Vt, Ft, per="vertex")
    ef = render3d.mesh_edge_lengths(Vt, Ft, per="face")
    assert ev.shape == (Vt.shape[0],) and ef.shape == (Ft.shape[0],) and ev.min() > 0
    with pytest.raises(ValueError):
        render3d.mesh_edge_lengths(V, F, per="hexagon")
    with pytest.raises(ValueError):
        render3d.mesh_subdivide(V, F, target_edge=0.0)
    with pytest.raises(ValueError):
        render3d.mesh_subdivide(V, F, target_edge=0.05, max_faces=500)


def test_band_gate_removes_octaves_shorter_than_twice_the_local_edge():
    """粗い平面パッチ(辺 ≈ 10)で波長 [80, 40, 20, 10, 5]: 10 と 5 は重み 0(エネルギー厳密 0)、
    20 = 2×辺 で 0 から立ち上がり、≥ 30 で 1。変位は許されたオクターブだけの和に一致。"""
    V, F = _plane(4, 20.0, 0.0)                              # 辺 10 の格子
    lam = np.array([80.0, 40.0, 20.0, 10.0, 5.0])
    g = render3d.displacement_band_weights(V, F, lam, nyquist=2.0, fade=1.0)
    e = render3d.mesh_edge_lengths(V, F, per="vertex")
    assert g.shape == (5, V.shape[0])
    assert np.all(g[3] == 0.0) and np.all(g[4] == 0.0)     # λ < 2e → 厳密 0
    assert np.all(g[0] == 1.0) and np.all(g[1] == 1.0)
    assert np.all(g[2] <= 0.6)                               # λ=20 ≈ 2e(対角の頂点は e>10)
    assert np.allclose(g, np.clip((lam[:, None] / e[None, :] - 2.0), 0.0, 1.0))
    amp = np.array([2.0, 1.0, 0.5, 0.25, 0.125])
    Vd, _ = render3d.mesh_displace_spectrum(V, F, lam, amp, seed=5)
    Vk, _ = render3d.mesh_displace_spectrum(V, F, lam[:3], amp[:3], seed=5)   # 短波長 2 つを外す
    assert np.allclose(Vd, Vk)                               # 短波長オクターブのエネルギー 0
    d = np.linalg.norm(Vd - V, axis=1)
    assert d.max() <= amp.sum() + 1e-12 and d.max() > 0.0
    # 重み(合成レリーフの重み)は (N,) でも (K,N) でも掛かる、範囲外は拒否
    Vw, _ = render3d.mesh_displace_spectrum(V, F, lam, amp, seed=5, weights=np.zeros(V.shape[0]))
    assert np.array_equal(Vw, V)
    with pytest.raises(ValueError):
        render3d.mesh_displace_spectrum(V, F, lam, amp, weights=np.full(V.shape[0], 2.0))
    with pytest.raises(ValueError):
        render3d.mesh_displace_spectrum(V, F, lam, amp[:2])
    # 細かい平面(辺 1)では全オクターブが変位される
    Vf, Ff = _plane(40, 20.0, 0.0)
    gf = render3d.displacement_band_weights(Vf, Ff, lam)
    assert np.all(gf == 1.0)


def test_bump_normals_are_unit_average_to_the_geometric_normal_and_complement_the_gate():
    n = np.zeros((48, 48, 3))
    n[..., 2] = 1.0
    xs, ys = np.meshgrid(np.arange(48) * 0.25, np.arange(48) * 0.25, indexing="ij")
    P = np.stack([xs, ys, np.zeros_like(xs)], axis=-1)
    P[0, 0] = np.nan                                          # 背景画素は触らない
    lam, amp = (2.0, 1.0), (0.05, 0.03)
    nb = render3d.bump_normals_fbm(n, P, lam, amp, seed=4)
    assert np.allclose(np.linalg.norm(nb, axis=-1), 1.0)
    assert np.array_equal(nb[0, 0], n[0, 0])
    mean_n = nb.reshape(-1, 3).mean(axis=0)
    assert np.linalg.norm(mean_n[:2]) < 0.02 and mean_n[2] > 0.99      # 平均は幾何法線
    tilt = np.degrees(np.arccos(np.clip(nb[..., 2], -1, 1)))
    assert 0.0 < tilt.max() < np.degrees(2 * np.pi * 0.05 / 2.0 + 2 * np.pi * 0.03 / 1.0)   # ≤ Σ 2πA/λ
    # 振幅 0 → 恒等、決定的、回転フレームでも同じ幾何
    assert np.array_equal(render3d.bump_normals_fbm(n, P, lam, (0.0, 0.0)), n)
    assert np.array_equal(render3d.bump_normals_fbm(n, P, lam, amp, seed=4), nb)
    Rz = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    nr = render3d.bump_normals_fbm(n @ Rz.T, P, lam, amp, seed=4, rotation=Rz)
    assert np.allclose(nr, nb @ Rz.T)
    # 補集合ゲート: 局所辺長 e=0.5 → λ=1 は 2e → 重み 1(gate 0)、λ=2 は 4e → gate 1 → 重み 0
    em = np.full((48, 48), 0.5)
    nc = render3d.bump_normals_fbm(n, P, lam, amp, seed=4, local_edge=em)
    only_short = render3d.bump_normals_fbm(n, P, (1.0,), (0.03,), seed=4)
    # 同じ seed でもオクターブ番号が違うと格子オフセットが違うので、直接 2 番目のみを比べる:
    nc2 = render3d.bump_normals_fbm(n, P, lam, (0.0, 0.03), seed=4)
    assert np.allclose(nc, nc2)
    assert not np.allclose(only_short, nc2)                  # (オフセットの違い = 別の場)
    with pytest.raises(ValueError):
        render3d.bump_normals_fbm(n, P, lam, amp, local_edge=np.zeros((48, 48)))
    with pytest.raises(ValueError):
        render3d.bump_normals_fbm(n[:, :, :2], P, lam, amp)


def test_hull_boulders_follow_the_power_law_cap_and_burial():
    V, F = _sphere(1.0, (0.0, 0.0, 0.0), subdiv=3)
    tri = V[F]
    area = float(0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum())
    dens, dmin, dmax, ex = 5000.0, 0.01, 0.2, 3.1
    lam_full = dens * area
    cap = 600
    s = render3d.sample_boulders(V, F, density=dens, d_min=dmin, d_max=dmax, exponent=ex, seed=9, max_count=cap)
    # cap: d_min を法則どおり引き上げ → 期待値 = cap、d_min_eff = d_min (λ/cap)^(1/ex)
    assert s["expected"] == pytest.approx(cap)
    assert s["d_min_effective"] == pytest.approx(dmin * (lam_full / cap) ** (1.0 / ex))
    n = s["diameter"].size
    assert abs(n - cap) < 4 * np.sqrt(cap)
    d0 = s["d_min_effective"]
    assert s["diameter"].min() >= d0 and s["diameter"].max() <= dmax
    frac = (s["diameter"] > 2 * d0).mean()
    expect = (2 ** -ex - (dmax / d0) ** -ex) / (1 - (dmax / d0) ** -ex)
    assert abs(frac - expect) < 4 * np.sqrt(expect * (1 - expect) / n)
    # 埋没率: 小さい岩ほど深い(log-線形 + ジッタ)、範囲 [0.3, 0.6]
    assert s["burial"].min() >= 0.3 and s["burial"].max() <= 0.6
    small = s["burial"][s["diameter"] < 1.5 * d0].mean()
    big = s["burial"][s["diameter"] > 4 * d0].mean()
    assert small > big
    Vb, Fb, info = render3d.mesh_scatter_boulders(V, F, density=dens, d_min=dmin, d_max=dmax, exponent=ex,
                                                  seed=9, max_count=cap, shape="hull", orientation="random",
                                                  return_info=True)
    assert info["n_boulders"] == n and Fb.shape[0] == F.shape[0] + info["faces_per_boulder"].sum()
    assert np.all(info["faces_per_boulder"] >= 8)           # 凸包(≥ 6 点)の面数
    # 幾何で埋没率を検証: 岩 k の頂点を法線に射影した範囲のうち、面の下にある割合 = burial[k]
    off_f = F.shape[0]
    for k in (0, 1, n // 2, n - 1):
        fk = Fb[off_f + int(info["faces_per_boulder"][:k].sum()): off_f + int(info["faces_per_boulder"][:k + 1].sum())]
        h = (Vb[np.unique(fk)] - info["centre"][k]) @ info["normal"][k]
        assert -h.min() / (h.max() - h.min()) == pytest.approx(info["burial"][k], abs=1e-9)
        # 外向き巻き: 岩の重心から見て面法線が外を向く
        T = Vb[fk]
        c = T.mean(axis=(0, 1))
        fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        assert np.all(np.einsum("ij,ij->i", fn, T.mean(axis=1) - c) > 0)
    Vb2, Fb2 = render3d.mesh_scatter_boulders(V, F, density=dens, d_min=dmin, d_max=dmax, exponent=ex,
                                              seed=9, max_count=cap, shape="hull", orientation="random")
    assert np.array_equal(Vb, Vb2) and np.array_equal(Fb, Fb2)
    with pytest.raises(ValueError):
        render3d.mesh_scatter_boulders(V, F, density=1.0, d_min=0.1, shape="cube")
    with pytest.raises(ValueError):
        render3d.sample_boulders(V, F, density=dens, d_min=dmin, d_max=dmax, max_count=1)


def test_render_regolith_median_exposure_and_bump_keep_geometry():
    V, F = _sphere(1.0, (0.0, 0.0, 0.0), subdiv=3)
    V, F = render3d.mesh_scatter_boulders(V, F, density=30.0, d_min=0.06, seed=2, shape="hull")
    kw = dict(size=96, ss=1, sun=(0.7, -0.5, 0.6), ao_samples=16, shadow_samples=1)
    a = rb.render_regolith(V, F, exposure="median", exposure_target=0.45, **kw)
    obj = a.max(axis=2)
    vals = obj[obj > 0]
    p = np.percentile(vals, 99.5)
    assert np.median(vals[vals > 0.3 * p]) == pytest.approx(0.45, abs=0.02)
    bump = dict(wavelengths=(0.2, 0.1), amplitudes=(0.01, 0.006), complement_edges=True)
    b = rb.render_regolith(V, F, exposure="median", bump=bump, **kw)
    assert b.shape == a.shape and not np.array_equal(a, b)
    assert np.array_equal((a.max(axis=2) > 0), (b.max(axis=2) > 0))   # シルエット(幾何)は不変
    assert np.array_equal(b, rb.render_regolith(V, F, exposure="median", bump=bump, **kw))
    with pytest.raises(ValueError):
        rb.render_regolith(V, F, exposure="p99", **kw)
    with pytest.raises(ValueError):
        rb.render_regolith(V, F, bump="fbm", **kw)
