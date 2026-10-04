# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacslip の門(マーカー配列 → せん断場・固着/滑り: Cattaneo–Mindlin の閉形式、Cerruti 畳み込み、相似則の逆算、追跡の罠の反例)。

 1. 閉形式の自己検算: ∫q dA = Q、c/a、dδx/dQ(0) = 1/kt、計画書の錨 70.5 µm、slipping の印、fail-closed
 2. ūr: 外側 = 点荷重、最大は r = 0.93a(縁でない)、ūr(a)/δ = 2(1−2ν)/(3π(1−ν))
 3. Cerruti 畳み込み vs Johnson 3.91(円内 1 %)、Mindlin の固着円の一様性(1 %)、遠方 1/r
 4. 相似則の逆算: 真の変位で c/a 0.01・μ 3 %、合成像からの追跡で Q/μP 0.05
 5. 反例: 規則格子の PIV エイリアス(5 px → −3 px、ジッタで 5)、最近傍は核で飛ぶが縁から伸ばす対応は飛ばない、素の重心の pixel-locking はガウス重みで減る
 6. 合成の規約: 描画は補間しない(整数シフトで像が厳密に動く)、エントロピー、模型なしの固着半径
 7. 有限要素の読み込み: 合成の半空間点荷重場で fem_vs_halfspace が r·u = 一定・Cerruti の ν を返す(構造入力)、ヘッダ・座標不一致は fail-closed、
    実データ(FULLSEYE_TAXIM_DATA)があるときだけ r½ と ν の門
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

import pivops
import tacsim as T
import tacslip as S

E, NU, R, P, MU = 0.2e6, 0.48, 6.0e-3, 0.5, 0.5
G = E / (2 * (1 + NU))
ES = T.combined_modulus(E, NU)
HZ = T.hertz_sphere(P, R, ES)
A = HZ["a"]
N, FOV = 128, 12.0e-3                     # 93.75 µm/px、a = 21.9 px(テストは PoC の半分の格子)
PITCH = FOV / N
_trapz = getattr(np, "trapezoid", None) or np.trapz


@pytest.fixture(scope="module")
def grid():
    X, Y, r, _ = T._grid(N, FOV)
    kern = S.cerruti_kernel(N, PITCH, G, NU)
    return X, Y, r, kern


@pytest.fixture(scope="module")
def scene(grid):
    """P + Q(Q/μP = 0.5)の合成像の対(マーカー 8 px ピッチ、半径 2.5 px。6 px だと隣の縞がガウス窓に入り 0.2 px 偏る、実測)。"""
    X, Y, r, kern = grid
    mp = S.mindlin_partial_slip(0.5 * MU * P, HZ, MU, G, NU)
    fld = S.membrane_shear_field(HZ, mp, X, Y, kern)
    gh = T.membrane_indent_sphere(HZ, N, FOV)
    bg = T.membrane_render_rgb(gh["normals"], T.membrane_lights(55.0), ambient=0.03)
    pts = S.membrane_markers(N, 8.0)
    p_ref = S.displace_markers(pts, fld["urx"], fld["ury"], PITCH)
    p_cur = S.displace_markers(pts, fld["urx"] + fld["ux"], fld["ury"] + fld["uy"], PITCH)
    m_ref = S.marker_image(S.membrane_render_markers(bg, p_ref, 2.5, 0.85), bg)
    m_cur = S.marker_image(S.membrane_render_markers(bg, p_cur, 2.5, 0.85), bg)
    return {"mp": mp, "fld": fld, "bg": bg, "pts": pts, "p_ref": p_ref, "p_cur": p_cur, "m_ref": m_ref, "m_cur": m_cur}


# ── 1. 閉形式 ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("qr", [0.25, 0.5, 0.9])
def test_partial_slip_identities(qr):
    mp = S.mindlin_partial_slip(qr * MU * P, HZ, MU, G, NU)
    assert mp["c_over_a"] == pytest.approx((1 - qr) ** (1 / 3), rel=1e-12)
    rr = np.linspace(0, A, 40001)
    assert 2 * math.pi * _trapz(S.mindlin_traction(rr, mp) * rr, rr) == pytest.approx(qr * MU * P, rel=1e-3)
    slip = np.linspace(mp["c"] * 1.001, A * 0.999, 200)
    assert np.allclose(S.mindlin_traction(slip, mp), MU * T.hertz_pressure(slip, A, HZ["p0"]), rtol=0, atol=1e-9 * MU * HZ["p0"])
    stick = np.linspace(0, mp["c"] * 0.999, 200)
    assert np.all(S.mindlin_traction(stick, mp) < MU * T.hertz_pressure(stick, A, HZ["p0"]))
    assert not mp["slipping"] and mp["delta_x"] == pytest.approx(3 * MU * P * (2 - NU) / (16 * G * A) * (1 - (1 - qr) ** (2 / 3)), rel=1e-12)


def test_partial_slip_stiffness_anchor_and_fail_closed():
    h = 1e-7 * MU * P
    full = S.mindlin_partial_slip(MU * P, HZ, MU, G, NU)
    assert S.mindlin_partial_slip(h, HZ, MU, G, NU)["delta_x"] / h == pytest.approx(1 / full["k_t"], rel=1e-6)
    assert full["k_t"] == pytest.approx(8 * G * A / (2 - NU), rel=1e-12) and full["c"] == 0.0 and full["slipping"]
    over = S.mindlin_partial_slip(1.3 * MU * P, HZ, MU, G, NU)
    assert over["slipping"] and over["c"] == 0.0 and over["delta_x"] == pytest.approx(full["delta_x"], rel=1e-12)
    hz3 = T.hertz_sphere(0.08, 3.0e-3, ES)                                         # 計画書の錨: R 3 mm・0.08 N・μ 0.5・Q/μP 0.5 → 70.5 µm
    assert S.mindlin_partial_slip(0.5 * 0.5 * 0.08, hz3, 0.5, G, NU)["delta_x"] * 1e6 == pytest.approx(70.5, abs=0.1)
    for bad in ((-0.1, HZ, MU, G, NU), (0.1, HZ, 0.0, G, NU), (0.1, HZ, MU, -1.0, NU), (0.1, HZ, MU, G, 0.6), (0.1, {"a": A}, MU, G, NU)):
        with pytest.raises(ValueError):
            S.mindlin_partial_slip(*bad)
    with pytest.raises(ValueError):
        S.mindlin_traction(np.zeros(3), {"a": A})


# ── 2. ūr ──────────────────────────────────────────────────────────────────────
def test_surface_ur_point_load_peak_and_ratio():
    ur = S.hertz_surface_ur(np.array([3 * A, 5 * A]), A, HZ["p0"], G, NU)
    assert np.allclose(ur, -(1 - 2 * NU) * P / (4 * math.pi * G * np.array([3 * A, 5 * A])), rtol=1e-12)
    rf = np.linspace(0.5 * A, 1.5 * A, 20001)
    u = np.abs(S.hertz_surface_ur(rf, A, HZ["p0"], G, NU))
    assert rf[np.argmax(u)] / A == pytest.approx(0.93, abs=0.01)                    # 最大は縁でなく内側
    assert u.max() / abs(S.hertz_surface_ur(np.array([A]), A, HZ["p0"], G, NU)[0]) == pytest.approx(1.022, abs=0.002)
    for nu, want in ((0.48, 1.63), (0.3, 12.1)):                                     # G・E*・Hertz の表を同じ ν で揃える(混ぜると比が壊れる)
        g_nu = E / (2 * (1 + nu)); hz_nu = T.hertz_sphere(P, R, T.combined_modulus(E, nu))
        ur_a = abs(S.hertz_surface_ur(np.array([hz_nu["a"]]), hz_nu["a"], hz_nu["p0"], g_nu, nu)[0])
        assert 100 * ur_a / hz_nu["delta"] == pytest.approx(want, abs=0.05)
        assert ur_a / hz_nu["delta"] == pytest.approx(2 * (1 - 2 * nu) / (3 * math.pi * (1 - nu)), rel=1e-9)
    assert S.hertz_surface_ur(np.array([0.0]), A, HZ["p0"], G, NU)[0] == 0.0
    with pytest.raises(ValueError):
        S.hertz_surface_ur(rf, -A, HZ["p0"], G, NU)


# ── 3. Cerruti 畳み込み ────────────────────────────────────────────────────────────
def test_cerruti_matches_johnson_391_and_mindlin_uniformity(grid):
    X, Y, r, kern = grid
    q0 = MU * HZ["p0"]
    u = S.cerruti_surface_displacement(np.where(r < A, q0 * np.sqrt(np.maximum(0, 1 - (r / A) ** 2)), 0.0), kern)
    cf = S.hertzian_tangential_inner(X, Y, q0, A, G, NU)
    inner = r < 0.9 * A
    ux0 = math.pi * q0 / (32 * G * A) * 4 * (2 - NU) * A * A
    assert np.sqrt(np.mean((u["ux"] - cf["ux"])[inner] ** 2)) / ux0 < 0.01
    assert np.sqrt(np.mean((u["uy"] - cf["uy"])[inner] ** 2)) / np.abs(cf["uy"][inner]).max() < 0.03
    assert np.ptp(cf["ux"][inner]) / ux0 > 0.3                                       # 非一様な場で核の形まで試している
    mp = S.mindlin_partial_slip(0.5 * MU * P, HZ, MU, G, NU)
    fld = S.membrane_shear_field(HZ, mp, X, Y, kern)
    core = r <= 0.9 * mp["c"]
    assert fld["ux"][core].std() / mp["delta_x"] < 0.01 and fld["ux"][core].mean() == pytest.approx(mp["delta_x"], rel=0.01)
    assert np.abs(fld["uy"][core]).max() < 0.01 * mp["delta_x"]
    band = np.abs(r - 2.5 * A) < 0.5 * PITCH                                          # 遠方 1/r(窓は 5.8a なので 2.5a で)
    assert (fld["ux"][band] * r[band]).mean() / (mp["Q"] * (2 - NU) / (4 * math.pi * G)) == pytest.approx(1.0, abs=0.06)
    assert fld["mask_stick"].sum() > 0 and fld["mask_slip"].sum() > 0 and not (fld["mask_stick"] & fld["mask_slip"]).any()
    k3 = S.cerruti_kernel(16, PITCH, G, NU, with_uz=True)
    assert "Kzx" in k3 and "uz" in S.cerruti_surface_displacement(np.ones((16, 16)), k3)
    with pytest.raises(ValueError):
        S.cerruti_surface_displacement(np.zeros((N + 1, N)), kern)
    with pytest.raises(ValueError):
        S.cerruti_kernel(4, PITCH, G, NU)


# ── 4. 逆算 ─────────────────────────────────────────────────────────────────────
def test_similarity_model_inverts_true_field_and_tracked_scene(grid, scene):
    X, Y, r, kern = grid
    model = S.mindlin_model(HZ, X, Y, kern, G, NU)
    pts = scene["p_ref"]
    inside = (pts[:, 0] > 3) & (pts[:, 0] < N - 4) & (pts[:, 1] > 3) & (pts[:, 1] < N - 4)
    pts = pts[inside]
    u_true = np.column_stack([S._sample(scene["fld"]["ux"], pts), S._sample(scene["fld"]["uy"], pts)])
    fit = S.mindlin_fit(model, pts, u_true)
    assert fit["c_over_a"] == pytest.approx(scene["mp"]["c_over_a"], abs=0.01) and fit["mu"] == pytest.approx(MU, rel=0.03)
    assert fit["q_ratio"] == pytest.approx(0.5, abs=0.02) and fit["Q"] == pytest.approx(scene["mp"]["Q"], rel=0.03)
    tr = S.marker_track(scene["m_ref"], scene["m_cur"], 0.85, 8.0, 2.5)
    assert tr["matched"] >= min(tr["n0"], tr["n1"]) - 2 and tr["matched"] > 180
    err = tr["u"] - np.column_stack([S._sample(scene["fld"]["ux"], tr["p0"]), S._sample(scene["fld"]["uy"], tr["p0"])]) / PITCH
    assert np.sqrt(np.mean(err ** 2)) < 0.05 and np.abs(err).max() < 0.3
    fit2 = S.mindlin_fit(model, tr["p0"], tr["u"] * PITCH)
    assert fit2["q_ratio"] == pytest.approx(0.5, abs=0.05) and fit2["c_over_a"] == pytest.approx(scene["mp"]["c_over_a"], abs=0.03)
    full = S.mindlin_fit(model, pts, 1.7 * np.column_stack([S._sample(model["gx"], pts), S._sample(model["gy"], pts)]) * HZ["p0"] / P)
    assert full["c_over_a"] < 0.03 and full["q_ratio"] > 0.99 and full["muP"] == pytest.approx(1.7, rel=0.02)   # 全滑りの場は q′ だけ
    with pytest.raises(ValueError):
        S.mindlin_fit(model, pts[:2], u_true[:2])


# ── 5. 反例(追跡の罠) ─────────────────────────────────────────────────────────────
def test_lattice_aliasing_counterexample(scene):
    bg = scene["bg"]
    pts = S.membrane_markers(N, 8.0, 0.0, 0.0)
    m0 = S.marker_image(S.membrane_render_markers(bg, pts, 2.5, 0.85), bg)
    reads = {}
    for dx in (3.0, 5.0):
        m1 = S.marker_image(S.membrane_render_markers(bg, pts + np.array([dx, 0.0]), 2.5, 0.85), bg)
        reads[dx] = float(np.nanmedian(np.asarray(pivops.piv_cross_correlate(m0, m1, window=32, overlap=0.5)[0])[1]))
    assert reads[3.0] == pytest.approx(3.0, abs=0.02) and reads[5.0] == pytest.approx(-3.0, abs=0.02)     # 5 − 8: 格子周期のエイリアス
    pj = pts + np.random.default_rng(0).uniform(-1.5, 1.5, pts.shape)
    mj0 = S.marker_image(S.membrane_render_markers(bg, pj, 2.5, 0.85), bg)
    mj1 = S.marker_image(S.membrane_render_markers(bg, pj + np.array([5.0, 0.0]), 2.5, 0.85), bg)
    assert float(np.nanmedian(np.asarray(pivops.piv_cross_correlate(mj0, mj1, window=32, overlap=0.5)[0])[1])) == pytest.approx(5.0, abs=0.02)


def test_grow_matching_beats_nearest_neighbour_on_a_core_shift():
    """核が 6.4 px(ピッチ 8 に近い)動き、縁は動かない場: 最近傍は核で隣に飛ぶ、縁から伸ばす対応は全部正しい。"""
    from scipy.spatial import cKDTree
    p0 = S.membrane_markers(160, 8.0, 0.0, 0.0)
    rc = np.hypot(p0[:, 0] - 79.5, p0[:, 1] - 79.5)
    u = 6.4 * np.exp(-(rc / 30.0) ** 2)
    p1 = p0 + np.column_stack([u, np.zeros_like(u)])
    mt = S.marker_match_grow(p0, p1, 8.0)
    assert mt["matched"] == len(p0) and np.array_equal(mt["i0"], mt["i1"])            # 同じ並びなので index が一致 = 正しい対応
    d, i = cKDTree(p1).query(p0)
    wrong_nn = int((i != np.arange(len(p0))).sum())
    assert wrong_nn > 20                                                               # 最近傍は核で隣のマーカーへ飛ぶ
    with pytest.raises(ValueError):
        S.marker_match_grow(p0[:, :1], p1, 8.0)


def test_pixel_locking_counterexample(scene):
    bg = scene["bg"]
    pts = S.membrane_markers(N, 8.0, 0.3, 0.3)
    m = S.marker_image(S.membrane_render_markers(bg, pts, 2.5, 0.85), bg)
    det = S.marker_detect(m, 0.85, 2.5, binary=True)
    inside = (pts[:, 0] > 5) & (pts[:, 0] < N - 6) & (pts[:, 1] > 5) & (pts[:, 1] < N - 6)
    from scipy.spatial import cKDTree
    for key, rms_max in (("binary", 0.3), ("weighted_plain", 0.04), ("weighted", 0.02)):
        d, i = cKDTree(det[key]).query(pts[inside], distance_upper_bound=1.5)
        assert np.isfinite(d).all()
        e = det[key][i] - pts[inside]
        assert np.sqrt((e ** 2).mean()) < rms_max
    bias_plain = np.hypot(*(det["weighted_plain"][cKDTree(det["weighted_plain"]).query(pts[inside])[1]] - pts[inside]).mean(0))
    bias_gauss = np.hypot(*(det["weighted"][cKDTree(det["weighted"]).query(pts[inside])[1]] - pts[inside]).mean(0))
    assert bias_plain > 0.008 and bias_gauss < 0.6 * bias_plain                        # 格子共通のバイアスが半分以下に
    assert len(det["weighted"]) == inside.sum() and det["n"] >= len(det["weighted"])
    with pytest.raises(ValueError):
        S.marker_detect(m, 1.5, 2.5)
    with pytest.raises(ValueError):
        S.marker_detect(m[0], 0.85, 2.5)


# ── 6. 合成の規約・指標 ─────────────────────────────────────────────────────────────
def test_render_moves_without_interpolation(scene):
    bg = scene["bg"]
    pts = S.membrane_markers(N, 8.0, 0.0, 0.0)
    img0 = S.membrane_render_markers(np.ones((N, N, 3)), pts, 2.5, 0.85)
    img1 = S.membrane_render_markers(np.ones((N, N, 3)), pts + np.array([1.0, 0.0]), 2.5, 0.85)
    assert np.allclose(img1[:, 8:-8], img0[:, 7:-9])                                   # 整数シフトで像が厳密に動く(補間なし)
    ic = int(np.argmin(np.hypot(pts[:, 0] - 63.5, pts[:, 1] - 63.5)))                  # 中心に最も近いマーカー(1 周目は視野の外)
    att = 1 - S.membrane_render_markers(np.ones((N, N, 3)), pts[ic:ic + 1], 2.5, 0.85)[..., 0]
    assert att.sum() / 0.85 == pytest.approx(math.pi * 2.5 ** 2, rel=0.02)              # 被覆率の和 = 円盤の面積
    assert S.marker_image(bg, bg).max() == 0.0
    with pytest.raises(ValueError):
        S.membrane_render_markers(np.ones((N, N)), pts, 2.5, 0.85)
    with pytest.raises(ValueError):
        S.membrane_render_markers(np.ones((N, N, 3)), pts, 2.5, 1.5)
    with pytest.raises(ValueError):
        S.membrane_markers(N, 1.0)
    with pytest.raises(ValueError):
        S.displace_markers(pts, np.zeros((N, N)), np.zeros((N, N + 1)), PITCH)


def test_slip_entropy_and_modelfree_stick_radius():
    assert S.slip_entropy(np.full(50, 1.0)) == 0.0
    spread = S.slip_entropy(np.linspace(0, 1, 50))
    narrow = S.slip_entropy(np.linspace(0.4, 0.6, 50), vmax=1.0)
    assert spread > narrow > 0.0 and spread == pytest.approx(1.0, abs=0.02)
    with pytest.raises(ValueError):
        S.slip_entropy(np.zeros(0))
    with pytest.raises(ValueError):
        S.slip_entropy(np.ones(3), bins=1)
    pts = S.membrane_markers(96, 8.0, 0.0, 0.0) - 47.5
    rc = np.hypot(pts[:, 0], pts[:, 1])
    u = np.column_stack([np.where(rc < 20.0, 3.0, 3.0 * 20.0 / np.maximum(rc, 20.0)), np.zeros(len(pts))])
    sr = S.stick_radius_modelfree(pts, u)
    assert abs(sr["c_px"] - 20.0) < 8.0 and sr["core_px"] == pytest.approx(3.0)
    with pytest.raises(ValueError):
        S.stick_radius_modelfree(pts[:4], u[:4])


# ── 7. 有限要素の読み込み(構造入力) ─────────────────────────────────────────────────
def _write_fem(tmp, name, X, Y, Z, dx, dy, dz, header=None):
    head = header or "Node Number\tX Location (m)\tY Location (m)\tZ Location (m)\tDirectional Deformation (m)\r\n"
    for comp, d in (("x", dx), ("y", dy), ("z", dz)):
        with open(os.path.join(tmp, "%s_%s.txt" % (name, comp)), "w", encoding="utf-8", newline="") as fh:
            fh.write(head)
            for k in range(len(X)):
                fh.write("%d\t%.6e\t%.6e\t%.6e\t%.6e\r\n" % (k + 1, X[k], Y[k], Z[k], d[k]))


def test_fem_load_and_halfspace_comparison_on_synthetic_point_load(tmp_path):
    """半空間の点荷重(Boussinesq / Cerruti)を節点に撒けば、fem_vs_halfspace は r·u = 1(一定)・r½ なし・Cerruti の ν を返すはず。"""
    rng = np.random.default_rng(3)
    n = 4000
    rr = np.sqrt(rng.uniform(0.05e-3 ** 2, 8e-3 ** 2, n)); th = rng.uniform(-np.pi, np.pi, n)
    X = 0.03 + rr * np.cos(th); Y = 0.035 + rr * np.sin(th); Z = 0.05 + rr ** 2 / (2 * 0.03)
    Fz, Fx, nu, Gm = 0.02, 0.02, 0.45, 6.0e4
    dz_n = (1 - nu) * Fz / (2 * np.pi * Gm * rr)
    dx_t = Fx / (4 * np.pi * Gm) * (2 * (1 - nu) / rr + 2 * nu * np.cos(th) ** 2 / rr)
    dy_t = Fx / (4 * np.pi * Gm) * 2 * nu * np.cos(th) * np.sin(th) / rr
    _write_fem(str(tmp_path), "dz_case", X, Y, Z, 0 * dz_n, 0 * dz_n, dz_n)
    _write_fem(str(tmp_path), "dxdz_case", X, Y, Z, dx_t, dy_t, dz_n)
    fz = S.fem_nodes_load(str(tmp_path), "dz_case"); fxz = S.fem_nodes_load(str(tmp_path), "dxdz_case")
    assert fz["n"] == n and np.allclose(fz["dz"], dz_n) and fxz["name"] == "dxdz_case"
    cmp = S.fem_vs_halfspace(fz, fxz)
    assert cmp["r_half"] is None and np.all(np.abs(cmp["rdz_n"] - 1.0) < 0.08)        # 半空間なら r·dz は一定
    assert cmp["R_dome"] == pytest.approx(0.03, rel=0.05)
    assert len(cmp["ang"]) >= 3
    for d in cmp["ang"][1:]:
        assert d["nu"] == pytest.approx(nu, abs=0.03) and d["R2"] > 0.6          # 環の幅で 1/r が 17 % 変わるので R² は 0.8 止まり
    assert cmp["dy_fit"]["R2"] > 0.9
    with pytest.raises(ValueError):
        _write_fem(str(tmp_path), "badhead", X[:10], Y[:10], Z[:10], dz_n[:10], dz_n[:10], dz_n[:10], header="Node\tX\tY\tZ\tU\r\n")
        S.fem_nodes_load(str(tmp_path), "badhead")
    _write_fem(str(tmp_path), "shift", X[:10], Y[:10], Z[:10], dz_n[:10], dz_n[:10], dz_n[:10])
    with open(os.path.join(str(tmp_path), "shift_y.txt"), "w", encoding="utf-8", newline="") as fh:        # y だけ座標をずらす
        fh.write("Node Number\tX Location (m)\tY Location (m)\tZ Location (m)\tDirectional Deformation (m)\r\n")
        for k in range(10):
            fh.write("%d\t%.6e\t%.6e\t%.6e\t%.6e\r\n" % (k + 1, X[k] + 1e-3, Y[k], Z[k], dz_n[k]))
    with pytest.raises(ValueError):
        S.fem_nodes_load(str(tmp_path), "shift")
    with pytest.raises(FileNotFoundError):
        S.fem_nodes_load(str(tmp_path), "nothing")


@pytest.mark.skipif(not os.environ.get("FULLSEYE_TAXIM_DATA"), reason="FULLSEYE_TAXIM_DATA が未設定(有限要素の節点テキストは repo の外)")
def test_fem_real_nodes_finite_thickness_and_cerruti_angle():
    root = os.environ["FULLSEYE_TAXIM_DATA"]
    fz = S.fem_nodes_load(os.path.join(root, "calibs", "0705_dome_node_dz_0.3"), "0705_dome_node_dz_0.3")
    fxz = S.fem_nodes_load(os.path.join(root, "calibs", "0705_dome_node_dxdz_0.3"), "0705_dome_node_dxdz_0.3")
    assert fz["n"] == 15230
    cmp = S.fem_vs_halfspace(fz, fxz)
    assert 1.5e-3 < cmp["r_half"] < 4e-3                                                # 半空間 1/r から 2 倍外れる半径(有限厚)
    assert cmp["R_dome"] == pytest.approx(27.6e-3, rel=0.05)
    mid = [d for d in cmp["ang"] if 1.4e-3 <= d["r"] <= 2.1e-3]
    assert len(mid) >= 2
    assert all(0.45 <= d["nu"] <= 0.52 and d["R2"] > 0.7 for d in mid)
    assert cmp["ang"][-1]["ratio"] > 2.0                                                # r½ の外では半空間の上限 2 を超える
