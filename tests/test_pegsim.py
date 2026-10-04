# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegsim の門(柔らかい手首のペグ挿入: Whitney の準静的幾何、既知半径の当てはめ、副画素の縁、手首 RGB-D の計測、MJCF)。

numpy だけの門(常に走る):
 1. 寸法の表と fail-closed、Whitney の量の手計算(c = 0.0385、θ_m = 15.9°、面取り許容 1.2 mm、くさびの境目 c/μ = 7.35°)
 2. 二点接触の深さ: 厳密 (1′) と小角 l₂ sin θ = 2c_r が 1〜6° で 0.0023 mm 以内、2-D の長方形近似は 6° で 0.52 mm ずれる(間違いの量)
 3. 第 2 実装: 真の姿勢から接触点数を幾何だけで予測する :func:`contact_state_predict` が l₂ ∓ 0.05 mm で 1 点 / 2 点に切り替わる
 4. くさび・かじり・面取りの閉形式(平行四辺形の縦軸切片 ±λ、原点は内側、1/μ の外は外側、λ < 1 ⇔ l/d < μ)
 5. 既知半径の円当てはめ = :func:`measure.fit_circle`(全周で 1e-9)、短い弧 + 雑音では既知半径のほうが中心が決まる
 6. 既知半径の円柱当てはめが軸を 1e-6 rad で戻す(構造のある半円柱の点群、雑音ありの rms = σ)
 7. 反エイリアスの被覆率から副画素の縁(16 倍の超標本で描いた円盤、半径方向の誤差 max < 0.1 px・平均 < 0.01 px、円の中心 0.01 px)
 8. PnP の恒等式: :func:`camera_world_to_cv` の (R, t) で投影した構造のある点群から :func:`camera.solve_pnp` が姿勢を 1e-9 で戻す
 9. 合成 RGB-D(:func:`peg_synthetic_rgbd`、解析的なレイキャスト、画素中心の深度 + 16 倍超標本の色)で穴中心 ≤ 0.1 px・
    相対ずれ ≤ 0.03 mm・先端の横 ≤ 0.1 px、既知半径(治具の図面)でも同じ中心
10. 成功率の格子の集計(手計算)、MJCF 文字列(壁 n_seg 個、offsamples、numslices=128、ヒンジの位置)
mujoco が要る門(無ければ skip):
11. 深度バッファの位置: offsamples=4 は (−0.125, +0.375) px、0 は画素中心
12. 1 姿勢の計測: 穴 ≤ 0.1 px、相対ずれ ≤ 0.03 mm、先端の横 ≤ 0.05 px、軸方向 ≤ 1.0 px(0.3 px は未達、正直に)
13. l₂ の第 2 実装(mj_geomDistance の二分法)が閉形式と 0.08 mm 以内、l₂ sin θ ∈ [0.395, 0.400] mm、接触状態が l₂ ∓ 0.3 mm で切り替わる
14. ルールベースの挿入 1 走行: ε = (2, 1) mm・θ = 2° を補正ありで成功、二点接触の始まりで l sin θ = 0.40 ± 0.01 mm、
    接触点数の予測と接触計算が ±1 で 90 % 以上一致、サーボの真のずれが単調に減る
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import camera
import measure as FM
import pegsim as P
import render3d

KP = P.peg_params()
DEG = math.pi / 180.0


# ── 1. 寸法と Whitney の量 ─────────────────────────────────────────────────────
def test_peg_params_defaults_and_fail_closed():
    assert KP["r"] == 5.0e-3 and KP["R"] == 5.2e-3 and KP["chamfer"] == 1.0e-3 and KP["mu"] == 0.3
    assert KP["d"] == 2 * KP["r"] and KP["D"] == 2 * KP["R"] and KP["image_size"] == (640, 480)
    for bad in (dict(r=5.2e-3, R=5.0e-3), dict(r=0.0), dict(chamfer=30e-3), dict(mu=-0.1), dict(chamfer_deg=90.0),
                dict(n_seg=4), dict(image_size=(8, 8))):
        with pytest.raises(ValueError):
            P.peg_params(**bad)
    with pytest.raises(ValueError, match="peg_params"):
        P.whitney_clearance({"r": 1.0})


def _rot_err_deg(R_est, R_true):
    """2 つの回転の差の角 [deg]。``acos((tr−1)/2)`` は単位行列の近くで ``acos(1−ε) ≈ √(2ε)`` の
    床(2e-8 rad = 1.2e-6°)を持ち、1e-7° の門は丸めの向きで通ったり落ちたりする(手元は tr = 3.0、
    Linux CI は 2.9999999999999996)。歪対称部 ‖D − Dᵀ‖_F = 2√2 |sin θ| は θ → 0 で桁を失わない。"""
    D = np.asarray(R_est, float) @ np.asarray(R_true, float).T
    s = np.linalg.norm(D - D.T) / (2.0 * math.sqrt(2.0))
    return math.degrees(math.asin(min(1.0, s)))



def test_whitney_clearance_hand_values():
    wc = P.whitney_clearance(KP)
    assert wc["c"] == pytest.approx(0.2 / 5.2, rel=1e-12)                    # (D − d)/D、OCW p.11
    assert wc["c_r"] == pytest.approx(0.2e-3, abs=1e-15)
    assert wc["theta_m"] == pytest.approx(math.sqrt(2 * 0.2 / 5.2), rel=1e-12)  # √(2c) = 0.2774 rad = 15.9°
    assert wc["theta_m_exact"] == pytest.approx(math.acos(5.0 / 5.2), rel=1e-12)
    assert abs(wc["theta_m"] - wc["theta_m_exact"]) < 1e-3                  # 2 次の近似は 0.05° 違う
    assert wc["eps_chamfer_max"] == pytest.approx(1.2e-3, abs=1e-15)
    assert wc["theta_wedge"] == pytest.approx((0.2 / 5.2) / 0.3, rel=1e-12)    # 7.35°
    assert P.whitney_clearance(P.peg_params(mu=0.0))["theta_wedge"] == math.inf


# ── 2-3. 二点接触の深さ ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("th_deg", [1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
def test_two_point_depth_small_angle_identity_and_the_rectangle_error(th_deg):
    th = th_deg * DEG
    l2 = P.two_point_depth(KP, th)
    l2s = P.two_point_depth(KP, th, "small_angle")
    l2r = P.two_point_depth(KP, th, "rectangle")
    assert 0.3975e-3 <= l2 * math.sin(th) <= 0.4e-3 + 1e-12                 # l₂ sin θ ≈ 2c_r、4 次の項で下がる(6° で 0.3977)
    assert abs(l2 - l2s) < 0.03e-3                                           # 小角の式との差
    assert l2r < l2 - 0.08e-3 * (th_deg / 1.0) ** 0.5                        # 長方形近似は常に浅い
    if th_deg == 6.0:
        assert 0.45e-3 < l2 - l2r < 0.6e-3                                   # 6° で 0.52 mm ずれる(試作で捨てた理由)
    if th_deg == 1.0:
        assert l2 > KP["hole_depth"]                                         # 1° では穴より深い = 二点接触は起きない


def test_two_point_depth_fail_closed():
    with pytest.raises(ValueError, match="theta"):
        P.two_point_depth(KP, 0.0)
    with pytest.raises(ValueError, match="does not enter"):
        P.two_point_depth(KP, P.whitney_clearance(KP)["theta_m_exact"])
    with pytest.raises(ValueError, match="model"):
        P.two_point_depth(KP, 0.03, "cylinder")


@pytest.mark.parametrize("th_deg", [1.5, 2.0, 3.0, 4.0, 6.0])
def test_contact_state_predict_is_a_second_implementation_of_l2(th_deg):
    """先端の縁を −x の壁に付けた姿勢で、l₂ − 0.05 mm は 1 点(tip)、l₂ + 0.05 mm は 2 点(tip+mouth)。"""
    th = th_deg * DEG
    l2 = P.two_point_depth(KP, th)
    xt = -KP["R"] + KP["r"] * math.cos(th)
    a = (math.sin(th), 0.0, math.cos(th))
    lo = P.contact_state_predict(KP, (xt, 0.0, -(KP["chamfer"] + l2 - 0.05e-3)), a, tol=1e-9)
    hi = P.contact_state_predict(KP, (xt, 0.0, -(KP["chamfer"] + l2 + 0.05e-3)), a, tol=1e-9)
    assert (lo["n"], lo["where"]) == (1, "tip")
    assert (hi["n"], hi["where"]) == (2, "tip+mouth")
    assert lo["tilt"] == pytest.approx(th, abs=1e-12)
    assert hi["depth_below_chamfer"] == pytest.approx(l2 + 0.05e-3, abs=1e-12)


def test_contact_state_predict_air_centre_chamfer_and_fail_closed():
    assert P.contact_state_predict(KP, (0.0, 0.0, 0.005), (0, 0, 1))["where"] == "none"            # 空中
    assert P.contact_state_predict(KP, (0.0, 0.0, -0.010), (0, 0, 1))["where"] == "none"           # 真ん中を垂直に
    assert P.contact_state_predict(KP, (0.0, 0.0, -0.010), (0, 0, -1))["tilt"] == 0.0              # 軸の向きは正規化
    c = P.contact_state_predict(KP, (1.0e-3, 0.0, -0.0005), (0, 0, 1))                              # 面取りの帯で縁に触れる
    assert (c["n"], c["where"]) == (1, "chamfer")                                                   # 5 + 1.0 ≥ 5.2 + 0.5
    assert P.contact_state_predict(KP, (0.5e-3, 0.0, -0.0005), (0, 0, 1))["where"] == "none"       # 5.5 < 5.7
    with pytest.raises(ValueError, match="axis"):
        P.contact_state_predict(KP, (0, 0, -0.01), (0, 0, 0))
    with pytest.raises(ValueError, match="3-vector"):
        P.contact_state_predict(KP, (0, 0), (0, 0, 1))


# ── 4. くさび・かじり・面取り ───────────────────────────────────────────────────
def test_wedging_check_closed_form():
    w3 = P.wedging_check(KP, 3 * DEG)
    assert w3["possible"] is False and w3["theta_limit"] == pytest.approx(7.3529 * DEG, rel=1e-3)
    assert w3["l2"] == pytest.approx(P.two_point_depth(KP, 3 * DEG), rel=1e-12)
    assert w3["lambda"] == pytest.approx(w3["l2"] / (KP["d"] * 0.3), rel=1e-12)
    assert P.wedging_check(KP, 8 * DEG)["possible"] is True
    kp6 = P.peg_params(mu=0.6)
    assert P.wedging_check(kp6, 3 * DEG)["possible"] is False and P.wedging_check(kp6, 4 * DEG)["possible"] is True
    # 小角では「θ > c/μ」と「l₂/d < μ」が同じ判定(OCW p.28 と p.9 の合成)
    for th_deg in (2.0, 3.0, 4.0, 6.0, 8.0, 10.0):
        w = P.wedging_check(KP, th_deg * DEG)
        assert w["possible"] == w["possible_small_angle"] == (w["lambda"] < 1.0), th_deg
    assert P.wedging_check(P.peg_params(mu=0.0), 10 * DEG)["possible"] is False
    assert P.wedging_check(KP, 20 * DEG)["l2"] == 0.0                        # θ_m を超えると入口で二点接触
    with pytest.raises(ValueError):
        P.wedging_check(KP, -0.1)


def test_jamming_diagram_parallelogram_closed_form():
    ell = 5.0e-3
    j = P.jamming_diagram(KP, ell)
    lam = ell / (KP["d"] * 0.3)
    assert j["lambda"] == pytest.approx(lam, rel=1e-12) and j["fx_limit"] == pytest.approx(1 / 0.3)
    V = j["vertices"]
    assert V.shape == (4, 2)
    assert np.allclose(V[:, 0], [-1 / 0.3, 1 / 0.3, 1 / 0.3, -1 / 0.3])
    assert np.allclose(V[:, 1], [2 * lam + 1, -1, -(2 * lam + 1), 1])
    # 辺 A→B と D→C の縦軸切片は ±λ(OCW p.34 "λ / −λ")
    for (p, q), want in (((V[0], V[1]), lam), ((V[3], V[2]), -lam)):
        y0 = p[1] + (q[1] - p[1]) * (0 - p[0]) / (q[0] - p[0])
        assert y0 == pytest.approx(want, abs=1e-12)
    assert P.jamming_diagram(KP, ell, 0.0, 0.0)["inside"] is True
    assert P.jamming_diagram(KP, ell, 1 / 0.3 + 0.01, 0.0)["inside"] is False
    assert P.jamming_diagram(KP, ell, 0.0, lam + 0.01)["inside"] is False
    assert P.jamming_diagram(KP, ell, 0.0, lam - 0.01)["inside"] is True
    assert P.jamming_diagram(KP, 2 * ell)["lambda"] > lam                   # 深いほど縦に広がる
    assert P.jamming_diagram(KP, 0.0)["lambda"] == 0.0
    with pytest.raises(ValueError):
        P.jamming_diagram(KP, -1e-3)
    with pytest.raises(ValueError, match="mu"):
        P.jamming_diagram(P.peg_params(mu=0.0), ell)


def test_chamfer_capture_limit_is_w_plus_cr():
    assert P.chamfer_capture(KP, 1.2e-3)["captured"] is True
    assert P.chamfer_capture(KP, -1.2e-3)["captured"] is True
    assert P.chamfer_capture(KP, 1.2001e-3)["captured"] is False
    for e in (2.0e-3, 3.0e-3):
        assert P.chamfer_capture(KP, e)["captured"] is False
    assert P.chamfer_capture(KP, 0.7e-3)["margin"] == pytest.approx(0.5e-3, abs=1e-12)
    assert P.chamfer_capture(P.peg_params(chamfer=0.0), 0.3e-3)["captured"] is False   # 面取りなしは c_r だけ


# ── 5-6. 既知半径の当てはめ ─────────────────────────────────────────────────────
def test_circle_fit_known_radius_equals_free_fit_on_a_full_circle_and_wins_on_an_arc():
    rng = np.random.default_rng(5)
    cy, cx, r = 120.3, 200.7, 37.0
    ph = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    full = np.column_stack([cy + r * np.sin(ph), cx + r * np.cos(ph)])
    a = P.circle_fit_known_radius(full, r)
    b = FM.fit_circle(full)
    assert abs(a["cy"] - cy) < 1e-9 and abs(a["cx"] - cx) < 1e-9 and a["rms"] < 1e-9
    assert abs(a["cy"] - b["cy"]) < 1e-9 and abs(a["cx"] - b["cx"]) < 1e-9
    # 25° の弧 + 0.1 px の雑音(10 種): 半径を固定すると中心が決まる(自由な当てはめは半径と中心が相殺する)。
    # 1 回の比較は運で逆転しうる(30 種で比の最小 1.84)ので、中央値で見る —— 実測 known 0.14 px / free 3.9 px。
    ph = np.linspace(0.2, 0.2 + math.radians(25.0), 25)
    err_k, err_f = [], []
    for seed in range(10):
        rng = np.random.default_rng(seed)
        arc = np.column_stack([cy + r * np.sin(ph), cx + r * np.cos(ph)]) + rng.normal(0, 0.1, (25, 2))
        k = P.circle_fit_known_radius(arc, r)
        f = FM.fit_circle(arc)
        err_k.append(math.hypot(k["cy"] - cy, k["cx"] - cx))
        err_f.append(math.hypot(f["cy"] - cy, f["cx"] - cx))
    assert len(err_k) == 10
    assert float(np.median(err_k)) < 0.3 and max(err_k) < 0.6, err_k
    assert float(np.median(err_f)) > 5.0 * float(np.median(err_k)), (np.median(err_k), np.median(err_f))
    with pytest.raises(ValueError):
        P.circle_fit_known_radius(full[:1], r)
    with pytest.raises(ValueError):
        P.circle_fit_known_radius(full, 0.0)
    with pytest.raises(ValueError):
        P.circle_fit_known_radius(np.array([[0.0, np.nan], [1.0, 1.0]]), r)


def _half_cylinder(axis_pt, axis, r, n_len=12, n_ang=15):
    """カメラから見える側の半円柱の点(構造のある入力: 一様乱数でなく格子)。"""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    e1 = np.cross(axis, [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    t = np.linspace(0, 0.03, n_len)
    ph = np.linspace(-np.pi / 2, np.pi / 2, n_ang)
    T, PH = np.meshgrid(t, ph, indexing="ij")
    return (np.asarray(axis_pt)[None, :] + T.ravel()[:, None] * axis[None, :]
            + r * np.cos(PH).ravel()[:, None] * e1[None, :] + r * np.sin(PH).ravel()[:, None] * e2[None, :])


def test_cylinder_fit_known_radius_recovers_the_axis():
    axis = np.array([0.03, 0.0, 1.0])
    axis /= np.linalg.norm(axis)
    c = np.array([0.002, -0.001, 0.09])
    pts = _half_cylinder(c, axis, 5e-3)
    assert len(pts) == 180
    a0 = axis + np.array([0.02, 0.01, 0.0])
    fit = P.cylinder_fit_known_radius(pts, 5e-3, c + np.array([0.3e-3, -0.2e-3, 0.0]), a0)
    assert math.acos(min(1.0, abs(float(fit["axis"] @ axis)))) < 1e-6
    d = fit["axis_point"] - c
    assert np.linalg.norm(d - (d @ axis) * axis) < 1e-7                      # 軸に垂直な成分だけが意味を持つ
    assert fit["rms"] < 1e-9 and fit["axis"] @ a0 > 0
    noisy = pts + np.random.default_rng(1).normal(0, 20e-6, pts.shape)
    fn = P.cylinder_fit_known_radius(noisy, 5e-3, c, a0)
    assert 10e-6 < fn["rms"] < 30e-6
    with pytest.raises(ValueError):
        P.cylinder_fit_known_radius(pts[:3], 5e-3, c, axis)
    with pytest.raises(ValueError):
        P.cylinder_fit_known_radius(pts, 5e-3, c, (0, 0, 0))


# ── 7. 副画素の縁 ───────────────────────────────────────────────────────────────
def _aa_disc(H, W, cy, cx, r, ss=16, bright=200.0, dark=20.0):
    """16 倍超標本の円盤(内側 dark・外側 bright)。被覆率で混ぜた灰色画像と、整数画素の内外マスク。"""
    yy, xx = np.mgrid[0:H * ss, 0:W * ss]
    y = (yy + 0.5) / ss - 0.5
    x = (xx + 0.5) / ss - 0.5
    inside = ((y - cy) ** 2 + (x - cx) ** 2) <= r * r
    cov = inside.reshape(H, ss, W, ss).mean(axis=(1, 3))
    gray = bright * (1 - cov) + dark * cov
    yi, xi = np.mgrid[0:H, 0:W]
    d = np.hypot(yi - cy, xi - cx)
    return gray, d > r, d <= r                                               # 画素中心で割った内外(隣り合う)


def test_coverage_edge_points_sit_on_the_circle_to_a_tenth_of_a_pixel():
    cy, cx, r = 60.37, 70.81, 25.3
    gray, outside_px, inside_px = _aa_disc(120, 140, cy, cx, r)
    uv = P.coverage_edge_points(gray, outside_px, inside_px)                 # 明るい側が inside(板)、暗い側が outside(穴)
    assert len(uv) >= 200
    rad = np.hypot(uv[:, 1] - cy, uv[:, 0] - cx) - r
    # 軸方向の被覆率は縁が軸に沿う所で厳密、45° に傾く所で 0.1 px まで崩れる(実測 max 0.097、平均 −0.0005)
    assert np.abs(rad).max() < 0.1 and abs(rad.mean()) < 0.01, (np.abs(rad).max(), rad.mean())
    c = FM.fit_circle(np.column_stack([uv[:, 1], uv[:, 0]]))
    assert abs(c["cy"] - cy) < 0.01 and abs(c["cx"] - cx) < 0.01 and abs(c["r"] - r) < 0.01
    with pytest.raises(ValueError, match="contrast"):
        P.coverage_edge_points(np.full((120, 140), 100.0), outside_px, inside_px)
    with pytest.raises(ValueError, match="shape"):
        P.coverage_edge_points(gray, outside_px[:10], inside_px)


# ── 8. PnP の恒等式 ──────────────────────────────────────────────────────────────
def _wrist_cam_xmat():
    """MJCF の xyaxes="0 -1 0  s2 0 s2"(45° 下向き)。列 = MuJoCo カメラ軸の世界表現。"""
    s2 = 1 / math.sqrt(2)
    x = np.array([0.0, -1.0, 0.0])
    y = np.array([s2, 0.0, s2])
    return np.column_stack([x, y, np.cross(x, y)])


def test_camera_world_to_cv_and_pnp_identity():
    Rwc = _wrist_cam_xmat()
    p = np.array([-0.06, 0.0, 0.07])
    ext = P.camera_world_to_cv(Rwc, p)
    R, t = ext["R"], ext["t"]
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12) and np.allclose(ext["R_cam_to_world"], R.T)
    assert np.allclose(R @ p + t, 0.0, atol=1e-15)                           # カメラ中心はカメラ座標の原点
    fwd = R.T @ np.array([0.0, 0.0, 1.0])                                    # OpenCV の +Z = MuJoCo の −Z
    assert np.allclose(fwd, -Rwc[:, 2], atol=1e-12) and fwd[2] < 0
    K = render3d.intrinsics_from_fov(40.0, 640, 480)
    phis = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    X = np.vstack([np.column_stack([6.2e-3 * np.cos(phis), 6.2e-3 * np.sin(phis), np.zeros(8)]),
                   [0.002, 0.001, 0.010], [0.002, 0.001, 0.030], [0.03, 0.02, 0.0], [-0.02, 0.03, 0.0]])
    uv, z = camera.project_points(X, K, R, t)
    assert np.all(z > 0) and np.all((uv >= 0) & (uv <= [639, 479])), uv
    R2, t2, rms = camera.solve_pnp(X, uv, K)
    assert rms < 1e-9
    assert _rot_err_deg(R2, R) < 1e-7
    assert np.linalg.norm(t2 - t) < 1e-9
    assert np.allclose(z, (X @ R.T + t)[:, 2])
    with pytest.raises(ValueError, match="rotation"):
        P.camera_world_to_cv(np.eye(3) * 2, p)


# ── 9. 合成 RGB-D ───────────────────────────────────────────────────────────────
def test_synthetic_rgbd_measurement_recovers_hole_tip_and_offset():
    th = 2.0 * DEG
    tip = np.array([0.002, 0.001, 0.010])
    axis = np.array([math.sin(th), 0.0, math.cos(th)])
    syn = P.peg_synthetic_rgbd(KP, tip, axis)
    rgb, depth, K, R, t = syn["rgb"], syn["depth"], syn["K"], syn["R"], syn["t"]
    assert rgb.shape == (240, 320, 3) and rgb.dtype == np.uint8 and depth.shape == (240, 320)
    assert np.allclose(syn["axis"], axis) and np.allclose(syn["uv_hole"], camera.project_points(np.zeros((1, 3)), K, R, t)[0][0])
    res = P.peg_offset_from_rgbd(rgb, depth, K, R.T)
    uv_true, _ = camera.project_points(np.vstack([tip, [0, 0, 0]]), K, R, t)
    hole_err = res["hole"]["uv"] - uv_true[1]
    tip_err = res["tip"]["uv"] - uv_true[0]
    assert np.abs(hole_err).max() < 0.1, hole_err
    assert abs(res["hole"]["radius"] - 6.2e-3) < 0.01e-3
    assert abs(res["dx"] - 0.002) < 0.03e-3 and abs(res["dy"] - 0.001) < 0.03e-3, (res["dx"], res["dy"])
    assert abs(res["height"] - 0.010) < 0.2e-3
    assert abs(tip_err[0]) < 0.1 and abs(tip_err[1]) < 1.0, tip_err           # 軸方向(画像の縦)は影の端の限界で 1 px
    assert math.acos(min(1.0, abs(float(res["tip"]["axis"] @ (R @ axis))))) < 0.3 * DEG
    # 画像面の楕円の中心は円の中心の投影ではない(3-D で当てる理由)
    ell = res["hole"]["ellipse"]
    assert math.hypot(ell["cx"] - uv_true[1][0], ell["cy"] - uv_true[1][1]) > 0.3
    with pytest.raises(ValueError, match="3x3"):
        P.peg_offset_from_rgbd(rgb, depth, K, np.eye(2))
    with pytest.raises(RuntimeError, match="not visible"):
        P.peg_tip_from_rgbd(np.full_like(rgb, 140), depth, K)
    # 既知半径(治具の図面 R + W)で当てても同じ中心
    res_k = P.peg_offset_from_rgbd(rgb, depth, K, R.T, hole_radius=6.2e-3)
    assert np.abs(res_k["hole"]["uv"] - uv_true[1]).max() < 0.1 and res_k["hole"]["radius"] == 6.2e-3
    with pytest.raises(ValueError, match="axis"):
        P.peg_synthetic_rgbd(KP, tip, (0, 0, 0))
    with pytest.raises(ValueError, match="width"):
        P.peg_synthetic_rgbd(KP, tip, axis, width=8, height=8)


# ── 10. 集計と MJCF ─────────────────────────────────────────────────────────────
def test_insertion_grid_summary_hand_rows():
    rows = []
    for corr in (False, True):
        for e in (0.0, 1.0, 2.0):
            for tl in (0.0, 2.0):
                rows.append({"eps_mm": e, "tilt_deg": tl, "correct": corr, "success": corr or e <= 1.0})
    s = P.insertion_grid_summary(rows)
    assert s["eps_mm"] == [0.0, 1.0, 2.0] and s["tilt_deg"] == [0.0, 2.0]
    assert np.array_equal(s["rate"][False], [[1, 1], [1, 1], [0, 0]])
    assert np.array_equal(s["rate"][True], np.ones((3, 2)))
    assert s["max_eps_all_ok"] == {False: 1.0, True: 2.0}
    assert s["success_count"] == {False: (4, 6), True: (6, 6)}
    assert int(s["n_runs"][False].sum()) == 6
    with pytest.raises(ValueError):
        P.insertion_grid_summary([])
    with pytest.raises(ValueError, match="success"):
        P.insertion_grid_summary([{"eps_mm": 0, "tilt_deg": 0, "correct": True}])


def test_peg_scene_mjcf_parses_and_carries_both_traps():
    root = ET.fromstring(P.peg_scene_mjcf(KP))
    geoms = root.findall(".//geom")
    names = {g.get("name") for g in geoms}
    assert sum(1 for n in names if n and n.startswith("wall")) == KP["n_seg"]
    assert sum(1 for n in names if n and n.startswith("chamf")) == KP["n_seg"]
    q = root.find("visual/quality")
    assert q.get("numslices") == "128" and q.get("offsamples") == "4"       # 円柱の多角形近似と MSAA
    assert ET.fromstring(P.peg_scene_mjcf(KP, offsamples=0)).find("visual/quality").get("offsamples") == "0"
    peg = next(g for g in geoms if g.get("name") == "peg")
    assert peg.get("type") == "cylinder" and float(peg.get("size").split()[0]) == KP["r"]
    hinge = next(j for j in root.iter("joint") if j.get("name") == "wry")
    assert float(hinge.get("pos").split()[2]) == 0.0                         # lg=None → 中心は手首原点
    hinge0 = next(j for j in ET.fromstring(P.peg_scene_mjcf(KP, lg=0.0)).iter("joint") if j.get("name") == "wry")
    assert float(hinge0.get("pos").split()[2]) == pytest.approx(-KP["peg_length"])   # lg=0 → 先端に中心(RCC)
    wall0 = next(g for g in geoms if g.get("name") == "wall0")
    assert float(wall0.get("pos").split()[0]) == pytest.approx(KP["R"] + 3e-3)        # 内接面は x = R(厚み 6 mm の中心)


# ── 11-14. mujoco ──────────────────────────────────────────────────────────────
def test_depth_buffer_position_depends_on_msaa():
    pytest.importorskip("mujoco")
    a = P.peg_depth_sample_offset(4)
    b = P.peg_depth_sample_offset(0)
    assert (a["du_px"], a["dv_px"]) == (-0.125, 0.375)                       # サンプル 0 の位置
    assert (b["du_px"], b["dv_px"]) == (0.0, 0.0)                            # 画素中心
    assert a["resid_mm"] < 0.001 and b["resid_mm"] < 0.001 and abs(a["frontal_rel_err"]) < 1e-5


def test_render_and_measure_one_pose():
    pytest.importorskip("mujoco")
    sc = P.peg_scene_build(KP)
    try:
        P.peg_set_pose(sc, (0.002, 0.001, 0.010), 2.0 * DEG)
        img = P.peg_wrist_render(sc)
        assert img["rgb"].shape == (480, 640, 3) and img["depth"].shape == (480, 640)
        res = P.peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=KP["r"])
        d, ids = sc["data"], sc["ids"]
        truth = np.vstack([d.site_xpos[ids["tip"]], d.site_xpos[ids["hole_center"]]])
        uv, _ = camera.project_points(truth, img["K"], img["R"], img["t"])
        assert np.abs(res["hole"]["uv"] - uv[1]).max() < 0.1
        assert abs(res["dx"] - 0.002) < 0.03e-3 and abs(res["dy"] - 0.001) < 0.03e-3
        tip_err = res["tip"]["uv"] - uv[0]
        assert abs(tip_err[0]) < 0.05 and abs(tip_err[1]) < 1.0, tip_err      # 軸方向 0.49 px(0.3 px は未達)
        assert abs(res["hole"]["radius"] - 6.2e-3) < 0.01e-3                # numslices=128 で半径が縮まない
        res_k = P.peg_offset_from_rgbd(img["rgb"], img["depth"], img["K"], img["R_cam_to_world"], r_peg=KP["r"],
                                       hole_radius=KP["R"] + KP["chamfer"])
        assert np.abs(res_k["hole"]["uv"] - uv[1]).max() < 0.1
        assert P.peg_contact_state(sc)["state"] == "air"
    finally:
        P.peg_scene_close(sc)


@pytest.mark.parametrize("th_deg", [2.0, 3.0])
def test_two_point_depth_sim_matches_the_closed_form(th_deg):
    pytest.importorskip("mujoco")
    th = th_deg * DEG
    sc = P.peg_scene_build(KP)
    l2_sim = P.peg_two_point_depth_sim(KP, th, scene=sc)
    l2 = P.two_point_depth(KP, th)
    assert abs(l2_sim - l2) < 0.08e-3, (l2_sim, l2)                          # 試作: −0.057 / −0.038 mm
    assert 0.395e-3 <= l2_sim * math.sin(th) <= 0.400e-3
    xt = -KP["R"] + KP["r"] * math.cos(th) - 0.004e-3                        # 先端を 4 µm 壁に押し込む
    P.peg_set_pose(sc, (xt, 0.0, -(KP["chamfer"] + l2_sim - 0.3e-3)), th)
    assert P.peg_contact_state(sc)["state"] == "one_point"
    P.peg_set_pose(sc, (xt, 0.0, -(KP["chamfer"] + l2_sim + 0.3e-3)), th)
    assert P.peg_contact_state(sc)["state"] == "two_point"
    with pytest.raises(ValueError, match="no two-point"):
        P.peg_two_point_depth_sim(KP, 1.0 * DEG, scene=sc)                   # l₂(1°) = 22.9 mm > 穴 20 mm


def test_insertion_run_succeeds_and_meets_whitney_at_the_two_point_onset():
    pytest.importorskip("mujoco")
    r = P.peg_insertion_run(KP, eps_mm=(2.0, 1.0), tilt_deg=2.0, correct=True)
    assert r["status"] == "success" and r["final_depth_mm"] >= 15.0 and r["max_force_N"] < 8.0
    servo = [s for s in r["servo"] if "error" not in s]
    assert len(servo) >= 4
    true_norm = [math.hypot(s["true_dx_mm"], s["true_dy_mm"]) for s in servo]
    assert len(true_norm) >= 4
    assert all(b < a for a, b in zip(true_norm, true_norm[1:])) and true_norm[-1] < 0.1
    assert abs(servo[0]["dx_mm"] - 2.0) < 0.02 and abs(servo[0]["dy_mm"] - 1.0) < 0.02
    nc, npd = np.asarray(r["rec"]["n_con"]), np.asarray(r["rec"]["n_pred"])
    assert len(nc) > 100
    assert np.mean(np.abs(nc - npd) <= 1) >= 0.9
    onset = [(dep, tl) for dep, tl, st in zip(r["rec"]["depth"], r["rec"]["tilt"], r["rec"]["state"]) if st == "two_point"]
    assert len(onset) >= 1
    dep, tl = onset[0]
    assert abs((dep - KP["chamfer"]) * math.sin(tl * DEG) - 0.4e-3) < 0.01e-3   # l sin θ = 2c_r
    assert {"air", "one_point", "two_point"} <= set(r["rec"]["state"])
