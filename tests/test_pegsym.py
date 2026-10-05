# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pegsym の門(ペグの n 回対称で回転の探索を 1/n に絞る: 群の恒等式・回転の窓の閉形式・期待試行回数・多角形の二点接触・MuJoCo)。

numpy だけの門(常に走る):
 1. 畳み込みの恒等式 symmetry_fold(α + 2πk/n) = symmetry_fold(α)、探索の候補が 1 周期を隙間なく覆う
 2. 回転の窓: 正 n 角形の閉形式 = 平行移動も自由な線形計画、キー付きは窓の外で口に入らない、摩擦の限界の両端
 3. 期待試行回数: 実装(小区間の最初の番号)= 区間の和の長さの式(この test の第 2 実装)、刻みがちょうど 2φ なら (M+1)/2、比 × n → 1
 4. 線形計画の余裕: 正方形を正方形の穴へ = 隙間 δ、ずらした点群は平行移動で戻る、入らない時は負
 5. 穴 = 辺を外へ δ: 正多角形は相似(辺心距離 + δ、向きはそのまま)
 6. 多角形の二点接触: 面に平行な傾きの正方形 = 円柱の式(内接円)、Goli ほか 2024 の (2.28) の小角の極限、他の向きは円の上下限の間
 7. 図から向き: 回した形の読みは同じだけ回る、検出した n、ペグと穴の図から向きの差
 8. 真上のカメラで打ち直した図 = 直接描いた図、下からの鏡像も同じ向き
 9. らせん: 十分条件で覆いの穴 0、破ると穴、期待点数の近似
10. 綴り壊しは ValueError、MJCF の部品
mujoco が要る門(無ければ skip):
11. 正方形の盲目の探索: 試行回数 = 予言、窓の端の内外
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import pegsym as S

A, DELTA, W = 5.0e-3, 0.2e-3, 0.5e-3
CUT = 1.8e-3


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _hole(n, cut=0.0, yaw=0.0):
    return S.polygon_offset(S.polygon_peg(n, A, yaw=yaw, cut=cut)["vertices"], DELTA)["vertices"]


def _px(V, res=0.12e-3, size=200):
    c = (size - 1) / 2.0
    return np.stack([c + V[:, 0] / res, c - V[:, 1] / res], axis=1)


def _arc_union(intervals, P):
    """第 2 実装: 周 P の円周上の閉区間の和の長さ。"""
    segs = []
    for a, b in intervals:
        if b - a >= P:
            return P
        a0 = a % P
        b0 = a0 + (b - a)
        if b0 <= P:
            segs.append((a0, b0))
        else:
            segs += [(a0, P), (0.0, b0 - P)]
    segs.sort()
    tot, ca, cb = 0.0, None, None
    for a, b in segs:
        if cb is None or a > cb:
            if cb is not None:
                tot += cb - ca
            ca, cb = a, b
        else:
            cb = max(cb, b)
    if cb is not None:
        tot += cb - ca
    return min(tot, P)


def test_fold_identity_and_plan_covers_one_period():
    rng = np.random.default_rng(0)
    for _ in range(200):
        n = int(rng.integers(1, 9))
        a = float(rng.uniform(-30, 30))
        k = int(rng.integers(-6, 7))
        assert abs(S.symmetry_fold(a + 2 * math.pi * k / n, n) - S.symmetry_fold(a, n)) < 1e-12
        f = S.symmetry_fold(a, n)
        assert -math.pi / n < f <= math.pi / n + 1e-15
    assert S.symmetry_fold(1.234, 0) == 0.0
    for n, cap in ((3, 0.08), (4, 0.15), (6, 0.12), (1, 0.15)):
        pl = S.rotation_search_plan(n, cap)
        P = pl["period"]
        assert pl["step"] <= 2 * cap + 1e-15
        assert abs(_arc_union([(a - cap, a + cap) for a in pl["angles"]], P) - P) < 1e-12
        assert len(set(np.round(pl["angles"] % P, 12))) == pl["M"]


def test_rotation_window_closed_form_equals_linear_programme():
    for n in (3, 4, 6):
        p = S.polygon_peg(n, A)["vertices"]
        rw = S.rotation_window(n, A, DELTA, W, p, _hole(n))
        assert abs(rw["phi_cap"] - rw["lp"]["plus"]) < 1e-8 and abs(rw["phi_cap"] - rw["lp"]["minus"]) < 1e-8
        rw0 = S.rotation_window(n, A, DELTA, 0.0, p, _hole(n))
        assert abs(rw0["phi_fit"] - rw0["lp"]["plus"]) < 1e-8
    # 窓いっぱい(x ≥ 1)は半周期
    assert S.rotation_window(6, A, DELTA, 2.0e-3)["phi_cap"] == pytest.approx(math.pi / 6)
    # キー付き: 窓の外で口に入らない
    pk = S.polygon_peg(4, A, cut=CUT)
    assert pk["n"] == 1
    rwk = S.rotation_window(1, A, DELTA, W, pk["vertices"], _hole(4, CUT))
    mouth = S.polygon_offset(_hole(4, CUT), W)["vertices"]
    c0 = pk["vertices"].mean(axis=0)
    for deg in range(0, 360, 3):
        a = math.radians(deg)
        Pv = (pk["vertices"] - c0) @ S._rot2(a).T + c0
        inside = abs(S.symmetry_fold(a, 1)) <= rwk["lp"]["plus"]
        assert S.polygon_fit_check(Pv, mouth)["fit"] == inside
    # 摩擦の限界: μ = 0 は π/n、窓の合成は最狭部の窓が下限
    r0 = S.rotation_window(6, A, DELTA, W, mu=0.0)
    assert r0["phi_friction"] == pytest.approx(math.pi / 6) and r0["phi_eff"] == pytest.approx(r0["phi_cap"])
    r5 = S.rotation_window(6, A, DELTA, W, mu=0.5)
    assert r5["phi_eff"] == pytest.approx(r5["phi_fit"])
    s = math.sin(S.rotation_window(4, A, DELTA, W, mu=0.3)["beta_star"])
    assert s * math.sqrt(1 + s * s) == pytest.approx(math.sqrt(2) * 0.3, rel=1e-12)


def test_expected_tries_two_implementations_and_one_over_n():
    for n, cap in ((3, 0.083), (4, 0.152), (6, 0.118), (1, 0.152)):
        for order in ("alternate", "sweep"):
            E = S.search_expected_tries(n, cap, order=order)
            pl = S.rotation_search_plan(n, cap, order=order)
            P = pl["period"]
            ang = pl["angles"]
            E2 = sum(1.0 - (_arc_union([(a - cap, a + cap) for a in ang[:k]], P) if k else 0.0) / P for k in range(len(ang)))
            assert abs(E["expected"] - E2) < 1e-9
    # 刻みがちょうど 2φ なら (M + 1)/2
    for n, M in ((4, 6), (3, 13), (1, 24)):
        cap = math.pi / (n * M)
        E = S.search_expected_tries(n, cap, order="sweep")
        assert E["M"] == M and abs(E["expected"] - (M + 1) / 2) < 1e-9
    for n in (3, 4, 6):
        assert abs(S.search_expected_tries(n, math.radians(0.2))["ratio_vs_blind"] * n - 1) < 0.01
    # 推定値つき: σ が小さいと 1 回に近い
    assert S.search_expected_tries(4, 0.15, estimate_sigma=0.01)["expected_with_estimate"] < 1.001


def test_fit_check_margin_and_translation():
    p = S.polygon_peg(4, A)["vertices"]
    h = _hole(4)
    r = S.polygon_fit_check(p, h)
    assert r["fit"] and abs(r["margin"] - DELTA) < 1e-12
    r2 = S.polygon_fit_check(p + np.array([1.0e-3, -0.5e-3]), h)
    assert np.allclose(r2["t"], [-1.0e-3, 0.5e-3], atol=1e-12) and abs(r2["margin"] - DELTA) < 1e-12
    big = S.polygon_peg(4, A + 0.3e-3)["vertices"]
    r3 = S.polygon_fit_check(big, h)
    assert (not r3["fit"]) and abs(r3["margin"] + 0.1e-3) < 1e-12


def test_offset_of_regular_polygon_is_similar():
    for n in (3, 4, 6):
        p = S.polygon_peg(n, A, yaw=0.3)
        o = S.polygon_offset(p["vertices"], DELTA)
        q = S.polygon_peg(n, A + DELTA, yaw=0.3)["vertices"]
        d = np.min(np.hypot(*(o["vertices"][:, None, :] - q[None, :, :]).transpose(2, 0, 1)), axis=1)
        assert d.max() < 1e-12
        assert np.allclose(o["offsets"], A + DELTA, atol=1e-12)


def test_two_point_depth_face_tilt_matches_cylinder_and_goli_limit():
    p, h = S.polygon_peg(4, A)["vertices"], _hole(4)
    for th in (1.0, 3.0, 6.0):
        r = S.polygon_two_point_depth(p, h, math.radians(th), 0.0)
        assert abs(r["l2"] - r["circle_in"]) < 1e-9
    r = S.polygon_two_point_depth(p, h, math.radians(0.5), 0.0, depth_max=0.2)
    assert abs(r["l2"] / r["goli_small_angle"] - 1) < 2e-3
    for n in (3, 4, 6):
        pv, hv = S.polygon_peg(n, A)["vertices"], _hole(n)
        for psi in np.linspace(0, 2 * math.pi / n, 5):
            r = S.polygon_two_point_depth(pv, hv, math.radians(3.0), float(psi))
            assert r["circle_in"] * (1 - 1e-3) <= r["l2"] <= r["circle_out"] + 1e-9


def test_yaw_read_equivariance_n_and_relative():
    for n, cut in ((3, 0.0), (4, 0.0), (6, 0.0), (4, CUT)):
        ref = S.polygon_yaw_read(S.polygon_coverage_image(_px(S.polygon_peg(n, A, cut=cut)["vertices"]), 200, 4), polarity="bright")
        nn = S.polygon_peg(n, A, cut=cut)["n"]
        assert ref["n_detected"] == nn
        for psi in (0.37, 2.1):
            r = S.polygon_yaw_read(S.polygon_coverage_image(_px(S.polygon_peg(n, A, yaw=psi, cut=cut)["vertices"]), 200, 4), polarity="bright")
            assert math.degrees(abs(S.symmetry_fold(r["yaw"] - ref["yaw"] - psi, nn))) < (0.15 if cut == 0 else 0.5)
    img_p = S.polygon_coverage_image(_px(S.polygon_peg(4, A, yaw=1.3)["vertices"]), 200, 3)
    mouth = S.polygon_offset(_hole(4, 0.0, 0.2), W)["vertices"]
    img_h = 1.0 - S.polygon_coverage_image(_px(mouth), 200, 3)
    rel = S.relative_yaw_from_images(img_p, img_h, 4)
    assert math.degrees(abs(S.symmetry_fold(rel["delta"] - 1.1, 4))) < 0.1


def test_topview_from_straight_down_and_from_below():
    res, size = 0.1e-3, 160
    K = np.array([[400.0, 0, 79.5], [0, 400.0, 79.5], [0, 0, 1]])
    zc = 400.0 * res                                                # 1 画素 = res になる高さ
    # 真下向き(OpenCV: x_c = x, y_c = −y, z_c = zc − z)
    R = np.diag([1.0, -1.0, -1.0])
    t = np.array([0.0, 0.0, zc])
    V = S.polygon_peg(4, 3.0e-3, yaw=0.4)["vertices"]
    direct = S.polygon_coverage_image(_px(V, res, size), size, 4)
    img = direct * 200.0                                            # 真下から見た画像 = 上から見た図そのもの
    top = S.plane_topview(img, K, R, t, z=0.0, extent=size * res, res=res)
    assert np.abs(top - img).max() < 1e-6
    # 下から(x_c = x, y_c = y, z_c = z + zc、カメラは z = −zc で +z を向く): 画像は鏡像、打ち直すと同じ向き
    Rb = np.diag([1.0, 1.0, 1.0])
    tb = np.array([0.0, 0.0, zc])
    mirror = img[::-1, :]
    topb = S.plane_topview(mirror, K, Rb, tb, z=0.0, extent=size * res, res=res)
    assert np.abs(topb - img).max() < 1e-6


def test_spiral_cover_and_expected_points():
    c = W + DELTA
    good = S.spiral_search_points(1.6 * c, c, 4.0e-3)
    eg = S.spiral_expected_tries(good["points"], c, 3.0e-3, grid=61)
    assert good["worst_gap"] <= c and eg["uncovered"] == 0
    assert abs(eg["measured"] - eg["closed"]) / eg["closed"] < 0.10
    bad = S.spiral_search_points(3.0 * c, c, 4.0e-3)
    assert S.spiral_expected_tries(bad["points"], c, 3.0e-3, grid=61)["uncovered"] > 0
    d = np.hypot(*np.diff(good["points"], axis=0).T)
    assert len(d) >= 10
    assert d.max() <= c * (1 + 1e-6) and np.allclose(d[10:], c, rtol=0.03)   # 弦 ≤ 弧長の刻み(中心の近くの巻きは弦が短い)


def test_fail_closed_and_mjcf():
    p4, h4 = S.polygon_peg(4, A)["vertices"], _hole(4)
    bad = [
        lambda: S.polygon_peg(2), lambda: S.polygon_peg(4, 0.0), lambda: S.polygon_peg(4, A, cut=5e-3), lambda: S.polygon_peg(4, A, yaw=float("inf")),
        lambda: S.polygon_offset([[0, 0], [1, 0], [0.2, 0.2], [0, 1]], 0.1), lambda: S.polygon_offset(p4, float("nan")),
        lambda: S.polygon_fit_check([[0, 0, 0]], h4), lambda: S.polygon_fit_check(p4, [[0, 0], [1, 0]]),
        lambda: S.rotation_window(4, -A, DELTA), lambda: S.rotation_window(4, A, DELTA, hole_vertices=h4), lambda: S.rotation_window(4, A, DELTA, mu=float("nan")),
        lambda: S.rotation_window(4, A + 1e-3, DELTA, 0.0, S.polygon_peg(4, A + 1e-3)["vertices"], h4),
        lambda: S.polygon_two_point_depth(p4, h4, math.radians(40)), lambda: S.polygon_two_point_depth(p4, h4, math.radians(3), depth_max=1e-3),
        lambda: S.polygon_coverage_image([[0, 0], [1, 0], [0, 1]], 100, 0), lambda: S.plane_topview(np.zeros((10, 10)), np.eye(3), np.eye(3), [0, 0, 1], extent=-1),
        lambda: S.plane_topview(np.zeros((10, 10)), np.eye(3), np.eye(3), [0, 0, 1], extent=1.0, res=1e-5),
        lambda: S.polygon_yaw_read(np.zeros((40, 40))), lambda: S.polygon_yaw_read(np.eye(40), n=-1),
        lambda: S.relative_yaw_from_images(np.eye(40), np.eye(40), 0), lambda: S.symmetry_fold(0.1, -1),
        lambda: S.rotation_search_plan(-1, 0.1), lambda: S.search_expected_tries(4, 0.1, estimate_sigma=0.0),
        lambda: S.spiral_search_points(1e-3, 1e-3, -1.0), lambda: S.spiral_expected_tries(np.zeros((5, 2)), 0.0, 1e-3),
        lambda: S.pegsym_scene_mjcf(p4, h4, hole_depth=0.0), lambda: S.pegsym_scene_mjcf(p4, h4, k_yaw=0.0),
    ]
    assert len(bad) >= 25
    assert all(_raises(f) for f in bad)
    root = ET.fromstring(S.pegsym_scene_mjcf(S.polygon_peg(3, A)["vertices"], _hole(3), chamfer=W))
    names = {g.get("name") for g in root.iter("geom")}
    assert all("wall%d" % i in names and "chamf%d" % i in names and "collar%d" % i in names for i in range(3))
    assert {c.get("name") for c in root.iter("camera")} == {"wrist", "up", "side"}
    assert len(root.find("asset/mesh").get("vertex").split()) == 3 * 6


def test_mujoco_square_search_matches_prediction():
    pytest.importorskip("mujoco")
    p = S.polygon_peg(4, A)
    hy = 0.9
    rw = S.rotation_window(4, A, DELTA, W, mu=0.3)
    cap = rw["phi_eff"]
    sc = S.pegsym_scene_build(p["vertices"], _hole(4, 0.0, hy), chamfer=W, mu=0.3)
    plan = S.rotation_search_plan(4, cap)
    r = S.pegsym_search_run(sc, 4, cap, hy)
    P = plan["period"]
    d = np.abs((r["e_true"] - plan["angles"] + P / 2) % P - P / 2)
    assert r["tries"] == int(np.argmax(d <= cap)) + 1
    assert S.pegsym_insert_try(sc, yaw=hy + cap - math.radians(0.75))["success"]
    assert not S.pegsym_insert_try(sc, yaw=hy + cap + math.radians(0.75))["success"]
