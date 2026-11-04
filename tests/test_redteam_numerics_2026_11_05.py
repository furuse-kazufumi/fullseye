"""敵対的検証 2026-11-05(numerics): 長さ・長さ² の絶対の床と、中心化しない当てはめ。

どの門も「真値(閉形式)」か「入力を並進・拡大しても答えが同じ動きをする」不変量で比べる。
尺度は 1e6〜1e-7 を渡り、修正前は少なくとも 1 つの尺度で落ちていた(報告に記載)。
"""
from __future__ import annotations

import numpy as np
import pytest

import measure

# ── N8 / N6: measure.fit_ellipse / fit_circle / fit_line ─────────────────────


def _ellipse_points(ra, rb, ang_deg, cy, cx, n=48):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ph = np.radians(ang_deg)
    x = ra * np.cos(t) * np.cos(ph) - rb * np.sin(t) * np.sin(ph)
    y = ra * np.cos(t) * np.sin(ph) + rb * np.sin(t) * np.cos(ph)
    return np.column_stack([cy + y, cx + x])


CENTRES = [(0.0, 0.0), (700.0, 500.0), (8000.0, 6000.0), (16000.0, 12000.0)]


@pytest.mark.parametrize("cy,cx", CENTRES)
def test_n8_fit_ellipse_is_translation_invariant(cy, cx):
    # 真値: ra=5, rb=4, 20°(雑音なし)。修正前は (8000, 6000) で 5.119 / 3.912 / 21.94°。
    r = measure.fit_ellipse(_ellipse_points(5.0, 4.0, 20.0, cy, cx))
    assert r["ra"] == pytest.approx(5.0, abs=1e-8)
    assert r["rb"] == pytest.approx(4.0, abs=1e-8)
    assert r["angle_deg"] == pytest.approx(20.0, abs=1e-6)
    assert r["cy"] == pytest.approx(cy, abs=1e-8)
    assert r["cx"] == pytest.approx(cx, abs=1e-8)


@pytest.mark.parametrize("s", [1e3, 1.0, 1e-4, 1e-7])
def test_n8_fit_ellipse_scales_with_input(s):
    r = measure.fit_ellipse(_ellipse_points(3.0 * s, 1.0 * s, -35.0, 2.0 * s, -1.0 * s))
    assert r["ra"] / s == pytest.approx(3.0, rel=1e-9)
    assert r["rb"] / s == pytest.approx(1.0, rel=1e-9)
    assert r["angle_deg"] == pytest.approx(-35.0, abs=1e-6)


@pytest.mark.parametrize("off", [0.0, 1e3, 1e5, 1e6])
def test_n6_fit_circle_is_translation_invariant(off):
    # 修正前: off=1e6 で r = 2.00003。
    t = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    pts = np.column_stack([off + 2.0 * np.sin(t), off + 2.0 * np.cos(t)])
    r = measure.fit_circle(pts)
    assert r["r"] == pytest.approx(2.0, abs=1e-9)
    assert r["cy"] == pytest.approx(off, abs=1e-9)
    assert r["cx"] == pytest.approx(off, abs=1e-9)


@pytest.mark.parametrize("s", [1e-6, 4e-7, 1e-7, 1e-10])
def test_n6_fit_circle_small_radius_is_not_degenerate(s):
    # 修正前: 半径 2·4e-7 = 8e-7 から下は r² <= 1e-12 の絶対の床で ValueError。
    t = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    pts = np.column_stack([2.0 * s * np.sin(t), 2.0 * s * np.cos(t)])
    assert measure.fit_circle(pts)["r"] / s == pytest.approx(2.0, rel=1e-9)


def test_n6_fit_line_short_segment_is_not_coincident():
    # 兄弟: fit_line の s[0] <= 1e-12 の絶対の床(長さ 1e-13 の線分を「一致点」と捨てていた)。
    s = 1e-13
    pts = np.column_stack([np.linspace(0, 1, 5) * s, np.linspace(0, 1, 5) * s])
    assert measure.fit_line(pts)["angle_deg"] == pytest.approx(45.0, abs=1e-9)


def test_n6_coincident_points_still_rejected():
    pts = np.full((6, 2), 1234.5)
    for fit in (measure.fit_line, measure.fit_circle, measure.fit_ellipse):
        with pytest.raises(ValueError):
            fit(pts)


# ── N5: superquadric.fit_superquadric ─────────────────────────────────────────


def _ellipsoid_cloud(noise=0.0):
    rng = np.random.default_rng(0)
    d = rng.standard_normal((400, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    P = np.array([1.0, -1.0, 2.0]) + d * np.array([2.0, 1.5, 1.0])
    return P + noise * rng.standard_normal(P.shape)


@pytest.mark.parametrize("s", [1e3, 1.0, 1e-4, 1e-6])
def test_n5_fit_superquadric_recovers_truth_at_any_scale(s):
    # 真値: 楕円体 a=(2,1.5,1)、eps=(1,1)、中心 (1,-1,2)(表面上の厳密点)。
    # 修正前は s <= 1e-4 で gtol が初回評価で満たされ、PCA 初期値 1.979/1.495/1.001 を返した。
    import superquadric as sq
    r = sq.fit_superquadric(_ellipsoid_cloud() * s)
    assert np.sort(r["a"])[::-1] / s == pytest.approx([2.0, 1.5, 1.0], abs=1e-6)
    assert r["t"] / s == pytest.approx([1.0, -1.0, 2.0], abs=1e-6)
    assert r["eps"] == pytest.approx([1.0, 1.0], abs=1e-6)


def test_n5_fit_superquadric_same_solution_for_s1_and_s1e6():
    # 雑音ありの点群(解は真値と少しずれる)でも、s=1 と s=1e-6 で同じ解・残差は s³ 倍。
    import superquadric as sq
    P = _ellipsoid_cloud(noise=0.02)
    r1 = sq.fit_superquadric(P)
    r6 = sq.fit_superquadric(P * 1e-6)
    assert r6["a"] / 1e-6 == pytest.approx(r1["a"], rel=1e-6)
    assert r6["t"] / 1e-6 == pytest.approx(r1["t"], abs=1e-6)
    assert r6["eps"] == pytest.approx(r1["eps"], abs=1e-6)
    assert r6["residual"] / 1e-18 == pytest.approx(r1["residual"], rel=1e-5, abs=0)
    # 返り値の residual は superquadric_residual と同じ量(元の単位)。approx の既定 abs=1e-12 は
    # 1e-21 の量を何とでも一致させるので abs=0 を明示する。
    assert r6["residual"] == pytest.approx(
        sq.superquadric_residual(P * 1e-6, r6["a"], r6["eps"], r6["R"], r6["t"]), rel=1e-9, abs=0)


def test_n5_superquadric_residual_scales_as_length_cubed():
    # 兄弟: superquadric_residual の体積補正 sqrt(max(a1a2a3, 1e-12)) の絶対の床。
    import superquadric as sq
    P = _ellipsoid_cloud(noise=0.02)
    a, eps, R, t = np.array([2.0, 1.5, 1.0]), (1.0, 1.0), np.eye(3), np.array([1.0, -1.0, 2.0])
    r1 = sq.superquadric_residual(P, a, eps, R, t)
    for s in (1e-3, 1e-6):
        rs = sq.superquadric_residual(P * s, a * s, eps, R, t * s)
        assert rs / s ** 3 == pytest.approx(r1, rel=1e-9, abs=0)


def test_n5_fit_superquadric_coincident_points_rejected():
    import superquadric as sq
    with pytest.raises(ValueError):
        sq.fit_superquadric(np.ones((10, 3)))


# ── N7: shapematch.create_cam_pose_look_at_point / render3d.look_at ───────────


def test_n7_look_at_parallel_up_rejected():
    # 修正前: 視線 ∥ up で det=0・rank 1 の行列を例外なく返した。
    import render3d
    import shapematch
    with pytest.raises(ValueError, match="parallel"):
        shapematch.create_cam_pose_look_at_point((0, 0, 5), (0, 0, 0), up=(0, 0, 1))
    with pytest.raises(ValueError, match="parallel"):
        render3d.look_at((0, 0, 5), (0, 0, 0), up=(0, 0, 1))
    with pytest.raises(ValueError, match="coincide"):
        shapematch.create_cam_pose_look_at_point((1, 2, 3), (1, 2, 3))


@pytest.mark.parametrize("tilt", [1e-2, 1e-6, 1e-8])
def test_n7_look_at_slightly_tilted_up_is_orthonormal(tilt):
    # 修正前: +1e-12 の床で tilt=1e-8 で det=0.9998、|RᵀR-I|=2e-4(1e-10 では 0.98)。
    import shapematch
    T = shapematch.create_cam_pose_look_at_point((0, 0, 5), (0, 0, 0), up=(tilt, 0, 1))
    R = T[:3, :3]
    assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-12)
    assert np.abs(R.T @ R - np.eye(3)).max() < 1e-12
    assert R[:, 2] == pytest.approx([0.0, 0.0, -1.0], abs=1e-15)    # z = 前方


def test_n7_look_at_tiny_scene_and_tiny_up():
    # 兄弟: 1e-13 離れた視点・|up| = 1e-12 は正しい入力(絶対の閾値で拒んでいた)。
    import render3d
    import shapematch
    T = shapematch.create_cam_pose_look_at_point((0, 0, 1e-13), (0, 0, 0), up=(0, 1e-12, 0))
    assert np.linalg.det(T[:3, :3]) == pytest.approx(1.0, abs=1e-12)
    ref = render3d.look_at((0, 0, 5), (0, 0, 0), up=(0, 1, 0))
    small = render3d.look_at((0, 0, 5e-13), (0, 0, 0), up=(0, 1e-12, 0))
    assert small[:3, :3] == pytest.approx(ref[:3, :3], abs=1e-12)


# ── N1: tools_geom / geometry2d の長さ² の床 ──────────────────────────────────

SCALES = [1.0, 1e-3, 1e-6, 1e-7]


@pytest.mark.parametrize("s", SCALES)
def test_n1_tools_geom_results_scale_with_input(s):
    import tools_geom as tg
    # 線分 (0,0)-(1,0) と横線 row=1.5: 交点 (1.5, 0) は線分の外 → None(修正前 s=1e-6 で交点を返した)
    assert tg.intersection_segment_line((0, 0, 1 * s, 0), (1.5 * s, -s, 1.5 * s, s)) is None
    # 線分の中の交点はそのまま
    hit = tg.intersection_segment_line((0, 0, 1 * s, 0), (0.5 * s, -s, 0.5 * s, s))
    assert hit is not None and hit / s == pytest.approx([0.5, 0.0], abs=1e-12)
    # 直交 2 直線(修正前 s=1e-7 で「平行」= None)
    il = tg.intersection_lines((0, 0, 1 * s, 0), (0.5 * s, -0.5 * s, 0.5 * s, 0.5 * s))
    assert il is not None and il / s == pytest.approx([0.5, 0.0], abs=1e-12)
    # Plücker: 点 (1,1,0)-(1,1,1) の直線と原点の距離 = √2(修正前 s=1e-6 で 0.707)
    pl = tg.points_to_pluecker_line(np.array([1, 1, 0.0]) * s, np.array([1, 1, 1.0]) * s)
    assert tg.distance_point_pluecker_line([0, 0, 0], pl) / s == pytest.approx(np.sqrt(2.0), rel=1e-12)
    pt = tg.pluecker_line_to_point_direction(pl)["point"] / s
    assert pt[:2] == pytest.approx([1.0, 1.0], rel=1e-12)
    # 線分と円: 線分 (0,-2)-(0,2)、中心 0 半径 1 → 2 点
    assert len(tg.intersection_segment_circle((0, -2 * s, 0, 2 * s), (0, 0), 1 * s)) == 2


@pytest.mark.parametrize("s", SCALES)
def test_n1_geometry2d_results_scale_with_input(s):
    import geometry2d as g2
    # 点 (0.5, 1) と線分 (0,0)-(1,0): 距離 1(修正前 s=1e-6 で 1.031、1e-7 で 1.116)
    assert g2.distance_ps(0.5 * s, 1 * s, 0, 0, 1 * s, 0) / s == pytest.approx(1.0, rel=1e-12)
    assert g2.distance_ps(2 * s, 0, 0, 0, 1 * s, 0) / s == pytest.approx(1.0, rel=1e-12)
    # 2 円 (0,0) r=1 と (1,0) r=1 → (0.5, ±√3/2) の 2 点(修正前 s=1e-6 で 1 点)
    pts = g2.intersection_circles(0, 0, 1 * s, 1 * s, 0, 1 * s)
    assert len(pts) == 2
    got = np.array(sorted([(p / s).tolist() for p in pts], key=lambda q: q[1]))
    assert got == pytest.approx(np.array([[0.5, -np.sqrt(3) / 2], [0.5, np.sqrt(3) / 2]]), abs=1e-12)
    # 点と直線・射影・交点
    assert g2.distance_pl(0.3 * s, 2 * s, 0, 0, 1 * s, 0) / s == pytest.approx(2.0, rel=1e-12)
    assert g2.projection_pl(0.3 * s, 2 * s, 0, 0, 1 * s, 0) / s == pytest.approx([0.3, 0.0], abs=1e-12)
    il = g2.intersection_lines(0, 0, 1 * s, 0, 0.5 * s, -0.5 * s, 0.5 * s, 0.5 * s)
    assert il is not None and il / s == pytest.approx([0.5, 0.0], abs=1e-12)
    assert g2.distance_point_line(0, 2 * s, 0, 0, 0, 0, 1 * s, 0, 0) / s == pytest.approx(2.0, rel=1e-12)


def test_n1_degenerate_inputs_are_explicit():
    import geometry2d as g2
    import tools_geom as tg
    # 長さ 0 の線分の点-線分距離は端点までの距離
    assert g2.distance_ps(3.0, 4.0, 0, 0, 0, 0) == pytest.approx(5.0, rel=1e-15)
    # 2 点が一致する直線: 交点は None、距離・射影は ValueError
    assert g2.intersection_lines(0, 0, 0, 0, 0, 1, 1, 1) is None
    assert tg.intersection_lines((0, 0, 0, 0), (0, 1, 1, 1)) is None
    for bad in (lambda: g2.distance_pl(1, 1, 2, 2, 2, 2),
                lambda: g2.projection_pl(1, 1, 2, 2, 2, 2),
                lambda: g2.distance_point_line(1, 1, 1, 0, 0, 0, 0, 0, 0),
                lambda: tg.pluecker_line_to_point_direction({"direction": [0, 0, 0], "moment": [0, 0, 0]}),
                lambda: tg.intersection_line_circle((1, 1, 1, 1), (0, 0), 1.0)):
        with pytest.raises(ValueError):
            bad()
    # 長さ 0 の線分(輪郭の重複点)と円は交点なし(contours_xld2 が重複点つきの輪郭を渡す)
    assert tg.intersection_segment_circle((0, 1, 0, 1), (0, 0), 1.0) == []
    # 同心円は交点なし、接する 2 円は 1 点
    assert g2.intersection_circles(0, 0, 1, 0, 0, 2) == []
    assert len(g2.intersection_circles(0, 0, 1e-6, 2e-6, 0, 1e-6)) == 1


# ── N4: ICP の収束判定・正則化 ───────────────────────────────────────────────


def _wavy_surface():
    from scipy.spatial.transform import Rotation
    u, v = np.meshgrid(np.linspace(-1, 1, 30), np.linspace(-1, 1, 30))
    Q = np.c_[u.ravel(), v.ravel(), (0.3 * np.sin(2 * u) * np.cos(3 * v)).ravel()]
    Rt = Rotation.from_rotvec([0.05, -0.08, 0.12]).as_matrix()
    tt = np.array([0.03, -0.02, 0.04])
    P = (Q - tt) @ Rt            # Rt·P + tt = Q(既知解)
    return P, Q, Rt, tt


def _rot_err_deg(R, Rt):
    # ‖R − Rt‖_F = 2√2·sin(θ/2)(arccos のトレース式は θ → 0 で √eps の桁しか分解しない)
    f = np.linalg.norm(np.asarray(R, float) - Rt) / (2.0 * np.sqrt(2.0))
    return float(np.degrees(2.0 * np.arcsin(min(f, 1.0))))


ICP_SCALES = [1e3, 1.0, 1e-6, 1e-8]


@pytest.mark.parametrize("s", ICP_SCALES)
def test_n4_registration_icp_converges_at_any_scale(s):
    # 修正前: tol=1e-8 が座標単位で、s=1e-6 で 4.25° ずれた姿勢で止まった。
    import registration
    P, Q, Rt, tt = _wavy_surface()
    R, t, _al, _rmse = registration.icp(P * s, Q * s)
    assert _rot_err_deg(R, Rt) < 1e-6
    assert np.linalg.norm(t / s - tt) < 1e-8


@pytest.mark.parametrize("s", ICP_SCALES)
@pytest.mark.parametrize("reproducible", [False, True])
def test_n4_point_to_plane_icp_converges_at_any_scale(s, reproducible):
    import pointcloud
    import registration
    P, Q, Rt, tt = _wavy_surface()
    N = pointcloud.estimate_normals(Q, k=16)
    R, t, _al, _rmse = registration.point_to_plane_icp(P * s, Q * s, dst_normals=N,
                                                       reproducible=reproducible)
    assert _rot_err_deg(R, Rt) < 1e-6
    assert np.linalg.norm(t / s - tt) < 1e-8


@pytest.mark.parametrize("s", [1.0, 1e-4, 1e-7, 1e-9])
@pytest.mark.parametrize("reproducible", [False, True])
def test_n4_match3d_icp_point2plane_regularisation_is_scale_free(s, reproducible):
    # 修正前: reg = 1e-12·I が生の JᵀJ に足され、s=1e-7 で 1.05° ずれた。
    import match3d
    import pointcloud
    P, Q, Rt, tt = _wavy_surface()
    N = pointcloud.estimate_normals(Q, k=16)
    R, t, *_ = match3d.icp_point2plane(P * s, Q * s, N, iters=30, reproducible=reproducible)
    assert _rot_err_deg(R, Rt) < 1e-6
    assert np.linalg.norm(t / s - tt) < 1e-8


@pytest.mark.parametrize("s", [1.0, 1e-7, 1e-8, 1e-10])
def test_n4_match3d_icp_point2point_small_rmse_gate_is_relative(s):
    # 兄弟: icp_point2point_3d の「rmse < 1e-9 で収束」は絶対量で、s=1e-8 で初回の
    # Kabsch 1 回で止まり 5.6° ずれた。
    import match3d
    P, Q, Rt, tt = _wavy_surface()
    out = match3d.icp_point2point_3d(P * s, Q * s, iters=50)
    R = out["R"] if isinstance(out, dict) else out[0]
    R = np.asarray(R.detach().cpu().numpy() if hasattr(R, "detach") else R)
    assert _rot_err_deg(R, Rt) < 1e-6
