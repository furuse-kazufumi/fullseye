# -*- coding: utf-8 -*-
"""convex_hull_gap(hull3d、2026-11-15)の真値の門。

「走った」ではなく「正しい数が出た」を門にする。真値は全部、op の外から決まる:

1. 軸平行の箱 2 つを x に d だけ離す → 隙間 = d(上限と下限の幅 ≤ tol)。線形計画の t も d。
2. 角どうしの斜めの配置 → √(dx² + dy² + dz²)。線形計画の t は ℓ1 = dx + dy + dz(‖w‖∞ ≤ 1)。
3. 接触(d = 0)と食い込み → 離れていない、隙間 0、t = 0。
4. 反例の対照: 細い棒 2 本の十字。凸包は交わるのに頂点の間は 1.4 離れている。頂点どうしの距離と
   hausdorff_distance(既存の op)は「離れている」と出す配置を、この op は重なりと判定する。
5. 剛体変換で値が変わらない。
6. 独立した実装との一致: 2 点ずつの凸包 = 線分どうしの距離(match3d.distance_segment_segment、閉形式)、
   乱数の凸多面体 = 重みの単体の上の QP を scipy の SLSQP で解いた値。
7. 直す前で落ちること: 同じ門を、頂点どうしの最短距離(製作の代わり)と Frank–Wolfe を 200 歩で止めた
   上限にかけると落ちる。囲いのアフィン最小点を壊した写しは、保証に届かず RuntimeError になる。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import hull3d
from hull3d import convex_hull_gap


def _box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    g = np.array(np.meshgrid([0, 1], [0, 1], [0, 1])).reshape(3, -1).T
    return lo + g * (hi - lo)


def _rot(rng):
    q = rng.standard_normal(4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


@pytest.mark.parametrize("d", [0.25, 0.01, 1e-4, 3.0])
def test_axis_aligned_boxes_gap_equals_the_offset(d):
    a = _box([0, 0, 0], [1, 1, 1])
    b = _box([1 + d, 0.2, -0.3], [2.5 + d, 0.9, 0.4])           # 面どうしが向き合う(y・z は重なる)
    r = convex_hull_gap(a, b)
    assert r["separated"]
    assert abs(r["gap"] - d) < 1e-12
    assert 0.0 <= r["gap_upper"] - r["gap_lower"] <= 1e-9
    assert r["gap_lower"] <= d + 1e-12 <= r["gap_upper"] + 2e-12
    assert np.allclose(r["separating_normal"], [1.0, 0.0, 0.0], atol=1e-9)
    assert abs(r["witness_b"][0] - r["witness_a"][0] - d) < 1e-12
    assert abs(r["lp_t"] - d) < 1e-6                             # w = (1, 0, 0) で t = d


def test_corner_to_corner_gap_is_the_euclidean_offset():
    dx, dy, dz = 0.3, 0.4, 0.5
    a = _box([0, 0, 0], [1, 1, 1])
    b = _box([1 + dx, 1 + dy, 1 + dz], [2 + dx, 2.5 + dy, 1.7 + dz])
    r = convex_hull_gap(a, b)
    assert abs(r["gap"] - math.sqrt(dx * dx + dy * dy + dz * dz)) < 1e-12
    assert np.allclose(r["witness_a"], [1, 1, 1]) and np.allclose(r["witness_b"], [1 + dx, 1 + dy, 1 + dz])
    assert abs(r["lp_t"] - (dx + dy + dz)) < 1e-6                # ‖w‖∞ ≤ 1 の最大は ℓ1
    assert r["lp_t"] / math.sqrt(3) <= r["gap"] <= r["lp_t"]


@pytest.mark.parametrize("d", [0.0, -0.1, -0.6])
def test_touching_and_overlapping_boxes_are_not_separated(d):
    a = _box([0, 0, 0], [1, 1, 1])
    b = _box([1 + d, 0.2, 0.1], [2 + d, 1.2, 1.1])
    r = convex_hull_gap(a, b)
    assert r["separated"] is False and r["gap"] == 0.0
    assert r["separating_normal"] is None
    assert r["gap_upper"] <= 1e-9
    assert np.allclose(r["witness_a"], r["witness_b"], atol=1e-9)   # 共通の点
    assert r["lp_t"] < 1e-6


def test_crossed_rods_overlap_although_their_vertices_are_far_apart():
    """反例の対照: 頂点の間の距離も hausdorff_distance も「離れている」と言う配置。"""
    import metrics3d
    rod_a = _box([-1, -0.01, -0.01], [1, 0.01, 0.01])
    rod_b = _box([-0.01, -1, -0.01], [0.01, 1, 0.01])
    vmin = float(np.min(np.linalg.norm(rod_a[:, None] - rod_b[None], axis=2)))
    assert vmin > 1.4                                            # 頂点どうしの最短距離
    assert metrics3d.hausdorff_distance(rod_a, rod_b) > 1.4
    r = convex_hull_gap(rod_a, rod_b)
    assert r["separated"] is False and r["gap"] == 0.0
    # 棒を z に 0.03 ずらせば、凸包は 0.01 だけ離れる(厚み 0.02)
    r2 = convex_hull_gap(rod_a, rod_b + [0.0, 0.0, 0.03])
    assert r2["separated"] and abs(r2["gap"] - 0.01) < 1e-12


def test_rigid_transform_does_not_change_the_gap():
    rng = np.random.default_rng(3)
    a = rng.standard_normal((40, 3))
    b = rng.standard_normal((25, 3)) + [7.0, 1.0, -0.5]
    g0 = convex_hull_gap(a, b)["gap"]
    assert g0 > 0.5
    for _ in range(5):
        R, t = _rot(rng), rng.standard_normal(3) * 50.0
        r = convex_hull_gap(a @ R.T + t, b @ R.T + t)
        assert abs(r["gap"] - g0) < 1e-9
    big = convex_hull_gap(a + 1e5, b + 1e5)                      # 遠い原点でも平均を引いて解く
    assert abs(big["gap"] - g0) < 1e-8


def test_two_point_hulls_agree_with_distance_segment_segment():
    """独立した閉形式(線分どうしの最短距離)と、乱数の 400 組で一致する。"""
    import match3d
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(400):
        p0, p1, q0, q1 = rng.standard_normal((4, 3))
        ref = match3d.distance_segment_segment(p0, p1, q0, q1)[0]
        r = convex_hull_gap(np.array([p0, p1]), np.array([q0, q1]))
        got = r["gap"] if r["separated"] else 0.0
        worst = max(worst, abs(got - ref))
    assert worst < 1e-9, worst


def test_random_polytopes_agree_with_an_independent_qp():
    """重みの単体の上の QP(scipy の SLSQP、別の算法)と 1e-6 で一致する。"""
    from scipy.optimize import minimize
    rng = np.random.default_rng(7)
    for _ in range(12):
        A = rng.standard_normal((int(rng.integers(2, 9)), 3))
        B = rng.standard_normal((int(rng.integers(2, 9)), 3)) + rng.standard_normal(3) * 2.5
        na, nb = len(A), len(B)

        def f(z, A=A, B=B, na=na):
            return float(np.sum((z[:na] @ A - z[na:] @ B) ** 2))
        cons = [{"type": "eq", "fun": lambda z, na=na: z[:na].sum() - 1.0},
                {"type": "eq", "fun": lambda z, na=na: z[na:].sum() - 1.0}]
        best = math.inf
        for _k in range(3):
            z0 = np.r_[rng.dirichlet(np.ones(na)), rng.dirichlet(np.ones(nb))]
            res = minimize(f, z0, bounds=[(0, 1)] * (na + nb), constraints=cons, method="SLSQP",
                           options={"ftol": 1e-16, "maxiter": 2000})
            best = min(best, math.sqrt(max(res.fun, 0.0)))
        r = convex_hull_gap(A, B)
        assert abs(r["gap"] - best) < 1e-6, (r["gap"], best)


def test_planar_polygons_in_two_dimensions():
    sq = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    r = convex_hull_gap(sq, sq + [2.0, 3.0])
    assert abs(r["gap"] - math.hypot(1.0, 2.0)) < 1e-12
    assert r["lp_t"] / math.sqrt(2) - 1e-6 <= r["gap"] <= r["lp_t"] + 1e-6
    tri = np.array([[0.5, 0.5], [3.0, 0.5], [0.5, 3.0]])
    assert convex_hull_gap(sq, tri)["separated"] is False


def test_gap_below_tol_counts_as_contact():
    a = _box([0, 0, 0], [1, 1, 1])
    b = a + [1.0 + 1e-10, 0.0, 0.0]
    assert convex_hull_gap(a, b)["separated"] is False                       # 既定 tol 1e-9
    r = convex_hull_gap(a, b, tol=1e-12, check="none")
    assert r["separated"] and abs(r["gap"] - 1e-10) < 1e-13 and r["lp_t"] is None


def test_refusals():
    a = _box([0, 0, 0], [1, 1, 1])
    with pytest.raises(ValueError, match="empty"):
        convex_hull_gap(np.zeros((0, 3)), a)
    with pytest.raises(ValueError, match="empty"):
        convex_hull_gap(a, [])
    with pytest.raises(ValueError, match="dimension"):
        convex_hull_gap(a, a[:, :2])
    with pytest.raises(ValueError, match="NaN"):
        convex_hull_gap(np.r_[a, [[np.nan, 0, 0]]], a)
    with pytest.raises(ValueError, match="tol"):
        convex_hull_gap(a, a + 3, tol=0.0)
    with pytest.raises(ValueError, match="max_iter"):
        convex_hull_gap(a, a + 3, max_iter=0)
    with pytest.raises(ValueError, match="check"):
        convex_hull_gap(a, a + 3, check="maybe")


def _gate(fn):
    """真値の門(関数にして、壊した写しにも同じ門をかける): 面の向き合う箱は d、十字の棒は重なり。"""
    a = _box([0, 0, 0], [1, 1, 1])
    for d in (0.25, 0.01):
        b = _box([1 + d, 0.2, -0.3], [2.5 + d, 0.9, 0.4])
        if not abs(fn(a, b) - d) < 1e-12:
            return False
    rod_a = _box([-1, -0.01, -0.01], [1, 0.01, 0.01])
    rod_b = _box([-0.01, -1, -0.01], [0.01, 1, 0.01])
    return fn(rod_a, rod_b) == 0.0


def _vertex_min(a, b):
    """製作で使っていた代わり: 頂点どうしの最短距離。"""
    return float(np.min(np.linalg.norm(a[:, None] - b[None], axis=2)))


def _frank_wolfe(a, b, iters=200):
    """製作の上限の作り方(Frank–Wolfe、O(1/k))を 200 歩で止めた写し。"""
    x, y = a.mean(0), b.mean(0)
    for _ in range(iters):
        r = x - y
        sa, sb = a[int(np.argmin(a @ r))], b[int(np.argmax(b @ r))]
        dz = (sa - x) - (sb - y)
        dd = float(dz @ dz)
        if dd < 1e-18:
            break
        g = min(1.0, max(0.0, -float(r @ dz) / dd))
        x, y = x + g * (sa - x), y + g * (sb - y)
    return float(np.linalg.norm(x - y))


def test_the_gate_fails_on_a_broken_copy(monkeypatch):
    """直す前(op が無い・壊した写し)で真値の門が落ちることを、同じ門で確かめる。

    (1) この op は門を通る。
    (2) 頂点どうしの最短距離(製作で使っていた代わり)は、箱の d に合わず、十字の棒を「離れている」と言う。
    (3) Frank–Wolfe を 200 歩で止めた上限(製作の hull_gap_bounds の作り方)は O(1/k) で、1e-12 に届かない。
    (4) 囲いのアフィン最小点を「最後に足した 1 点」に壊すと、止める条件(上限 − 下限 ≤ tol)に届かず
        RuntimeError —— 保証の無い近似値を黙って返さない。
    """
    assert _gate(lambda a, b: convex_hull_gap(a, b)["gap"])
    assert not _gate(_vertex_min)
    assert not _gate(_frank_wolfe)
    monkeypatch.setattr(hull3d, "_affine_minimizer", lambda S: np.eye(len(S))[-1])
    a = _box([0, 0, 0], [1, 1, 1])
    with pytest.raises(RuntimeError, match="no certified answer"):
        convex_hull_gap(a, _box([1.25, 0.2, -0.3], [2.75, 0.9, 0.4]), check="none")


def test_docstring_call_example_runs():
    doc = hull3d.convex_hull_gap.__doc__
    code = doc.split("呼び出し例::")[1]
    import textwrap
    exec(compile(textwrap.dedent(code), "<convex_hull_gap example>", "exec"), {})


def test_registered_in_the_3d_ledger_and_composes_with_an_outlier_filter():
    """台帳(ops3d の bounds)から引け、孤立点の除去(既存の radius_outlier_removal)の後ろに繋がる。"""
    import ops3d
    import pcl_filter
    assert ("convex_hull_gap", "hull3d", ["points", "points"], "table", False) in ops3d._CATALOG["bounds"]
    assert ops3d.get("convex_hull_gap") is not None
    rng = np.random.default_rng(5)
    part_a = np.r_[np.c_[np.ones(400), rng.random((400, 2))], rng.random((1600, 3))]   # A の x = 1 の面 + 中身
    fly_yz = np.array([[0.2, 0.2], [0.2, 0.8], [0.5, 0.5], [0.8, 0.2], [0.8, 0.8], [0.5, 0.15]])
    fly = np.c_[1.135 + 0.03 * rng.random(6), fly_yz]                    # 隙間の真ん中の飛び点(互いに離す)
    part_b = np.r_[np.c_[np.full(400, 1.3), rng.random((400, 2))], rng.random((800, 3)) + [1.3, 0, 0]]
    raw = convex_hull_gap(np.r_[part_a, fly], part_b)
    clean, keep = pcl_filter.radius_outlier_removal(np.r_[part_a, fly], radius=0.06, min_neighbors=2)
    r = convex_hull_gap(clean, part_b)
    assert not keep[-6:].any()                                   # 飛び点は全部落ちる
    assert raw["gap"] < 0.2                                      # 飛び点が隙間を詰めて見せる
    assert abs(r["gap"] - 0.3) < 1e-9                            # 除いた後は面の間の 0.3
