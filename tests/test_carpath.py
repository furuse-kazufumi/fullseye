"""carpath(Dubins / Reeds–Shepp / Hybrid A*)の門。

固定する性質:
- 閉形式の候補は全部、前進積分で目標に着く(n_rejected == 0)—— 式の写し間違いは候補が落ちて数に出る
- Reeds–Shepp の 18 の語族が全部、候補にも最短にも現れる(OMPL の mod2pi は (−π, π]。[0, 2π) にすると
  CCSC 系 8 語が一度も出ない —— 2026-09-28 に踏んだ)
- 第 2 実装: 語ごとの区間長を未知数にした終点方程式を SLSQP で多数の初期値から解いた最小値は、閉形式を
  下回らない(閉形式が最小)。かつ閉形式に届く(最適化器が同じ答えを見つける)
- 定理の不等式: ユークリッド距離 ≤ RS ≤ Dubins、可逆対称 L(s,g) = L(g,s)、鏡映対称、剛体変換で不変、
  ρ に比例、三角不等式
- 整列した目標(真っ直ぐ前)では RS = Dubins = 距離、語は S
- Hybrid A*: 障害物の無い格子で費用 = RS 長(前進のみなら Dubins 長)と厳密一致、障害物では費用 ≥ 下界、
  返す姿勢列は衝突せず運動学的に実現可能(|Δθ| ≤ Δs/ρ)、始点と終点が一致
- fail-closed: 形の悪い入力・格子外・衝突・到達不能は ValueError
"""
import math

import numpy as np
import pytest
from scipy.optimize import minimize

import carpath as C

RS_TYPES = ("LRL", "RLR", "LRLR", "RLRL", "LRSL", "RLSR", "LSRL", "RSLR", "LRSR", "RLSL",
            "RSRL", "LSLR", "LSR", "RSL", "LSL", "RSR", "LRSLR", "RLSRL")
DUBINS_TYPES = ("LSL", "RSR", "LSR", "RSL", "RLR", "LRL")


def _random_pair(rng, span=4.0):
    s = (rng.uniform(-span, span), rng.uniform(-span, span), rng.uniform(-math.pi, math.pi))
    g = (rng.uniform(-span, span), rng.uniform(-span, span), rng.uniform(-math.pi, math.pi))
    return s, g


def _oracle(start, goal, rho, types, forward_only, n_starts=24, seed=0):
    """第 2 実装: 語 word の区間長 l を未知数に、min Σ|l| s.t. 終点 = goal を SLSQP で多数の初期値から解く。
    閉形式の構造(中央の区間が u, −u や π/2 に固定される等)を仮定しない。全語の最小値を返す(単位 = 実寸)。"""
    x, y, phi = C._relative(start, goal, rho)
    rng = np.random.default_rng(seed)
    d = math.hypot(x, y)
    best = math.inf
    for word in types:
        n = len(word)
        lo = [0.0 if forward_only else -(2 * math.pi if k != "S" else d + 4.0) for k in word]
        hi = [(2 * math.pi if k != "S" else d + 4.0) for k in word]

        def endpoint(l):
            ex, ey, eth = C._integrate(word, l, (0.0, 0.0, 0.0), 1.0)
            return np.array([ex - x, ey - y, 2.0 * math.sin(0.5 * (eth - phi))])  # 3 未知数に 3 式(角は滑らかな 2 sin(Δ/2))

        cons = {"type": "eq", "fun": endpoint}
        for _ in range(n_starts):
            l0 = rng.uniform(lo, hi)
            r = minimize(lambda l: float(np.sum(np.sqrt(l * l + 1e-12))), l0, method="SLSQP",
                         bounds=list(zip(lo, hi)), constraints=[cons], options={"maxiter": 200, "ftol": 1e-12})
            if np.max(np.abs(endpoint(r.x))) < 1e-6:
                best = min(best, float(np.sum(np.abs(r.x))))
    return best * rho


# ---- 閉形式の健全性 ----------------------------------------------------------------------------------
def test_all_candidates_reach_goal_and_families_are_complete():
    rng = np.random.default_rng(0)
    fam_cand, fam_best = set(), set()
    for _ in range(600):
        s, g = _random_pair(rng, 6.0)
        rho = rng.uniform(0.5, 2.0)
        d = C.car_dubins_path([s, g], radius=rho)
        r = C.car_reeds_shepp_path([s, g], radius=rho)
        assert d["n_rejected"] == 0 and r["n_rejected"] == 0
        assert 1 <= r["n_candidates"] <= 44
        for w, _L in r["candidates"]:
            fam_cand.add(w.upper())
        fam_best.add(r["word"].upper())
        for res in (d, r):
            p = res["points"][-1]
            assert max(abs(p[0] - g[0]), abs(p[1] - g[1]), abs(C._wrap(p[2] - g[2]))) < 1e-6
            assert res["points"][0] == pytest.approx(s)
            assert res["length"] == pytest.approx(sum(seg[2] for seg in res["segments"]))
    assert fam_cand == set(RS_TYPES), sorted(set(RS_TYPES) - fam_cand)
    assert fam_best == set(RS_TYPES), sorted(set(RS_TYPES) - fam_best)


def test_theorem_inequalities_and_symmetries():
    rng = np.random.default_rng(1)
    for _ in range(300):
        s, g = _random_pair(rng)
        rho = rng.uniform(0.5, 2.0)
        d = C.car_dubins_path([s, g], radius=rho)["length"]
        r = C.car_reeds_shepp_path([s, g], radius=rho)["length"]
        eu = math.hypot(g[0] - s[0], g[1] - s[1])
        assert eu - 1e-9 <= r <= d + 1e-9
        # 可逆対称(RS)と時間反転対称(Dubins: 向きを π 回して逆に走る)
        assert C.car_reeds_shepp_path([g, s], radius=rho)["length"] == pytest.approx(r, rel=1e-9, abs=1e-9)
        d2 = C.car_dubins_path([(g[0], g[1], g[2] + math.pi), (s[0], s[1], s[2] + math.pi)], radius=rho)["length"]
        assert d2 == pytest.approx(d, rel=1e-9, abs=1e-9)
        # 鏡映
        m = C.car_reeds_shepp_path([(s[0], -s[1], -s[2]), (g[0], -g[1], -g[2])], radius=rho)["length"]
        assert m == pytest.approx(r, rel=1e-9, abs=1e-9)
        # 剛体変換で不変、ρ に比例
        a, tx, ty = rng.uniform(-math.pi, math.pi), rng.uniform(-5, 5), rng.uniform(-5, 5)
        ca, sa = math.cos(a), math.sin(a)
        T = lambda p: (ca * p[0] - sa * p[1] + tx, sa * p[0] + ca * p[1] + ty, p[2] + a)  # noqa: E731
        assert C.car_reeds_shepp_path([T(s), T(g)], radius=rho)["length"] == pytest.approx(r, rel=1e-9, abs=1e-9)
        k = rng.uniform(0.3, 3.0)
        S = lambda p: (k * p[0], k * p[1], p[2])  # noqa: E731
        assert C.car_reeds_shepp_path([S(s), S(g)], radius=k * rho)["length"] == pytest.approx(k * r, rel=1e-9)
        assert C.car_dubins_path([S(s), S(g)], radius=k * rho)["length"] == pytest.approx(k * d, rel=1e-9)


def test_triangle_inequality():
    rng = np.random.default_rng(2)
    for _ in range(200):
        a, b = _random_pair(rng)
        c = _random_pair(rng)[0]
        for fn in (C.car_reeds_shepp_path, C.car_dubins_path):
            ac = fn([a, c], radius=1.0)["length"]
            ab = fn([a, b], radius=1.0)["length"]
            bc = fn([b, c], radius=1.0)["length"]
            assert ac <= ab + bc + 1e-9


def test_aligned_goal_is_a_straight_line():
    for L in (0.5, 3.0, 20.0):
        d = C.car_dubins_path([(1.0, 2.0, 0.3), (1.0 + L * math.cos(0.3), 2.0 + L * math.sin(0.3), 0.3)], radius=1.7)
        r = C.car_reeds_shepp_path([(1.0, 2.0, 0.3), (1.0 + L * math.cos(0.3), 2.0 + L * math.sin(0.3), 0.3)], radius=1.7)
        assert d["length"] == pytest.approx(L, abs=1e-9) and r["length"] == pytest.approx(L, abs=1e-9)
        assert d["word"].replace("L", "").replace("R", "") == "S" or d["segments"] == [("S", 1, pytest.approx(L))]
        assert r["word"] == "S"
    # 真後ろ: RS は後退 1 本、Dubins は回り込む
    r = C.car_reeds_shepp_path([(0, 0, 0), (-2.0, 0, 0)], radius=1.0)
    assert r["word"] == "s" and r["length"] == pytest.approx(2.0, abs=1e-9)
    assert C.car_dubins_path([(0, 0, 0), (-2.0, 0, 0)], radius=1.0)["length"] > 2.0 + math.pi


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_second_implementation_by_optimizer(seed):
    rng = np.random.default_rng(100 + seed)
    s, g = _random_pair(rng, 3.0)
    rho = 1.0
    rs = C.car_reeds_shepp_path([s, g], radius=rho)["length"]
    du = C.car_dubins_path([s, g], radius=rho)["length"]
    o_rs = _oracle(s, g, rho, RS_TYPES, forward_only=False, seed=seed)
    o_du = _oracle(s, g, rho, DUBINS_TYPES, forward_only=True, seed=seed)
    # 閉形式は最小(最適化器はそれを下回れない)、かつ最適化器は同じ最小に届く
    assert o_rs >= rs - 1e-6 and o_du >= du - 1e-6
    assert o_rs == pytest.approx(rs, abs=1e-4)
    assert o_du == pytest.approx(du, abs=1e-4)


# ---- Hybrid A* ------------------------------------------------------------------------------------
def _feasible(points, rho, tol=1e-6):
    dd = np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))
    dth = np.abs([C._wrap(v) for v in np.diff(points[:, 2])])
    ok = dd > 1e-9
    return bool(np.all(dth[ok] * rho <= dd[ok] * (1 + 1e-3) + tol))


def test_hybrid_astar_empty_grid_equals_reeds_shepp_and_dubins():
    occ = np.zeros((24, 40), bool)
    s, g = (3.0, 3.0, 0.0), (30.0, 18.0, math.pi / 2)
    h = C.car_hybrid_astar(occ, [s, g], radius=4.0, cell=1.0)
    rs = C.car_reeds_shepp_path([s, g], radius=4.0)["length"]
    assert h["cost"] == pytest.approx(rs, abs=1e-9) and h["length"] == pytest.approx(rs, abs=1e-9)
    assert h["closed_by_shot"] and h["n_expanded"] == 1 and h["lower_bound"] == pytest.approx(rs)
    assert h["points"][0] == pytest.approx(s) and h["points"][-1] == pytest.approx(g)
    hd = C.car_hybrid_astar(occ, [s, g], radius=4.0, cell=1.0, allow_reverse=False)
    du = C.car_dubins_path([s, g], radius=4.0)["length"]
    assert hd["cost"] == pytest.approx(du, abs=1e-9) and hd["closed_by_shot"]


def test_hybrid_astar_detours_a_wall():
    occ = np.zeros((24, 40), bool)
    occ[:, 20] = True
    occ[1:5, 20] = False
    s, g = (3.0, 12.0, 0.0), (36.0, 12.0, 0.0)
    fp = (2.0, 1.2, 0.5)
    h = C.car_hybrid_astar(occ, [s, g], radius=4.0, cell=1.0, footprint=fp, return_tree=True)
    rs = C.car_reeds_shepp_path([s, g], radius=4.0)["length"]
    assert h["lower_bound"] == pytest.approx(rs) and h["cost"] > rs + 1.0  # 壁を回るぶん長い
    assert h["cost"] == pytest.approx(h["length"])  # 罰則 0 → 費用 = 長さ
    assert h["length"] == pytest.approx(sum(seg[2] for seg in h["segments"]), rel=1e-9)
    P = h["points"]
    assert not C._Collision(occ, 1.0, 0.0, fp).blocked(P)
    assert _feasible(P, 4.0)
    assert P[0] == pytest.approx(s) and P[-1] == pytest.approx(g)
    assert np.all(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1])) <= 0.5 + 1e-9)  # cell/2 刻み
    assert h["tree"].shape[1] == 3 and len(h["tree"]) == h["n_generated"] + 1
    # 隙間(行 1..4)を通る
    near = P[np.abs(P[:, 0] - 20.5) < 0.6]
    assert len(near) and np.all((near[:, 1] >= 1.0) & (near[:, 1] < 5.0))
    # 罰則は費用を増やすが長さの門はそのまま
    h2 = C.car_hybrid_astar(occ, [s, g], radius=4.0, cell=1.0, footprint=fp, reverse_penalty=1.0, switch_penalty=2.0)
    assert h2["cost"] >= h2["length"] - 1e-9 and h2["cost"] >= rs


def test_hybrid_astar_fail_closed():
    occ = np.zeros((24, 40), bool)
    s, g = (3.0, 12.0, 0.0), (36.0, 12.0, 0.0)
    with pytest.raises(ValueError):
        C.car_hybrid_astar(occ, [s], radius=4.0)
    with pytest.raises(ValueError):
        C.car_hybrid_astar(occ, [s, (60.0, 12.0, 0.0)], radius=4.0)  # 格子外
    blocked = occ.copy()
    blocked[12, 36] = True
    with pytest.raises(ValueError):
        C.car_hybrid_astar(blocked, [s, g], radius=4.0)  # 目標が障害物
    wall = occ.copy()
    wall[:, 20] = True
    with pytest.raises(ValueError, match="unreachable"):
        C.car_hybrid_astar(wall, [s, g], radius=4.0, n_theta=24)
    with pytest.raises(ValueError, match="max_expansions"):
        C.car_hybrid_astar(wall, [s, g], radius=4.0, n_theta=24, max_expansions=50)
    for bad in (dict(radius=0), dict(cell=-1), dict(n_theta=3), dict(reverse_penalty=-1), dict(footprint=(0, 1, 0))):
        with pytest.raises(ValueError):
            C.car_hybrid_astar(occ, [s, g], **{"radius": 4.0, **bad})
    with pytest.raises(ValueError):
        C.car_hybrid_astar(np.zeros((0, 5)), [s, g], radius=4.0)
    for fn in (C.car_dubins_path, C.car_reeds_shepp_path):
        with pytest.raises(ValueError):
            fn([s, g], radius=0.0)
        with pytest.raises(ValueError):
            fn([[0, 0, np.nan], [1, 1, 0]])
        with pytest.raises(ValueError):
            fn([[0, 0, 0, 0], [1, 1, 0, 0]])
