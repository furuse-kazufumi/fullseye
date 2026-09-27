"""粘菌(Physarum)の管ネットワーク・モデルで最短路を解く(device 非依存)。

正本の構想 = ``afterman/docs/SUBSTRATE_REDESIGN.md`` の「2. 粘菌 —— 表現の中で
動く探索」。ここはその PoC の第一歩(答えの分かっている小さな課題 = 迷路の最短路)。

## なぜ imgevolve に置くか

``pyramid_gate.py`` が「何がピラミッドになるか = **硬い枝刈り**(粗い階層が真の上位を
落とせば静かに最適解を失う)」を扱っている。粘菌はその対極 —— **軟らかい枝刈り**。
管は使われなければ細るが 0 にはならず、状況が変われば太り直せる。同じ「複数ターゲット
探索」を、ピラミッド(硬い)と粘菌(軟らかい)で並べて比べるのがこの一族の狙い。

## モデル(Tero ら 2010, *Science*、収束証明は Bonifaci ら 2012)

ノード間の管に長さ ``L_ij`` と伝導率 ``D_ij``。管を流れる流量:

    Q_ij = (D_ij / L_ij) (p_i - p_j)

各ノードで流量保存(キルヒホッフ)。源で +I0、吸込で -I0、他は 0。これを解くと
**重み付きグラフ・ラプラシアン** の線形系 ``L(D) p = b`` になる。伝導率の適応:

    dD_ij/dt = f(|Q_ij|) - D_ij      f は単調増加・f(0)=0

``f(Q) = |Q|^mu`` とし ``mu = 1`` で最短路に収束することが証明されている
(Bonifaci)。流量の多い管が太り、少ない管が細る。それだけで最短路が残る。

**GPU について(正直に)**: 中身は「疎ラプラシアンの線形ソルブを時間反復」で、
バッチ次元(多数の迷路・多数のパラメータ)に対して完全並列。いまは torch/jax とも
CPU ビルドしか入っておらず GPU で走らない。まず CPU で **正しさ**(最短路への収束)を
確定させ、それから CUDA ビルドを入れて ``device="cuda"`` に切り替える段取り
(memory ``feedback_cpu_short_poc_before_gpu``)。API は最初から batch + device で書く。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import torch
    _HAS_TORCH = True
except Exception:                       # torch 不在でも numpy で動く
    _HAS_TORCH = False


# ── グラフの構築(迷路 -> ノード/辺) ───────────────────────────────────────── #
@dataclass
class Graph:
    n: int                      # ノード数
    edges: np.ndarray           # (E, 2) int、各辺の (i, j)
    length: np.ndarray          # (E,) float、辺の長さ L_ij
    coords: np.ndarray          # (n, 2) int、格子上の (row, col)。可視化・照合用


def maze_to_graph(free: np.ndarray) -> Graph:
    """迷路(``free`` = True が通行可)を 4 近傍グラフにする。"""
    free = np.asarray(free, dtype=bool)
    H, W = free.shape
    idx = -np.ones((H, W), dtype=int)
    ys, xs = np.nonzero(free)
    idx[ys, xs] = np.arange(len(ys))
    coords = np.column_stack([ys, xs])
    edges = []
    for (y, x) in zip(ys, xs):
        i = idx[y, x]
        for dy, dx in ((0, 1), (1, 0)):          # 右と下だけ見れば各辺 1 回
            ny, nx = y + dy, x + dx
            if ny < H and nx < W and free[ny, nx]:
                edges.append((i, idx[ny, nx]))
    edges = np.asarray(edges, dtype=int) if edges else np.zeros((0, 2), int)
    length = np.ones(len(edges), dtype=float)
    return Graph(n=len(ys), edges=edges, length=length, coords=coords)


def node_at(graph: Graph, row: int, col: int) -> int:
    """格子座標からノード番号を引く(源/吸込の指定用)。"""
    hit = np.nonzero((graph.coords[:, 0] == row) & (graph.coords[:, 1] == col))[0]
    if len(hit) == 0:
        raise ValueError(f"({row},{col}) is not a traversable node")
    return int(hit[0])


# ── 粘菌ソルバ ────────────────────────────────────────────────────────────── #
@dataclass
class PhysarumResult:
    D: np.ndarray               # (E,) 最終伝導率
    Q: np.ndarray               # (E,) 最終流量
    iters: int
    converged: bool
    history: list               # 各反復の max|dD|(収束の観察用)


def _xp(device):
    """device 文字列から (バックエンド, 使うかどうか) を返す。"""
    if device == "numpy" or not _HAS_TORCH:
        return None
    return torch


def solve_physarum(graph: Graph, source: int, sink: int, *,
                   I0: float = 1.0, mu: float = 1.0, dt: float = 0.1,
                   max_iters: int = 5000, tol: float = 1e-6,
                   D_init=None, device: str = "numpy") -> PhysarumResult:
    """1 源 1 吸込で粘菌方程式を回し、収束した伝導率/流量を返す。

    ``device`` の選択:

    - ``"numpy"``(既定) —— 疎ラプラシアン + 共役勾配 + warm start。実測で
      dense の 14-34 倍(``docs/GPU_OPTIMIZATION_PATTERNS.md``)。
    - ``"numpy_dense"`` —— dense な O(n^3) 参照実装。疎版の答え合わせ用。
    - ``"cpu"`` / ``"cuda"`` —— torch(GPU へ載せる前提の同一式。今は CPU ビルドのみ)。

    **式はどれも同一。** ユニーク最短路では疎版と dense 版は完全一致し、等長最短路が
    多数ある縮退では違うタイ(等価な最短路)を選ぶ。
    """
    E = len(graph.edges)
    if E == 0:
        return PhysarumResult(np.zeros(0), np.zeros(0), 0, True, [])
    # **源と吸込が別成分なら、縮約ラプラシアンが特異になって解けない。**
    # 物理的にも「道が無い = 流れない」なので、全管を 0 にして即返す。
    if bfs_shortest_len(graph, source, sink) < 0:
        return PhysarumResult(np.zeros(E), np.zeros(E), 0, True, [])
    ii = graph.edges[:, 0]
    jj = graph.edges[:, 1]
    L = graph.length
    n = graph.n

    use_torch = device in ("cpu", "cuda") and _HAS_TORCH
    if use_torch:
        dev = torch.device(device)
        tii = torch.as_tensor(ii, device=dev, dtype=torch.long)
        tjj = torch.as_tensor(jj, device=dev, dtype=torch.long)
        tL = torch.as_tensor(L, device=dev, dtype=torch.float64)
        D = (torch.ones(E, device=dev, dtype=torch.float64) if D_init is None
             else torch.as_tensor(D_init, device=dev, dtype=torch.float64))
        b = torch.zeros(n, device=dev, dtype=torch.float64)
        b[source] = I0
        b[sink] = -I0
        keep = [k for k in range(n) if k != sink]        # ゲージ: p_sink = 0
        keep_t = torch.as_tensor(keep, device=dev, dtype=torch.long)
        history = []
        converged = False
        for it in range(max_iters):
            g = D / tL                                    # 辺コンダクタンス
            A = torch.zeros(n, n, device=dev, dtype=torch.float64)
            A.index_put_((tii, tjj), -g, accumulate=True)
            A.index_put_((tjj, tii), -g, accumulate=True)
            deg = torch.zeros(n, device=dev, dtype=torch.float64)
            deg.index_add_(0, tii, g)
            deg.index_add_(0, tjj, g)
            A += torch.diag(deg)
            Ar = A.index_select(0, keep_t).index_select(1, keep_t)
            br = b.index_select(0, keep_t)
            pr = torch.linalg.solve(Ar, br)
            p = torch.zeros(n, device=dev, dtype=torch.float64)
            p[keep_t] = pr
            Q = g * (p[tii] - p[tjj])
            newD = D + dt * (torch.abs(Q) ** mu - D)
            d = float(torch.max(torch.abs(newD - D)))
            history.append(d)
            D = newD
            if d < tol:
                converged = True
                break
        return PhysarumResult(D.cpu().numpy(), Q.cpu().numpy(), it + 1,
                              converged, history)

    if device == "numpy_dense":
        return _solve_numpy_dense(graph, source, sink, I0=I0, mu=mu, dt=dt,
                                  max_iters=max_iters, tol=tol, D_init=D_init)
    return _solve_numpy_sparse(graph, source, sink, I0=I0, mu=mu, dt=dt,
                               max_iters=max_iters, tol=tol, D_init=D_init)


def _solve_numpy_dense(graph, source, sink, *, I0, mu, dt, max_iters, tol, D_init):
    """dense な O(n^3) 参照実装。疎版の答え合わせ用に残す。"""
    ii, jj, L, n = graph.edges[:, 0], graph.edges[:, 1], graph.length, graph.n
    E = len(graph.edges)
    D = np.ones(E) if D_init is None else np.asarray(D_init, float).copy()
    b = np.zeros(n); b[source] = I0; b[sink] = -I0
    keep = np.array([k for k in range(n) if k != sink])
    history = []; converged = False; Q = np.zeros(E)
    for it in range(max_iters):
        g = D / L
        A = np.zeros((n, n))
        np.add.at(A, (ii, jj), -g); np.add.at(A, (jj, ii), -g)
        np.add.at(A, (ii, ii), g); np.add.at(A, (jj, jj), g)
        pr = np.linalg.solve(A[np.ix_(keep, keep)], b[keep])
        p = np.zeros(n); p[keep] = pr
        Q = g * (p[ii] - p[jj])
        newD = D + dt * (np.abs(Q) ** mu - D)
        d = float(np.max(np.abs(newD - D))); history.append(d); D = newD
        if d < tol:
            converged = True; break
    return PhysarumResult(D, Q, it + 1, converged, history)


def _solve_numpy_sparse(graph, source, sink, *, I0, mu, dt, max_iters, tol, D_init):
    """疎ラプラシアン + 共役勾配 + warm start。

    GPU 調査と実測の一致した結論(``docs/GPU_OPTIMIZATION_PATTERNS.md``):
    律速は毎反復の dense 解 O(n^3) で、per-iter の 97% を占めていた。3 つ直す:

    1. **疎化** —— ラプラシアンは 4 近傍で 1 行 5 要素。dense n×n を組むのをやめ、
       疎パターンを **1 回だけ** 作って毎反復 data だけ差し替える
    2. **反復法(CG)** —— 縮約ラプラシアンは SPD なので共役勾配が使える。
       直接解の O(n^3) を、疎行列ベクトル積 × 反復回数に落とす
    3. **warm start** —— D は 1 反復で少ししか動かない(実測: 収束まで ~100 反復で
       max|dD| が単調減少)。前反復の圧力 p を CG の初期値にすると反復が数回で済む
       (Taming Preconditioner Drift 2602.19271 と同じ発想。ここは前解の使い回し)
    """
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import cg

    ii, jj, L, n = graph.edges[:, 0], graph.edges[:, 1], graph.length, graph.n
    E = len(graph.edges)
    D = np.ones(E) if D_init is None else np.asarray(D_init, float).copy()

    # ゲージ: p_sink = 0。sink 以外を並べ替える index を 1 回だけ作る。
    keep = np.array([k for k in range(n) if k != sink])
    remap = -np.ones(n, dtype=int); remap[keep] = np.arange(n - 1)
    b = np.zeros(n); b[source] = I0; b[sink] = -I0
    br = b[keep]

    # **疎パターンは固定**。各辺は縮約系で (ri,rj) の off-diag 2 つと
    # (ri,ri)/(rj,rj) の diag に効く。sink に触れる辺は該当行/列が消える。
    ri, rj = remap[ii], remap[jj]
    rows, cols, tag = [], [], []      # tag: この (row,col) にどの辺が符号どちらで効くか
    for e in range(E):
        a, c = ri[e], rj[e]
        if a >= 0 and c >= 0:
            rows += [a, c, a, c]; cols += [c, a, a, c]; tag.append(("both", e))
        elif a >= 0:                  # c は sink(消える列)。a の diag だけ
            rows += [a]; cols += [a]; tag.append(("a", e))
        elif c >= 0:
            rows += [c]; cols += [c]; tag.append(("c", e))
        else:
            tag.append(("none", e))
    rows = np.asarray(rows); cols = np.asarray(cols)

    history = []; converged = False; Q = np.zeros(E)
    p = np.zeros(n)                   # warm start 用に前反復の圧力を持ち越す
    x0 = np.zeros(n - 1)
    for it in range(max_iters):
        g = D / L
        data = []
        for kind, e in tag:
            ge = g[e]
            if kind == "both":
                data += [-ge, -ge, ge, ge]
            elif kind in ("a", "c"):
                data += [ge]
        A = csr_matrix((np.asarray(data), (rows, cols)), shape=(n - 1, n - 1))
        pr, info = cg(A, br, x0=x0, rtol=1e-10, atol=0.0, maxiter=1000)
        x0 = pr                       # 次反復の初期値(warm start)
        p = np.zeros(n); p[keep] = pr
        Q = g * (p[ii] - p[jj])
        newD = D + dt * (np.abs(Q) ** mu - D)
        d = float(np.max(np.abs(newD - D))); history.append(d); D = newD
        if d < tol:
            converged = True; break
    return PhysarumResult(D, Q, it + 1, converged, history)


# ── 結果の読み取り ────────────────────────────────────────────────────────── #
def surviving_path(graph: Graph, res: PhysarumResult, source: int, sink: int,
                   frac: float = 0.5) -> list:
    """伝導率の生き残った辺だけを辿って源->吸込の道を復元する。

    最終 D の最大値の ``frac`` 倍を超える辺を「太い管」とみなし、その部分グラフ上で
    源から吸込へ BFS。返すのはノード列(道が無ければ空)。
    """
    if len(res.D) == 0:
        return []
    thr = frac * res.D.max()
    adj = {}
    for (i, j), d in zip(graph.edges, res.D):
        if d >= thr:
            adj.setdefault(i, []).append(j)
            adj.setdefault(j, []).append(i)
    # BFS
    from collections import deque
    prev = {source: -1}
    dq = deque([source])
    while dq:
        u = dq.popleft()
        if u == sink:
            break
        for v in adj.get(u, []):
            if v not in prev:
                prev[v] = u
                dq.append(v)
    if sink not in prev:
        return []
    path = []
    u = sink
    while u != -1:
        path.append(u)
        u = prev[u]
    return path[::-1]


def bfs_shortest_len(graph: Graph, source: int, sink: int) -> int:
    """照合用: グラフ上の最短ホップ数(全辺長 1 前提)。到達不能なら -1。"""
    from collections import deque
    adj = {}
    for i, j in graph.edges:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    dist = {source: 0}
    dq = deque([source])
    while dq:
        u = dq.popleft()
        for v in adj.get(u, []):
            if v not in dist:
                dist[v] = dist[u] + 1
                dq.append(v)
    return dist.get(sink, -1)


# ── GPU 向け: matrix-free バッチ CG ───────────────────────────────────────── #
# 効率の要点(docs/GPU_OPTIMIZATION_PATTERNS.md の P18/P9/P20/P7):
#   - **行列を作らない**(matrix-free): L(D)x は「各辺で g*(x_i-x_j) を両端へ
#     scatter する」だけ。dense n×n も疎行列の組み立ても要らない。gather/scatter
#     だけなので GPU のバンド幅で走る。
#   - **バッチ軸**(P9): 多数のグラフ/パラメータを 1 本の (B, ...) テンソルに畳んで
#     1 カーネルで回す。1 個ずつ GPU に投げると起動と転送で CPU より遅い(P7 の罠)。
#   - **warm start**(P20): 時間反復で D は少ししか動かないので、前ステップの圧力を
#     CG の初期値にする。反復が数回で済む。
#   - **host 同期を出さない**(P7): 収束判定を毎反復 float() で CPU に降ろさない。
#     固定反復数で回し、結果(最終 D)だけ最後に 1 回返す。
def _laplacian_matvec(x, g, src, dst, free_mask):
    """matrix-free な L(D)x(バッチ)。x:(B,n) g:(B,E) src/dst:(E,) 返り:(B,n)。

    ゲージ(p_sink=0)は free_mask:(B,n) の False 位置を 0 に落として課す。
    """
    diff = x.index_select(1, src) - x.index_select(1, dst)   # (B, E)
    flow = g * diff
    y = torch.zeros_like(x)
    B = x.shape[0]
    si = src.unsqueeze(0).expand(B, -1)
    di = dst.unsqueeze(0).expand(B, -1)
    y.scatter_add_(1, si, flow)
    y.scatter_add_(1, di, -flow)
    return y * free_mask


def _cg_batched(g, b, src, dst, free_mask, x0, iters=200, tol=1e-10,
                check_every=1):
    """バッチ共役勾配。全問題を同時に回す(matrix-free)。

    A(=L(D)) は SPD(縮約後)。free_mask で sink をディリクレ固定。
    x0 = 前ステップ解(warm start)。

    収束判定 = **バッチ全体の最大残差** を 1 スカラーに畳んで見る。ただし
    ``float(rs.max())`` は device→host 同期を起こし、GPU では 1 反復ごとにやると
    4 万回の同期でパイプラインが直列化する(実測でここが律速)。``check_every`` で
    間引き、その間は非同期に反復を回す(GPU 向け。CPU は既定 1 のまま)。
    """
    x = x0 * free_mask
    r = (b - _laplacian_matvec(x, g, src, dst, free_mask)) * free_mask
    p = r.clone()
    rs = (r * r).sum(1, keepdim=True)             # (B,1)
    for i in range(iters):
        Ap = _laplacian_matvec(p, g, src, dst, free_mask)
        denom = (p * Ap).sum(1, keepdim=True)
        alpha = rs / denom.clamp_min(1e-30)
        x = x + alpha * p
        r = r - alpha * Ap
        rs_new = (r * r).sum(1, keepdim=True)
        if tol > 0 and (i + 1) % check_every == 0:
            if float(rs_new.max()) < tol:         # ここでだけ同期
                break
        p = r + (rs_new / rs.clamp_min(1e-30)) * p
        rs = rs_new
    return x


def solve_physarum_batch(graph: Graph, sources, sinks, *, I0=1.0, mu=1.0,
                         dt=0.1, time_steps=200, cg_iters=200,
                         D_init=None, device="cpu",
                         dtype="float64", cg_tol=1e-10, cg_check_every=25,
                         use_cuda_graph=False):
    """**同じグラフ構造の上で、多数の(源, 吸込)を一度に**解く(バッチ)。

    形状マッチングの複数スケール掃引と同じ発想 —— 変わらないもの(辺の index)は
    共有し、変わるもの(境界条件 b、必要なら D_init)だけ (B, ...) に積む。
    Tero らの多端子ネットワーク設計やパラメータ sweep がこの形。

    ``device="cuda"`` で **同じコードがそのまま GPU で走る**。GPU 向けの効率化:

    - ``dtype="float32"`` —— コンシューマ GPU(RTX 50 系)は FP64 が FP32 の
      1/64 しか出ない。経路探索の粘菌は FP32 で十分な精度が出るので既定より速い。
    - ``cg_check_every`` —— CG の収束チェック(``rs.max()`` の host 同期)を間引く。
      GPU では 1 反復ごとの同期が最大の直列化要因。FP64 参照一致テストでは
      ``cg_tol=0`` を渡して固定反復にする(同期ゼロ)。
    - ``use_cuda_graph=True`` —— この規模(辺数が数万でも)GPU は計算量でなく
      **1 反復あたりのカーネル起動レイテンシで律速**する(壁時計はグラフを 22 倍に
      しても ~一定)。1 タイムステップ分(固定反復 CG + D 更新)を CUDA graph に
      一度捕獲し replay すると起動を消せる(実測 4.4x、結果はビット一致)。捕獲は
      静的形状・host 同期なしが要るので **固定反復**(``cg_tol`` は無視)になる。

    返り値: D (B, E) の numpy。各行が対応する(源, 吸込)の最終伝導率。
    """
    if not _HAS_TORCH:
        raise RuntimeError("torch is required")
    dev = torch.device(device)
    if use_cuda_graph:
        if dev.type != "cuda":
            raise ValueError("use_cuda_graph is only valid when device='cuda'")
        return _solve_batch_cudagraph(
            graph, sources, sinks, I0=I0, mu=mu, dt=dt, time_steps=time_steps,
            cg_iters=cg_iters, D_init=D_init, dev=dev, dtype=dtype)
    ftype = torch.float32 if dtype == "float32" else torch.float64
    E = len(graph.edges)
    n = graph.n
    sources = list(sources)
    sinks = list(sinks)
    B = len(sources)

    src = torch.as_tensor(graph.edges[:, 0], device=dev, dtype=torch.long)
    dst = torch.as_tensor(graph.edges[:, 1], device=dev, dtype=torch.long)
    L = torch.as_tensor(graph.length, device=dev, dtype=ftype)

    D = (torch.ones(B, E, device=dev, dtype=ftype) if D_init is None
         else torch.as_tensor(D_init, device=dev, dtype=ftype).reshape(B, E))
    b = torch.zeros(B, n, device=dev, dtype=ftype)
    free_mask = torch.ones(B, n, device=dev, dtype=ftype)
    for k, (s, t) in enumerate(zip(sources, sinks)):
        b[k, s] = I0
        b[k, t] = -I0
        free_mask[k, t] = 0.0          # p_sink = 0(ディリクレ)
    b = b * free_mask

    x = torch.zeros(B, n, device=dev, dtype=ftype)   # warm start 用
    for _ in range(time_steps):
        g = D / L                       # (B, E)
        x = _cg_batched(g, b, src, dst, free_mask, x, iters=cg_iters,
                        tol=cg_tol, check_every=cg_check_every)
        Q = g * (x.index_select(1, src) - x.index_select(1, dst))
        D = D + dt * (torch.abs(Q) ** mu - D)
    return D.cpu().numpy()


def _solve_batch_cudagraph(graph: Graph, sources, sinks, *, I0, mu, dt,
                           time_steps, cg_iters, D_init, dev, dtype):
    """CUDA graph 捕獲版。1 タイムステップ(固定反復 CG + D 更新)を捕獲し replay。

    捕獲の条件: 静的形状・in-place 更新・host 同期なし。よって CG は **固定反復**
    (収束の早期打ち切りをしない)。永続バッファ D_buf/x_buf を in-place で回し、
    graph はその番地の上で同じ演算列を再実行する。
    """
    ftype = torch.float32 if dtype == "float32" else torch.float64
    E = len(graph.edges)
    n = graph.n
    sources = list(sources)
    sinks = list(sinks)
    B = len(sources)

    src = torch.as_tensor(graph.edges[:, 0], device=dev, dtype=torch.long)
    dst = torch.as_tensor(graph.edges[:, 1], device=dev, dtype=torch.long)
    si = src.unsqueeze(0).expand(B, -1)
    di = dst.unsqueeze(0).expand(B, -1)
    L = torch.as_tensor(graph.length, device=dev, dtype=ftype)
    b = torch.zeros(B, n, device=dev, dtype=ftype)
    free_mask = torch.ones(B, n, device=dev, dtype=ftype)
    for k, (s, t) in enumerate(zip(sources, sinks)):
        b[k, s] = I0
        b[k, t] = -I0
        free_mask[k, t] = 0.0
    b = b * free_mask

    D_init_t = (torch.ones(B, E, device=dev, dtype=ftype) if D_init is None
                else torch.as_tensor(D_init, device=dev, dtype=ftype).reshape(B, E))
    D_buf = D_init_t.clone()
    x_buf = torch.zeros(B, n, device=dev, dtype=ftype)   # warm start(step 間で持越し)

    def matvec(vec, g):
        diff = vec.index_select(1, src) - vec.index_select(1, dst)
        flow = g * diff
        y = torch.zeros_like(vec)
        y.scatter_add_(1, si, flow)
        y.scatter_add_(1, di, -flow)
        return y * free_mask

    def one_step(D, x0):
        g = D / L
        x = x0 * free_mask
        r = (b - matvec(x, g)) * free_mask
        p = r.clone()
        rs = (r * r).sum(1, keepdim=True)
        for _ in range(cg_iters):                # 固定反復(同期なし)
            Ap = matvec(p, g)
            alpha = rs / (p * Ap).sum(1, keepdim=True).clamp_min(1e-30)
            x = x + alpha * p
            r = r - alpha * Ap
            rs_new = (r * r).sum(1, keepdim=True)
            p = r + (rs_new / rs.clamp_min(1e-30)) * p
            rs = rs_new
        Q = g * (x.index_select(1, src) - x.index_select(1, dst))
        D_new = D + dt * (torch.abs(Q) ** mu - D)
        return D_new, x

    # --- warmup(副ストリーム。捕獲前に allocator/カーネルを温める)---
    s = torch.cuda.Stream()
    s.wait_stream(torch.cuda.current_stream())
    with torch.cuda.stream(s):
        for _ in range(3):
            Dn, xn = one_step(D_buf, x_buf)
            D_buf.copy_(Dn)
            x_buf.copy_(xn)
    torch.cuda.current_stream().wait_stream(s)

    # --- 捕獲(初期状態へ戻してから)---
    D_buf.copy_(D_init_t)
    x_buf.zero_()
    gr = torch.cuda.CUDAGraph()
    with torch.cuda.graph(gr):
        Dn, xn = one_step(D_buf, x_buf)
        D_buf.copy_(Dn)
        x_buf.copy_(xn)

    # --- replay(初期状態から time_steps 回)---
    D_buf.copy_(D_init_t)
    x_buf.zero_()
    for _ in range(time_steps):
        gr.replay()
    return D_buf.cpu().numpy()



# ── 型付き台帳の op(opsgraph "flow")───────────────────────────────────────── #
def _lengths_matrix(lengths, op):
    a = np.asarray(lengths)
    if isinstance(lengths, (str, bytes)) or np.ma.isMaskedArray(lengths) or a.dtype.kind not in "fiub":
        raise ValueError("%s: lengths must be a numeric (n, n) matrix" % op)
    a = a.astype(np.float64)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or a.shape[0] < 2:
        raise ValueError("%s: lengths must be a square (n, n) matrix with n >= 2, got %r" % (op, a.shape))
    if not np.isfinite(a).all() or (a < 0).any():
        raise ValueError("%s: lengths must be finite and non-negative (0 = no edge)" % op)
    if not np.array_equal(a, a.T):
        raise ValueError("%s: lengths must be symmetric (tubes have no direction)" % op)
    if (np.diag(a) != 0).any():
        raise ValueError("%s: the diagonal must be 0 (no self-loops)" % op)
    return a


def _node(k, n, name, op, default):
    if k is None:
        return default
    try:
        k = int(k)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer node index" % (op, name)) from None
    if not 0 <= k < n:
        raise ValueError("%s: %s %d is outside [0, %d)" % (op, name, k, n))
    return k


def _run(graph, source, sink, dt, max_iters, tol, frac, op):
    if not (0.0 < float(dt) <= 1.0) or not np.isfinite(dt):
        raise ValueError("%s: dt must lie in (0, 1], got %r" % (op, dt))
    if int(max_iters) < 1 or not (float(tol) >= 0) or not np.isfinite(tol):
        raise ValueError("%s: max_iters must be >= 1 and tol >= 0 (0 = run exactly max_iters)" % op)
    if not (0.0 < float(frac) <= 1.0):
        raise ValueError("%s: frac must lie in (0, 1], got %r" % (op, frac))
    if bfs_shortest_len(graph, source, sink) < 0:
        raise ValueError("%s: sink is not reachable from source (no tube can carry the flow)" % op)
    res = solve_physarum(graph, source, sink, I0=1.0, mu=1.0, dt=float(dt),
                         max_iters=int(max_iters), tol=float(tol), device="numpy")
    path = _follow_flow(graph, res.Q, source, sink)
    if path is None:
        raise ValueError("%s: following the flow from source did not reach sink (the solve failed)" % op)
    thick = res.D[_edge_index(graph.edges, path)]
    if res.D.max() > 0 and thick.min() < float(frac) * res.D.max():
        raise ValueError("%s: the route still shares flow with a tube %.3g times thicker than its thinnest one "
                         "(not converged: raise max_iters or lower tol; a tie between equal-length routes never converges)"
                         % (op, res.D.max() / max(thick.min(), 1e-300)))
    return res, path


def _follow_flow(graph, Q, source, sink):
    """源から、流量が最も多く出ていく管を辿って吸込へ(ポテンシャル流は閉路を持たない)。"""
    n = graph.n
    out = [[] for _ in range(n)]
    for k, (u, v) in enumerate(graph.edges):
        if Q[k] > 0:
            out[u].append((Q[k], v))
        elif Q[k] < 0:
            out[v].append((-Q[k], u))
    path, u, seen = [source], source, {source}
    while u != sink:
        if not out[u]:
            return None
        _, v = max(out[u])
        if v in seen:                                    # 数値誤差で閉路に見えたら失敗として返す
            return None
        seen.add(v)
        path.append(v)
        u = v
        if len(path) > n:
            return None
    return np.asarray(path, dtype=np.int64)


def graph_physarum_path(lengths, source=0, sink=None, dt=0.1, max_iters=5000, tol=1e-6, frac=0.5):
    """Shortest path by the slime mould's tube dynamics (Tero et al. 2010) on a weighted graph.

    ``lengths`` is a symmetric ``(n, n)`` matrix of tube lengths (``0`` = no tube, diagonal 0).
    A unit flow is pushed from ``source`` to ``sink`` (default ``n - 1``) through tubes of
    conductance ``D_e``; the pressures solve the weighted Laplacian (Kirchhoff), the flow in a
    tube is ``Q_e = D_e (p_u - p_v) / L_e``, and each tube adapts ``dD_e/dt = |Q_e| - D_e``
    (explicit Euler, step ``dt``). Bonifaci, Mehlhorn and Varma (2012) prove that with a unique
    shortest path the conductances converge to its indicator: ``D_e -> 1`` on it, ``0`` off it.
    The path is read by following, from the source, the tube that carries the most flow out of
    each node (a potential flow has no cycle); it must be at least ``frac`` of the thickest tube
    all along, else the run is refused as not converged.

    Returns ``conductance`` and ``flow`` (``(n, n)`` matrices, flow antisymmetric), ``path``
    (node indices source → sink), ``path_length`` (sum of the tube lengths along it),
    ``flow_length`` = ``sum |Q_e| L_e`` (the length of the unit flow; it is ``>= path_length``
    for every unit flow and equal only when all flow rides shortest paths), ``iters``,
    ``converged`` (max |dD| fell below ``tol``), ``history`` (max |dD| per iteration).

    **Raises** ``ValueError``: matrix not square / symmetric / finite / non-negative, self-loops;
    bad node indices or ``source == sink``; sink unreachable; ``dt`` outside (0, 1]; no path
    survived the threshold (not converged).
    """
    op = "graph_physarum_path"
    a = _lengths_matrix(lengths, op)
    n = a.shape[0]
    source = _node(source, n, "source", op, 0)
    sink = _node(sink, n, "sink", op, n - 1)
    if source == sink:
        raise ValueError("%s: source and sink must differ" % op)
    iu, ju = np.nonzero(np.triu(a, 1))
    if len(iu) == 0:
        raise ValueError("%s: the matrix has no edge" % op)
    graph = Graph(n=n, edges=np.column_stack([iu, ju]).astype(int), length=a[iu, ju],
                  coords=np.zeros((n, 2), dtype=int))
    res, path = _run(graph, source, sink, dt, max_iters, tol, frac, op)
    cond = np.zeros((n, n))
    cond[iu, ju] = res.D
    cond[ju, iu] = res.D
    flow = np.zeros((n, n))
    flow[iu, ju] = res.Q
    flow[ju, iu] = -res.Q
    return {"conductance": cond, "flow": flow, "path": path,
            "path_length": float(a[path[:-1], path[1:]].sum()),
            "flow_length": float((np.abs(res.Q) * graph.length).sum()),
            "iters": int(res.iters), "converged": bool(res.converged),
            "history": np.asarray(res.history, dtype=np.float64)}


def physarum_route(cost, start=None, end=None, connectivity=4, dt=0.1, max_iters=5000, tol=1e-6,
                   frac=0.5, snapshots=0):
    """Minimum-cost route through a cost image found by the slime mould's tube dynamics.

    Every pixel is a node; neighbouring pixels (``connectivity`` 4 or 8) are joined by a tube of
    length ``(c_u + c_v) / 2`` (times ``sqrt(2)`` on diagonals), so the length of a route equals
    the sum of the pixel costs it visits minus half the cost of its two ends — the same quantity
    ``skimage.graph.route_through_array(..., geometric=False)`` minimises (it counts both ends
    fully). ``start`` / ``end`` are ``(row, col)``; defaults are the top-left and bottom-right
    corners. Dynamics and convergence as in :func:`graph_physarum_path`.

    Returns ``conductance`` (an image: each pixel's thickest incident tube, 1 on the route
    when converged), ``path`` (``(k, 2)`` pixel coordinates start → end), ``path_cost`` (sum of
    the pixel costs along it, comparable to ``route_through_array``), ``route_length`` (sum
    of the tube lengths), ``flow_length``, ``iters``, ``converged``, ``history``, and, with
    ``snapshots = m > 0``, ``snapshots`` (``m`` conductance images at evenly spaced
    iterations, the last one final) for watching the tubes thicken, ``snapshot_iters`` and
    ``snapshot_cost`` = ``sum L_e D_e`` at those iterations (Bonifaci's Lyapunov function, which
    never increases in continuous time).

    **Raises** ``ValueError``: cost not a 2-D finite image of positive values; ``start`` / ``end``
    outside the image or equal; ``connectivity`` not 4 or 8; and as :func:`graph_physarum_path`.
    """
    op = "physarum_route"
    c = np.asarray(cost)
    if isinstance(cost, (str, bytes)) or np.ma.isMaskedArray(cost) or c.dtype.kind not in "fiub":
        raise ValueError("%s: cost must be a numeric 2-D image" % op)
    c = c.astype(np.float64)
    if c.ndim != 2 or min(c.shape) < 2:
        raise ValueError("%s: cost must be a 2-D image with at least 2 rows and columns, got %r" % (op, c.shape))
    if not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("%s: every cost must be finite and > 0 (a tube of length 0 carries infinite flow)" % op)
    H, W = c.shape
    if int(connectivity) not in (4, 8):
        raise ValueError("%s: connectivity must be 4 or 8, got %r" % (op, connectivity))

    def pix(p, name, default):
        if p is None:
            return default
        try:
            r, q = int(p[0]), int(p[1])
        except (TypeError, ValueError, IndexError):
            raise ValueError("%s: %s must be (row, col)" % (op, name)) from None
        if not (0 <= r < H and 0 <= q < W):
            raise ValueError("%s: %s %r is outside the %dx%d image" % (op, name, (r, q), H, W))
        return r, q

    s = pix(start, "start", (0, 0))
    e = pix(end, "end", (H - 1, W - 1))
    if s == e:
        raise ValueError("%s: start and end must differ" % op)
    idx = np.arange(H * W).reshape(H, W)
    steps = [((0, 1), 1.0), ((1, 0), 1.0)]
    if int(connectivity) == 8:
        steps += [((1, 1), np.sqrt(2.0)), ((1, -1), np.sqrt(2.0))]
    us, vs, ls = [], [], []
    for (dr, dq), k in steps:
        r0, r1 = max(0, -dr), H - max(0, dr)
        q0, q1 = max(0, -dq), W - max(0, dq)
        u = idx[r0:r1, q0:q1]
        v = idx[r0 + dr:r1 + dr, q0 + dq:q1 + dq]
        us.append(u.ravel())
        vs.append(v.ravel())
        ls.append(k * 0.5 * (c.ravel()[u.ravel()] + c.ravel()[v.ravel()]))
    edges = np.column_stack([np.concatenate(us), np.concatenate(vs)]).astype(int)
    length = np.concatenate(ls)
    graph = Graph(n=H * W, edges=edges, length=length, coords=np.column_stack(np.divmod(np.arange(H * W), W)))
    src, dst = int(idx[s]), int(idx[e])
    m = int(snapshots)
    if m < 0:
        raise ValueError("%s: snapshots must be >= 0" % op)
    res, path = _run(graph, src, dst, dt, max_iters, tol, frac, op)

    def image_of(D):
        img = np.zeros(H * W)
        np.maximum.at(img, edges[:, 0], D)
        np.maximum.at(img, edges[:, 1], D)
        return img.reshape(H, W)

    out = {"conductance": image_of(res.D), "path": graph.coords[path],
           "path_cost": float(c.ravel()[path].sum()),
           "route_length": float(length[_edge_index(edges, path)].sum()),
           "flow_length": float((np.abs(res.Q) * length).sum()),
           "iters": int(res.iters), "converged": bool(res.converged),
           "history": np.asarray(res.history, dtype=np.float64)}
    if m > 0:
        # 同じ式を途中で止めて撮る(warm start で続きを回す)。最後の 1 枚は上の最終状態と同じ反復数。
        marks = np.unique(np.maximum(1, np.round(np.linspace(0, res.iters, m + 1)[1:]).astype(int)))
        shots, costs, D, done = [], [], None, 0
        for k in marks:
            r = solve_physarum(graph, src, dst, I0=1.0, mu=1.0, dt=float(dt), max_iters=int(k - done),
                               tol=0.0, D_init=D, device="numpy")
            D, done = r.D, k
            shots.append(image_of(D))
            costs.append(float((length * D).sum()))
        out["snapshots"] = shots
        out["snapshot_iters"] = marks
        out["snapshot_cost"] = np.asarray(costs)          # V = Σ L_e D_e、Bonifaci の Lyapunov 関数(連続時間で単調非増加)
    return out


def _edge_index(edges, path):
    key = {(int(u), int(v)): k for k, (u, v) in enumerate(edges)}
    return np.array([key.get((int(u), int(v)), key.get((int(v), int(u)))) for u, v in zip(path[:-1], path[1:])], dtype=int)
