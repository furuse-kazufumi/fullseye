"""非構造点群の法線を大域一貫に向き付け(Hoppe の MST 伝播)。

各点の PCA 法線(近傍共分散の最小固有ベクトル)は**符号未定**で、隣接点どうしの向きが
バラバラになる。ここでは Hoppe et al. (SIGGRAPH 1992) の Riemannian graph 法で
kNN グラフ上に重み ``1 - |n_i·n_j|`` の最小全域木(MST)を張り、最外点(または
``seed_dir`` で与えた基準)を種として木を辿りながら隣接法線の符号を揃える。重みは
「接平面がよく揃った辺ほど安く」なるため、薄い構造や鋭いエッジを跨がずに滑らかな面を
たどって伝播する。

**既存法線モジュールとの違い(固有価値, honest)**:
  - ``pointcloud.estimate_normals`` / ``match3d.estimate_point_normals`` … *viewpoint*
    (カメラ位置 or 重心)基準の向き付け。単一視点から全点が見える 2.5D や凸形状には効くが、
    全周をサンプルした閉曲面(球・トーラス・非凸)では 1 視点では裏面が見えず破綻する。
  - ``curvature3d.estimate_normals`` … 近傍重心から離れる向きヒューリスティクス。開いた面や
    平面では実質**向き未定**(平面では重心方向が面内 → 符号が定まらない)。
  - ``range_image.normals_from_depth`` … organized 深度専用(カメラ由来の向きが最初からある)。
  - **本モジュール** … *視点に依存しない* 大域伝播。閉曲面や非凸でも局所的な面の滑らかさだけを
    頼りに全点の向きを揃える。得た向き付き法線を ``curvature3d.shape_index`` に渡すと凹/凸符号が
    正しく出る(凸球=cap → +1・凹球=cup → −1。wave7 監査 [2] の実ギャップを埋める)。

限界: MST 伝播はグラフが連結な範囲でしか一貫させられない(分断されたクラスタは各成分ごとに
独立に種を取り向き付ける — 成分間の相対向きは保証しない)。薄板を挟んで表裏が近接する(kNN が
裏面に漏れる)ような病的形状では伝播が裏へ飛ぶことがあり、これは近傍数 k とサンプル密度に依存する。

Reference (public): H. Hoppe, T. DeRose, T. Duchamp, J. McDonald, W. Stuetzle,
"Surface Reconstruction from Unorganized Points", SIGGRAPH 1992.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import minimum_spanning_tree, connected_components

__all__ = ["estimate_normals", "orient_normals", "estimate_oriented_normals"]

# 種の向き付けで「基準方向と法線が(ほぼ)直交=向きが原理的に定まらない」と判定する
# コサインしきい値。単位法線どうしの内積は無次元(コサイン)なのでスケール不変。
_PERP_COS = 0.1

# 連結成分の大域符号を seed_dir で決めるときの「一貫度」しきい値。成分全法線の
# seed_dir 射影について ``|mean(proj)| / mean(|proj|)`` を測り、これ以上なら「単一の
# 大域符号が定義できる面(平面・開いた面, あるいは seed_dir に沿った向き)」とみなして
# bulk の符号で一括整合する。未満なら閉曲面(球など)で符号が一意でないと判断する。
# 平面=1.0 / 球≈0 と大きく分離するので 0.5 で頑健に弁別できる(単位法線ゆえスケール不変)。
_COHERENCE = 0.5


def _as_points(points) -> np.ndarray:
    """入力を (N,3) の float 配列へ検証。fail-closed(形状不正/非有限は ValueError)。"""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points must be (N, 3), got shape {P.shape}")
    if not np.all(np.isfinite(P)):
        raise ValueError("points contains non-finite values")
    return P


def _as_normals(normals, n: int) -> np.ndarray:
    """法線を (n,3) 単位ベクトルへ検証・正規化。fail-closed(形状不正/非有限/ゼロ長)。"""
    N = np.asarray(normals, np.float64)
    if N.shape != (n, 3):
        raise ValueError(f"normals must be ({n}, 3), got shape {N.shape}")
    if not np.all(np.isfinite(N)):
        raise ValueError("normals contains non-finite values")
    mag = np.linalg.norm(N, axis=1, keepdims=True)
    if np.any(mag < 1e-12):
        raise ValueError("normals contains a zero-length vector (undefined direction)")
    return N / mag


def _knn(P: np.ndarray, k: int):
    """(N,3) → 各点の近傍 index (自身を含む k+1 まで, 端数は N で頭打ち)。→ (N, kq) int。"""
    kq = min(k + 1, len(P))
    _, idx = cKDTree(P).query(P, k=kq)
    return np.atleast_2d(idx)


def estimate_normals(points, k: int = 20) -> np.ndarray:
    """PCA(近傍共分散の最小固有ベクトル)による**向き未定**の単位法線。→ (N,3)。

    各点の k 近傍(自身含む)の共分散行列の最小固有値方向が局所面の法線。符号は
    未定(``eigh`` 依存)なので、大域一貫させるには :func:`orient_normals` を続けて掛ける。
    縮退(点数 < k)は fail-closed(ValueError)。

    Args:
        points: (N,3) の点群。
        k: 近傍数(自身を除く目安)。
    Returns:
        (N,3) の単位法線(向き未定)。
    """
    P = _as_points(points)
    n = len(P)
    if n < k:
        raise ValueError(f"need at least k={k} points for normal estimation, got {n}")
    idx = _knn(P, k)
    nb = P[idx]                                   # (N, kq, 3)
    c = nb - nb.mean(1, keepdims=True)
    cov = np.einsum("nki,nkj->nij", c, c)         # 各点の近傍共分散 (N,3,3)
    _, V = np.linalg.eigh(cov)                    # 昇順固有値
    normals = V[:, :, 0]                          # 最小固有値方向 = 法線
    mag = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(mag, 1e-12)


def _orient_seed(N: np.ndarray, seed: int, refdir) -> None:
    """種点の法線を基準方向 refdir に整合(in-place)。直交/未定は最大成分を正に(決定的)。"""
    ns = N[seed]
    if refdir is not None:
        proj = float(np.dot(ns, refdir))
        if abs(proj) > _PERP_COS:                 # 非直交: 基準向きへ揃える
            if proj < 0.0:
                N[seed] = -ns
            return
    # 縮退(平面など基準⊥法線)or 基準なし: 最大成分の符号を正にして決定的に固定
    j = int(np.argmax(np.abs(ns)))
    if ns[j] < 0.0:
        N[seed] = -ns


def orient_normals(points, normals, k: int = 20, seed_dir=None) -> np.ndarray:
    """Hoppe 法で法線を**大域一貫**に向き付け(MST 伝播)。→ (N,3)。

    kNN グラフ上に重み ``1 - |n_i·n_j|``(接平面が揃うほど安い)の最小全域木を張り、
    種から木を BFS しながら親と符号が逆の子を反転させる。種は ``seed_dir`` 指定時は
    その向きに最も突き出た点(向きを ``seed_dir`` に整合)、未指定時は**最外点**(重心から
    最遠, 向きは外向き=重心から離れる向き)。グラフが分断されていれば連結成分ごとに独立に
    種を取り伝播する(成分間の相対向きは未保証)。

    Args:
        points: (N,3) の点群。
        normals: (N,3) の向き未定法線(内部で単位化)。
        k: kNN グラフの近傍数。
        seed_dir: 大域基準向き (3,)。None なら重心から外向きを基準にする。
    Returns:
        符号を大域一貫にそろえた (N,3) 単位法線。
    """
    P = _as_points(points)
    n = len(P)
    if n < k:
        raise ValueError(f"need at least k={k} points for orientation, got {n}")
    N = _as_normals(normals, n).copy()

    idx = _knn(P, k)
    neigh = idx[:, 1:]                            # 自身を除く近傍 (N, m)
    m = neigh.shape[1]
    if m == 0:                                    # 近傍が取れない(N==1 等)→ 種のみ
        rows = np.empty(0, int)
        cols = np.empty(0, int)
        weights = np.empty(0, float)
    else:
        rows = np.repeat(np.arange(n), m)
        cols = neigh.ravel()
        dots = np.abs(np.einsum("ij,ij->i", N[rows], N[cols]))
        weights = 1.0 - dots + 1e-6              # 厳密に正(疎行列の暗黙ゼロを避ける)
    W = coo_matrix((weights, (rows, cols)), shape=(n, n)).tocsr()
    W = W.maximum(W.T)                            # 無向グラフへ対称化
    mst = minimum_spanning_tree(W)                # 分断時は最小全域森
    M = (mst + mst.T).tocsr()                     # 無向隣接
    indptr, indices = M.indptr, M.indices

    ncomp, labels = connected_components(M, directed=False)
    centroid = P.mean(0)
    ref = None
    if seed_dir is not None:
        r = np.asarray(seed_dir, np.float64).reshape(3)
        rn = np.linalg.norm(r)
        if rn < 1e-12:
            raise ValueError("seed_dir must be a non-zero vector")
        ref = r / rn

    visited = np.zeros(n, bool)
    for comp in range(ncomp):
        members = np.where(labels == comp)[0]
        if ref is not None:
            seed = int(members[np.argmax(P[members] @ ref)])   # 基準向きの最突出点
            refdir = ref
        else:
            d = P[members] - centroid
            seed = int(members[np.argmax(np.einsum("ij,ij->i", d, d))])  # 最外点
            v = P[seed] - centroid
            nv = np.linalg.norm(v)
            refdir = v / nv if nv > 1e-12 else None                # 重心から外向き
        _orient_seed(N, seed, refdir)
        # 木を BFS/DFS で辿り、親と逆向きの子を反転
        stack = [seed]
        visited[seed] = True
        while stack:
            u = stack.pop()
            for w in indices[indptr[u]:indptr[u + 1]]:
                if not visited[w]:
                    visited[w] = True
                    if np.dot(N[u], N[w]) < 0.0:
                        N[w] = -N[w]
                    stack.append(int(w))
    return N


def estimate_oriented_normals(points, k: int = 20, seed_dir=None) -> np.ndarray:
    """PCA 法線推定 + Hoppe 大域向き付けの合成。→ (N,3) の向き付き単位法線。

    :func:`estimate_normals`(向き未定)→ :func:`orient_normals`(MST 伝播)を通す。
    閉曲面なら全点外向き、平面なら全点同一半球にそろう。得た法線を
    ``curvature3d.shape_index`` に渡すと凹/凸符号が正しく出る。

    Args:
        points: (N,3) の点群。
        k: PCA 近傍数と kNN グラフ近傍数(共通)。
        seed_dir: 大域基準向き (3,)。None なら重心から外向き。
    Returns:
        (N,3) の大域一貫・向き付き単位法線。
    """
    N = estimate_normals(points, k=k)
    return orient_normals(points, N, k=k, seed_dir=seed_dir)
