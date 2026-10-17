# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for radiosity3d (3-D form factors, progressive radiosity, the inspection render with interreflection): truth through independent code.

真値の経路(テストする op とは別のコード):
  * 形態係数: Howell のカタログの表の値 0.199825(C-11、X = Y = 1)と 0.200044(C-14、H = W = 1)を
    数で書き写した定数。閉形式の op はこの 6 桁に丸めて一致、数値の op は閉形式と一致。
    離れた多角形は、核 cosθi cosθj / (π r²) の Gauss–Legendre 二重積分(本テストで書いた、
    点 → 多角形の輪郭和を使わない式)とも照合する。閉じた立方体の行和 = 1、相反則。
  * 漸進ラジオシティ: ``numpy.linalg.solve`` の逆行列の解。押し出した V 溝の中央の断面は
    ``lighttransport.transport_matrix_radiosity``(2-D、crossed-strings の厳密解)へ長さとともに収束。
  * 描画: 反射 0 回は ``optscene.render_optscene``(別の op、同じ照明)。画素の相互反射は、
    本テストでパッチの上を点で数えた核の和(final gather の閉形式を使わない)と照合。

壊して確かめたこと(2026-10-15、各 1 回、括弧は落ちた門の数): shooting の式 8 の A_i/A_j を落とす(2)/
撃った後に ΔB_i を 0 に戻さない(5)/ 点 → 多角形の 1/(2π) を 1/π に(15)/ 画素の照度に ρ/π を掛け忘れる(2)/
反射 n 回の Neumann 和を 1 回ずらす(2)。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import illumdesign as ID
import lighttransport as lt
import optscene as OS
import radiosity3d as R

HOWELL_C11 = 0.199825      # Howell, C-11 の表: X = Y = 1
HOWELL_C14 = 0.200044      # Howell, C-14 の表: H = W = 1


def _sq(z, flip=False):
    q = np.array([[0, 0, z], [1, 0, z], [1, 1, z], [0, 1, z]], float)
    return q[::-1] if flip else q


def _cube(n):
    """内向きの単位立方体を n×n に割った 6n² 枚(閉じた囲い)。"""
    ps = []
    e = np.linspace(0, 1, n + 1)
    for ax in range(3):
        u, v = [a for a in range(3) if a != ax]
        for val, sgn in ((0.0, 1.0), (1.0, -1.0)):
            for i in range(n):
                for j in range(n):
                    q = []
                    for (a, b) in ((e[i], e[j]), (e[i + 1], e[j]), (e[i + 1], e[j + 1]), (e[i], e[j + 1])):
                        p = [0.0, 0.0, 0.0]
                        p[ax], p[u], p[v] = val, a, b
                        q.append(p)
                    q = np.array(q)
                    nrm = np.cross(q[1] - q[0], q[2] - q[1])
                    ps.append(q if nrm[ax] * sgn > 0 else q[::-1])
    return np.array(ps)


def _kernel_ff(pi_, pj_, n=24):
    """独立の経路: 両方の面の上の Gauss 点で核 cosθi cosθj/(π r²) を二重に積む(離れた面だけ)。"""
    x, w = np.polynomial.legendre.leggauss(n)
    s, ws = 0.5 * (x + 1), 0.5 * w

    def pts(q):
        out, wt = [], []
        for a, wa in zip(s, ws):
            for b, wb in zip(s, ws):
                p = (1 - a) * (1 - b) * q[0] + a * (1 - b) * q[1] + a * b * q[2] + (1 - a) * b * q[3]
                ds = (1 - b) * (q[1] - q[0]) + b * (q[2] - q[3])
                dt = (1 - a) * (q[3] - q[0]) + a * (q[2] - q[1])
                out.append(p)
                wt.append(wa * wb * np.linalg.norm(np.cross(ds, dt)))
        return np.array(out), np.array(wt)

    xi, wi = pts(pi_)
    xj, wj = pts(pj_)
    ni = np.cross(pi_[1] - pi_[0], pi_[2] - pi_[1])
    ni /= np.linalg.norm(ni)
    nj = np.cross(pj_[1] - pj_[0], pj_[2] - pj_[1])
    nj /= np.linalg.norm(nj)
    d = xj[None] - xi[:, None]
    r2 = (d * d).sum(-1)
    ci = np.abs((d * ni).sum(-1)) / np.sqrt(r2)
    cj = np.abs((d * nj).sum(-1)) / np.sqrt(r2)
    return float((wi[:, None] * wj[None] * ci * cj / (math.pi * r2)).sum() / wi.sum())


# --------------------------------------------------------------------------- #
# 形態係数
# --------------------------------------------------------------------------- #
def test_closed_forms_reproduce_howells_table():
    assert round(R.form_factor_parallel_rects(1.0, 1.0, 1.0), 6) == HOWELL_C11
    assert round(R.form_factor_perpendicular_rects(1.0, 1.0, 1.0), 6) == HOWELL_C14
    # 尺度に依らない(X, Y / H, W だけで決まる)
    assert R.form_factor_parallel_rects(3.0, 3.0, 3.0) == pytest.approx(R.form_factor_parallel_rects(), rel=1e-14)
    # C-14 の相反則 w F12 = h F21
    h, w, L = 2.0, 0.5, 1.5
    assert w * R.form_factor_perpendicular_rects(h, w, L) == pytest.approx(
        h * R.form_factor_perpendicular_rects(w, h, L), rel=1e-12)
    # 遠ざかると 0、近づくと 1(平行): 単調
    vals = [R.form_factor_parallel_rects(1, 1, c) for c in (0.05, 0.3, 1.0, 3.0, 10.0)]
    assert all(a > b for a, b in zip(vals, vals[1:])) and vals[0] > 0.9 and vals[-1] < 0.004


@pytest.mark.parametrize("abc", [(1.0, 1.0, 1.0), (2.0, 3.0, 1.5), (0.4, 1.0, 2.0)])
def test_numeric_parallel_matches_c11(abc):
    a, b, c = abc
    A = np.array([[0, 0, 0], [a, 0, 0], [a, b, 0], [0, b, 0]], float)
    B = A + [0, 0, c]
    ref = R.form_factor_parallel_rects(a, b, c)
    assert R.form_factor_polygons(A, B, n_quad=12) == pytest.approx(ref, rel=2e-6)
    assert R.form_factor_polygons(B, A, n_quad=12) == pytest.approx(ref, rel=2e-6)
    # 別の式(核の二重積分)とも
    assert _kernel_ff(A, B) == pytest.approx(ref, rel=1e-4)


@pytest.mark.parametrize("hwl", [(1.0, 1.0, 1.0), (2.0, 0.5, 1.5), (0.3, 1.2, 0.8)])
def test_numeric_perpendicular_matches_c14(hwl):
    h, w, L = hwl
    A1 = np.array([[0, 0, 0], [w, 0, 0], [w, L, 0], [0, L, 0]], float)          # w の側(z = 0)
    A2 = np.array([[0, 0, 0], [0, L, 0], [0, L, h], [0, 0, h]], float)          # h の側(x = 0)、辺を共有
    ref = R.form_factor_perpendicular_rects(h, w, L)
    # 共有辺で被積分関数が対数的に特異なので、点数を上げると収束する(単調ではないので上限で見る)
    errs = [abs(R.form_factor_polygons(A1, A2, n_quad=n) - ref) for n in (2, 8, 32)]
    assert errs[0] > errs[2] and errs[2] < 2e-6 * max(ref, 1e-3) / 1e-3


def test_unit_squares_hit_the_table_value_to_its_digits():
    assert R.form_factor_polygons(_sq(0.0), _sq(1.0), n_quad=16) == pytest.approx(HOWELL_C11, abs=6e-7)
    A1 = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    A2 = np.array([[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]], float)
    assert R.form_factor_polygons(A1, A2, n_quad=16) == pytest.approx(HOWELL_C14, abs=6e-7)


def test_reciprocity_and_triangles():
    tri = np.array([[0.2, 0.1, 0.0], [1.4, 0.3, 0.0], [0.6, 1.2, 0.0]])
    quad = np.array([[0.0, 0.0, 0.9], [1.5, 0.0, 1.3], [1.5, 1.0, 1.3], [0.0, 1.0, 0.9]])
    Ft = R.form_factor_polygons(tri, quad, n_quad=16)
    Fq = R.form_factor_polygons(quad, tri, n_quad=16)
    At = 0.5 * np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0]))
    Aq = 1.0 * math.hypot(1.5, 0.4)
    assert At * Ft == pytest.approx(Aq * Fq, rel=1e-6)
    # 三角形は退化した四角形として積む: 核の二重積分(別の式)と
    tri4 = np.vstack([tri, tri[2:3]])
    assert Ft == pytest.approx(_kernel_ff(tri4, quad, n=32), rel=2e-3)


def test_closed_cube_rows_sum_to_one_and_reciprocity():
    P = R.radiosity_patches(polygons=_cube(3), albedo=0.6)
    Fr = R.form_factor_matrix(P, n_quad=3, symmetric=False)
    A = P["areas"]
    assert np.abs(Fr.sum(1) - 1.0).max() < 1e-12              # 輪郭和は閉じた囲いで厳密に 1
    assert np.abs(A[:, None] * Fr - (A[:, None] * Fr).T).max() < 2e-6
    F = R.form_factor_matrix(P, n_quad=3)
    assert np.abs(A[:, None] * F - (A[:, None] * F).T).max() < 1e-15
    assert np.abs(F.sum(1) - 1.0).max() < 3e-5                # 対称化で相反則を入れた代わりに行和が少し動く(実測 1.6e-5)
    assert (np.diag(F) == 0).all() and (F >= 0).all()


def test_occluder_blocks_the_view():
    plate = OS.scene_box((0.5, 0.5, 0.5), (2.0, 2.0, 0.05))               # 2 枚の間に板
    free = R.form_factor_polygons(_sq(0.0), _sq(1.0, flip=True), n_quad=4)
    blocked = R.form_factor_polygons(_sq(0.0), _sq(1.0, flip=True), n_quad=4, occluders=[plate])
    assert free > 0.19 and blocked == 0.0


# --------------------------------------------------------------------------- #
# 漸進ラジオシティ
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def cube_problem():
    P = R.radiosity_patches(polygons=_cube(3), albedo=0.7)
    F = R.form_factor_matrix(P, n_quad=3)
    E = np.zeros(len(P["areas"]))
    E[:9] = 1.0                                                            # 1 面だけ光る
    return P, F, E


def test_progressive_matches_matrix_inverse(cube_problem):
    P, F, E = cube_problem
    A = P["areas"]
    sol = R.radiosity_progressive_3d(P, E, form_factors=F, tol=1e-13)
    M = np.eye(len(A)) - 0.7 * (F.T * A[None, :]) / A[:, None]             # B = E + ρ F̃ B、F̃_ij = F_ji A_j/A_i
    Bx = np.linalg.solve(M, E)
    assert sol["converged"]
    assert np.abs(sol["radiosity"][:, 0] - Bx).max() < 1e-11 * Bx.max()
    h = sol["unshot_history"]
    assert h[0] == pytest.approx((E * A).sum()) and (np.diff(h) <= 1e-15 * h[0]).all()   # 残エネルギーは減るだけ
    assert sol["residual_energy"] <= 1e-13


def test_stop_rule_and_shot_cap(cube_problem):
    P, F, E = cube_problem
    loose = R.radiosity_progressive_3d(P, E, form_factors=F, tol=1e-3)
    tight = R.radiosity_progressive_3d(P, E, form_factors=F, tol=1e-9)
    assert loose["converged"] and tight["converged"] and loose["n_shots"] < tight["n_shots"]
    capped = R.radiosity_progressive_3d(P, E, form_factors=F, tol=1e-9, max_shots=5)
    assert not capped["converged"] and capped["n_shots"] == 5
    assert "our choice" in tight["stop_rule"]


def test_first_shot_is_the_largest_unshot_energy_and_ties_go_by_index(cube_problem):
    P, F, _ = cube_problem
    E = np.zeros(len(P["areas"]))
    E[[4, 13]] = 1.0                                                       # 同じエネルギーの 2 枚(面積も同じ)
    one = R.radiosity_progressive_3d(P, E, form_factors=F, max_shots=1)
    B = one["radiosity"][:, 0]
    # 撃ったのは 4 番: 13 番は 4 番から受け取った分だけ増え、4 番は変わらない
    assert B[4] == pytest.approx(1.0) and B[13] == pytest.approx(1.0 + 0.7 * F[4, 13])
    E[13] = 1.0 + 1e-6
    one = R.radiosity_progressive_3d(P, E, form_factors=F, max_shots=1)
    assert one["radiosity"][4, 0] > 1.0                                    # 大きい方(13 番)が先に撃つ


def test_extruded_groove_converges_to_the_2d_solution():
    prof = lt.groove_profile("vgroove", n_patches=8, width=1.0)
    rho = 0.8
    B2 = lt.transport_matrix_radiosity(prof, albedo=rho)["transport"] @ np.clip(prof["normals"][:, 1], 0, None)
    v = prof["vertices"]
    errs = []
    for Lw, ny in ((1, 8), (4, 24), (16, 64)):
        ys = np.linspace(-Lw / 2, Lw / 2, ny + 1)
        polys, E = [], []
        for j in range(ny):
            for i in range(len(v) - 1):
                a, b = v[i], v[i + 1]
                q = np.array([[a[0], ys[j], a[1]], [b[0], ys[j], b[1]], [b[0], ys[j + 1], b[1]], [a[0], ys[j + 1], a[1]]])
                if np.cross(q[1] - q[0], q[2] - q[1])[2] < 0:
                    q = q[::-1]
                polys.append(q)
                E.append(rho * max(prof["normals"][i, 1], 0.0))
        P = R.radiosity_patches(polygons=np.array(polys), albedo=rho)
        sol = R.radiosity_progressive_3d(P, np.array(E), tol=1e-11)
        B3 = sol["radiosity"][:, 0].reshape(ny, -1)
        errs.append(float(np.abs(0.5 * (B3[ny // 2] + B3[ny // 2 - 1]) - B2).max() / B2.max()))
    assert errs[0] > errs[1] > errs[2] and errs[2] < 1e-4, errs       # 実測 4.7e-2 / 2.9e-3 / 4.8e-5


# --------------------------------------------------------------------------- #
# 検査用の多重反射描画
# --------------------------------------------------------------------------- #
def _pocket_scene(rho=0.7):
    m = OS.scene_material("lambert", albedo=rho)
    part = OS.scene_difference(OS.scene_box((0, 0, 5), (10, 8, 5), m), OS.scene_box((0, 0, 8), (6, 4, 5)))
    return [part, OS.scene_plane(0.0, OS.scene_material("lambert", albedo=0.0))]


@pytest.fixture(scope="module")
def setup():
    cam = OS.optical_camera(focal_mm=12.0, pixel_um=55.2, resolution=(40, 40), working_distance_mm=150.0,
                            image_distance_mm=12.0 * 150.0 / 138.0)
    light = ID.light_source(kind="dome", radius_mm=50.0, n=24)
    return _pocket_scene(), cam, light


def test_zero_bounces_is_render_optscene(setup):
    sc, cam, light = setup
    r0 = R.render_optscene_gi(sc, cam, light, bounces=0, patch_mm=2.5, study_bounces=0)
    ref = OS.render_optscene(sc, cam, [light])
    assert np.abs(r0["image"] - ref).max() <= 1e-12 * ref.max()
    assert np.abs(r0["direct"] - ref).max() <= 1e-12 * ref.max()
    assert np.abs(r0["difference"]).max() == 0.0


def test_bounces_increase_to_the_converged_image(setup):
    sc, cam, light = setup
    imgs = [R.render_optscene_gi(sc, cam, light, bounces=k, patch_mm=2.5, study_bounces=0)["image"]
            for k in (0, 1, 2, 4, 60)]
    conv = R.render_optscene_gi(sc, cam, light, bounces=None, patch_mm=2.5, tol=1e-12, study_bounces=0)
    for a, b in zip(imgs, imgs[1:]):
        assert (b >= a - 1e-15).all()
    assert np.abs(imgs[-1] - conv["image"]).max() < 1e-8 * conv["image"].max()
    assert conv["converged"] and conv["difference"].max() > 0.2 * conv["image"].max()
    # 直接光は反射の回数に依らない
    assert np.array_equal(conv["direct"], R.render_optscene_gi(sc, cam, light, bounces=1, patch_mm=2.5,
                                                               study_bounces=0)["direct"])


def test_gather_matches_point_sampled_kernel(setup):
    """1 回反射の画素の照度 = Σ_j B_j ∫ cos cos/(π r²) dA_j を、パッチの上の点で本テストが数えた値と照合。"""
    sc, cam, light = setup
    r1 = R.render_optscene_gi(sc, cam, light, bounces=1, patch_mm=2.5, study_bounces=0)
    g = next(v for v in R._GEOM_CACHE.values() if v["patches"]["patch_mm"] == 2.5 and v["hit"]["index"].size == 1600)
    pt, hit = g["patches"], g["hit"]
    B = r1["patch_radiosity"][:, 1]
    floor = np.flatnonzero((hit["index"] == 0) & (np.abs(hit["point"][:, 2] - 3.0) < 1e-6))
    pix = floor[np.argmin(np.hypot(*hit["point"][floor, :2].T))]               # 床の中央(壁際は核の求積が足りない)
    x, nx = hit["point"][pix], hit["normal"][pix]
    q, w = R._quad_points(pt["polygons"], 12)
    d = q - x
    r2 = (d * d).sum(-1)
    ci = np.clip((d * nx).sum(-1) / np.sqrt(r2), 0, None)
    cj = np.clip(-(d * pt["normals"][:, None, :]).sum(-1) / np.sqrt(r2), 0, None)
    H = float(((w * ci * cj / (math.pi * r2)).sum(-1) * B).sum())         # 床の点からは全パッチが見える(凸な空洞)
    ind = r1["difference"].reshape(-1, 3)[pix, 1]
    assert ind == pytest.approx(0.7 / math.pi * H, rel=2e-3)


def test_intensity_is_linear_and_albedo_is_read_each_call(setup):
    sc, cam, light = setup
    a = R.render_optscene_gi(sc, cam, light, patch_mm=2.5, study_bounces=0)
    b = R.render_optscene_gi(sc, cam, ID.light_source(kind="dome", radius_mm=50.0, n=24, intensity=2.5),
                             patch_mm=2.5, study_bounces=0)
    assert np.abs(b["image"] - 2.5 * a["image"]).max() < 1e-12 * b["image"].max()
    dark = R.render_optscene_gi(_pocket_scene(0.3), cam, light, patch_mm=2.5, study_bounces=0)
    assert dark["indirect_share"].max() < a["indirect_share"].max()
    zero = R.render_optscene_gi(_pocket_scene(1e-9), cam, light, patch_mm=2.5, study_bounces=0)
    assert np.abs(zero["difference"]).max() < 1e-15


def test_bounce_study_estimate_is_conservative(setup):
    sc, cam, light = setup
    r = R.render_optscene_gi(sc, cam, light, patch_mm=2.5, study_bounces=10, study_tol=0.02)
    rows = r["bounce_study"]
    assert [x["bounces"] for x in rows] == list(range(11))
    asym = [x for x in rows if x["asymptotic"]]
    assert len(asym) >= 4
    for x in rows[3:]:
        assert 0.0 < x["observed_ratio"] < 1.0
    for x in asym:
        assert x["gci"] >= x["error_vs_converged"]                     # 漸近域の見積もりは楽観しない
        assert x["gci"] <= 3.0 * x["error_vs_converged"]                # 過大すぎもしない
    k = r["bounces_needed"]
    assert k is not None and rows[k]["asymptotic"] and rows[k]["gci"] <= 0.02 and rows[k]["error_vs_converged"] <= 0.02
    assert all(not (x["asymptotic"] and x["gci"] <= 0.02) for x in rows[:k])
    assert rows[0]["increment"] is None and rows[1]["observed_ratio"] is None   # 定義できない量は NaN でなく None


def test_supersample_box_averages(setup):
    sc, cam, light = setup
    r2 = R.render_optscene_gi(sc, cam, light, bounces=0, patch_mm=2.5, supersample=2, study_bounces=0)
    ref = OS.render_optscene(sc, cam, [light], supersample=2)
    assert np.abs(r2["image"] - ref).max() <= 1e-12 * ref.max()


# --------------------------------------------------------------------------- #
# 拒否(fail-closed)
# --------------------------------------------------------------------------- #
def test_refusals(setup):
    sc, cam, light = setup
    with pytest.raises(ValueError, match="only Lambertian"):
        R.radiosity_patches(scene=[OS.scene_box((0, 0, 1), (1, 1, 1), OS.scene_material("conductor"))])
    with pytest.raises(ValueError, match="support boxes"):
        R.radiosity_patches(scene=[OS.scene_sphere((0, 0, 1), 1.0)])
    with pytest.raises(ValueError, match="infinite plane"):
        R.radiosity_patches(scene=[OS.scene_plane(0.0)])
    with pytest.raises(ValueError, match="box minus a box"):
        R.radiosity_patches(scene=[OS.scene_difference(OS.scene_box((0, 0, 1), (1, 1, 1)),
                                                       OS.scene_sphere((0, 0, 2), 0.5))])
    with pytest.raises(ValueError, match="exactly one"):
        R.radiosity_patches()
    with pytest.raises(ValueError, match="non-planar"):
        R.radiosity_patches(polygons=[[[0, 0, 0], [1, 0, 0], [1, 1, 0.3], [0, 1, 0]]])
    with pytest.raises(ValueError, match="non-convex"):
        R.radiosity_patches(polygons=[[[0, 0, 0], [1, 0, 0], [0.2, 0.2, 0], [0, 1, 0]]])
    with pytest.raises(ValueError, match="degenerate"):
        R.form_factor_polygons([[0, 0, 0], [1, 0, 0], [2, 0, 0]], _sq(1.0))
    with pytest.raises(ValueError, match="albedo"):
        R.radiosity_patches(polygons=_cube(1), albedo=1.2)
    with pytest.raises(ValueError, match="radiosity_patches table"):
        R.form_factor_matrix({"kind": "lt_profile"})
    with pytest.raises(ValueError, match="tol"):
        R.radiosity_progressive_3d(R.radiosity_patches(polygons=_cube(1)), np.ones(6), tol=0.0)
    with pytest.raises(ValueError, match=">= 0"):
        R.radiosity_progressive_3d(R.radiosity_patches(polygons=_cube(1)), -np.ones(6))
    with pytest.raises(ValueError, match="bounces"):
        R.render_optscene_gi(sc, cam, light, bounces=-1)
    with pytest.raises(ValueError, match="lights"):
        R.render_optscene_gi(sc, cam, [])
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            R.form_factor_parallel_rects(1.0, bad, 1.0)
        with pytest.raises(ValueError):
            R.form_factor_perpendicular_rects(bad, 1.0, 1.0)
