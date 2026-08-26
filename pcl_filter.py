"""pcl_filter — 点群 (N,3) の前処理フィルタ群(numpy in / numpy out, scipy KD-Tree)。

深度・ステレオ・LiDAR から起こした生の点群は、まばらな外れ値・密度ムラ・センサノイズ
を含む。位置合わせ(ICP)や特徴量・法線推定の前に、この 5 つの古典フィルタで雲を
整える: 統計的/半径外れ値除去(飛び点の掃除)、voxel グリッド間引き(密度の均一化と
点数削減)、MLS 平滑(局所曲面へ射影してノイズを落とす)、解像度推定(スケールの当たり付け)。

:mod:`pointcloud`(法線・FPFH・別実装の間引き/外れ値)の姉妹モジュール。座標系は
``points`` = (N, 3) の float、単位はワールド/カメラの実寸を想定。すべて numpy 完結で、
近傍探索のみ ``scipy.spatial.cKDTree`` を使う(数十万点でも実用速度)。

参考(公開): Rusu et al. "Towards 3D Point Cloud Based Object Maps" (2008, 統計的外れ値)、
Alexa et al. "Computing and Rendering Point Set Surfaces" (2003, MLS 射影)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "statistical_outlier_removal",
    "radius_outlier_removal",
    "voxel_grid_downsample",
    "mls_smooth",
    "estimate_resolution",
]


def _as_points(points) -> np.ndarray:
    """入力を (N,3) の float64 配列へ正規化する(形が違えば ValueError)。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3), got shape %r" % (P.shape,))
    return P


def statistical_outlier_removal(points, k: int = 16, std_ratio: float = 2.0):
    """各点の k 近傍平均距離が大域的に外れる点を除去する(統計的外れ値除去)。

    点ごとに「最も近い k 個(自分自身は除く)までの平均距離」を測り、その全点分布の
    ``mean + std_ratio*std`` を超える点を飛び点とみなして落とす。まばらな飛び点の掃除に
    有効で、密な面上の点は残る。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。
    k : int
        近傍数(既定 16)。点数が少なければ内部で ``n-1`` に丸める。
    std_ratio : float
        しきい値の緩さ。大きいほど残りやすい(除去が緩い)。

    Returns
    -------
    filtered : ndarray, shape (M, 3)
        生き残った点(元の順序を保持)。
    keep_mask : ndarray of bool, shape (N,)
        各入力点を残すか(True=残す)。``points[keep_mask]`` が ``filtered`` に等しい。

    Notes
    -----
    点数 < 3 では統計が立たないため、全点を残す(graceful)。
    """
    from scipy.spatial import cKDTree

    P = _as_points(points)
    n = P.shape[0]
    if n < 3:
        return P.copy(), np.ones(n, dtype=bool)

    kk = int(min(max(1, k), n - 1))
    # k+1 を引くのは 0 番目に必ず自分自身(距離 0)が入るため。
    dist, _ = cKDTree(P).query(P, k=kk + 1)
    mean_d = dist[:, 1:].mean(axis=1)          # 自分を除いた k 近傍の平均距離
    thr = float(mean_d.mean() + float(std_ratio) * mean_d.std())
    keep = mean_d <= thr
    return P[keep], keep


def radius_outlier_removal(points, radius: float, min_neighbors: int = 8):
    """半径 radius 内の近傍数が min_neighbors 未満の点を除去する(孤立点除去)。

    各点を中心に半径 ``radius`` の球を張り、その中に居る他点の数が ``min_neighbors``
    に満たない点を「孤立した粒」として落とす。統計的手法より局所的・直接的で、
    センサの実スケールが分かっているときにしきい値を決めやすい。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。
    radius : float
        近傍とみなす球の半径(> 0)。
    min_neighbors : int
        残すのに必要な近傍数(自分自身は数えない、既定 8)。

    Returns
    -------
    filtered : ndarray, shape (M, 3)
        生き残った点(元の順序を保持)。
    keep_mask : ndarray of bool, shape (N,)
        各入力点を残すか(True=残す)。

    Notes
    -----
    ``radius <= 0`` は ValueError。空入力は空を返す(graceful)。
    """
    from scipy.spatial import cKDTree

    P = _as_points(points)
    if float(radius) <= 0.0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    n = P.shape[0]
    if n == 0:
        return P.copy(), np.ones(0, dtype=bool)

    counts = cKDTree(P).query_ball_point(P, r=float(radius), return_length=True)
    # -1 で自分自身を数えない。
    keep = (np.asarray(counts, dtype=np.int64) - 1) >= int(min_neighbors)
    return P[keep], keep


def voxel_grid_downsample(points, voxel_size: float):
    """辺 voxel_size の格子で点群を間引き、各セルを重心 1 点に集約する(決定論的)。

    空間を一辺 ``voxel_size`` の立方体セルに区切り、同じセルに落ちた点をその重心
    1 点で代表させる。密度ムラを均し、下流(ICP・特徴量)の計算量を点数で抑える標準手法。
    出力順はボクセル座標の辞書順で固定(同じ入力なら常に同じ出力=決定論的)。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。
    voxel_size : float
        セルの一辺(> 0)。大きいほど強く間引く。

    Returns
    -------
    ndarray, shape (M, 3)
        各占有セルの重心(M <= N)。すべて入力の軸並行 bounding box 内に収まる。

    Notes
    -----
    ``voxel_size <= 0`` は ValueError。空入力は空 (0,3) を返す(graceful)。
    重心はセル内の点の平均なので、必ず入力点の凸包(ゆえに bbox)内に入る。
    """
    P = _as_points(points)
    if float(voxel_size) <= 0.0:
        raise ValueError("voxel_size must be > 0, got %r" % (voxel_size,))
    if P.shape[0] == 0:
        return P.copy()

    keys = np.floor((P - P.min(axis=0)) / float(voxel_size)).astype(np.int64)
    # 辞書順の一意キー(axis=0)→ inverse で各点の代表セル番号。順序は決定論的。
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()
    m = int(inv.max()) + 1
    sums = np.zeros((m, 3), dtype=np.float64)
    counts = np.zeros(m, dtype=np.float64)
    np.add.at(sums, inv, P)
    np.add.at(counts, inv, 1.0)
    return sums / counts[:, None]


def _poly_terms(u: np.ndarray, v: np.ndarray, order: int) -> np.ndarray:
    """2 変数 (u,v) の order 次までの単項式行列を作る。列 0 は定数項 1。

    列は次数昇順で ``[1, u, v, u^2, uv, v^2, ...]``。定数項を先頭に置くのは、後で
    (u,v)=(0,0)(=注目点)での曲面高さ = 係数[0] を直接読むため。
    """
    cols = []
    for total in range(order + 1):
        for a in range(total + 1):
            b = total - a
            cols.append((u ** a) * (v ** b))
    return np.stack(cols, axis=1)


def _n_poly_terms(order: int) -> int:
    """order 次 2 変数多項式の項数 (order+1)(order+2)/2。"""
    return (order + 1) * (order + 2) // 2


def mls_smooth(points, radius: float, order: int = 2):
    """各点を局所多項式曲面へ射影してノイズを落とす(Moving Least Squares 平滑)。

    点ごとに半径 ``radius`` 内の近傍を集め、重み付き PCA で局所平面(法線 n と接平面の
    2 軸)を推定し、近傍の「接平面上座標 (u,v) → 法線方向の高さ h」に order 次の
    多項式曲面をガウス重み付き最小二乗で当てはめる。注目点自身は局所座標の原点 (0,0)
    にあたるので、当てはめた曲面の (0,0) での高さ(= 定数項)ぶんだけ法線方向へ動かして
    曲面上へ射影する。面の形は保ったままセンサノイズだけを均せる。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。
    radius : float
        近傍球の半径(> 0)。局所曲面のサポート。
    order : int
        局所多項式の次数(既定 2)。項数は (order+1)(order+2)/2。

    Returns
    -------
    ndarray, shape (N, 3)
        平滑後の点群(順序・点数は保持)。近傍が多項式の項数に満たない点は原位置のまま。

    Notes
    -----
    近似手法である。近傍数が項数未満/局所平面が縮退する点は動かさず原位置を維持する
    (穴や境界で暴れないための安全策)。``radius <= 0`` は ValueError、空入力は空を返す。
    """
    from scipy.spatial import cKDTree

    P = _as_points(points)
    if float(radius) <= 0.0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    n = P.shape[0]
    if n == 0:
        return P.copy()

    order = int(max(0, order))
    n_terms = _n_poly_terms(order)
    r = float(radius)
    sigma2 = (r * 0.5) ** 2 + 1e-30      # ガウス重みの帯域(半径の半分を目安)

    tree = cKDTree(P)
    neigh = tree.query_ball_point(P, r=r)      # 各点の近傍 index(自分自身を含む)

    out = P.copy()
    for i in range(n):
        idx = neigh[i]
        if len(idx) < n_terms:                 # 曲面を決めるに足る点が無い → 原位置維持
            continue
        Q = P[idx]
        c = Q - P[i]                           # 注目点を原点に取る(注目点は局所座標 (0,0,0))
        d2 = np.einsum("ij,ij->i", c, c)
        w = np.exp(-d2 / sigma2)               # 距離ガウス重み
        wsum = w.sum()
        if wsum <= 1e-30:
            continue

        # 重み付き PCA で局所平面: 最小固有値方向 = 法線、他 2 軸 = 接平面。
        mean = (w[:, None] * c).sum(axis=0) / wsum
        cc = c - mean
        cov = (cc * w[:, None]).T @ cc / wsum
        evals, evecs = np.linalg.eigh(cov)     # 昇順
        normal = evecs[:, 0]
        t1, t2 = evecs[:, 1], evecs[:, 2]

        u = c @ t1
        v = c @ t2
        h = c @ normal                         # 接平面からの高さ(注目点は h=0)

        A = _poly_terms(u, v, order)
        sw = np.sqrt(w)
        # 重み付き最小二乗 (sqrt-weight で両辺を掛ける)。lstsq は縮退に頑健。
        coef, *_ = np.linalg.lstsq(A * sw[:, None], h * sw, rcond=None)
        h0 = float(coef[0])                    # 曲面の (u,v)=(0,0) での高さ = 射影量
        if not np.isfinite(h0):
            continue
        out[i] = P[i] + h0 * normal
    return out


def estimate_resolution(points) -> float:
    """最近傍距離の中央値を返す(点群スケールの当たり付けヘルパ)。

    各点について自分以外で最も近い点までの距離を求め、その中央値を返す。voxel サイズや
    近傍半径など、他フィルタのパラメータを実データのスケールに合わせて決める土台になる。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        入力点群。

    Returns
    -------
    float
        最近傍距離の中央値。点数 < 2 では近傍が無いため ``nan`` を返す(graceful)。
    """
    from scipy.spatial import cKDTree

    P = _as_points(points)
    n = P.shape[0]
    if n < 2:
        return float("nan")

    dist, _ = cKDTree(P).query(P, k=2)     # [:,0]=自分(0), [:,1]=最近傍
    return float(np.median(dist[:, 1]))
