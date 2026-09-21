# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""conngraph — 結合グラフ(connectome)の閉形式解析・帰無モデル・reservoir 計算。

## なぜ要るか(2026-09-20)

コネクトーム(神経の結合表)は「pre → post に count 本のシナプス」という
**重みつき有向グラフ**で、fullseye が持つ画像・点群・信号のどの型でもない。
既存の ``graph`` 種は ``ops3d.knn_graph``(点群 → 近傍グラフ)の 1 op だけで、
隣接行列そのものを受けて**次数・クラスタ係数・媒介中心性・スペクトル・
モジュラリティ・モチーフ**を返す層は空いていた。この族はその第 1 陣で、

* **build** … シナプス表 → 隣接行列、次数保存シャッフル(帰無モデル)、二値化
* **stats** … 次数表・クラスタ係数・媒介中心性・Laplacian スペクトル・
  スペクトル半径・弱連結成分・モジュラリティ・rich club・3 点モチーフ
* **reservoir** … 結合行列を reservoir にして時系列の状態列 / 静的入力の一括符号化を作り、
  リッジ回帰で読み出す(echo state network の閉形式)
* **view** … スペクトル配置(点群)・辺の線分表・隣接行列の画像(Studio で見る出口)
* **activity** … 状態列の到達潜時・活動の空間的な広がり・座標に活動を載せて回す色動画
  (2026-09-20、MaleCNS の soma 座標に刺激の波を描く PoC から)

の 23 op / 5 カテゴリ。実装は numpy のみ(``networkx`` / ``scipy.sparse`` に
依存しない)。すべて教科書の閉形式で、``tests/test_conngraph.py`` が
リング・スター・完全グラフ・2 クリークの厳密な真値と突き合わせる。

## 型語彙(台帳 ``opsconngraph.py`` に理由を書いた)

* ``conn_graph`` … float64 の n×n 正方行列。``W[i, j]`` = i → j の重み。
  NaN / inf は**入口で拒否**する(隣接行列の NaN は「辺が無い」とも「未計測」とも
  読めるので、黙って 0 に潰すと結果がもっともらしく間違う)。
* ``synapse_table`` … float64 の m×3(pre_id, post_id, count)。id は 0 始まりの
  整数を float で持つ(CSV から読んだ表をそのまま渡せるように)。

★ 有向グラフの**構造**を見る op(次数・媒介中心性・成分・モチーフ・シャッフル)は
``W != 0`` の二値構造を使い、対角(自己結合)は無視する。重みを使うのは
strength・モジュラリティ・スペクトル半径・reservoir・画像の 5 系統だけで、
各 docstring に「重み / 二値」を明記した。

Provenance(公開の教科書・論文のみ): Brandes, *J. Math. Sociol.* 2001(媒介中心性)/
Watts & Strogatz, *Nature* 1998(クラスタ係数)/ Fiedler 1973 & Hall 1970(スペクトル配置)/
Leicht & Newman, *PRL* 2008(有向モジュラリティ)/ Maslov & Sneppen, *Science* 2002
(次数保存シャッフル)/ Milo et al., *Science* 2002(ネットワークモチーフ)/
Colizza et al., *Nature Phys.* 2006(rich club)/ Jaeger 2001 & Lukoševičius 2012
(echo state network とリッジ読み出し)。
"""
from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    # build
    "graph_from_synapses", "graph_degree_preserving_shuffle", "graph_binarize",
    # stats
    "graph_degree_table", "graph_clustering_coefficient", "graph_betweenness",
    "graph_laplacian_spectrum", "graph_spectral_radius", "graph_components",
    "graph_modularity", "graph_rich_club", "graph_motif_count",
    # reservoir
    "reservoir_from_graph", "reservoir_states", "reservoir_encode", "ridge_readout", "ridge_predict",
    # view
    "graph_layout_spectral", "graph_edges_as_lines", "graph_adjacency_image",
    # activity
    "graph_activation_latency", "graph_activity_spread", "points_activity_video",
    # dimension(2026-09-21): 層を通す・次元を数える
    "graph_block_shuffle", "graph_layer_propagate", "states_participation_ratio", "states_layer_dimension",
    # 回路(2026-09-22): 配線をそのままコンダクタンス回路として回す(学習なし)
    "graph_conductance_states",
    # constants
    "MOTIFS", "NONLINEARITIES", "ADJACENCY_ORDERS", "MAX_NODES", "ACTIVATIONS",
    "RELEASES",
]

#: 数えられる 3 点モチーフ。reciprocal = 相互結合の対、ffl = feed-forward loop
#: (a→b, b→c, a→c)、cycle3 = 3 点の巡回(a→b→c→a)。
MOTIFS: tuple[str, ...] = ("reciprocal", "ffl", "cycle3")
#: reservoir の非線形。linear は閉形式の検算用(tanh を外すと線形再帰そのもの)。
NONLINEARITIES: tuple[str, ...] = ("tanh", "linear")
#: 隣接行列画像の並べ替え。
ADJACENCY_ORDERS: tuple[str, ...] = ("none", "degree", "component")
#: ``graph_conductance_states`` の前シナプス放出。どちらも**非負**で、負のコンダクタンス
#: (物理的に存在しない)を作らない —— 状態の有界性はここに掛かっている。
RELEASES: tuple[str, ...] = ("relu", "sigmoid")
#: 受け付ける最大ノード数。媒介中心性は O(n·m)、固有分解は O(n³) で、これを超える
#: 密行列は float64 で 128 MB を超える —— 黙って何十分も回すより入口で断る。
MAX_NODES = 4096


# --------------------------------------------------------------------------- #
# 入口の門(fail-closed)                                                       #
# --------------------------------------------------------------------------- #
def _as_finite_float(a: Any, op: str, name: str) -> np.ndarray:
    """float64 に昇格して返す。NaN/inf・複素・bool・文字列・object は名指しで拒否。"""
    if isinstance(a, (str, bytes)):
        raise TypeError(f"{op}: {name} is a string — expected a numeric array")
    if np.ma.is_masked(a):
        raise ValueError(f"{op}: {name} is a masked array with masked entries — fill or drop them first")
    arr = np.asarray(a)
    if arr.dtype.kind in ("U", "S", "O", "V"):
        raise TypeError(f"{op}: {name} has dtype {arr.dtype} — expected a numeric array")
    if arr.dtype.kind == "b":
        raise TypeError(f"{op}: {name} is boolean — pass numbers (use graph_binarize to make a 0/1 graph)")
    if arr.dtype.kind == "c":
        raise ValueError(f"{op}: {name} is complex — coercion would silently drop the imaginary part")
    arr = arr.astype(np.float64, copy=False)
    if not np.isfinite(arr).all():
        raise ValueError(f"{op}: {name} has non-finite values (nan/inf) — a NaN edge is neither "
                         "'absent' nor 'measured', so it is refused instead of being zeroed")
    return arr


def _as_graph(W: Any, op: str, name: str = "W") -> np.ndarray:
    """``conn_graph`` として受ける: float64 の正方 n×n、有限、1 ≤ n ≤ MAX_NODES。"""
    arr = _as_finite_float(W, op, name)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError(f"{op}: {name} must be a square (n, n) adjacency matrix, got shape {arr.shape}")
    n = int(arr.shape[0])
    if n < 1:
        raise ValueError(f"{op}: {name} is empty (0 nodes)")
    if n > MAX_NODES:
        raise ValueError(f"{op}: {name} has {n} nodes, over the {MAX_NODES} cap for dense analysis")
    return arr


def _as_matrix(X: Any, op: str, name: str) -> np.ndarray:
    """一般の 2-D 実数行列(``matrix``)。1-D は (T, 1) に立てる。"""
    arr = _as_finite_float(X, op, name)
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2 or arr.size == 0:
        raise ValueError(f"{op}: {name} must be a non-empty 2-D matrix, got shape {arr.shape}")
    return arr


def _as_labels(labels: Any, op: str, n: int, name: str = "labels") -> np.ndarray:
    """ノードごとの整数ラベル(長さ n の 1-D)。実数は整数値のときだけ通す。"""
    if isinstance(labels, dict):
        raise TypeError(f"{op}: {name} is a dict — pass a 1-D integer label per node (e.g. graph_components(W))")
    arr = np.asarray(labels)
    if arr.dtype.kind in ("U", "S", "O", "V", "c"):
        raise TypeError(f"{op}: {name} has dtype {arr.dtype} — expected integer labels")
    if arr.ndim != 1 or arr.shape[0] != n:
        raise ValueError(f"{op}: {name} must be a 1-D array with one label per node ({n}), got shape {arr.shape}")
    if arr.dtype.kind == "f":
        if not np.isfinite(arr).all() or not np.all(arr == np.round(arr)):
            raise ValueError(f"{op}: {name} must hold whole numbers, got non-integer values")
    return arr.astype(np.int64, copy=False)


def _binary(W: np.ndarray) -> np.ndarray:
    """二値構造(``W != 0``、対角は落とす)。構造だけを見る op の共通入口。"""
    A = W != 0.0
    np.fill_diagonal(A, False)
    return A


def _undirected(A: np.ndarray) -> np.ndarray:
    """向きを畳んだ二値構造(A ∨ Aᵀ)。"""
    return np.logical_or(A, A.T)


# --------------------------------------------------------------------------- #
# build                                                                       #
# --------------------------------------------------------------------------- #
def graph_from_synapses(syn: Any, n: int | None = None, sign: float = 1.0) -> np.ndarray:
    """シナプス表 (m, 3) = (pre_id, post_id, count) を n×n の重みつき有向隣接行列にする。

    ``W[pre, post] += count * sign``。同じ (pre, post) の行は足し合わせる。
    ``n`` を省くと ``max(id) + 1``。id は 0 始まりの整数値(float で持っていてよい)
    で、範囲外・非整数・負の id は拒否する。``sign`` は抑制性シナプスを負で
    入れたいときの係数(count 自体は符号を持たない量として扱う)。
    """
    op = "graph_from_synapses"
    tab = _as_finite_float(syn, op, "syn")
    if tab.ndim != 2 or tab.shape[1] != 3:
        raise ValueError(f"{op}: syn must be an (m, 3) table of (pre_id, post_id, count), got shape {tab.shape}")
    if tab.shape[0] == 0 and n is None:
        raise ValueError(f"{op}: syn is empty and n was not given — the node count cannot be inferred")
    ids = tab[:, :2]
    if ids.size and (not np.all(ids == np.round(ids)) or ids.min() < 0):
        raise ValueError(f"{op}: pre_id / post_id must be whole numbers >= 0")
    if n is None:
        n = int(ids.max()) + 1
    n = int(n)
    if n < 1 or n > MAX_NODES:
        raise ValueError(f"{op}: n must be in 1..{MAX_NODES}, got {n}")
    if ids.size and ids.max() >= n:
        raise ValueError(f"{op}: an id ({int(ids.max())}) is out of range for n={n}")
    if not np.isfinite(float(sign)):
        raise ValueError(f"{op}: sign must be finite")
    W = np.zeros((n, n), dtype=np.float64)
    if tab.shape[0]:
        np.add.at(W, (ids[:, 0].astype(np.int64), ids[:, 1].astype(np.int64)), tab[:, 2] * float(sign))
    return W


def graph_degree_preserving_shuffle(W: Any, n_swaps: int | None = None, seed: int = 0) -> np.ndarray:
    """次数保存シャッフル(帰無モデル): 各ノードの入次数・出次数と重みの多重集合を保って辺を繋ぎ替える。

    有向 double-edge swap(Maslov & Sneppen 2002): 辺 (a→b, w1) と (c→d, w2) を
    (a→d, w1) と (c→b, w2) に替える。自己結合と重複辺を作る組は捨てる。
    ``n_swaps`` の既定は 10 × 辺数。**二値構造の次数**を保つ(重みは辺に付いて
    移動するので strength は変わりうる)。対角(自己結合)は動かさずそのまま残す。
    辺が 2 本未満なら複製を返す。
    """
    op = "graph_degree_preserving_shuffle"
    W = _as_graph(W, op)
    if seed is None or int(seed) != seed:
        raise ValueError(f"{op}: seed must be an integer")
    src, dst = np.nonzero(_binary(W))
    m = int(src.size)
    out = np.zeros_like(W)
    np.fill_diagonal(out, np.diag(W))
    if m < 2:
        out[src, dst] = W[src, dst]
        return out
    if n_swaps is None:
        n_swaps = 10 * m
    n_swaps = int(n_swaps)
    if n_swaps < 0:
        raise ValueError(f"{op}: n_swaps must be >= 0, got {n_swaps}")
    src = src.astype(np.int64).tolist()
    dst = dst.astype(np.int64).tolist()
    wts = W[np.array(src), np.array(dst)].tolist()
    present = set(zip(src, dst))
    rng = np.random.default_rng(int(seed))
    # 乱数は塊で引く(1 回ずつ引くと Python ループの大半が乱数呼び出しになる)
    picks = rng.integers(0, m, size=(max(n_swaps, 1), 2))
    for k in range(n_swaps):
        i, j = int(picks[k, 0]), int(picks[k, 1])
        a, b = src[i], dst[i]
        c, d = src[j], dst[j]
        if i == j or a == d or c == b or b == d or a == c:
            continue
        if (a, d) in present or (c, b) in present:
            continue
        present.discard((a, b))
        present.discard((c, d))
        present.add((a, d))
        present.add((c, b))
        dst[i], dst[j] = d, b
    out[np.array(src), np.array(dst)] = np.array(wts)
    return out


def graph_binarize(W: Any, thresh: float = 0.0) -> np.ndarray:
    """|W| > thresh の辺を 1.0、それ以外を 0.0 にした conn_graph(対角も同じ規則)。"""
    op = "graph_binarize"
    W = _as_graph(W, op)
    thresh = float(thresh)
    if not np.isfinite(thresh) or thresh < 0.0:
        raise ValueError(f"{op}: thresh must be a finite number >= 0, got {thresh}")
    return (np.abs(W) > thresh).astype(np.float64)


# --------------------------------------------------------------------------- #
# stats                                                                       #
# --------------------------------------------------------------------------- #
def graph_degree_table(W: Any) -> dict[str, np.ndarray]:
    """ノードごとの in_degree / out_degree(二値)と in_strength / out_strength(重み和)の表。

    度数は ``W != 0`` の本数(対角は除く)、strength は重みの和(対角は除く)。
    返りは列名 → 長さ n の配列の dict(この repo の ``table``)。
    """
    W = _as_graph(W, "graph_degree_table")
    A = _binary(W)
    Wo = W.copy()
    np.fill_diagonal(Wo, 0.0)
    return {
        "in_degree": A.sum(axis=0).astype(np.float64),
        "out_degree": A.sum(axis=1).astype(np.float64),
        "in_strength": Wo.sum(axis=0),
        "out_strength": Wo.sum(axis=1),
    }


def graph_clustering_coefficient(W: Any) -> float:
    """平均局所クラスタ係数(向きを畳んだ二値グラフ、Watts–Strogatz)。次数 < 2 のノードは 0 と数える。

    C_i = (A³)_ii / (k_i (k_i − 1))、A は対称二値。完全グラフで 1、木で 0。
    """
    W = _as_graph(W, "graph_clustering_coefficient")
    A = _undirected(_binary(W)).astype(np.float64)
    k = A.sum(axis=1)
    tri = np.einsum("ij,jk,ki->i", A, A, A)
    denom = k * (k - 1.0)
    c = np.where(denom > 0, tri / np.where(denom > 0, denom, 1.0), 0.0)
    return float(c.mean())


def graph_betweenness(W: Any) -> np.ndarray:
    """媒介中心性(Brandes 2001、二値有向、正規化なし)。ノードごとの長さ n の配列。

    ノード v の値 = Σ_{s≠v≠t} σ_st(v) / σ_st(最短路の本数比)。二値構造が対称
    (すべての辺が相互)なら無向グラフとして (s, t) と (t, s) を 1 対と数え 2 で割る
    —— 無向スター(n 個)の中心が (n−1)(n−2)/2、葉が 0 になる教科書の値。
    有向(非対称)なら順序対のまま数える。
    """
    W = _as_graph(W, "graph_betweenness")
    A = _binary(W)
    n = A.shape[0]
    nbrs = [np.nonzero(A[i])[0].tolist() for i in range(n)]
    cb = np.zeros(n, dtype=np.float64)
    for s in range(n):
        stack: list[int] = []
        pred: list[list[int]] = [[] for _ in range(n)]
        sigma = np.zeros(n, dtype=np.float64)
        sigma[s] = 1.0
        dist = np.full(n, -1, dtype=np.int64)
        dist[s] = 0
        queue = [s]
        qi = 0
        while qi < len(queue):
            v = queue[qi]
            qi += 1
            stack.append(v)
            dv = dist[v]
            for w in nbrs[v]:
                if dist[w] < 0:
                    dist[w] = dv + 1
                    queue.append(w)
                if dist[w] == dv + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = np.zeros(n, dtype=np.float64)
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += sigma[v] / sigma[w] * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]
    if np.array_equal(A, A.T):
        cb /= 2.0                                     # 無向: (s,t) と (t,s) は同じ対
    return cb


def graph_laplacian_spectrum(W: Any) -> np.ndarray:
    """向きを畳んだ二値グラフの Laplacian L = D − A の固有値(昇順、長さ n)。

    リング(n 個)で 2 − 2cos(2πk/n)、ゼロ固有値の個数 = 連結成分の数。
    """
    W = _as_graph(W, "graph_laplacian_spectrum")
    A = _undirected(_binary(W)).astype(np.float64)
    L = np.diag(A.sum(axis=1)) - A
    return np.sort(np.linalg.eigvalsh(L))


def _spectral_radius(W: np.ndarray) -> float:
    """max |λ|。**非負**で n > 400 なら疎行列の ARPACK(最大絶対値の固有値 1 本)、それ以外は密の eigvals。

    ★2026-09-20: 2,952 ノードの密 eigvals は 7 秒で、幼虫 PoC が CI(2 コア)の 600 秒枠を超えた
    (9 回呼んで 66 秒 / 92 秒)。ARPACK は 0.02 秒。ただし**符号つきの乱数行列では最大絶対値に
    収束しない**(固有値が円状に並び、隣の固有値を返す —— ガウス乱数 reservoir で実測、
    reservoir_from_graph が黙って違う半径に縮めた)。非負行列なら Perron–Frobenius で最大固有値は
    実・非負で絶対値最大なので ARPACK が確実に届く。その条件の外は密のまま(遅いが正確)。
    """
    n = W.shape[0]
    if n > 400 and np.count_nonzero(W) > 0 and bool((W >= 0.0).all()):
        try:
            import scipy.sparse as sp
            import scipy.sparse.linalg as spl
            v = spl.eigs(sp.csr_matrix(W), k=1, which="LM", return_eigenvectors=False, tol=1e-10, maxiter=20000)
            r = float(np.abs(v).max())
            if np.isfinite(r):
                return r
        except Exception:                                  # noqa: BLE001 - 未収束 / scipy 無し → 密で正確に
            pass
    return float(np.max(np.abs(np.linalg.eigvals(W))))


def graph_spectral_radius(W: Any) -> float:
    """重みつき隣接行列 W の固有値の最大絶対値(スペクトル半径)。"""
    W = _as_graph(W, "graph_spectral_radius")
    return _spectral_radius(W)


def graph_components(W: Any) -> np.ndarray:
    """弱連結成分のラベル(0 始まり、ノード番号順の初出で番号づけ)。長さ n の int64。"""
    W = _as_graph(W, "graph_components")
    A = _undirected(_binary(W))
    n = A.shape[0]
    lab = np.full(n, -1, dtype=np.int64)
    nxt = 0
    for s in range(n):
        if lab[s] >= 0:
            continue
        lab[s] = nxt
        frontier = [s]
        while frontier:
            v = frontier.pop()
            for w in np.nonzero(A[v])[0]:
                if lab[w] < 0:
                    lab[w] = nxt
                    frontier.append(int(w))
        nxt += 1
    return lab


def graph_modularity(W: Any, labels: Any) -> float:
    """有向・重みつきモジュラリティ Q(Leicht–Newman 2008)。

    Q = (1/m) Σ_ij (W_ij − k_i^out k_j^in / m) δ(c_i, c_j)、m = Σ W。全ノードが
    1 つの群なら厳密に 0。対角(自己結合)は落とす。重みは非負であること。
    """
    op = "graph_modularity"
    W = _as_graph(W, op)
    n = W.shape[0]
    lab = _as_labels(labels, op, n)
    Wo = W.copy()
    np.fill_diagonal(Wo, 0.0)
    if (Wo < 0).any():
        raise ValueError(f"{op}: modularity is defined for non-negative weights (take abs or binarize first)")
    m = float(Wo.sum())
    if m <= 0.0:
        raise ValueError(f"{op}: the graph has no edges (total weight 0), Q is undefined")
    kout = Wo.sum(axis=1)
    kin = Wo.sum(axis=0)
    same = lab[:, None] == lab[None, :]
    return float(((Wo - np.outer(kout, kin) / m) * same).sum() / m)


def graph_rich_club(W: Any, k: int) -> float:
    """rich club 係数 φ(k): 総次数 (in+out、二値) > k のノードが張る部分グラフの有向密度。

    φ = 辺数 / (r (r − 1))、r = 該当ノード数。r < 2 なら 0(NaN を返さない)。
    """
    op = "graph_rich_club"
    W = _as_graph(W, op)
    if k is None or int(k) != k or int(k) < 0:
        raise ValueError(f"{op}: k must be a non-negative integer, got {k!r}")
    A = _binary(W)
    deg = A.sum(axis=0) + A.sum(axis=1)
    rich = np.nonzero(deg > int(k))[0]
    r = int(rich.size)
    if r < 2:
        return 0.0
    sub = A[np.ix_(rich, rich)]
    return float(sub.sum()) / float(r * (r - 1))


def graph_motif_count(W: Any, motif: str = "ffl") -> float:
    """3 点モチーフの個数(二値有向、対角は除く): reciprocal / ffl / cycle3。

    reciprocal = 相互結合の対の数 (Σ A∧Aᵀ)/2、ffl = Σ_ac (A²)_ac A_ac
    (a→b, b→c, a→c)、cycle3 = tr(A³)/3。各インスタンスを 1 回だけ数える。
    """
    op = "graph_motif_count"
    W = _as_graph(W, op)
    if motif not in MOTIFS:
        raise ValueError(f"{op}: motif must be one of {MOTIFS}, got {motif!r}")
    A = _binary(W).astype(np.float64)
    if motif == "reciprocal":
        return float((A * A.T).sum() / 2.0)
    A2 = A @ A
    if motif == "ffl":
        return float((A2 * A).sum())
    return float(np.trace(A2 @ A) / 3.0)


# --------------------------------------------------------------------------- #
# reservoir                                                                   #
# --------------------------------------------------------------------------- #
def _input_weights(n: int, d: int, in_scale: float, seed: int) -> np.ndarray:
    """入力重み W_in (n, d): seed で決まる一様 (−in_scale, in_scale)。

    ★ reservoir_states と reservoir_encode の**唯一の**構成入口。別々に書くと
    「時系列で学習した読み出しを静的符号化に当てる」経路が黙って別の W_in を使う。
    """
    if seed is None or int(seed) != seed:
        raise ValueError(f"reservoir: seed must be an integer, got {seed!r}")
    rng = np.random.default_rng(int(seed))
    return rng.uniform(-in_scale, in_scale, size=(int(n), int(d)))


def _nonlinearity(name: str):
    """名前 → 要素ごとの非線形(NONLINEARITIES の検証は呼び出し側で済ませてある)。"""
    return np.tanh if name == "tanh" else (lambda z: z)


def reservoir_from_graph(W: Any, rho: float = 0.9) -> np.ndarray:
    """W をスペクトル半径が rho になるように定数倍した conn_graph(echo state の前処理)。半径 0 は拒否。"""
    op = "reservoir_from_graph"
    W = _as_graph(W, op)
    rho = float(rho)
    if not np.isfinite(rho) or rho <= 0.0:
        raise ValueError(f"{op}: rho must be a positive finite number, got {rho}")
    r = _spectral_radius(W)
    if r <= 0.0:
        raise ValueError(f"{op}: W has spectral radius 0 (nilpotent or empty) — it cannot be rescaled to {rho}")
    return W * (rho / r)


def reservoir_states(W: Any, U: Any, in_scale: float = 1.0, leak: float = 1.0,
                     nonlinearity: str = "tanh", seed: int = 0, washout: int = 0,
                     W_in: Any = None) -> np.ndarray:
    """reservoir の状態列: x_{t+1} = (1−leak) x_t + leak · f(Wᵀ x_t + W_in u_t)。返りは (T − washout, n)。

    ``U`` は (T, d) の入力列(1-D は (T, 1))。``W_in`` は seed で決まる一様 (−in_scale, in_scale)
    の (n, d) 行列。``nonlinearity`` は tanh / linear。x_0 = 0 から始め、各ステップの更新後の
    状態を並べる。``washout`` 行を先頭から捨てる(T 以上は拒否)。

    ``W_in`` を渡すと乱数の代わりにその (n, d) 行列を使う(``in_scale`` / ``seed`` は無視)——
    決まったノード群に刺激を入れる(列 = 刺激するノードの指示子)のはこちら。
    """
    op = "reservoir_states"
    W = _as_graph(W, op)
    U = _as_matrix(U, op, "U")
    n = W.shape[0]
    T, d = U.shape
    leak = float(leak)
    if not (0.0 < leak <= 1.0):
        raise ValueError(f"{op}: leak must be in (0, 1], got {leak}")
    if nonlinearity not in NONLINEARITIES:
        raise ValueError(f"{op}: nonlinearity must be one of {NONLINEARITIES}, got {nonlinearity!r}")
    in_scale = float(in_scale)
    if not np.isfinite(in_scale) or in_scale < 0.0:
        raise ValueError(f"{op}: in_scale must be a finite number >= 0, got {in_scale}")
    washout = int(washout)
    if washout < 0 or washout >= T:
        raise ValueError(f"{op}: washout must be in 0..T-1 (T={T}), got {washout}")
    if W_in is None:
        W_in = _input_weights(n, d, in_scale, seed)
    else:
        W_in = _as_matrix(W_in, op, "W_in")
        if W_in.shape != (n, d):
            raise ValueError(f"{op}: W_in must be (n, d) = ({n}, {d}) for {n} nodes and {d} input channels, "
                             f"got shape {W_in.shape}")
    f = _nonlinearity(nonlinearity)
    Wt = W.T
    x = np.zeros(n, dtype=np.float64)
    X = np.empty((T, n), dtype=np.float64)
    for t in range(T):
        x = (1.0 - leak) * x + leak * f(Wt @ x + W_in @ U[t])
        X[t] = x
    if not np.isfinite(X).all():
        raise ValueError(f"{op}: the states diverged (non-finite) — lower the spectral radius "
                         "(reservoir_from_graph) or use nonlinearity='tanh'")
    return X[washout:]


def reservoir_encode(W: Any, X: Any, steps: int = 6, in_scale: float = 0.1, leak: float = 0.3,
                     nonlinearity: str = "tanh", seed: int = 0) -> np.ndarray:
    """静的入力の一括 reservoir 符号化(分類用): X の各行を零状態から steps 回回した最終状態 (N, n)。

    行 x ごとに x_{t+1} = (1−leak) x_t + leak · f(Wᵀ x_t + W_in x) を steps 回。
    ``W_in`` は reservoir_states と同じ seed 付き一様 (−in_scale, in_scale) の (n, d)。
    行のループは書かず、1 ステップ = (N, n) @ (n, n) の行列積 1 回で全行を同時に進める。
    linear・leak 1・steps 1 なら X W_inᵀ、steps 2 なら (X W_inᵀ) W + X W_inᵀ に厳密一致。
    """
    op = "reservoir_encode"
    W = _as_graph(W, op)
    X = _as_matrix(X, op, "X")
    n = W.shape[0]
    N, d = X.shape
    steps = int(steps)
    if steps < 1:
        raise ValueError(f"{op}: steps must be >= 1, got {steps}")
    leak = float(leak)
    if not (0.0 < leak <= 1.0):
        raise ValueError(f"{op}: leak must be in (0, 1], got {leak}")
    if nonlinearity not in NONLINEARITIES:
        raise ValueError(f"{op}: nonlinearity must be one of {NONLINEARITIES}, got {nonlinearity!r}")
    in_scale = float(in_scale)
    if not np.isfinite(in_scale) or in_scale < 0.0:
        raise ValueError(f"{op}: in_scale must be a finite number >= 0, got {in_scale}")
    W_in = _input_weights(n, d, in_scale, seed)
    f = _nonlinearity(nonlinearity)
    drive = X @ W_in.T                                   # (N, n)、全ステップで同じ入力
    S = np.zeros((N, n), dtype=np.float64)
    for _ in range(steps):
        S = (1.0 - leak) * S + leak * f(S @ W + drive)   # 行ベクトル x に対する Wᵀx = x W
    if not np.isfinite(S).all():
        raise ValueError(f"{op}: the states diverged (non-finite) — lower the spectral radius "
                         "(reservoir_from_graph) or use nonlinearity='tanh'")
    return S


def ridge_readout(X: Any, Y: Any, alpha: float = 1e-3) -> np.ndarray:
    """リッジ回帰の読み出し重み (d+1, k) = (X̃ᵀX̃ + αI)⁻¹ X̃ᵀY、X̃ = [X, 1](バイアス列を付ける)。"""
    op = "ridge_readout"
    X = _as_matrix(X, op, "X")
    Y = _as_matrix(Y, op, "Y")
    if X.shape[0] != Y.shape[0]:
        raise ValueError(f"{op}: X and Y must have the same number of rows, got {X.shape[0]} and {Y.shape[0]}")
    alpha = float(alpha)
    if not np.isfinite(alpha) or alpha < 0.0:
        raise ValueError(f"{op}: alpha must be a finite number >= 0, got {alpha}")
    Xb = np.hstack([X, np.ones((X.shape[0], 1))])
    G = Xb.T @ Xb + alpha * np.eye(Xb.shape[1])
    try:
        return np.linalg.solve(G, Xb.T @ Y)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"{op}: XᵀX + αI is singular (alpha=0 with collinear columns) — raise alpha") from exc


def ridge_predict(X: Any, Wout: Any) -> np.ndarray:
    """読み出し重みで予測 (T, k) = [X, 1] · Wout。Wout は ridge_readout の (d+1, k)。"""
    op = "ridge_predict"
    X = _as_matrix(X, op, "X")
    Wout = _as_matrix(Wout, op, "Wout")
    if Wout.shape[0] != X.shape[1] + 1:
        raise ValueError(f"{op}: Wout must have {X.shape[1] + 1} rows (d + 1 for the bias), got {Wout.shape[0]}")
    return np.hstack([X, np.ones((X.shape[0], 1))]) @ Wout


# --------------------------------------------------------------------------- #
# view                                                                        #
# --------------------------------------------------------------------------- #
def _fiedler_coords(A: np.ndarray, dim: int, rng: np.random.Generator) -> np.ndarray:
    """連結な対称二値グラフ 1 つの Fiedler 座標 (n, dim)。縮退した固有空間は seed で回す。

    ★ 縮退(同じ固有値が複数)の固有ベクトルは LAPACK の返す任意の基底で、環境ごとに
    違う絵になる。ここでは同じ固有値の塊を seed 付きの直交行列で回して**決定的**にする
    (完全グラフや正多角形など対称の高いグラフで効く)。
    """
    n = A.shape[0]
    if n == 1:
        return np.zeros((1, dim))
    L = np.diag(A.sum(axis=1)) - A
    vals, vecs = np.linalg.eigh(L)
    tol = 1e-9 * max(float(vals[-1]), 1.0)
    # 固有値の塊ごとに(必要なら)基底を回す
    i = 0
    while i < n:
        j = i + 1
        while j < n and vals[j] - vals[i] <= tol:
            j += 1
        if j - i > 1 and j > 1 and i < dim + 1:
            q, _ = np.linalg.qr(rng.standard_normal((j - i, j - i)))
            vecs[:, i:j] = vecs[:, i:j] @ q
        i = j
    coords = np.zeros((n, dim))
    for c in range(dim):
        if 1 + c < n:
            v = vecs[:, 1 + c]
            v = v if v[np.argmax(np.abs(v))] >= 0 else -v     # 符号の任意性を潰す
            coords[:, c] = v
    return coords


def _unit_box(P: np.ndarray) -> np.ndarray:
    """各列を [0, 1] に伸ばす。定数の列は 0.5。"""
    lo, hi = P.min(axis=0), P.max(axis=0)
    span = hi - lo
    out = np.full_like(P, 0.5)
    ok = span > 1e-12
    out[:, ok] = (P[:, ok] - lo[ok]) / span[ok]
    return out


def graph_layout_spectral(W: Any, dim: int = 2, seed: int = 0) -> np.ndarray:
    """スペクトル配置: 向きを畳んだ Laplacian の Fiedler ベクトル(第 2..dim+1 固有ベクトル)を座標にした点群 (n, 3)、各軸 [0, 1]。

    ``dim`` は 2 か 3(2 なら z = 0)。連結成分ごとに配置してから格子に並べる —— 非連結の
    グラフでは零固有空間が縮退して Fiedler ベクトルが成分を分けるとは限らないので、
    成分は明示的に分ける(成分内は箱の 0.3 倍、成分間は 1 の間隔)。
    """
    op = "graph_layout_spectral"
    W = _as_graph(W, op)
    if dim not in (2, 3):
        raise ValueError(f"{op}: dim must be 2 or 3, got {dim!r}")
    dim = int(dim)
    A = _undirected(_binary(W)).astype(np.float64)
    comp = graph_components(W)
    ncomp = int(comp.max()) + 1
    rng = np.random.default_rng(int(seed))
    n = A.shape[0]
    P = np.zeros((n, dim))
    if ncomp == 1:
        P[:] = _unit_box(_fiedler_coords(A, dim, rng))
    else:
        g = int(np.ceil(np.sqrt(ncomp)))
        for c in range(ncomp):
            idx = np.nonzero(comp == c)[0]
            local = _unit_box(_fiedler_coords(A[np.ix_(idx, idx)], dim, rng)) * 0.3
            cell = np.array([c % g, c // g, (c // (g * g))][:dim], dtype=np.float64)
            P[idx] = local + cell
        # ★ 軸ごとに [0,1] へ伸ばすと(成分が横一列のとき)縦だけ 3 倍に伸びて
        #   成分内の距離が成分間より大きくなる —— 全体は**一様に**縮める。
        P -= P.min(axis=0)
        P /= max(float(P.max()), 1e-12)
    out = np.zeros((n, 3))
    out[:, :dim] = P
    return out


def graph_edges_as_lines(W: Any, P: Any, thresh: float = 0.0) -> dict[str, np.ndarray]:
    """辺を線分の表にする(Studio で点群に重ねる出口): 列 pre / post / x0 y0 z0 / x1 y1 z1 / weight。

    ``P`` は graph_layout_spectral の (n, 3)(または (n, 2)、z = 0 を足す)。
    |W| > thresh の辺だけ、対角(自己結合)は長さ 0 なので出さない。
    """
    op = "graph_edges_as_lines"
    W = _as_graph(W, op)
    n = W.shape[0]
    pts = _as_finite_float(P, op, "P")
    if pts.ndim != 2 or pts.shape[0] != n or pts.shape[1] not in (2, 3):
        raise ValueError(f"{op}: P must be (n, 3) or (n, 2) coordinates for the {n} nodes, got shape {pts.shape}")
    if pts.shape[1] == 2:
        pts = np.hstack([pts, np.zeros((n, 1))])
    thresh = float(thresh)
    if not np.isfinite(thresh) or thresh < 0.0:
        raise ValueError(f"{op}: thresh must be a finite number >= 0, got {thresh}")
    keep = np.abs(W) > thresh
    np.fill_diagonal(keep, False)
    src, dst = np.nonzero(keep)
    return {
        "pre": src.astype(np.int64), "post": dst.astype(np.int64),
        "x0": pts[src, 0], "y0": pts[src, 1], "z0": pts[src, 2],
        "x1": pts[dst, 0], "y1": pts[dst, 1], "z1": pts[dst, 2],
        "weight": W[src, dst],
    }


def graph_adjacency_image(W: Any, order: str = "none", log: bool = True) -> np.ndarray:
    """隣接行列を [0, 1] の画像 (n, n) にする。order = none / degree(総次数の降順)/ component(成分順)。

    値は |W| を(log なら log1p してから)最大値で割る。全零なら全零の画像。
    """
    op = "graph_adjacency_image"
    W = _as_graph(W, op)
    if order not in ADJACENCY_ORDERS:
        raise ValueError(f"{op}: order must be one of {ADJACENCY_ORDERS}, got {order!r}")
    n = W.shape[0]
    if order == "degree":
        A = _binary(W)
        perm = np.argsort(-(A.sum(axis=0) + A.sum(axis=1)), kind="stable")
    elif order == "component":
        perm = np.argsort(graph_components(W), kind="stable")
    else:
        perm = np.arange(n)
    img = np.abs(W[np.ix_(perm, perm)])
    if log:
        img = np.log1p(img)
    peak = float(img.max())
    return img / peak if peak > 0.0 else np.zeros_like(img)


# --------------------------------------------------------------------------- #
# activity —— 状態列 (T, n) を「いつ・どこで点いたか」に読む(2026-09-20)           #
# --------------------------------------------------------------------------- #
#: points_activity_video の出力の上限(要素数、F×H×W×3)。1 GB の float64 を超えない。
MAX_VIDEO_ELEMENTS = 2 ** 27


def _as_points(P: Any, op: str, n: int | None = None, name: str = "P") -> np.ndarray:
    """(n, 3) の座標(``points``)。(n, 2) は z = 0 を足す。``n`` を渡せば行数を照合する。"""
    pts = _as_finite_float(P, op, name)
    if pts.ndim != 2 or pts.shape[1] not in (2, 3):
        raise ValueError(f"{op}: {name} must be (n, 3) or (n, 2) coordinates, got shape {pts.shape}")
    if n is not None and pts.shape[0] != n:
        raise ValueError(f"{op}: {name} has {pts.shape[0]} rows but the states have {n} nodes")
    if pts.shape[1] == 2:
        pts = np.hstack([pts, np.zeros((pts.shape[0], 1))])
    return pts


def _activity(X: np.ndarray, thresh: float, op: str) -> tuple[np.ndarray, float]:
    """|X| と、点いた/点かないを分ける**1 つの**尺度(全体の最大値 × thresh)。"""
    thresh = float(thresh)
    if not (0.0 < thresh <= 1.0):
        raise ValueError(f"{op}: thresh must be in (0, 1], got {thresh}")
    A = np.abs(X)
    return A, thresh * float(A.max())


def graph_activation_latency(X: Any, thresh: float = 0.1) -> np.ndarray:
    """各ノードが初めて「点いた」ステップ(0 始まり)の列 (n,)、整数。点かなかったノードは −1。

    ``X`` は reservoir_states の (T, n)。「点いた」= |x| ≥ **全体の最大値** × thresh(thresh は
    (0, 1])。尺度はノードごとでなく 1 つ —— ノードごとに伸ばすと、ほとんど動かないノードの
    丸め屑も「点いた」になる。全零の X はすべて −1。
    """
    op = "graph_activation_latency"
    X = _as_matrix(X, op, "X")
    A, level = _activity(X, thresh, op)
    lat = np.full(X.shape[1], -1, dtype=np.int64)
    if level <= 0.0:
        return lat
    on = A >= level
    hit = on.any(axis=0)
    lat[hit] = on.argmax(axis=0)[hit]
    return lat


def graph_activity_spread(X: Any, P: Any, source: Any, thresh: float = 0.1) -> dict[str, np.ndarray]:
    """活動がどこまで広がったかの時系列の表: 列 step / mean_distance / active_fraction / source_fraction。

    ``X`` = (T, n) の状態列、``P`` = (n, 3) の座標、``source`` = 刺激したノードの指示子(長さ n の
    整数、非零 = 刺激。1 つ以上)。
    mean_distance[t] = Σ|x_i(t)| ‖P_i − c‖ / Σ|x_i(t)|(c = 刺激ノードの重心、|x| で重みづけた
    活動の平均距離、単位は P と同じ。活動が全零のステップは 0)。
    active_fraction[t] = |x_i(t)| ≥ 全体最大 × thresh のノードの割合。
    source_fraction[t] = 活動のうち刺激ノードにある分 Σ_source |x| / Σ|x|(全零なら 0)。
    """
    op = "graph_activity_spread"
    X = _as_matrix(X, op, "X")
    T, n = X.shape
    pts = _as_points(P, op, n)
    src = _as_labels(source, op, n, "source") != 0
    if not src.any():
        raise ValueError(f"{op}: source marks no node (all zero) — mark the stimulated nodes with a non-zero label")
    A, level = _activity(X, thresh, op)
    c = pts[src].mean(axis=0)
    dist = np.linalg.norm(pts - c, axis=1)
    tot = A.sum(axis=1)
    ok = tot > 0.0
    mean_distance = np.zeros(T)
    source_fraction = np.zeros(T)
    mean_distance[ok] = (A[ok] @ dist) / tot[ok]
    source_fraction[ok] = A[ok][:, src].sum(axis=1) / tot[ok]
    active_fraction = (A >= level).mean(axis=1) if level > 0.0 else np.zeros(T)
    return {"step": np.arange(T, dtype=np.int64), "mean_distance": mean_distance,
            "active_fraction": active_fraction, "source_fraction": source_fraction}


def _orbit_camera(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    """回転台のカメラ(world → view の 3×3): yaw は世界の z 軸まわり、pitch はそこへ傾ける。
    行 = 画面の右・画面の下・奥(値が大きいほど遠い)。yaw = pitch = 0 で +y を見て +z が上。"""
    ya, pa = np.radians(float(yaw_deg)), np.radians(float(pitch_deg))
    cy, sy, cp, sp = np.cos(ya), np.sin(ya), np.cos(pa), np.sin(pa)
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, sp, -cp], [0.0, cp, sp]])
    return rx @ rz


def _splat(img: np.ndarray, pts: np.ndarray, cols: np.ndarray, cam: np.ndarray,
           center: np.ndarray, radius: float, px: int) -> None:
    """正射影して奥から順に px×px の点を塗る(画家のアルゴリズム: 手前が勝つ)。"""
    H, Wd = img.shape[:2]
    V = (pts - center) @ cam.T
    sc = 0.48 * H / radius
    xy = V[:, :2] * sc + np.array([Wd / 2.0, H / 2.0])
    order = np.argsort(V[:, 2])[::-1]
    xi = np.floor(xy[order, 0]).astype(np.int64) - px // 2
    yi = np.floor(xy[order, 1]).astype(np.int64) - px // 2
    Co = cols[order]
    for dy in range(px):
        for dx in range(px):
            xs, ys = xi + dx, yi + dy
            ok = (xs >= 0) & (xs < Wd) & (ys >= 0) & (ys < H)
            img[ys[ok], xs[ok]] = Co[ok]


def points_activity_video(P: Any, X: Any, colors: Any = None, size: int = 480, aspect: float = 0.75,
                          pitch: float = 15.0, yaw_start: float = 0.0, yaw_span: float = 360.0,
                          substeps: int = 1, point_px: int = 2, gain: float = 100.0,
                          background: Any = None, views: Any = None) -> np.ndarray:
    """点群に活動を載せて回す色動画 (F, H, W, 3)、値 [0, 1]。F = T × substeps、H = size、W = size × aspect。

    ``views`` に (yaw, pitch) の並び(度)を渡すと**回さずに**、その方向から見たコマを横に並べる
    (W = views 数 × size × aspect + 4 px の隙間、yaw_start / yaw_span は使わない)。同じ瞬間を
    複数の方向から見比べる用(例: 背側 (0, 0) / 側面 (90, 0) / 体軸方向 (0, 90))。

    ``P`` = (n, 3) の座標、``X`` = (T, n) の状態列(reservoir_states)。コマ k は時刻 k / substeps の
    状態(隣り合うステップの線形補間)を、yaw = yaw_start + yaw_span × k / F のカメラで正射影する。
    明るさ b = log1p(gain · |x| / max|X|) / log1p(gain) —— **尺度は全コマで 1 つ**(コマごとに伸ばすと
    動いていないものがちらつく)。ノードの色 = ``colors``((n, 3)、[0, 1]、None なら白)× (0.2 + 0.8 b)、
    b > 0.5 のノードは一回り大きく明るく塗る。``background`` は (m, 3) の点群を薄い灰で先に敷く
    (脳の全 soma の上に選んだノードを載せる、など)。画角は P と background を合わせた箱で決める。
    出力は F×H×W×3 ≤ MAX_VIDEO_ELEMENTS(2^27)に制限する。
    """
    op = "points_activity_video"
    X = _as_matrix(X, op, "X")
    T, n = X.shape
    pts = _as_points(P, op, n)
    size = int(size)
    aspect = float(aspect)
    substeps = int(substeps)
    point_px = int(point_px)
    gain = float(gain)
    if size < 8:
        raise ValueError(f"{op}: size must be >= 8 pixels, got {size}")
    if not np.isfinite(aspect) or aspect <= 0.0:
        raise ValueError(f"{op}: aspect must be a positive number, got {aspect}")
    if substeps < 1:
        raise ValueError(f"{op}: substeps must be >= 1, got {substeps}")
    if point_px < 1:
        raise ValueError(f"{op}: point_px must be >= 1, got {point_px}")
    if not np.isfinite(gain) or gain <= 0.0:
        raise ValueError(f"{op}: gain must be a positive number, got {gain}")
    for nm, v in (("pitch", pitch), ("yaw_start", yaw_start), ("yaw_span", yaw_span)):
        if not np.isfinite(float(v)):
            raise ValueError(f"{op}: {nm} must be finite, got {v!r}")
    Wd = max(8, int(round(size * aspect)))
    F = T * substeps
    if views is not None:
        vw = np.asarray(views, dtype=np.float64)
        if vw.ndim != 2 or vw.shape[1] != 2 or vw.shape[0] < 1 or not np.isfinite(vw).all():
            raise ValueError(f"{op}: views must be a non-empty list of finite (yaw, pitch) pairs in degrees, got {views!r}")
        cams = [_orbit_camera(y, pt) for y, pt in vw]
        GAP = 4
        Wtot = len(cams) * Wd + GAP * (len(cams) - 1)
    else:
        cams = None
        Wtot = Wd
    if F * size * Wtot * 3 > MAX_VIDEO_ELEMENTS:
        raise ValueError(f"{op}: {F} frames of {size}x{Wtot} would be {F * size * Wtot * 3} elements, over the "
                         f"{MAX_VIDEO_ELEMENTS} cap — fewer steps / substeps / views or a smaller size")
    if colors is None:
        base = np.full((n, 3), 0.92)
    else:
        base = _as_finite_float(colors, op, "colors")
        if base.shape != (n, 3):
            raise ValueError(f"{op}: colors must be (n, 3) = ({n}, 3) RGB in [0, 1], got shape {base.shape}")
        if base.min() < 0.0 or base.max() > 1.0:
            raise ValueError(f"{op}: colors must lie in [0, 1], got [{base.min()}, {base.max()}]")
    bg_pts = None if background is None else _as_points(background, op, None, "background")
    allp = pts if bg_pts is None else np.vstack([pts, bg_pts])
    center = 0.5 * (allp.min(axis=0) + allp.max(axis=0))
    radius = float(np.linalg.norm(allp - center, axis=1).max()) or 1.0
    peak = float(np.abs(X).max())
    BG = np.array([0.06, 0.07, 0.10])
    DIM = np.array([0.17, 0.18, 0.22])
    out = np.empty((F, size, Wtot, 3), dtype=np.float64)

    def paint(img, cam, b):
        img[:] = BG
        if bg_pts is not None:
            _splat(img, bg_pts, np.broadcast_to(DIM, (bg_pts.shape[0], 3)), cam, center, radius, 1)
        cols = base * (0.2 + 0.8 * b[:, None])
        _splat(img, pts, cols, cam, center, radius, point_px)
        hot = b > 0.5
        if hot.any():
            _splat(img, pts[hot], np.minimum(cols[hot] * 1.3, 1.0), cam, center, radius, point_px + 2)

    for k in range(F):
        t_f = k / substeps
        t0 = int(np.floor(t_f))
        a = t_f - t0
        x = X[t0] if a == 0.0 else (1.0 - a) * X[t0] + a * X[min(t0 + 1, T - 1)]
        b = np.log1p(gain * np.abs(x) / peak) / np.log1p(gain) if peak > 0.0 else np.zeros(n)
        if cams is None:
            paint(out[k], _orbit_camera(yaw_start + yaw_span * k / F, pitch), b)
        else:
            out[k] = 0.02
            for j, cam in enumerate(cams):
                x0 = j * (Wd + GAP)
                paint(out[k, :, x0:x0 + Wd], cam, b)
    return out


# --------------------------------------------------------------------------- #
# 層を通す・次元を数える(2026-09-21、動きの量子化 PoC)                            #
# --------------------------------------------------------------------------- #
#: ``graph_layer_propagate`` の活性化。linear は閉形式の検算用、tanh は飽和する連続値、
#: kwta は「上位 active_frac だけ発火」(疎な符号 —— 発火する組み合わせの空間を見る)。
ACTIVATIONS: tuple[str, ...] = ("linear", "tanh", "kwta")


def _as_layer_labels(labels: Any, n: int, op: str) -> np.ndarray:
    lab = np.asarray(labels)
    if lab.ndim != 1 or lab.shape[0] != n:
        raise ValueError(f"{op}: labels must be one integer per node (length {n}), got shape {lab.shape}")
    if lab.dtype.kind == "b" or not np.issubdtype(lab.dtype, np.integer):
        if lab.dtype.kind == "f" and np.all(np.isfinite(lab)) and np.all(lab == np.rint(lab)):
            lab = lab.astype(np.int64)
        else:
            raise ValueError(f"{op}: labels must be integers (layer ids 0..L-1), got dtype {lab.dtype}")
    lab = lab.astype(np.int64)
    if lab.min() < 0:
        raise ValueError(f"{op}: labels must be >= 0, got min {lab.min()}")
    L = int(lab.max()) + 1
    missing = [k for k in range(L) if not np.any(lab == k)]
    if missing:
        raise ValueError(f"{op}: layer ids must be consecutive 0..{L - 1}; empty layers {missing}")
    return lab


def graph_block_shuffle(W: Any, labels: Any, seed: int = 0) -> np.ndarray:
    """層(ラベル)のブロックごとに**送り手を混ぜた**対照の ``conn_graph``: 各受け手が受ける重みの多重集合と
    層間の総結線量は保ったまま、「誰から」だけを壊す。

    ``graph_degree_preserving_shuffle`` が全体の次数列を保つのに対し、こちらは**層構造を保つ**(脳 → 首 → 腹髄 →
    筋 のブロックは動かさず、ブロックの中で行を並べ替える)。層の大きさと収束(fan-in)の効果を残して
    「配線の特異性」だけを消した対照として使う。同じ ``seed`` で再現。
    """
    op = "graph_block_shuffle"
    A = _as_graph(W, op)
    lab = _as_layer_labels(labels, A.shape[0], op)
    rng = np.random.default_rng(int(seed))
    out = np.zeros_like(A)
    L = int(lab.max()) + 1
    for a in range(L):
        src = np.nonzero(lab == a)[0]
        perm = rng.permutation(len(src))
        for c in range(L):
            dst = np.nonzero(lab == c)[0]
            out[np.ix_(src, dst)] = A[np.ix_(src[perm], dst)]
    return out


def graph_layer_propagate(W: Any, labels: Any, U: Any, activation: str = "kwta", active_frac: float = 0.1,
                          gain: float = 1.0) -> np.ndarray:
    """層 0 の状態 ``U`` (N, n_0) を、ブロック ``W[layer a → layer a+1]`` で**前向きに一段ずつ**通した全層の状態
    ``(N, n)``(``matrix``、列はノード順で層 0 の列は ``U`` そのもの)。

    受け手ごとに入力重みの和を 1 に正規化してから重みつき和を取り(層の大きさに依らない)、``activation`` で
    活性化する: ``"linear"`` はそのまま(平均絶対値を ``gain`` に)、``"tanh"`` は飽和、``"kwta"`` は各刺激で
    入力が上位 ``active_frac`` の受け手だけが(閾値上の余剰で)発火し、平均が 1 になるよう正規化する。
    層をまたぐ結線(層 a → a+2)と層内の再帰は**使わない**(前向きの一段ごとの写像だけを見る道具)。
    """
    op = "graph_layer_propagate"
    A = _as_graph(W, op)
    n = A.shape[0]
    lab = _as_layer_labels(labels, n, op)
    X0 = _as_matrix(U, op, "U")
    if activation not in ACTIVATIONS:
        raise ValueError(f"{op}: activation must be one of {ACTIVATIONS}, got {activation!r}")
    fr = float(active_frac)
    if not np.isfinite(fr) or not 0.0 < fr <= 1.0:
        raise ValueError(f"{op}: active_frac must be in (0, 1], got {active_frac!r}")
    g = float(gain)
    if not np.isfinite(g) or g <= 0.0:
        raise ValueError(f"{op}: gain must be a positive finite number, got {gain!r}")
    L = int(lab.max()) + 1
    n0 = int((lab == 0).sum())
    if X0.shape[1] != n0:
        raise ValueError(f"{op}: U must have one column per layer-0 node ({n0}), got {X0.shape[1]}")
    out = np.zeros((X0.shape[0], n))
    out[:, lab == 0] = X0
    x = X0
    for a in range(L - 1):
        src = lab == a
        dst = lab == a + 1
        B = A[src][:, dst]
        col = B.sum(axis=0)
        B = B / np.maximum(col, 1e-300)[None, :]
        u = x @ B
        if activation == "linear":
            x = u / max(float(np.abs(u).mean()), 1e-300) * g
        elif activation == "tanh":
            x = np.tanh(u / max(float(np.abs(u).mean()), 1e-300) * g)
        else:
            thr = np.quantile(u, 1.0 - fr, axis=1, keepdims=True)
            x = np.where(u >= thr, u - thr, 0.0)
            x = x / max(float(x.mean()), 1e-300) * g
        out[:, dst] = x
    return out


def states_participation_ratio(X: Any) -> float:
    """状態列 ``X`` (N, n) の**実効次元** = participation ratio ``PR = (Σλ)² / Σλ²``(λ は共分散の固有値、
    Gao et al. 2017)。全列が独立で同じ分散なら n、1 本の方向に乗っていれば 1。

    標本数 N に依存する(N が小さいと PR ≤ N に頭打ち)ので、比べるときは N を揃える。定数(分散 0)なら 0。
    """
    op = "states_participation_ratio"
    A = _as_matrix(X, op, "X")
    Xc = A - A.mean(axis=0, keepdims=True)
    G = Xc @ Xc.T if Xc.shape[0] < Xc.shape[1] else Xc.T @ Xc
    lam = np.clip(np.linalg.eigvalsh(G), 0.0, None)
    s = float(lam.sum())
    return float(s * s / float((lam ** 2).sum())) if s > 0.0 else 0.0


def states_layer_dimension(X: Any, labels: Any) -> dict[str, np.ndarray]:
    """層ごとの実効次元の表: 列 layer / n / participation_ratio / ratio(= PR / n)。

    ``X`` = ``graph_layer_propagate`` の返り (N, n)、``labels`` = ノードの層 id。「脳 → 首 → 腹髄 → 筋」で
    次元がどこで落ちるか(動きの量子化)を 1 つの数式で読む。
    """
    op = "states_layer_dimension"
    A = _as_matrix(X, op, "X")
    lab = _as_layer_labels(labels, A.shape[1], op)
    L = int(lab.max()) + 1
    ns, prs = [], []
    for a in range(L):
        cols = lab == a
        ns.append(int(cols.sum()))
        prs.append(states_participation_ratio(A[:, cols]))
    ns_arr = np.asarray(ns, dtype=np.int64)
    pr_arr = np.asarray(prs, dtype=np.float64)
    return {"layer": np.arange(L, dtype=np.int64), "n": ns_arr, "participation_ratio": pr_arr,
            "ratio": pr_arr / ns_arr}


# --------------------------------------------------------------------------- #
# 回路 —— コンダクタンスで動く段階電位ニューロンを、配線そのものの上で回す         #
# --------------------------------------------------------------------------- #
def graph_conductance_states(W: Any, drive: Any, dt_s: float = 0.001, tau_s: float = 0.02,
                             e_rest: float = 0.0, e_exc: float = 1.0, e_inh: float = -1.0,
                             release: str = "relu", v_half: float = 0.5, slope: float = 4.0,
                             gain: float = 1.0, v0: Any = None) -> np.ndarray:
    """配線 ``W`` を**そのまま回路として回した**膜電位の時系列 ``(T, n)``(``matrix``、学習なし)。

    ハエの視葉で「掛け算」に見えていた非線形の正体は、樹状突起のコンダクタンス比だった
    (Groschner ら 2022: 定常では ``Vm = Σgᵢ Eᵢ / Σgᵢ``)。同じ形の式が、コネクトームを
    配線として固定した全脳モデルの標準形でもある(Lappalainen ら 2024:
    ``τᵢ V̇ᵢ = −Vᵢ + Σ sᵢⱼ + V_rest``)。この op はその**動的な版**を、``conn_graph``
    1 枚と外部入力 1 枚だけで回す:

        τ dVᵢ/dt = −(Vᵢ − e_rest) + g⁺ᵢ (e_exc − Vᵢ) + g⁻ᵢ (e_inh − Vᵢ)

    ``g⁺`` は ``W`` の**正の重み**、``g⁻`` は**負の重み**の絶対値を、前シナプス側の
    放出 ``f(V)`` で重みづけて足したもの(``drive`` の正負も同じ向きに足す)。重みは
    与えられたまま使う —— **学習も当てはめも一切しない**。時定数が入力で縮む
    (実効 τ = ``τ/(1+g⁺+g⁻)``)ので、これは liquid time-constant 型の力学そのものだが、
    パラメータは配線と定数だけで、勾配で決めた数は 1 つも無い。

    W: ``(n, n)`` の重みつき隣接行列(``W[pre, post]``、正 = 興奮性、負 = 抑制性)。
    drive: ``(T, n)`` の外部入力。正はそのノードを ``e_exc`` へ、負は ``e_inh`` へ引く
      コンダクタンスとして入る(電流ではない —— 電流だと下の有界性が壊れる)。
    dt_s / tau_s: 刻みと膜時定数[秒]。e_rest / e_exc / e_inh: 静止電位と 2 つの反転電位。
    release: 前シナプス放出 ``f(V)``。``"relu"`` は ``gain·max(V, 0)``、``"sigmoid"`` は
      ``gain/(1+exp(−slope(V−v_half)))``。**どちらも非負**で、負のコンダクタンス
      (物理的に存在しない)を作らない —— それが下の有界性の前提。
    v_half / slope: シグモイドの半値と傾き。gain: 放出の利得(非負)。
    v0: 初期状態 ``(n,)``。既定は全ノード ``e_rest``。

    各段は**コンダクタンスを固定した厳密解**で進める(``V ← V∞ + (V − V∞)e^{−dt·g_tot/τ}``)
    ので、刻みを粗くしても発散しない。

    閉じた式で検査できること:

    * **有界性**: 放出が非負である限り、``V∞`` は 3 つの反転電位の**凸結合**なので
      ``[min(e_rest, e_exc, e_inh), max(...)]`` の中にある。各段は ``V`` をその
      ``V∞`` へ指数で寄せるだけなので、**箱の中から始めれば必ず箱の中に留まり、
      箱の外から始めても外へは行かず箱へ向かう**。どんな配線・どんな入力でも
      発散しない、が構造で保証される(``v0`` の既定は ``e_rest`` = 箱の中)。
    * **減衰**: 入力も結合も無ければ ``V(t) = e_rest + (V₀ − e_rest)e^{−t/τ}`` ちょうど。
    * **定常**: 一定の入力 ``d > 0`` を 1 ノードに入れると ``V∞ = (e_rest + d·e_exc)/(1 + d)``、
      そこへ向かう実効時定数は ``τ/(1 + d)`` ちょうど(入力で時定数が縮む、の数値)。

    **ValueError**: 正方でない / 非有限の ``W``、``(T, n)`` でない ``drive``、
    非正の ``dt_s`` / ``tau_s``、負の ``gain``、未知の ``release``、長さの合わない ``v0``。
    """
    op = "graph_conductance_states"
    A = _as_graph(W, op)
    n = A.shape[0]
    D = _as_matrix(drive, op, "drive")
    if D.shape[1] != n:
        raise ValueError(f"{op}: drive has {D.shape[1]} column(s) but the graph has {n} nodes — "
                         "one column per node is required (rows are time)")
    if D.shape[0] < 1:
        raise ValueError(f"{op}: drive has no rows (no time samples)")
    dt = float(dt_s)
    tau = float(tau_s)
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError(f"{op}: dt_s must be a positive finite number, got {dt_s!r}")
    if not np.isfinite(tau) or tau <= 0.0:
        raise ValueError(f"{op}: tau_s must be a positive finite number, got {tau_s!r}")
    if release not in RELEASES:
        raise ValueError(f"{op}: release must be one of {RELEASES}, got {release!r}")
    g0 = float(gain)
    if not np.isfinite(g0) or g0 < 0.0:
        raise ValueError(f"{op}: gain must be a non-negative finite number, got {gain!r}")
    for nm, v in (("e_rest", e_rest), ("e_exc", e_exc), ("e_inh", e_inh),
                  ("v_half", v_half), ("slope", slope)):
        if not np.isfinite(float(v)):
            raise ValueError(f"{op}: {nm} must be finite, got {v!r}")
    er, ee, ei = float(e_rest), float(e_exc), float(e_inh)
    if v0 is None:
        V = np.full(n, er, dtype=np.float64)
    else:
        V = _as_finite_float(v0, op, "v0").ravel()
        if V.size != n:
            raise ValueError(f"{op}: v0 has {V.size} entries but the graph has {n} nodes")
        V = V.astype(np.float64, copy=True)
    Wp = np.maximum(A, 0.0)
    Wn = np.maximum(-A, 0.0)
    out = np.empty((D.shape[0], n), dtype=np.float64)
    for t in range(D.shape[0]):
        if release == "relu":
            s = g0 * np.maximum(V, 0.0)
        else:
            s = g0 / (1.0 + np.exp(-float(slope) * (V - float(v_half))))
        ge = s @ Wp + np.maximum(D[t], 0.0)
        gi = s @ Wn + np.maximum(-D[t], 0.0)
        gt = 1.0 + ge + gi
        vinf = (er + ge * ee + gi * ei) / gt
        V = vinf + (V - vinf) * np.exp(-dt * gt / tau)
        out[t] = V
    return out
