# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""agvfleet —— 工場・倉庫の AGV の群れ: 格子の上の複数台の経路計画と、遅れても詰まらない実行。

AGV の現場で止まる原因の上位は「複数台の交通」—— 交差点・狭い通路での**デッドロック**と、計画どおりに
走れない(滑り・人・荷役で遅れる)ときの**連鎖的な詰まり**である。ここでは床の格子(QR / AprilTag の
格子航法、Amazon の Kiva 型)を走る車両を対象に、古典的で**性質が定理として言える**手法だけを置く:

* :func:`mapf_cbs` —— Conflict-Based Search(Sharon ら 2015)。総コスト(sum of costs)が**最適**。
* :func:`mapf_joint_astar` —— 全台の位置を 1 つの状態にした A*。遅いが最適の**第 2 実装**(門の真値)。
* :func:`mapf_prioritized` —— 優先度付き計画(予約表)。速いが**不完全**(解があるのに見つけられない)。
* :func:`adg_build` / :func:`adg_execute` —— 行動依存グラフ(Action Dependency Graph、Hönig ら 2019)。
  計画が衝突なしなら、どの車両がどれだけ遅れても**衝突もデッドロックも起きない**。
* :func:`naive_execute` —— 比較用の素朴な実行(次のマスが空いていれば進む)。遅れで詰まる。
* :func:`vda5050_order` / :func:`vda5050_check` —— 計画を VDA 5050(v3.0.0、MIT)の order にし、仕様の規則
  (ノードの sequenceId は偶数・エッジは奇数・エッジ数 = ノード数 − 1 …)を検査する。

座標は格子の ``(row, col)``。1 手 = 4 近傍への移動か、その場の待ち。時刻は整数。

★衝突の定義は 3 種類: 同じマス(vertex)・すれ違い(edge)・**追従**(follow = 1 手前に他車が居たマスへ入る)。
追従を禁じるのは、実車は前の車が抜けた同じ瞬間にそのマスへ入れない(車間ゼロ)からで、これを許すと
3 台以上の**回転**(輪になって同時に 1 マスずつ回る)が「衝突なし」になり、行動依存グラフで実行すると
互いに相手の退出を待って詰まる。CBS・結合 A*・優先度付き計画のすべてが同じ定義を使う(最適性の比較が同じ問題になるように)。
運転の部品と同じく**ルールベースだけ**(学習した方策は使わない)。
"""
from __future__ import annotations

import heapq
import itertools
from collections import deque

import numpy as np

__all__ = [
    "warehouse_grid", "grid_distances", "mapf_cbs", "mapf_ecbs", "mapf_joint_astar", "mapf_prioritized",
    "plan_conflicts", "plan_cost", "adg_build", "adg_execute", "naive_execute",
    "vda5050_order", "vda5050_check",
]

_MOVES = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))     # 待ち・上・下・左・右


# --------------------------------------------------------------------------- #
# 地図
# --------------------------------------------------------------------------- #
def _free(grid):
    g = np.asarray(grid)
    if g.ndim != 2 or g.size == 0:
        raise ValueError("grid must be a non-empty 2-D array (True / 1 = free cell), got shape %s" % (g.shape,))
    return g.astype(bool)


def warehouse_grid(n_rack_rows=3, n_rack_cols=4, rack_len=4, aisle=1, margin=2):
    """棚の列と通路でできた倉庫の格子(True = 走れる)。

    棚は横長の 1 行 × ``rack_len`` マスのブロックで、上下左右を幅 ``aisle`` の通路が囲む。外周に ``margin``
    マスの走行帯(ステーションの前)を置く。返りは ``(grid, info)``、info に棚のマスの一覧と外周の帯。
    """
    for name, v in (("n_rack_rows", n_rack_rows), ("n_rack_cols", n_rack_cols), ("rack_len", rack_len),
                    ("aisle", aisle), ("margin", margin)):
        if int(v) < 1:
            raise ValueError("%s must be >= 1, got %r" % (name, v))
    h = 2 * margin + n_rack_rows + (n_rack_rows - 1) * aisle
    w = 2 * margin + n_rack_cols * rack_len + (n_rack_cols - 1) * aisle
    g = np.ones((h, w), dtype=bool)
    racks = []
    for i in range(n_rack_rows):
        r = margin + i * (1 + aisle)
        for j in range(n_rack_cols):
            c0 = margin + j * (rack_len + aisle)
            g[r, c0:c0 + rack_len] = False
            racks.extend((r, c) for c in range(c0, c0 + rack_len))
    return g, {"racks": racks, "shape": g.shape}


def grid_distances(grid, goal):
    """``goal`` までの格子上の最短手数(BFS、障害物は通れない)。届かないマスは ``inf``。"""
    g = _free(grid)
    r0, c0 = map(int, goal)
    if not g[r0, c0]:
        raise ValueError("goal %r is not a free cell" % (goal,))
    d = np.full(g.shape, np.inf)
    d[r0, c0] = 0
    q = deque([(r0, c0)])
    while q:
        r, c = q.popleft()
        for dr, dc in _MOVES[1:]:
            rr, cc = r + dr, c + dc
            if 0 <= rr < g.shape[0] and 0 <= cc < g.shape[1] and g[rr, cc] and d[rr, cc] == np.inf:
                d[rr, cc] = d[r, c] + 1
                q.append((rr, cc))
    return d


def _check_agents(g, starts, goals):
    S = [tuple(map(int, s)) for s in starts]
    G = [tuple(map(int, s)) for s in goals]
    if len(S) != len(G) or not S:
        raise ValueError("starts and goals must be non-empty and the same length (%d vs %d)" % (len(S), len(G)))
    for name, pts in (("start", S), ("goal", G)):
        for p in pts:
            if not (0 <= p[0] < g.shape[0] and 0 <= p[1] < g.shape[1]) or not g[p]:
                raise ValueError("%s %r is not a free cell of the %dx%d grid" % (name, p, *g.shape))
        if len(set(pts)) != len(pts):
            raise ValueError("two agents share a %s cell: %r" % (name, pts))
    return S, G


# --------------------------------------------------------------------------- #
# 計画の検査と費用
# --------------------------------------------------------------------------- #
def _at(path, t):
    return path[t] if t < len(path) else path[-1]


def plan_cost(paths):
    """総コスト(sum of costs): 各車両が**最後に**目的地へ着いた時刻の和(着いた後に動かないこと)。"""
    total = 0
    for p in paths:
        k = len(p) - 1
        while k > 0 and p[k - 1] == p[-1]:
            k -= 1
        total += k
    return int(total)


def plan_conflicts(paths):
    """衝突の一覧: 同じ時刻に同じマス(vertex)・すれ違い(edge)・追従(follow)。

    返りは ``[(種類, i, j, 時刻, マス)]``。着いた車両はその場に居続けるものとして数える。
    follow は「i が時刻 t にマス v へ**入った**とき、j が t-1 に v に居た」(i ≠ j)。
    """
    out = []
    T = max(len(p) for p in paths)
    for t in range(T):
        seen = {}
        for i, p in enumerate(paths):
            v = _at(p, t)
            if v in seen:
                out.append(("vertex", seen[v], i, t, v))
            else:
                seen[v] = i
        if t == 0:
            continue
        for i, j in itertools.combinations(range(len(paths)), 2):
            a0, a1 = _at(paths[i], t - 1), _at(paths[i], t)
            b0, b1 = _at(paths[j], t - 1), _at(paths[j], t)
            if a0 == b1 and a1 == b0 and a0 != a1:
                out.append(("edge", i, j, t, (a0, a1)))
        for i in range(len(paths)):
            a0, a1 = _at(paths[i], t - 1), _at(paths[i], t)
            if a0 == a1:
                continue
            for j in range(len(paths)):
                if j != i and _at(paths[j], t - 1) == a1 and _at(paths[j], t) != a1:
                    out.append(("follow", i, j, t, a1))     # j は t に出て、i が同じ t に入った
    return out


# --------------------------------------------------------------------------- #
# 1 台の時空間 A*(CBS と PP の下段)
# --------------------------------------------------------------------------- #
def _st_astar(g, start, goal, dist, vcons, econs, horizon, reserved_goal_from=None, others=None):
    """時空間 A*。``vcons`` = {(マス, t)} 通れない、``econs`` = {(from, to, t)} t-1→t の移動禁止。

    目的地では「その時刻以降に vcons が無い」ときだけ終われる(着いた後に居座れる)。
    ``reserved_goal_from`` = {マス: t0}: 他車が t0 以降ずっと居座るマス(PP 用、通れない)。
    ``others`` = 他車の経路の列(衝突回避表)。同じ長さの経路のうち、他車と**ぶつかる回数が少ない**ものを選ぶ
    (CBS の標準の改良。長さ = 費用は変えないので最適性は保たれる)。
    """
    if dist[start] == np.inf:
        return None
    if (start, 0) in vcons:
        # 「時刻 0 に出発マスに居るな」は満たせない(追従の枝で付く)。ここで断らないと同じ経路を返し、
        # CBS は同じ衝突を解消できないまま木を育て続けた(2026-10-03、結合 A* との比較で発見)
        return None
    last_v = {}
    for (v, t) in vcons:
        if v == goal:
            last_v[v] = max(last_v.get(v, -1), t)
    goal_ok_from = last_v.get(goal, -1) + 1
    if reserved_goal_from and goal in reserved_goal_from:
        return None
    rsv = reserved_goal_from or {}
    occ = {}
    if others:
        for op in others:
            for tt in range(horizon + 2):
                occ.setdefault((_at(op, tt), tt), 0)
                occ[(_at(op, tt), tt)] += 1

    def clash(w, nt):
        # 同じ時刻に居る(vertex)か、1 手前に居た(追従)他車の数
        return occ.get((w, nt), 0) + occ.get((w, nt - 1), 0) if occ else 0

    parent = {(start, 0): None}
    best = {(start, 0): 0}
    closed = set()
    tie = itertools.count()
    openl = [(float(dist[start]), 0, 0, next(tie), start, 0)]
    while openl:
        f, nconf, gcost, _, v, t = heapq.heappop(openl)
        if (v, t) in closed:
            continue
        closed.add((v, t))
        if v == goal and t >= goal_ok_from:
            path = []
            node = (v, t)
            while node is not None:
                path.append(node[0])
                node = parent[node]
            return path[::-1]
        if t >= horizon:
            continue
        for dr, dc in _MOVES:
            w = (v[0] + dr, v[1] + dc)
            if not (0 <= w[0] < g.shape[0] and 0 <= w[1] < g.shape[1]) or not g[w]:
                continue
            nt = t + 1
            if (w, nt) in vcons or (v, w, nt) in econs:
                continue
            if w in rsv and nt >= rsv[w]:
                continue
            key = (w, nt)
            nc = nconf + clash(w, nt)
            if key in closed or nc >= best.get(key, 1 << 30):
                continue
            best[key] = nc
            parent[key] = (v, t)
            heapq.heappush(openl, (nt + float(dist[w]), nc, nt, next(tie), w, nt))
    return None


# --------------------------------------------------------------------------- #
# CBS(最適)
# --------------------------------------------------------------------------- #
def mapf_cbs(grid, starts, goals, max_nodes=20000, horizon=None):
    """Conflict-Based Search(Sharon, Stern, Felner, Sturtevant 2015)。総コストが最適な衝突なしの計画。

    上段は「衝突を 1 つ選び、2 台のどちらかに制約を足す」二分木の最良優先探索、下段は 1 台の時空間 A*。
    返りは dict: ``paths``(各車両のマスの列)、``cost``(sum of costs)、``nodes``(展開した節の数)、
    ``solved``。節の上限に達したら ``solved=False``(**黙って最適でない解を返さない**)。
    """
    g = _free(grid)
    S, G = _check_agents(g, starts, goals)
    dists = [grid_distances(g, goal) for goal in G]
    H = int(horizon if horizon is not None else g.size + 4 * len(S))
    cons = [(frozenset(), frozenset()) for _ in S]
    paths = []
    for i in range(len(S)):
        p = _st_astar(g, S[i], G[i], dists[i], set(), set(), H, others=paths)
        if p is None:
            return {"paths": None, "cost": None, "nodes": 0, "solved": False}
        paths.append(p)
    tie = itertools.count()
    openl = [(plan_cost(paths), len(plan_conflicts(paths)), next(tie), cons, paths)]
    nodes = 0
    while openl and nodes < max_nodes:
        cost, _nc, _, cons, paths = heapq.heappop(openl)
        nodes += 1
        conf = plan_conflicts(paths)
        if not conf:
            return {"paths": paths, "cost": cost, "nodes": nodes, "solved": True}
        kind, i, j, t, v = min(conf, key=lambda c: c[3])          # いちばん早い衝突から分ける
        for a in (i, j):
            vc, ec = cons[a]
            if kind == "vertex":
                vc = vc | {(v, t)}
            elif kind == "follow":
                # どの解も「i は t に v に居ない」か「j は t-1 に v に居ない」のどちらかを満たす
                vc = vc | ({(v, t)} if a == i else {(v, t - 1)})
            else:
                frm, to = (v[0], v[1]) if a == i else (v[1], v[0])
                ec = ec | {(frm, to, t)}
            newp = _st_astar(g, S[a], G[a], dists[a], vc, ec, H,
                             others=[p for b, p in enumerate(paths) if b != a])
            if newp is None:
                continue
            ncons = list(cons)
            ncons[a] = (vc, ec)
            npaths = list(paths)
            npaths[a] = newp
            heapq.heappush(openl, (plan_cost(npaths), len(plan_conflicts(npaths)), next(tie), ncons, npaths))
    return {"paths": None, "cost": None, "nodes": nodes, "solved": False}


def mapf_ecbs(grid, starts, goals, w=1.2, max_nodes=50000, horizon=None):
    """上段を焦点探索にした CBS(ECBS の上段と同じ考え方、Barer ら 2014)。総コストが **最適の w 倍以内**。

    開いている節のうち最小の総コスト ``LB`` は最適値以下(最適解はどれかの節の下にある)。そこで
    ``コスト ≤ w · LB`` の節(焦点)の中から**衝突の少ない**ものを展開する。返す計画は
    ``cost ≤ w · LB ≤ w · 最適``(門)。返りは :func:`mapf_cbs` の dict に ``lower_bound`` と ``w`` を足したもの。
    細い通路で最適の CBS が同じ長さの譲り合いの組を全部調べて止まるのを、衝突の少ない側へ寄せて抜ける。
    """
    if not w >= 1.0:
        raise ValueError("w must be >= 1 (w = 1 is optimal CBS), got %r" % (w,))
    g = _free(grid)
    S, G = _check_agents(g, starts, goals)
    dists = [grid_distances(g, goal) for goal in G]
    H = int(horizon if horizon is not None else g.size + 4 * len(S))
    paths = []
    for i in range(len(S)):
        p = _st_astar(g, S[i], G[i], dists[i], set(), set(), H, others=paths)
        if p is None:
            return {"paths": None, "cost": None, "nodes": 0, "solved": False, "lower_bound": None, "w": w}
        paths.append(p)
    nodes_store = {}
    tie = itertools.count()
    open_h, focal_h = [], []

    def push(cons, pths):
        nid = next(tie)
        c, k = plan_cost(pths), len(plan_conflicts(pths))
        nodes_store[nid] = (c, k, cons, pths)
        heapq.heappush(open_h, (c, k, nid))
        return nid

    def lb():
        while open_h and open_h[0][2] not in nodes_store:
            heapq.heappop(open_h)
        return open_h[0][0] if open_h else None

    push([(frozenset(), frozenset()) for _ in S], paths)
    expanded = 0
    in_focal = set()
    while nodes_store and expanded < max_nodes:
        low = lb()
        for c, k, nid in list(open_h):                 # 焦点へ入る節(コスト ≤ w·LB)を足す
            if nid in nodes_store and nid not in in_focal and c <= w * low + 1e-9:
                heapq.heappush(focal_h, (k, c, nid))
                in_focal.add(nid)
        while focal_h and focal_h[0][2] not in nodes_store:
            heapq.heappop(focal_h)
        if not focal_h:
            break
        k, c, nid = heapq.heappop(focal_h)
        cost, _k, cons, pths = nodes_store.pop(nid)
        in_focal.discard(nid)
        expanded += 1
        conf = plan_conflicts(pths)
        if not conf:
            return {"paths": pths, "cost": cost, "nodes": expanded, "solved": True, "lower_bound": low, "w": w}
        kind, i, j, t, v = min(conf, key=lambda q: q[3])
        for a in (i, j):
            vc, ec = cons[a]
            if kind == "vertex":
                vc = vc | {(v, t)}
            elif kind == "follow":
                vc = vc | ({(v, t)} if a == i else {(v, t - 1)})
            else:
                frm, to = (v[0], v[1]) if a == i else (v[1], v[0])
                ec = ec | {(frm, to, t)}
            newp = _st_astar(g, S[a], G[a], dists[a], vc, ec, H, others=[p for b, p in enumerate(pths) if b != a])
            if newp is None:
                continue
            ncons = list(cons)
            ncons[a] = (vc, ec)
            npaths = list(pths)
            npaths[a] = newp
            push(ncons, npaths)
    return {"paths": None, "cost": None, "nodes": expanded, "solved": False, "lower_bound": lb(), "w": w}


# --------------------------------------------------------------------------- #
# 全台の結合 A*(第 2 実装・最適の真値)
# --------------------------------------------------------------------------- #
def mapf_joint_astar(grid, starts, goals, max_expansions=2_000_000):
    """全台の位置を 1 つの状態にした A*。**小さな問題専用**の最適解(CBS の門の真値)。

    sum of costs を厳密に数えるため、各車両に「終わった(以後は目的地に居続ける)」の旗を持たせる:
    目的地に居る車両はその手の前に終わってよく、1 手の費用 = まだ終わっていない台数。
    ヒューリスティック = 終わっていない車両の BFS 距離の和(許容的)。
    """
    g = _free(grid)
    S, G = _check_agents(g, starts, goals)
    n = len(S)
    dists = [grid_distances(g, goal) for goal in G]
    if any(dists[i][S[i]] == np.inf for i in range(n)):
        return {"paths": None, "cost": None, "solved": False, "expanded": 0}

    def h(pos, fin):
        return sum(0 if fin[i] else dists[i][pos[i]] for i in range(n))

    start = (tuple(S), (False,) * n)
    tie = itertools.count()
    openl = [(h(*start), 0, next(tie), start)]
    best = {start: 0}
    parent = {start: None}
    expanded = 0
    while openl:
        f, cost, _, state = heapq.heappop(openl)
        if cost > best.get(state, np.inf):
            continue
        pos, fin = state
        if all(fin):
            seq = []
            s = state
            while s is not None:
                seq.append(s[0])
                s = parent[s]
            seq = seq[::-1]
            paths = [[seq[t][i] for t in range(len(seq))] for i in range(n)]
            return {"paths": paths, "cost": int(cost), "solved": True, "expanded": expanded}
        expanded += 1
        if expanded > max_expansions:
            break
        # 終わる/終わらないの選び方(目的地に居る未了の車両だけが選べる)
        can = [i for i in range(n) if not fin[i] and pos[i] == G[i]]
        for k in range(len(can) + 1):
            for chosen in itertools.combinations(can, k):
                nfin = tuple(fin[i] or (i in chosen) for i in range(n))
                active = [i for i in range(n) if not nfin[i]]
                if not active:
                    ns = (pos, nfin)
                    if cost < best.get(ns, np.inf):
                        best[ns] = cost
                        parent[ns] = state
                        heapq.heappush(openl, (cost, cost, next(tie), ns))
                    continue
                options = []
                for i in active:
                    opts = []
                    for dr, dc in _MOVES:
                        w = (pos[i][0] + dr, pos[i][1] + dc)
                        if 0 <= w[0] < g.shape[0] and 0 <= w[1] < g.shape[1] and g[w]:
                            opts.append(w)
                    options.append(opts)
                for combo in itertools.product(*options):
                    npos = list(pos)
                    for i, w in zip(active, combo):
                        npos[i] = w
                    if len(set(npos)) < n:
                        continue
                    # 追従の禁止(すれ違いと回転も含む): 動いた車両は、1 手前に他車が居たマスへ入れない
                    if any(npos[a] != pos[a] and npos[a] == pos[b]
                           for a in range(n) for b in range(n) if a != b):
                        continue
                    ns = (tuple(npos), nfin)
                    nc = cost + len(active)
                    if nc < best.get(ns, np.inf):
                        best[ns] = nc
                        parent[ns] = state
                        heapq.heappush(openl, (nc + h(*ns), nc, next(tie), ns))
    return {"paths": None, "cost": None, "solved": False, "expanded": expanded}


# --------------------------------------------------------------------------- #
# 優先度付き計画(不完全)
# --------------------------------------------------------------------------- #
def mapf_prioritized(grid, starts, goals, order=None, horizon=None):
    """優先度付き計画: 順に 1 台ずつ、先に決まった車両の通り道(予約表)を避けて計画する。

    速いが**不完全** —— 解がある問題でも、優先順によっては(どの順でも)見つけられない(Ma ら 2019)。
    返りは dict: ``paths``(失敗なら None)、``cost``、``solved``、``failed_agent``(最初に詰まった車両)。
    """
    g = _free(grid)
    S, G = _check_agents(g, starts, goals)
    n = len(S)
    order = list(range(n)) if order is None else [int(i) for i in order]
    if sorted(order) != list(range(n)):
        raise ValueError("order must be a permutation of 0..%d, got %r" % (n - 1, order))
    H = int(horizon if horizon is not None else g.size + 4 * n)
    vcons, econs, goal_from = set(), set(), {}
    paths = [None] * n
    for a in order:
        p = _st_astar(g, S[a], G[a], grid_distances(g, G[a]), vcons, econs, H, reserved_goal_from=goal_from)
        if p is None:
            return {"paths": None, "cost": None, "solved": False, "failed_agent": a}
        paths[a] = p
        for t, v in enumerate(p):
            vcons.add((v, t))
            vcons.add((v, t + 1))                     # 追従の禁止: 出た直後の時刻にも入れない
            if t and p[t - 1] != v:
                vcons.add((v, t - 1))                 # 入ってくる直前の時刻に居てはいけない
                econs.add((v, p[t - 1], t))           # 逆向きの入れ替えを禁止
        goal_from[p[-1]] = len(p) - 1
        if len(p) >= 2 and p[-2] != p[-1]:
            vcons.add((p[-1], len(p) - 2))
        # 着いた後も居座る: 先の時刻の vertex も塞ぐのは goal_from で表す
    return {"paths": paths, "cost": plan_cost(paths), "solved": True, "failed_agent": None}


# --------------------------------------------------------------------------- #
# 行動依存グラフ(遅れても詰まらない実行)
# --------------------------------------------------------------------------- #
def _compress(path):
    """待ちを除いた「訪れるマスの列」と、各マスに入った計画上の時刻。"""
    cells, times = [path[0]], [0]
    for t in range(1, len(path)):
        if path[t] != cells[-1]:
            cells.append(path[t])
            times.append(t)
    return cells, times


def adg_build(paths):
    """行動依存グラフ(Hönig, Kiesel, Tinka, Durham, Ayanian 2019)。

    各車両の行動 = 「訪れるマスの列の k 番目に入る」。依存は 2 種類:
    (1) 同じ車両の前の行動、(2) **同じマスを先に使う他車がそのマスを出ること**(計画の時刻順)。
    返りは dict: ``cells``(各車両のマスの列)、``deps``(``(i, k)`` → それより先に終わるべき ``(j, m)`` の集合)。
    計画に衝突があれば ValueError(依存の向きが決まらない)。
    """
    conf = plan_conflicts(paths)
    if conf:
        raise ValueError("the plan has %d conflict(s) (first: %r); an ADG needs a collision-free plan" % (len(conf), conf[0]))
    comp = [_compress(p) for p in paths]
    deps = {}
    visits = {}                                        # マス → [(入った時刻, 車両, k)]
    for i, (cells, times) in enumerate(comp):
        for k, (v, t) in enumerate(zip(cells, times)):
            visits.setdefault(v, []).append((t, i, k))
            deps[(i, k)] = {(i, k - 1)} if k else set()
    for v, lst in visits.items():
        lst.sort()
        for a in range(len(lst)):
            ta, i, k = lst[a]
            for b in range(a + 1, len(lst)):
                tb, j, m = lst[b]
                if i == j:
                    continue
                # j が v に入る(m)前に、i が v を出る = i の次の行動(k+1)が済んでいること
                cells_i = comp[i][0]
                if k + 1 < len(cells_i):
                    deps[(j, m)].add((i, k + 1))
                else:
                    raise ValueError("agent %d ends at %r but agent %d enters it later — the plan is not "
                                     "collision-free for parked agents" % (i, v, j))
    return {"cells": [c for c, _ in comp], "deps": deps}


def adg_execute(adg, delay_prob=0.3, seed=0, max_steps=10000):
    """ADG に従って実行する。各時刻、各車両は確率 ``delay_prob`` で止まる(滑り・人・荷役の遅れ)。

    次の行動の依存がすべて済んでいる車両だけが 1 マス進む。返りは dict: ``trajectories``(実際の位置の列)、
    ``makespan``、``collisions``(同じマス・すれ違い)、``deadlock``(誰も進めず未了)、``finished``。
    """
    rng = np.random.default_rng(int(seed))
    cells, deps = adg["cells"], adg["deps"]
    n = len(cells)
    k = [0] * n                                         # 各車両の済んだ行動の番号
    traj = [[c[0]] for c in cells]
    collisions = 0
    for step in range(int(max_steps)):
        if all(k[i] == len(cells[i]) - 1 for i in range(n)):
            return {"trajectories": traj, "makespan": step, "collisions": collisions, "deadlock": False, "finished": True}
        ready = []
        for i in range(n):
            nk = k[i] + 1
            if nk < len(cells[i]) and all(k[j] >= m for (j, m) in deps[(i, nk)]):
                ready.append(i)
        progressed = False
        moved = [i for i in ready if rng.random() >= delay_prob]
        prev = [cells[i][k[i]] for i in range(n)]
        for i in moved:
            k[i] += 1
            progressed = True
        now = [cells[i][k[i]] for i in range(n)]
        collisions += len(now) - len(set(now))
        collisions += sum(1 for a in range(n) for b in range(a + 1, n)
                          if now[a] == prev[b] and now[b] == prev[a] and now[a] != prev[a])
        for i in range(n):
            traj[i].append(now[i])
        if not ready and not progressed:
            return {"trajectories": traj, "makespan": step, "collisions": collisions, "deadlock": True, "finished": False}
    return {"trajectories": traj, "makespan": int(max_steps), "collisions": collisions, "deadlock": False, "finished": False}


def naive_execute(paths, delay_prob=0.3, seed=0, max_steps=10000):
    """比較用の素朴な実行: 計画の**マスの列**だけを使い、次のマスが空いていれば進む(順番の約束は無い)。

    遅れが入ると、計画では時間差ですれ違うはずの 2 台が向かい合って止まる。返りは :func:`adg_execute` と
    同じ形に ``waits_for``(デッドロックの瞬間の「誰が誰を待つか」の辺)を足したもの。
    """
    rng = np.random.default_rng(int(seed))
    cells = [_compress(p)[0] for p in paths]
    n = len(cells)
    k = [0] * n
    traj = [[c[0]] for c in cells]
    for step in range(int(max_steps)):
        if all(k[i] == len(cells[i]) - 1 for i in range(n)):
            return {"trajectories": traj, "makespan": step, "collisions": 0, "deadlock": False, "finished": True,
                    "waits_for": []}
        occ = {cells[i][k[i]]: i for i in range(n)}
        want = {i: cells[i][k[i] + 1] for i in range(n) if k[i] + 1 < len(cells[i])}
        movable = [i for i, w in want.items() if w not in occ]
        if not movable:
            edges = [(i, occ[w]) for i, w in want.items() if w in occ]
            return {"trajectories": traj, "makespan": step, "collisions": 0, "deadlock": True, "finished": False,
                    "waits_for": edges}
        taken = set()
        for i in movable:
            if rng.random() < delay_prob or want[i] in taken:
                continue
            taken.add(want[i])
            k[i] += 1
        for i in range(n):
            traj[i].append(cells[i][k[i]])
    return {"trajectories": traj, "makespan": int(max_steps), "collisions": 0, "deadlock": False, "finished": False,
            "waits_for": []}


# --------------------------------------------------------------------------- #
# VDA 5050(v3.0.0, MIT)の order
# --------------------------------------------------------------------------- #
def vda5050_order(path, *, order_id="order-1", order_update_id=0, cell_size=1.0, map_id="floor",
                  allowed_xy=0.05, allowed_theta=0.087, max_speed=1.0, released_nodes=None):
    """1 台の計画(マスの列)を VDA 5050 の order(dict)にする。待ちは除き、マスの中心をノードにする。

    ノードの ``sequenceId`` は 0, 2, 4 …(偶数)、エッジは 1, 3, 5 …(奇数)、エッジ数 = ノード数 − 1。
    ``released_nodes`` 個までを base(released=True)、残りを horizon にする(既定 = 全部 base)。
    座標は ``x = col * cell_size``、``y = −row * cell_size``(行は下向き、地図の y は上向き)。
    """
    cells, _ = _compress(list(map(tuple, path)))
    nr = len(cells) if released_nodes is None else int(released_nodes)
    if not 1 <= nr <= len(cells):
        raise ValueError("released_nodes must be in 1..%d, got %r" % (len(cells), released_nodes))
    nodes, edges = [], []
    for k, (r, c) in enumerate(cells):
        nodes.append({"nodeId": "n%d_%d" % (r, c), "sequenceId": 2 * k, "released": k < nr,
                      "nodePosition": {"x": float(c * cell_size), "y": float(-r * cell_size), "mapId": map_id,
                                       "allowedDeviationXY": float(allowed_xy),
                                       "allowedDeviationTheta": float(allowed_theta)},
                      "actions": []})
        if k:
            a, b = cells[k - 1], cells[k]
            edges.append({"edgeId": "e%d_%d__%d_%d" % (a[0], a[1], b[0], b[1]), "sequenceId": 2 * k - 1,
                          "released": k < nr, "startNodeId": nodes[k - 1]["nodeId"], "endNodeId": nodes[k]["nodeId"],
                          "maxSpeed": float(max_speed), "actions": []})
    return {"headerId": 0, "timestamp": "1970-01-01T00:00:00.00Z", "version": "3.0.0", "manufacturer": "fullseye",
            "serialNumber": "agv", "orderId": order_id, "orderUpdateId": int(order_update_id),
            "nodes": nodes, "edges": edges}


def vda5050_check(order):
    """VDA 5050 の order の**構造の規則**を検査する(公式 JSON スキーマとは別の、自前の第 2 実装)。

    規則: 必須キー / ノードの sequenceId は 0 から偶数で連番、エッジは奇数で連番 / エッジ数 = ノード数 − 1 /
    各エッジの始点・終点が前後のノード / released は base の先頭から連続(base → horizon の 1 回の切替のみ)/
    エッジの released はその終点ノードと同じ。返りは違反の文言のリスト(空 = 合格)。
    """
    errs = []
    for key in ("headerId", "timestamp", "version", "manufacturer", "serialNumber", "orderId",
                "orderUpdateId", "nodes", "edges"):
        if key not in order:
            errs.append("missing key %s" % key)
    if errs:
        return errs
    nodes, edges = order["nodes"], order["edges"]
    if not nodes:
        return ["an order needs at least one node"]
    if len(edges) != len(nodes) - 1:
        errs.append("edges %d != nodes %d - 1" % (len(edges), len(nodes)))
    for k, nd in enumerate(nodes):
        if nd.get("sequenceId") != 2 * k:
            errs.append("node %d sequenceId %r != %d" % (k, nd.get("sequenceId"), 2 * k))
        for key in ("nodeId", "released", "actions"):
            if key not in nd:
                errs.append("node %d missing %s" % (k, key))
    for k, ed in enumerate(edges):
        if ed.get("sequenceId") != 2 * k + 1:
            errs.append("edge %d sequenceId %r != %d" % (k, ed.get("sequenceId"), 2 * k + 1))
        if k + 1 < len(nodes):
            if ed.get("startNodeId") != nodes[k].get("nodeId") or ed.get("endNodeId") != nodes[k + 1].get("nodeId"):
                errs.append("edge %d does not join node %d -> %d" % (k, k, k + 1))
            if ed.get("released") != nodes[k + 1].get("released"):
                errs.append("edge %d released %r != its end node's %r" % (k, ed.get("released"), nodes[k + 1].get("released")))
    rel = [bool(nd.get("released")) for nd in nodes]
    if not rel[0]:
        errs.append("the first node must be released (base)")
    if any(rel[k] and not rel[k - 1] for k in range(1, len(rel))):
        errs.append("released nodes must form one prefix (base), then horizon")
    return errs
