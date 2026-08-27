# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群セグメンテーション: 法線領域成長 / Euclidean 距離クラスタ / 反復平面抽出。

生の 3D 点群を「連結した意味のある部分」へ分割する解析層。:mod:`pointcloud`
(法線推定・ダウンサンプル)と :mod:`ransac_fit`(頑健プリミティブ適合)の上に載る。
Physical AI のロボット知覚フロントエンド(掴む対象の分離・接地面の除去・面パッチ分割)。

固有価値 / 既存モジュールとの差別化(honest):
- :mod:`pcseg` にも ``euclidean_clusters`` / ``region_growing`` があるが **返り値の契約が違う**。
  pcseg は *index 配列のリスト*(大きい順)を返す。ここでは全 3 関数が **点ごとの
  ラベル配列 ``labels`` (N,)** を返す統一契約(-1 = ノイズ/未割当)。sklearn DBSCAN /
  PCL の per-point label と同形で、`labels == c` で c 番目のセグメントを即取り出せる。
- ``plane_segmentation`` は **反復(逐次)平面抽出**で pcseg には無い機能。pcseg は単一
  ``fit_plane_ransac`` / ``remove_ground`` のみ。ここでは最大 ``max_planes`` 枚まで
  「最大 consensus 平面を検出 → inlier を除去 → 残りで再検出」を繰り返し、各平面へ別ラベル、
  どの平面にも属さない残差点へ -1 を与える(複数の壁・床・階段状の面を一度に分ける)。
- ``region_growing`` は **曲率ゲート無しの純・法線角度 BFS**(pcseg は Rabbani の曲率シード
  平滑度制約)。隣接点の法線角度 < 閾値だけで連結成分を作る素直な変種。曲率推定不要で軽い。

しきい値はすべて呼び出し側がスケールに合わせて渡す設計(``tol`` / ``thresh`` は距離、
``angle_thresh_deg`` は角度で無次元)。内部に距離の絶対 epsilon は持たない(数値ガード 1e-12 のみ)。

References (public literature — reimplemented):
- Rusu, "Semantic 3D Object Maps for Everyday Manipulation", PhD 2009 (Euclidean cluster).
- Rabbani et al., "Segmentation of point clouds using smoothness constraint", ISPRS 2006.
- Fischler & Bolles, "Random Sample Consensus", CACM 1981 (RANSAC plane).
"""
from __future__ import annotations

import numpy as np

__all__ = ["region_growing", "euclidean_cluster", "plane_segmentation"]


# ═══════════════════════════════════════════════════════════════════════════
# 内部ヘルパ
# ═══════════════════════════════════════════════════════════════════════════
def _pts3(points, name: str) -> np.ndarray:
    """(N,3) 検証 → float64 配列。縮退入力は fail-closed(ValueError)。"""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"{name}: points は (N,3) 形状が必要(得た shape={P.shape})")
    if not np.all(np.isfinite(P)):
        raise ValueError(f"{name}: points に非有限値(NaN/Inf)が含まれる")
    return P


def _knn_index(P: np.ndarray, k: int):
    """各点の k 近傍 index (N,k)。自己を含むので呼び出し側で [:,1:] を使う。"""
    from scipy.spatial import cKDTree

    n = len(P)
    kk = int(min(max(2, k + 1), n))          # +1 は自己を含めるため
    _, idx = cKDTree(P).query(P, k=kk)
    if idx.ndim == 1:                        # kk==1 (n==1) の保険
        idx = idx.reshape(n, 1)
    return idx


# ═══════════════════════════════════════════════════════════════════════════
# 1. 法線領域成長(normal region growing)
# ═══════════════════════════════════════════════════════════════════════════
def region_growing(points, normals=None, angle_thresh_deg: float = 15.0,
                   k: int = 20, min_region_size: int = 3) -> np.ndarray:
    """法線類似で領域成長し連結した平滑領域へ同ラベルを付す(曲率ゲート無し変種)。

    各点を k 近傍グラフ上で BFS 成長させ、隣接点 q を「法線 n_p と n_q の成す角が
    ``angle_thresh_deg`` 未満」のときだけ同領域に加える。平面内の法線はほぼ平行なので
    同一領域に連結し、向きの違う面の境界では角度が開いて連結が切れる → 面ごとに別領域。
    法線は符号不定(PCA 由来)なので ``|n_p·n_q|`` で判定(表裏を同一視)。

    Args:
        points: (N,3) 点群。
        normals: (N,3) 単位法線。None なら :func:`pointcloud.estimate_normals` で PCA 推定。
        angle_thresh_deg: 隣接法線角度の許容上限[度]。(0,180) の範囲。
        k: 近傍数(kNN グラフの次数)。

    Returns:
        labels: (N,) int。連結平滑領域ごとに 0,1,2,... を付与。**min_region_size 未満の
        小領域(孤立点・向き不一致のゴミ)は -1(ノイズ/未割当)** = 統一契約(-1=ノイズ)に従う。
        空入力は shape (0,) を返す。
    """
    P = _pts3(points, "region_growing")
    if not (0.0 < float(angle_thresh_deg) < 180.0):
        raise ValueError(f"region_growing: angle_thresh_deg は (0,180) が必要(得た {angle_thresh_deg})")
    if int(k) < 1:
        raise ValueError(f"region_growing: k>=1 が必要(得た {k})")
    n = len(P)
    if n == 0:
        return np.zeros(0, np.int64)
    if n == 1:
        return np.zeros(1, np.int64)

    if normals is None:
        from pointcloud import estimate_normals
        Nrm = estimate_normals(P, k=k)
    else:
        Nrm = np.asarray(normals, np.float64)
        if Nrm.shape != P.shape:
            raise ValueError(f"region_growing: normals は points と同 shape が必要"
                             f"(points={P.shape}, normals={Nrm.shape})")
        nrm = np.linalg.norm(Nrm, axis=1, keepdims=True)
        Nrm = Nrm / np.maximum(nrm, 1e-12)   # 単位化(入力が非正規化でも安全)

    idx = _knn_index(P, k)
    cos_thr = np.cos(np.radians(float(angle_thresh_deg)))
    labels = np.full(n, -1, np.int64)
    cur = 0
    # 決定論のため seed は昇順 index で選ぶ
    for seed in range(n):
        if labels[seed] != -1:
            continue
        labels[seed] = cur
        stack = [seed]
        while stack:
            p = stack.pop()
            for q in idx[p, 1:]:             # 自己 [0] を除く近傍
                if labels[q] != -1:
                    continue
                if abs(float(Nrm[p] @ Nrm[q])) < cos_thr:
                    continue                 # 法線が開きすぎ → 境界、連結しない
                labels[q] = cur
                stack.append(q)
        cur += 1
    # 統一契約(-1=ノイズ/未割当)を守る: min_region_size 未満の小領域(孤立点・ゴミ)は -1 に。
    if int(min_region_size) > 1 and cur > 0:
        counts = np.bincount(labels, minlength=cur)
        remap = np.full(cur, -1, np.int64)
        nxt = 0
        for r in range(cur):
            if counts[r] >= int(min_region_size):
                remap[r] = nxt
                nxt += 1
        labels = remap[labels]
    return labels


# ═══════════════════════════════════════════════════════════════════════════
# 2. Euclidean 距離クラスタリング(連結成分)
# ═══════════════════════════════════════════════════════════════════════════
def euclidean_cluster(points, tol: float, min_size: int = 10) -> np.ndarray:
    """半径 tol の近接グラフの連結成分で距離クラスタリング(-1=ノイズ)。

    互いに ``tol`` 以内の点を(推移的に)同一クラスタへ束ねる。空間的に離れた物体が
    別クラスタになる(接地面除去後の「どの塊が掴める物か」の分離に使う)。連結成分のうち
    ``min_size`` 未満のものはノイズとして -1。ラベルはクラスタサイズ降順で 0,1,2,...
    (決定論)。

    Args:
        points: (N,3) 点群。
        tol: 同一クラスタとみなす近接半径(距離、要 > 0)。
        min_size: これ未満の連結成分はノイズ(-1)。

    Returns:
        labels: (N,) int。0..(n_clusters-1) がクラスタ、-1 がノイズ。空入力は shape (0,)。
    """
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree

    P = _pts3(points, "euclidean_cluster")
    if not (float(tol) > 0.0):
        raise ValueError(f"euclidean_cluster: tol>0 が必要(得た {tol})")
    if int(min_size) < 1:
        raise ValueError(f"euclidean_cluster: min_size>=1 が必要(得た {min_size})")
    n = len(P)
    if n == 0:
        return np.zeros(0, np.int64)

    pairs = cKDTree(P).query_pairs(r=float(tol), output_type="ndarray")
    if pairs.size == 0:
        rows = cols = np.zeros(0, np.int64)
    else:
        rows = np.concatenate([pairs[:, 0], pairs[:, 1]])
        cols = np.concatenate([pairs[:, 1], pairs[:, 0]])
    graph = csr_matrix((np.ones(rows.size), (rows, cols)), shape=(n, n))
    ncomp, comp = connected_components(graph, directed=False)

    # 成分サイズ降順で有効クラスタへ 0,1,2,... を再ラベル。min_size 未満は -1。
    sizes = np.bincount(comp, minlength=ncomp)
    order = np.argsort(-sizes, kind="stable")     # 大きい順(決定論)
    labels = np.full(n, -1, np.int64)
    next_label = 0
    for c in order:
        if sizes[c] < min_size:
            continue
        labels[comp == c] = next_label
        next_label += 1
    return labels


# ═══════════════════════════════════════════════════════════════════════════
# 3. 反復 RANSAC 平面抽出(multi-plane segmentation)
# ═══════════════════════════════════════════════════════════════════════════
def plane_segmentation(points, thresh: float, min_inliers: int,
                       max_planes: int = 5, iters: int = 300,
                       seed: int = 0) -> np.ndarray:
    """反復 RANSAC で最大 max_planes 枚の平面を逐次抽出(残差点 -1)。

    残り点集合に :func:`ransac_fit.ransac_plane` を掛け、その最大 consensus 平面の
    inlier 数が ``min_inliers`` 以上なら新ラベルを与えて除去 → 残りで再検出、を繰り返す。
    複数の床/壁/階段状の面を一度に分離する(単一平面適合の pcseg との差)。inlier が
    ``min_inliers`` に満たなくなった時点で停止し、以降の点は残差 -1(球や複雑物体はここに残る)。

    Args:
        points: (N,3) 点群。
        thresh: 点-平面距離の inlier しきい値(距離、要 > 0)。
        min_inliers: 平面として採用する最小 inlier 数(要 >= 3)。
        max_planes: 抽出する平面の最大枚数(要 >= 1)。
        iters: 各 RANSAC 反復数。
        seed: 乱数シード(決定論。各平面で seed+平面index を使う)。

    Returns:
        labels: (N,) int。検出順(=consensus 大きい順に近い)に 0,1,2,... を平面へ付与、
        どの平面にも属さない残差点は -1。空入力は shape (0,)。
    """
    from ransac_fit import ransac_plane

    P = _pts3(points, "plane_segmentation")
    if not (float(thresh) > 0.0):
        raise ValueError(f"plane_segmentation: thresh>0 が必要(得た {thresh})")
    if int(min_inliers) < 3:
        raise ValueError(f"plane_segmentation: min_inliers>=3 が必要(得た {min_inliers})")
    if int(max_planes) < 1:
        raise ValueError(f"plane_segmentation: max_planes>=1 が必要(得た {max_planes})")
    n = len(P)
    labels = np.full(n, -1, np.int64)
    if n == 0:
        return labels

    remaining = np.arange(n)                 # まだどの平面にも割当てられていない global index
    for pi in range(int(max_planes)):
        if len(remaining) < max(3, int(min_inliers)):
            break                            # 残り点が最小 inlier 数未満 → これ以上平面は出せない
        sub = P[remaining]
        _params, mask, _info = ransac_plane(sub, float(thresh),
                                            iters=int(iters), seed=int(seed) + pi)
        n_in = int(mask.sum())
        if n_in < int(min_inliers):
            break                            # 最大 consensus でも min_inliers 未満 → 停止
        hit = remaining[mask]                # global index の inlier
        labels[hit] = pi
        remaining = remaining[~mask]         # 除去して次の平面へ
    return labels
