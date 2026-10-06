# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""braidpath — 複数エージェントの経路を「組紐」で数え、同じ始点と終点を結ぶ経路族をホモトピー類に分ける(2026-10-06)。

平面を動く K 台のエージェントと、動かない M 個の障害物を時空(x, y, t)に描くと、K + M 本の紐が編まれた
**組紐**になる。始点と終点を止めたまま連続に変形できる 2 つの計画は同じ組紐を与え、逆も成り立つ —— だから
「この 2 つの計画は回り方が同じか」は組紐群の語の問題になる。題材の背景は平面の複数エージェント経路計画の
ホモトピー(doi:10.1613/jair.1.19243、CC BY)。本文の転載はしていない —— 下の外から来る数学だけで組む。

外から来るもの(恒等式と閉形式の真値):
  * **組紐群の関係式**(Artin 1925): σᵢσᵢ₊₁σᵢ = σᵢ₊₁σᵢσᵢ₊₁、|i − j| ≥ 2 なら σᵢσⱼ = σⱼσᵢ、σᵢσᵢ⁻¹ = 1。
  * **Dynnikov 座標**(Dynnikov 2002、更新式は Hall & Yurttaş 2009 の区分線形の形): 穴あき円板の上の曲線(多重曲線)を
    整数の組 (a; b) で表し、σᵢ を max / min だけの式で作用させる。関係式は**どんな実数の (a; b) でも恒等的に**成り立つ
    (門 1)。標準の曲線図 E = (0, …, 0; −1, …, −1) への作用は忠実 —— 座標が等しい ⇔ 組紐が等しい。
  * **Artin 表現**(自由群の自己同型 xᵢ ↦ xᵢxᵢ₊₁xᵢ⁻¹、xᵢ₊₁ ↦ xᵢ): 忠実で、自由簡約だけで語の問題を厳密に解く。
    Dynnikov と**独立な第 2 実装**(門で両者の「等しい」を突き合わせる)。
  * **Dehornoy の取っ手簡約**(1997): σᵢ^e u σᵢ^(−e)(u に σᵢ・σᵢ₋₁ が無い)を書き換える。空語に着く ⇔ 自明な組紐。
  * **巻き数の閉形式**: 2 台の相対ベクトルの偏角の総変化 Δθ。純粋な組紐(各紐が自分の始点に戻る)では、2 本の紐の間の
    交差の符号つきの数を c とすると Δθ = π c ちょうど(射影の交差 = 相対ベクトルが射影の軸に垂直な向きを横切ること)。

numpy 層(台帳 ``braidpath``、opsdrive): :func:`braid_from_trajectories` 軌道群 → 組紐語(交差の符号列)/
  :func:`braid_reduce` 取っ手簡約 / :func:`braid_artin_images` Artin 表現(自由群の像)/ :func:`dynnikov_coordinates`
  標準の曲線図の座標 / :func:`dynnikov_act` 任意の座標への作用 / :func:`braid_equivalent` 2 語が同じ組紐か /
  :func:`homotopy_class_compare` 2 つの経路族が同じホモトピー類か / :func:`pairwise_winding` 対ごとの巻き数 /
  :func:`homotopy_shortest_paths` 格子の上で類ごとの最短経路を短い順に k 本(類で持ち上げた Dijkstra)/
  :func:`braid_class_representatives` 既存の計画器が出した候補を類に分け、類ごとの代表を選ぶ /
  :func:`grid_hole_points` 格子の穴ごとの代表の点 / :func:`grid_paths_to_xy` 格子の経路 → (K, T, 2) の軌道。

規約:
  * 組紐語は符号つき整数の列。``+i`` = σᵢ(位置 i と i+1 の紐が**反時計回り**に半回転して入れ替わる)、``−i`` = σᵢ⁻¹。
    位置は 1 始まりで、射影の軸 x' = x cos θ + y sin θ の小さい順(同じ x' なら y' の小さい順 —— 軸を無限小だけ回した
    のと同じ)。紐の番号はエージェント 0..K−1、障害物 K..K+M−1。
  * Dynnikov 座標は n 本の紐に**右端の穴を 1 つ足した** n + 1 個の穴の円板で取る(σₙ を使わないので最後の穴の特別な
    式が要らない)。返りは ``a``・``b``(長さ n − 1 ずつ)、Python の整数(長い語で 64 bit を超えても溢れない)。
  * 軌道は (K, T, 2) の配列 [x, y]、または格子の経路の列(各台の (row, col) の列、長さは違ってよい —— 着いた後は
    その場に居続ける)。格子の経路は x = col、y = −row に写す(行は下向き)。
  * 角度は rad。逆三角は使わない(偏角の差は atan2(外積, 内積))。

呼び出し例(台帳の op を繋ぐ。tests/test_braidpath.py の test_usage_example_in_the_module_docstring_runs が実行する)::

    import numpy as np
    import braidpath
    grid = np.ones((7, 9), bool)
    grid[2:5, 3:6] = False                                          # 真ん中に柱(走れないマス)
    hsp = braidpath.homotopy_shortest_paths(grid, (3, 0), (3, 8), k=3)   # 類ごとの最短を短い順に(柱の上 / 下 / 1 周多く)
    holes = braidpath.grid_hole_points(grid)                        # 柱の代表の点 [x, y]
    up, down = (braidpath.grid_paths_to_xy([p]) for p in hsp["paths"][:2])   # 1 台の経路を (1, T, 2) の軌道に
    cmp = braidpath.homotopy_class_compare(up, down, obstacles=holes)       # 上を回る経路と下を回る経路は別の類
    br = braidpath.braid_from_trajectories(up, obstacles=holes)     # 時空の組紐語(交差の符号列)
    red = braidpath.braid_reduce(br["word"], br["n_strands"])       # Dehornoy の取っ手簡約
    dyn = braidpath.dynnikov_coordinates(br["word"], br["n_strands"])   # Dynnikov 座標(整数、等しい ⇔ 同じ組紐)
    eq = braidpath.braid_equivalent(br["word"], red, br["n_strands"], method="all")   # 3 つの判定で同じ組紐
    W = braidpath.pairwise_winding(up, obstacles=holes)             # 台と柱の巻き数 [回転]
    print(hsp["costs"], cmp["same"], eq["equal"], dyn["a"], dyn["b"], round(float(W[0, 1]), 2))
"""
from __future__ import annotations

import heapq
import itertools
import math

import numpy as np

__all__ = [
    "braid_from_trajectories", "braid_reduce", "braid_artin_images", "dynnikov_coordinates", "dynnikov_act",
    "braid_equivalent", "homotopy_class_compare", "pairwise_winding", "homotopy_shortest_paths",
    "braid_class_representatives", "grid_hole_points", "grid_paths_to_xy",
]

#: 射影の軸の既定の角度 [rad]。格子の動き(軸に平行・整数の座標)で 2 組の交差が同時になる偶然を避ける、一般の位置の角。
DEFAULT_ANGLE = 0.1
#: 同じ時刻とみなす交差の時刻の差(1 刻みに対する割合)。
_T_TIE = 1e-12
#: 取っ手簡約・自由群の像が膨らみすぎたら止める語の長さ。
MAX_WORD = 200_000


# ======================================================================================================================
# 0. 検査の小道具
def _int(x, name: str, op: str, lo: int | None = None) -> int:
    if isinstance(x, bool) or not isinstance(x, (int, np.integer)):
        try:
            fx = float(x)
        except (TypeError, ValueError):
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, x)) from None
        if not math.isfinite(fx) or fx != int(fx):
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, x))
        x = int(fx)
    v = int(x)
    if lo is not None and v < lo:
        raise ValueError("%s: %s must be >= %d, got %r" % (op, name, lo, x))
    return v


def _angle(angle, op: str) -> float:
    try:
        a = float(angle)
    except (TypeError, ValueError):
        raise ValueError("%s: angle must be a number [rad], got %r" % (op, angle)) from None
    if not math.isfinite(a):
        raise ValueError("%s: angle must be finite, got %r" % (op, angle))
    return a


def _word(word, n_strands: int, op: str) -> list[int]:
    """組紐語を検査して Python の int の list にする(0 は無い、|letter| ≤ n − 1)。"""
    if isinstance(word, dict):
        if "word" not in word:
            raise ValueError("%s: a dict word must carry the key 'word' (the output of braid_from_trajectories)" % op)
        word = word["word"]
    try:
        arr = np.asarray(word)
    except Exception:  # pragma: no cover - numpy は大抵どれでも配列にする
        raise ValueError("%s: word must be a 1-D sequence of signed integers" % op) from None
    if arr.size == 0:
        return []
    if arr.ndim != 1:
        raise ValueError("%s: word must be 1-D, got shape %s" % (op, arr.shape))
    out = []
    for k, x in enumerate(arr.tolist()):
        v = _int(x, "word[%d]" % k, op)
        if v == 0 or abs(v) > n_strands - 1:
            raise ValueError("%s: word[%d] = %d is not a generator of B_%d (use ±1..±%d, 0 is not a letter)"
                             % (op, k, v, n_strands, n_strands - 1))
        out.append(v)
    return out


def _n_strands(n, op: str) -> int:
    return _int(n, "n_strands", op, lo=2)


# ======================================================================================================================
# 1. 軌道 → 組紐語
def _as_traj(trajectories, op: str) -> np.ndarray:
    """(K, T, 2) の float 配列にする。

    規則は型で決める(形で推し量らない —— 同じ長さの格子の経路が黙って [x, y] に読まれる罠を避ける):
    numpy の配列 = [x, y] の軌道 (K, T, 2)。list / tuple の経路の列、または dict の ``paths`` = 格子の経路
    (各台の (row, col) の列、長さは違ってよい)で、x = col、y = −row にして最後の点で詰める。
    """
    if isinstance(trajectories, dict):
        if "paths" not in trajectories:
            raise ValueError("%s: a dict plan must carry 'paths' (a planner's output)" % op)
        trajectories = trajectories["paths"]
        if trajectories is None:
            raise ValueError("%s: the plan has no paths (did the planner fail?)" % op)
    if trajectories is None:
        raise ValueError("%s: trajectories is None (did the planner fail?)" % op)
    if isinstance(trajectories, np.ndarray):
        P = np.asarray(trajectories, dtype=float)
    else:
        seq = list(trajectories)
        if not seq:
            raise ValueError("%s: no paths" % op)
        try:
            arrs = [np.asarray(s, dtype=float) for s in seq]
        except (TypeError, ValueError):
            raise ValueError("%s: each grid path must be a sequence of (row, col) cells" % op) from None
        if any(a.ndim != 2 or a.shape[1] != 2 or a.shape[0] == 0 for a in arrs):
            raise ValueError("%s: each grid path must be an (L, 2) sequence of (row, col) cells" % op)
        P = grid_paths_to_xy(arrs)
    if P.ndim != 3 or P.shape[2] != 2 or P.shape[0] < 1 or P.shape[1] < 1:
        raise ValueError("%s: trajectories must have shape (K, T, 2), got %s" % (op, P.shape))
    if not np.all(np.isfinite(P)):
        raise ValueError("%s: trajectories contain NaN / inf" % op)
    return P


def grid_paths_to_xy(paths) -> np.ndarray:
    """格子の経路(各台の (row, col) の列)を (K, T, 2) の [x, y] = [col, −row] にする(短い経路は最後の点で詰める)。"""
    arrs = [np.asarray(s, dtype=float) for s in paths]
    T = max(a.shape[0] for a in arrs)
    P = np.empty((len(arrs), T, 2))
    for i, a in enumerate(arrs):
        full = np.vstack([a, np.repeat(a[-1:], T - a.shape[0], axis=0)])
        P[i, :, 0] = full[:, 1]
        P[i, :, 1] = -full[:, 0]
    return P


def _strands(trajectories, obstacles, op):
    P = _as_traj(trajectories, op)
    K, T = P.shape[:2]
    if obstacles is None or (hasattr(obstacles, "__len__") and len(obstacles) == 0):
        O = np.zeros((0, 2))
    else:
        O = np.asarray(obstacles, dtype=float)
        if O.ndim == 1 and O.size == 2:
            O = O[None, :]
        if O.ndim != 2 or O.shape[1] != 2:
            raise ValueError("%s: obstacles must be an (M, 2) array of points, got shape %s" % (op, O.shape))
        if not np.all(np.isfinite(O)):
            raise ValueError("%s: obstacles contain NaN / inf" % op)
    if K + O.shape[0] < 2:
        raise ValueError("%s: a braid needs at least 2 strands (agents + obstacle points), got %d" % (op, K + O.shape[0]))
    S = np.concatenate([P, np.repeat(O[:, None, :], T, axis=1)], axis=0)
    return S, K


def _lex_order(X: np.ndarray, Y: np.ndarray) -> list[int]:
    return sorted(range(len(X)), key=lambda i: (X[i], Y[i]))


def _sgn(x: float, y: float) -> int:
    """x' の符号、x' = 0 なら y' の符号(軸を無限小だけ回したのと同じ順)。0 = 同じ点。"""
    if x > 0 or (x == 0 and y > 0):
        return 1
    if x < 0 or (x == 0 and y < 0):
        return -1
    return 0


def _step_events(x0, y0, x1, y1, step: int, op: str):
    """1 刻みの間(各紐は直線で動く)に起きる対の交差を全部返す: [(t*, i, j, y'_i − y'_j)]、i < j は紐の番号。"""
    n = len(x0)
    ev = []
    for i in range(n):
        for j in range(i + 1, n):
            dx0, dy0 = x0[i] - x0[j], y0[i] - y0[j]
            dx1, dy1 = x1[i] - x1[j], y1[i] - y1[j]
            s0, s1 = _sgn(dx0, dy0), _sgn(dx1, dy1)
            if s0 == 0 or s1 == 0:
                raise ValueError("%s: strands %d and %d occupy the same point at step %d — a collision has no braid"
                                 % (op, i, j, step + (s0 != 0)))
            if s0 == s1:
                continue
            if dx0 == 0.0 and dx1 == 0.0:
                raise ValueError("%s: strands %d and %d pass through each other at step %d (collision)" % (op, i, j, step))
            t = dx0 / (dx0 - dx1)
            t = min(max(t, 0.0), 1.0)
            dy = dy0 + t * (dy1 - dy0)
            if dy == 0.0:
                raise ValueError("%s: strands %d and %d meet at step %d (t = %.6f) — a collision has no braid"
                                 % (op, i, j, step, t))
            ev.append((t, i, j, dy))
    ev.sort(key=lambda e: e[0])
    return ev


class TriplePointError(ValueError):
    """同じ時刻の交差が紐を共有する(射影の三重点)。格子の対称な動きでは軸の角度を変えても消えない(3 点が一直線の
    まま回る)—— :func:`braid_from_trajectories` は既定でごく小さな一定のずらしを紐ごとに足して取り直す。"""


def _apply_events(ev, order: list[int], rank: list[int], word: list[int], times: list[float], step: int, op: str):
    """交差を時刻の順に組紐の文字にする。同じ時刻の交差が紐を共有する(射影の三重点)ときは向きが決まらないので止める。"""
    k = 0
    while k < len(ev):
        g = [ev[k]]
        while k + len(g) < len(ev) and ev[k + len(g)][0] - ev[k][0] <= _T_TIE:
            g.append(ev[k + len(g)])
        if len(g) > 1:
            used = [s for e in g for s in e[1:3]]
            if len(set(used)) != len(used):
                raise TriplePointError("%s: simultaneous crossings sharing a strand at step %d (a triple point of the "
                                       "projection) — the order of the letters is ambiguous" % (op, step))
        for t, i, j, dy in g:
            ri, rj = rank[i], rank[j]
            if abs(ri - rj) != 1:
                raise ValueError("%s: strands %d and %d cross at step %d but are not neighbours in the projection "
                                 "(ranks %d, %d) — the sampling is too coarse or the input is degenerate" % (op, i, j, step, ri, rj))
            left, right = (i, j) if ri < rj else (j, i)
            dy_lr = dy if left == i else -dy                # y'_left − y'_right
            pos = min(ri, rj) + 1                          # 1 始まり
            word.append(pos if dy_lr < 0 else -pos)        # 左の紐が下を通って右へ = 反時計回り = +
            times.append(step + t)
            order[pos - 1], order[pos] = right, left
            rank[left], rank[right] = pos, pos - 1
        k += len(g)


def _clearance(S: np.ndarray) -> float:
    """紐どうしの最小距離(各刻みの間は直線 → 対ごとに閉形式の最小)。T = 1 なら点の間の距離。"""
    n, T = S.shape[:2]
    best = float("inf")
    for i in range(n - 1):
        d = S[i + 1:] - S[i]                                   # (n-i-1, T, 2)
        if T == 1:
            best = min(best, float(np.min(np.hypot(d[..., 0], d[..., 1]))))
            continue
        d0, e = d[:, :-1], d[:, 1:] - d[:, :-1]
        ee = np.einsum("kti,kti->kt", e, e)
        safe = np.where(ee > 0, ee, 1.0)
        t = np.where(ee > 0, np.clip(-np.einsum("kti,kti->kt", d0, e) / safe, 0.0, 1.0), 0.0)
        m = d0 + t[..., None] * e
        best = min(best, float(np.min(np.hypot(m[..., 0], m[..., 1]))))
    return best


def _jitter_offsets(n: int) -> np.ndarray:
    """紐ごとの一定のずらしの向き(黄金角で回す、決定的)。"""
    k = np.arange(n, dtype=float)
    phi = k * math.pi * (3.0 - math.sqrt(5.0)) + 0.3
    return np.stack([np.cos(phi), np.sin(phi)], axis=1)


def _braid_core(S: np.ndarray, K: int, th: float, eps: float, op: str) -> dict:
    n, T = S.shape[:2]
    if eps > 0.0:
        S = S + eps * _jitter_offsets(n)[:, None, :]
    c, s = math.cos(th), math.sin(th)
    X = S[:, :, 0] * c + S[:, :, 1] * s
    Y = -S[:, :, 0] * s + S[:, :, 1] * c
    order = _lex_order(X[:, 0], Y[:, 0])
    rank = [0] * n
    for p, i in enumerate(order):
        rank[i] = p
    start = list(order)
    word: list[int] = []
    times: list[float] = []
    for t in range(T - 1):
        ev = _step_events(X[:, t].tolist(), Y[:, t].tolist(), X[:, t + 1].tolist(), Y[:, t + 1].tolist(), t, op)
        if ev:
            _apply_events(ev, order, rank, word, times, t, op)
    return {"word": np.asarray(word, dtype=np.int64), "n_strands": int(n), "n_agents": int(K),
            "start_order": np.asarray(start, dtype=np.int64), "end_order": np.asarray(order, dtype=np.int64),
            "times": np.asarray(times, dtype=float), "angle": th, "jitter": float(eps)}


#: 三重点を崩すずらしの大きさ(紐どうしの最小距離に対する割合)。最小距離より十分小さいので組紐は変わらない。
JITTER_FRACTION = 1e-6


def _braids_consistent(trajs, obstacles, th, jitter, op):
    """複数の計画の組紐を**同じ条件で**取る(どれか 1 つでも三重点なら、全部を同じずらしで取り直す)。"""
    strands = [_strands(P, obstacles, op) for P in trajs]
    clear = min(_clearance(S) for S, _K in strands)
    if not clear > 0.0:
        raise ValueError("%s: two strands collide (minimum distance 0) — a collision has no braid" % op)
    if isinstance(jitter, str):
        if jitter != "auto":
            raise ValueError("%s: jitter must be 'auto' or a number, got %r" % (op, jitter))
        try:
            return [_braid_core(S, K, th, 0.0, op) for S, K in strands], clear
        except TriplePointError:
            eps = JITTER_FRACTION * clear
    else:
        try:
            eps = float(jitter)
        except (TypeError, ValueError):
            raise ValueError("%s: jitter must be 'auto' or a number, got %r" % (op, jitter)) from None
        if not (math.isfinite(eps) and 0.0 <= eps <= 0.01 * clear):
            raise ValueError("%s: jitter must lie in [0, 0.01 * clearance = %.3g], got %r" % (op, 0.01 * clear, jitter))
    return [_braid_core(S, K, th, eps, op) for S, K in strands], clear


def braid_from_trajectories(trajectories, obstacles=None, angle=DEFAULT_ANGLE, jitter="auto"):
    """平面の軌道群(と動かない障害物の点)から組紐語を作る(交差の符号列)。

    各刻みの間は直線で動くとして、射影の軸 x' = x cos θ + y sin θ の上で隣り合う 2 本の紐の順が入れ替わる時刻を
    閉形式で求め(相対の動きも直線なので零点は高々 1 つ)、時刻の順に文字にする。左の紐が**下**(y' の小さい側)を
    通って右へ出れば ``+i``(反時計回りの半回転)、上を通れば ``−i``。

    ★射影の三重点: 格子の対称な動き(2 台が障害物の点をはさんで点対称に動く等)では 3 本が一直線のまま回り、
    どの角度でも 3 つの交差が同時になる。``jitter="auto"`` は、そのときだけ紐ごとに一定の小さなずらし
    (最小距離 × ``JITTER_FRACTION``、向きは黄金角)を足して取り直す。ずらしは最小距離よりずっと小さいので組紐は
    変わらない(門で確かめる)。

    Parameters
    ----------
    trajectories : numpy の (K, T, 2) = [x, y]、または list の格子の経路(各台の (row, col) の列)/ 計画器の dict(``paths``)。
    obstacles : (M, 2) の点、任意。穴を 1 点で代表させる(穴の中の点ならどれでも類は変わらない)。
    angle : 射影の軸の角度 [rad]。類の判定(:func:`homotopy_class_compare`)は角度に依らないが、語そのものは変わる。
    jitter : ``"auto"`` か、ずらしの大きさ(0 = ずらさない、上限は最小距離の 1 %)。

    Returns
    -------
    dict: ``word`` (int の 1-D 配列)、``n_strands``、``n_agents``、``start_order`` / ``end_order``(位置の順の紐の番号)、
    ``times``(各文字の時刻、刻みの単位)、``angle``、``jitter``(使ったずらし)、``clearance``(紐どうしの最小距離)。

    Raises
    ------
    ValueError: 2 本の紐が同じ点に来る(衝突に組紐は無い)、jitter=0 で三重点(TriplePointError)、形が違う、NaN。
    """
    op = "braid_from_trajectories"
    th = _angle(angle, op)
    (res,), clear = _braids_consistent([trajectories], obstacles, th, jitter, op)
    res["clearance"] = clear
    return res


# ======================================================================================================================
# 2. 取っ手簡約(Dehornoy)
def _free_reduce(w: list[int]) -> list[int]:
    out: list[int] = []
    for x in w:
        if out and out[-1] == -x:
            out.pop()
        else:
            out.append(x)
    return out


def _handle_reduce(w: list[int], op: str, max_steps: int = 1_000_000) -> list[int]:
    """左から見て最初に閉じる取っ手を書き換え続ける(その取っ手の中に別の取っ手は無い = 許される取っ手)。"""
    w = _free_reduce(w)
    for _ in range(max_steps):
        last: dict[int, int] = {}
        found = None
        for b, x in enumerate(w):
            j = abs(x)
            a = last.get(j)
            if a is not None and w[a] == -x and last.get(j - 1, -1) < a:
                found = (a, b)
                break
            last[j] = b
        if found is None:
            return w
        a, b = found
        j, e = abs(w[a]), (1 if w[a] > 0 else -1)
        mid: list[int] = []
        for x in w[a + 1:b]:
            if abs(x) == j + 1:
                d = 1 if x > 0 else -1
                mid.extend((-e * (j + 1), d * j, e * (j + 1)))
            else:
                mid.append(x)
        w = _free_reduce(w[:a] + mid + w[b + 1:])
        if len(w) > MAX_WORD:
            raise RuntimeError("%s: handle reduction grew the word beyond %d letters" % (op, MAX_WORD))
    raise RuntimeError("%s: handle reduction did not finish in %d steps" % (op, max_steps))


def braid_reduce(word, n_strands):
    """組紐語を Dehornoy の取っ手簡約で簡約する。**空の語が返る ⇔ 自明な組紐**(同じ類)。

    取っ手 = σⱼ^e u σⱼ^(−e)(u に σⱼ^(±1)・σⱼ₋₁^(±1) が無い)。u の中の σⱼ₊₁^d を σⱼ₊₁^(−e) σⱼ^d σⱼ₊₁^e に替え、外側の
    2 文字を消す(関係式だけを使うので組紐は変わらない)。左から最初に閉じる取っ手を選ぶ —— その中には別の取っ手が
    無いので Dehornoy の意味で許され、有限回で止まる。返りの語は取っ手を持たず、空でなければ現れる最小の添字の
    文字の符号がそろう(σ 正 / σ 負)。

    Returns: int の 1-D 配列(簡約した語)。
    Raises: ValueError(添字が範囲の外・0)、RuntimeError(語が ``MAX_WORD`` を超えて膨らんだ)。
    """
    op = "braid_reduce"
    n = _n_strands(n_strands, op)
    return np.asarray(_handle_reduce(_word(word, n, op), op), dtype=np.int64)


# ======================================================================================================================
# 3. Artin 表現(自由群の自己同型)—— 独立な第 2 実装
def braid_artin_images(word, n_strands, max_length=MAX_WORD):
    """組紐の Artin 表現: 自由群 F_n の生成元 x₁..xₙ の像(自由簡約した語)。

    σᵢ: xᵢ ↦ xᵢ xᵢ₊₁ xᵢ⁻¹、xᵢ₊₁ ↦ xᵢ、ほかは動かさない。語 w = σ_{i1} σ_{i2} … の像は左から順に代入して作る。
    この表現は忠実(Artin 1925)なので、**像が全部一致 ⇔ 同じ組紐**。自由簡約だけの厳密な判定で、Dynnikov 座標と
    独立に「等しい」を確かめる第 2 実装になる。像の長さは語の長さに対して指数で伸びうるので ``max_length`` で止める。

    Returns: dict ``images``(長さ n の list、各要素は符号つき整数の list で ±k = x_k^(±1))、``lengths``、``identity``
    (全部 xₖ そのものか)。
    """
    op = "braid_artin_images"
    n = _n_strands(n_strands, op)
    w = _word(word, n, op)
    lim = _int(max_length, "max_length", op, lo=1)
    img = [[k] for k in range(1, n + 1)]

    def inv(u):
        return [-x for x in reversed(u)]

    def sub(u):                       # 生成元の語 u に今の像を代入
        out: list[int] = []
        for x in u:
            out.extend(img[x - 1] if x > 0 else inv(img[-x - 1]))
        return _free_reduce(out)

    for x in w:
        i = abs(x)
        if x > 0:                     # σᵢ: xᵢ ↦ xᵢ xᵢ₊₁ xᵢ⁻¹、xᵢ₊₁ ↦ xᵢ
            new_i, new_j = sub([i, i + 1, -i]), list(img[i - 1])
        else:                         # σᵢ⁻¹: xᵢ ↦ xᵢ₊₁、xᵢ₊₁ ↦ xᵢ₊₁⁻¹ xᵢ xᵢ₊₁
            new_i, new_j = list(img[i]), sub([-(i + 1), i, i + 1])
        img[i - 1], img[i] = new_i, new_j
        if len(new_i) > lim or len(new_j) > lim:
            raise RuntimeError("%s: an image grew beyond %d letters (the word is long and mixing); use dynnikov_coordinates"
                               % (op, lim))
    return {"images": img, "lengths": np.asarray([len(u) for u in img], dtype=np.int64),
            "identity": all(u == [k + 1] for k, u in enumerate(img))}


# ======================================================================================================================
# 4. Dynnikov 座標
def _p(x):
    return x if x > 0 else 0 * x


def _q(x):
    return x if x < 0 else 0 * x


def _act(a: list, b: list, w: list[int]) -> None:
    """(a; b) に語を左から作用させる(その場で書き換える)。σᵢ の i は 1 始まり、a・b の添字は 0 始まり。"""
    for x in w:
        i = abs(x)
        if i == 1:
            a1, b1 = a[0], b[0]
            if x > 0:
                bb = a1 + _p(b1)
                a[0], b[0] = -b1 + _p(bb), bb
            else:
                bb = _p(b1) - a1
                a[0], b[0] = b1 - _p(bb), bb
            continue
        k = i - 2                                   # a_{i-1} = a[k]、a_i = a[k+1]
        A0, B0, A1, B1 = a[k], b[k], a[k + 1], b[k + 1]
        if x > 0:
            c = A0 + _q(B0) - A1 - _p(B1)
            a[k] = A0 - _p(B0) - _p(_p(B1) + c)
            b[k] = B1 + _q(c)
            a[k + 1] = A1 - _q(B1) - _q(_q(B0) - c)
            b[k + 1] = B0 - _q(c)
        else:
            d = A0 - _q(B0) - A1 + _p(B1)
            a[k] = A0 + _p(B0) + _p(_p(B1) - d)
            b[k] = B1 - _p(d)
            a[k + 1] = A1 + _q(B1) + _q(_q(B0) + d)
            b[k + 1] = B0 + _p(d)


def _dyn_out(a, b, n):
    m = max([abs(v) for v in a + b] + [0])
    return {"a": list(a), "b": list(b), "key": tuple(a) + tuple(b), "n_strands": int(n), "n_punctures": int(n + 1),
            "max_abs": m, "bits": int(m).bit_length() if isinstance(m, int) else None}


def dynnikov_coordinates(word, n_strands):
    """標準の曲線図 E = (0, …, 0; −1, …, −1) に組紐を作用させた Dynnikov 座標(整数、溢れない)。

    n 本の紐に右端の穴を 1 つ足した n + 1 個の穴の円板で取る(a・b とも長さ n − 1)。この作用は忠実なので、
    **座標が等しい ⇔ 同じ組紐**。1 文字あたり定数回の加減算と max / min だけで、語の長さに比例する時間で済む
    (取っ手簡約や自由群の像と違って膨らまない —— 数が大きくなるだけで、Python の整数は溢れない)。

    Returns: dict ``a``・``b``(int の list)、``key``(a + b の tuple、類の鍵に使う)、``n_strands``、``n_punctures``、
    ``max_abs``(座標の最大の絶対値)、``bits``。
    """
    op = "dynnikov_coordinates"
    n = _n_strands(n_strands, op)
    w = _word(word, n, op)
    a, b = [0] * (n - 1), [-1] * (n - 1)
    _act(a, b, w)
    return _dyn_out(a, b, n)


def dynnikov_act(coords, word):
    """任意の Dynnikov 座標 (a; b)(整数でも実数でもよい —— 式は区分線形)に組紐の語を作用させる。

    ``coords`` は dict(``a``・``b``)か、長さ 2(n − 1) の列(前半 a、後半 b)。紐の本数は n = len(a) + 1。関係式
    σᵢσᵢ₊₁σᵢ = σᵢ₊₁σᵢσᵢ₊₁・σᵢσⱼ = σⱼσᵢ・σᵢσᵢ⁻¹ = 1 は**どの (a; b) でも恒等的に**成り立つ(門 1 で乱数の実数座標に)。

    Returns: :func:`dynnikov_coordinates` と同じ形の dict(実数の入力なら float のまま)。
    """
    op = "dynnikov_act"
    if isinstance(coords, dict):
        if "a" not in coords or "b" not in coords:
            raise ValueError("%s: coords dict must carry 'a' and 'b'" % op)
        a, b = list(coords["a"]), list(coords["b"])
    else:
        arr = np.asarray(coords)
        if arr.ndim != 1 or arr.size < 2 or arr.size % 2:
            raise ValueError("%s: coords must be a 1-D sequence of even length 2(n-1) >= 2, got shape %s" % (op, arr.shape))
        h = arr.size // 2
        lst = arr.tolist()
        a, b = lst[:h], lst[h:]
    if len(a) != len(b) or not a:
        raise ValueError("%s: a and b must have the same non-zero length" % op)
    for v in a + b:
        if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)) or not math.isfinite(float(v)):
            raise ValueError("%s: coordinates must be finite numbers, got %r" % (op, v))
    a = [int(v) if isinstance(v, (int, np.integer)) else float(v) for v in a]
    b = [int(v) if isinstance(v, (int, np.integer)) else float(v) for v in b]
    n = len(a) + 1
    w = _word(word, n, op)
    _act(a, b, w)
    return _dyn_out(a, b, n)


# ======================================================================================================================
# 5. 同じ組紐か / 同じホモトピー類か
def braid_equivalent(word_a, word_b, n_strands, method="dynnikov"):
    """2 つの組紐語が同じ組紐か(関係式だけで移り合うか)。

    method: ``"dynnikov"``(座標を比べる、速い)/ ``"handle"``(a b⁻¹ を取っ手簡約して空か)/ ``"artin"``(自由群の像を
    比べる)/ ``"all"``(3 つとも計算し、食い違えば RuntimeError —— 実装の検査)。

    Returns: dict ``equal``、``method``、``key_a`` / ``key_b``(Dynnikov の鍵)、``reduced_quotient``(a b⁻¹ の簡約、
    handle / all のとき)。
    """
    op = "braid_equivalent"
    n = _n_strands(n_strands, op)
    wa, wb = _word(word_a, n, op), _word(word_b, n, op)
    if method not in ("dynnikov", "handle", "artin", "all"):
        raise ValueError("%s: method must be 'dynnikov', 'handle', 'artin' or 'all', got %r" % (op, method))
    out = {"method": method}
    da, db = dynnikov_coordinates(wa, n), dynnikov_coordinates(wb, n)
    out["key_a"], out["key_b"] = da["key"], db["key"]
    verdicts = {}
    if method in ("dynnikov", "all"):
        verdicts["dynnikov"] = da["key"] == db["key"]
    if method in ("handle", "all"):
        q = _handle_reduce(wa + [-x for x in reversed(wb)], op)
        out["reduced_quotient"] = np.asarray(q, dtype=np.int64)
        verdicts["handle"] = len(q) == 0
    if method in ("artin", "all"):
        verdicts["artin"] = braid_artin_images(wa, n)["images"] == braid_artin_images(wb, n)["images"]
    if len(set(verdicts.values())) != 1:
        raise RuntimeError("%s: the implementations disagree: %r" % (op, verdicts))
    out["equal"] = bool(next(iter(verdicts.values())))
    out["verdicts"] = verdicts
    return out


def homotopy_class_compare(traj_a, traj_b, obstacles=None, angle=DEFAULT_ANGLE, tol=1e-9, jitter="auto"):
    """始点と終点が同じ 2 つの経路族(複数エージェントの計画)が、同じホモトピー類か。

    衝突せずに(エージェント同士も障害物の点とも重ならずに)始点と終点を止めたまま連続に変形できる ⇔ 組紐が等しい。
    組紐は :func:`braid_from_trajectories`、比較は Dynnikov 座標。射影の角度に依らない(門で複数の角度を振る)。

    Returns: dict ``same``、``word_a`` / ``word_b``、``key_a`` / ``key_b``、``quotient``(a b⁻¹ を簡約した語 —— 空なら同じ類、
    空でなければ「どう回り方が違うか」の語)、``endpoint_error``(始点・終点の最大のずれ)。
    Raises: ValueError(台数が違う、始点か終点が ``tol`` より離れている、衝突)。
    """
    op = "homotopy_class_compare"
    A, B = _as_traj(traj_a, op), _as_traj(traj_b, op)
    if A.shape[0] != B.shape[0]:
        raise ValueError("%s: the two plans have %d and %d agents" % (op, A.shape[0], B.shape[0]))
    err = max(float(np.max(np.abs(A[:, 0] - B[:, 0]))), float(np.max(np.abs(A[:, -1] - B[:, -1]))))
    if not err <= float(tol):
        raise ValueError("%s: start / goal positions differ by %.3g (> tol %.3g) — homotopy classes compare plans "
                         "with the same endpoints" % (op, err, tol))
    (ba, bb), clear = _braids_consistent([A, B], obstacles, _angle(angle, op), jitter, op)
    if not np.array_equal(ba["start_order"], bb["start_order"]):
        raise ValueError("%s: the start order along the projection differs (two strands tie within tol); pass another "
                         "angle" % op)
    n = ba["n_strands"]
    da, db = dynnikov_coordinates(ba["word"], n), dynnikov_coordinates(bb["word"], n)
    q = _handle_reduce(ba["word"].tolist() + [-x for x in reversed(bb["word"].tolist())], op)
    same = da["key"] == db["key"]
    if same != (len(q) == 0):
        raise RuntimeError("%s: Dynnikov and handle reduction disagree (same=%s, |quotient|=%d)" % (op, same, len(q)))
    return {"same": bool(same), "word_a": ba["word"], "word_b": bb["word"], "key_a": da["key"], "key_b": db["key"],
            "quotient": np.asarray(q, dtype=np.int64), "endpoint_error": err, "n_strands": n, "clearance": clear,
            "jitter": ba["jitter"]}


# ======================================================================================================================
# 6. 巻き数
def pairwise_winding(trajectories, obstacles=None):
    """紐の対ごとの相対の巻き数 [回転] (相対ベクトルの偏角の総変化 / 2π)。対称行列、対角は 0。

    偏角の増分は atan2(外積, 内積) で取る(主値 (−π, π])。1 刻みで半回転以上回ると向きが決まらないので止める。
    閉形式: 純粋な組紐では 2 本の間の交差の符号つきの数を c として 2π·W = π c ちょうど(門)。巻き数は可換な
    不変量なので、交換子 [A, B] の形の組紐(全部の対で巻き数 0 なのに自明でない)を区別できない —— それが組紐を使う理由。

    Returns: (n, n) の float 配列(n = エージェント + 障害物の点)。
    Raises: ValueError(2 本が同じ点に来る、1 刻みの増分が π に届く —— 刻みを細かく)。
    """
    op = "pairwise_winding"
    S, _K = _strands(trajectories, obstacles, op)
    n = S.shape[0]
    W = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = S[j] - S[i]
            r2 = np.einsum("ij,ij->i", d, d)
            if np.any(r2 == 0.0):
                raise ValueError("%s: strands %d and %d meet at step %d" % (op, i, j, int(np.flatnonzero(r2 == 0.0)[0])))
            cr = d[:-1, 0] * d[1:, 1] - d[:-1, 1] * d[1:, 0]
            dt = d[:-1, 0] * d[1:, 0] + d[:-1, 1] * d[1:, 1]
            inc = np.arctan2(cr, dt)
            if inc.size and np.max(np.abs(inc)) >= math.pi - 1e-9:
                k = int(np.argmax(np.abs(inc)))
                raise ValueError("%s: strands %d and %d turn by >= pi between steps %d and %d — refine the sampling"
                                 % (op, i, j, k, k + 1))
            W[i, j] = W[j, i] = float(np.sum(inc)) / (2.0 * math.pi)
    return W


# ======================================================================================================================
# 7. 格子の上で類ごとの最短経路(類で持ち上げた Dijkstra)
_MOVES4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def grid_hole_points(grid) -> np.ndarray:
    """格子の穴(外周に触れない、塞がったマスの連結成分)ごとに代表の点を 1 つ: 重心に最も近い塞がったマスの中心 [x, y]。

    外周に触れる塞がりは外の世界とつながっているので穴にならない(経路の類を増やさない)。4 連結(移動と同じ)。
    """
    from scipy import ndimage

    g = np.asarray(grid).astype(bool)
    lab, nl = ndimage.label(~g, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    pts = []
    for k in range(1, nl + 1):
        if k in border:
            continue
        rr, cc = np.nonzero(lab == k)
        r0, c0 = rr.mean(), cc.mean()
        m = int(np.argmin((rr - r0) ** 2 + (cc - c0) ** 2))
        pts.append((float(cc[m]), -float(rr[m])))
    return np.asarray(pts, dtype=float).reshape(-1, 2)


def homotopy_shortest_paths(grid, start, goal, k=4, obstacles=None, angle=DEFAULT_ANGLE, max_states=400_000,
                            max_cost=None):
    """格子(True = 走れる、4 近傍)の上で、start から goal へのホモトピー類の違う最短経路を短い順に k 本。

    状態 = (マス, 組紐の Dynnikov 座標)。障害物の点を動かない紐として、1 手ごとに交差の文字を足して座標を更新する
    (座標は類の完全な不変量なので、同じ (マス, 座標) は 1 回しか開かない)。Dijkstra がこの「類で持ち上げた」格子を
    費用の順に開くので、goal に新しい座標で着いた順が、類ごとの最短経路の短い順になる。

    Parameters
    ----------
    obstacles : 穴の代表の点 (M, 2)。省略すると :func:`grid_hole_points`(外周に触れない塞がりの成分ごとに 1 点)。
    max_states / max_cost : 開く状態の数・費用の上限(類は無限にある —— 穴のまわりを何周でも回れる)。

    Returns: dict ``paths``(各類の (L, 2) の (row, col) の列、短い順)、``costs``、``words``(障害物と合わせた組紐語)、
    ``keys``、``obstacles``、``states``(開いた状態の数)、``complete``(k 本そろったか)。
    """
    op = "homotopy_shortest_paths"
    g = np.asarray(grid)
    if g.ndim != 2 or g.size == 0:
        raise ValueError("%s: grid must be a non-empty 2-D array (True = free)" % op)
    g = g.astype(bool)
    k = _int(k, "k", op, lo=1)
    th = _angle(angle, op)
    s0 = tuple(_int(v, "start", op) for v in start)
    g0 = tuple(_int(v, "goal", op) for v in goal)
    for name, p in (("start", s0), ("goal", g0)):
        if len(p) != 2 or not (0 <= p[0] < g.shape[0] and 0 <= p[1] < g.shape[1]) or not g[p]:
            raise ValueError("%s: %s %r is not a free cell of the %dx%d grid" % (op, name, p, *g.shape))
    O = grid_hole_points(g) if obstacles is None else np.asarray(obstacles, dtype=float).reshape(-1, 2)
    if O.shape[0] == 0:
        raise ValueError("%s: no holes — every path is in the same class (add obstacle points or a closed obstacle)" % op)
    max_cost = float("inf") if max_cost is None else float(max_cost)
    c, s = math.cos(th), math.sin(th)
    ox = [float(x * c + y * s) for x, y in O]
    oy = [float(-x * s + y * c) for x, y in O]
    M = len(ox)

    def proj(cell):
        x, y = float(cell[1]), -float(cell[0])
        return x * c + y * s, -x * s + y * c

    # 紐 0 = エージェント、1..M = 障害物。始めの順と、エージェントの位置(rank)。
    x0, y0 = proj(s0)
    for m in range(M):
        if ox[m] == x0 and oy[m] == y0:
            raise ValueError("%s: start sits on obstacle point %d" % (op, m))
    order0 = _lex_order([x0] + ox, [y0] + oy)
    n = M + 1

    def step(cell, nxt, rank):
        """エージェントが cell → nxt に動く間の文字(障害物は止まっている)。返り: (文字の list, 新しい rank)。"""
        xa, ya = proj(cell)
        xb, yb = proj(nxt)
        ev = []
        for m in range(M):
            dx0, dy0, dx1, dy1 = xa - ox[m], ya - oy[m], xb - ox[m], yb - oy[m]
            sa, sb = _sgn(dx0, dy0), _sgn(dx1, dy1)
            if sa == 0 or sb == 0:
                raise ValueError("%s: the path touches obstacle point %d (put the point inside a blocked cell)" % (op, m))
            if sa == sb:
                continue
            t = 0.0 if dx0 == dx1 else min(max(dx0 / (dx0 - dx1), 0.0), 1.0)
            dy = dy0 + t * (dy1 - dy0)
            if dy == 0.0:
                raise ValueError("%s: the path passes through obstacle point %d" % (op, m))
            ev.append((t, sa, dy))
        ev.sort(key=lambda e: e[0])
        for e0, e1 in zip(ev, ev[1:]):
            if e1[0] - e0[0] <= _T_TIE:
                raise ValueError("%s: two obstacle points share a projection line (simultaneous crossings); pass another angle" % op)
        letters = []
        for _t, sa, dy in ev:
            if sa < 0:                       # エージェントが左 → 右へ: 位置 rank と rank+1 の入れ替え
                pos = rank + 1
                letters.append(pos if dy < 0 else -pos)
                rank += 1
            else:                            # 右 → 左: 位置 rank-1 と rank(左の紐 = 障害物)
                pos = rank
                letters.append(pos if dy > 0 else -pos)   # 障害物(左)が下 ⇔ エージェントが上
                rank -= 1
        return letters, rank

    r0 = order0.index(0)
    a0, b0 = [0] * (n - 1), [-1] * (n - 1)
    key0 = (s0, r0, tuple(a0) + tuple(b0))
    dist = {key0: 0}
    parent = {key0: None}
    words_at = {key0: ()}
    tie = itertools.count()
    heap = [(0, next(tie), key0)]
    found = []
    seen_goal = set()
    opened = 0
    while heap and len(found) < k:
        d, _, st = heapq.heappop(heap)
        if d > dist.get(st, float("inf")):
            continue
        opened += 1
        if opened > max_states or d > max_cost:
            break
        cell, rank, key = st
        if cell == g0 and key not in seen_goal:
            seen_goal.add(key)
            path = []
            cur = st
            while cur is not None:
                path.append(cur[0])
                cur = parent[cur]
            found.append((d, path[::-1], words_at[st], key))
            if len(found) >= k:
                break
        h = len(key) // 2
        for dr, dc in _MOVES4:
            nxt = (cell[0] + dr, cell[1] + dc)
            if not (0 <= nxt[0] < g.shape[0] and 0 <= nxt[1] < g.shape[1]) or not g[nxt]:
                continue
            letters, nrank = step(cell, nxt, rank)
            if letters:
                a, b = list(key[:h]), list(key[h:])
                _act(a, b, letters)
                nkey = tuple(a) + tuple(b)
            else:
                nkey = key
            ns = (nxt, nrank, nkey)
            nd = d + 1
            if nd < dist.get(ns, float("inf")):
                dist[ns] = nd
                parent[ns] = st
                words_at[ns] = words_at[st] + tuple(letters)
                heapq.heappush(heap, (nd, next(tie), ns))
    return {"paths": [np.asarray(p, dtype=np.int64) for _d, p, _w, _k in found],
            "costs": np.asarray([d for d, *_ in found], dtype=float),
            "words": [np.asarray(w, dtype=np.int64) for _d, _p, w, _k in found],
            "keys": [kk for *_, kk in found], "obstacles": O, "n_strands": n, "states": opened,
            "complete": len(found) >= k}


# ======================================================================================================================
# 8. 候補を類に分ける
def _plan_cost(P: np.ndarray) -> float:
    return float(np.sum(np.hypot(*np.diff(P, axis=1).transpose(2, 0, 1))))


def braid_class_representatives(plans, obstacles=None, costs=None, angle=DEFAULT_ANGLE, jitter="auto"):
    """複数の計画(どの計画器の出力でもよい)をホモトピー類に分け、類ごとに費用の最も小さい計画を代表に選ぶ。

    計画は (K, T, 2) の軌道か、格子の経路の列か、計画器の dict(``paths``、失敗した ``None`` は飛ばして数える)。
    全部の計画の始点と終点がそろっている必要がある(類は端を止めた変形の類)。費用は ``costs`` か、なければ軌道の
    長さの和。

    Returns: dict ``classes``(費用の安い順の list、各要素 dict: ``key``・``word``(代表の語)・``best``(計画の番号)・
    ``cost``・``count``・``members``)、``n_plans``、``n_failed``、``n_classes``。
    """
    op = "braid_class_representatives"
    if plans is None or len(plans) == 0:
        raise ValueError("%s: no plans" % op)
    if costs is not None and len(costs) != len(plans):
        raise ValueError("%s: costs has %d entries for %d plans" % (op, len(costs), len(plans)))
    trajs, idx, failed = [], [], 0
    for i, p in enumerate(plans):
        if p is None or (isinstance(p, dict) and p.get("paths") is None):
            failed += 1
            continue
        trajs.append(_as_traj(p, op))
        idx.append(i)
    if not trajs:
        raise ValueError("%s: every plan failed (None)" % op)
    T0 = trajs[0]
    for P, i in zip(trajs, idx):
        if P.shape[0] != T0.shape[0] or not (np.allclose(P[:, 0], T0[:, 0]) and np.allclose(P[:, -1], T0[:, -1])):
            raise ValueError("%s: plan %d has other endpoints than plan %d" % (op, i, idx[0]))
    classes: dict = {}
    brs, clear = _braids_consistent(trajs, obstacles, _angle(angle, op), jitter, op)
    for P, i, br in zip(trajs, idx, brs):
        key = dynnikov_coordinates(br["word"], br["n_strands"])["key"]
        cst = float(costs[i]) if costs is not None else _plan_cost(P)
        e = classes.setdefault(key, {"key": key, "members": [], "best": i, "cost": cst, "word": br["word"]})
        e["members"].append(i)
        if cst < e["cost"]:
            e["best"], e["cost"], e["word"] = i, cst, br["word"]
    out = sorted(classes.values(), key=lambda e: (e["cost"], e["best"]))
    for e in out:
        e["count"] = len(e["members"])
        e["word"] = np.asarray(_handle_reduce(e["word"].tolist(), op), dtype=np.int64)
    return {"classes": out, "n_plans": len(plans), "n_failed": failed, "n_classes": len(out), "clearance": clear,
            "jitter": brs[0]["jitter"]}
