# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""medial — 3D medial surface / 3D 骨格(TRIZ 原理 #17「多次元化(線→面)」)。

2D の形状照合は「輪郭(1D 境界)→ 2D スケルトン(中心線)」で位相を捉える。これを 1 次元
上げると「曲面(2D 境界)→ **medial surface(中心面)/ 3D 骨格**」になる。太い塊は面状の
medial surface に、細い管は線状の骨格に潰れる——同じ抽出器が形状の局所次元に応じて自然に
面/線を出し分ける。これが位相不変な形状照合の土台になる。

原理:
    距離変換(EDT)の **リッジ(尾根 = 勾配方向の極大)** が medial(中心)である。各 voxel から
    最近傍の背景までの距離を測ると、物体の「芯」ほど値が大きく、そこが局所的な峰になる。峰の
    次元(点/線/面)が物体の局所的な太さ次元に対応する。

公開 API:
    distance_ridge(vol)      -> (ridge_mask, edt)   EDT のリッジを medial として抽出
    skeletonize_vol(vol)     -> skeleton(bool 3D)   skimage Lee(1994)3D 細線化ラッパ
    medial_axis_points(vol)  -> (points, radius)    medial voxel 座標 + 局所半径(=EDT)
    topology_signature(skel) -> dict                26 近傍次数による位相記述子
    medial_match(a, b)       -> float               位相 + 半径分布による粗照合スコア

入力はバイナリ voxel(bool / 0-1 の 3D numpy 配列)。距離は voxel 単位(等方サンプリング前提)。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve, distance_transform_edt, maximum_filter

__all__ = [
    "distance_ridge",
    "skeletonize_vol",
    "medial_axis_points",
    "topology_signature",
    "medial_match",
    "skeleton_junctions3d",
    "skeleton_endpoints3d",
    "skeleton_prune3d",
    "skeleton_branches3d",
]


def _as_binary_volume(vol, name="vol"):
    """入力を bool の 3D 配列に正規化(信頼境界での再検証: 型/次元/中身を必ず確認)。

    bool / 0-1 / 任意の数値配列を受け、非ゼロを前景とみなす。3D 以外・空配列・NaN/Inf 混入は
    fail-closed で ValueError。返り値は連続な bool 配列(以降のシフト/畳み込みが安全)。
    """
    arr = np.asarray(vol)
    if arr.ndim != 3:
        raise ValueError(f"{name} must be a 3D voxel array (got ndim={arr.ndim}, shape={arr.shape})")
    if arr.size == 0:
        raise ValueError(f"{name} is empty (shape={arr.shape})")
    if np.issubdtype(arr.dtype, np.floating) and not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains NaN/Inf (pass a binary voxel array)")
    return np.ascontiguousarray(arr).astype(bool)


def distance_ridge(vol, min_radius=0.0):
    """EDT のリッジ(距離場の局所極大)を medial として抽出。返り値 (ridge_mask, edt)。

    各前景 voxel の EDT を計算し、**26 近傍の局所極大**(自分の EDT が周囲 26 voxel の最大以上)を
    medial とみなす。この基準は物体の局所次元に応じて自然に次元を出し分ける:
        塊(球)  -> EDT が単峰 -> 点状の medial(中心 1 点)。
        管(円柱)-> 軸方向に平坦・半径方向に単峰 -> 線状の medial(軸線)。
        板(スラブ)-> 面内で平坦・厚み方向に単峰 -> 面状の medial(中心面)。
    境界 voxel は内側の隣が必ず大きいため極大にならず、外殻は自然に除かれる。平坦な尾根
    (軸/面)は同値の隣接を許容(>=)することで連続した線/面として残る。

    Args:
        vol: バイナリ voxel(bool / 0-1 の 3D)。
        min_radius: この EDT 値以下の弱い尾根を捨てる閾値(既定 0 = 捨てない)。ノイズ抑制用。

    Returns:
        ridge_mask (bool 3D): medial voxel。
        edt (float64 3D): 各 voxel の背景までのユークリッド距離(= 局所半径)。
    """
    mask = _as_binary_volume(vol)
    if float(min_radius) < 0.0:
        raise ValueError(f"min_radius must be non-negative (got: {min_radius})")
    edt = distance_transform_edt(mask).astype(np.float64)
    # 3x3x3 の最大値フィルタ(外側 = 背景 = 0)。自分自身を含むので edt >= local_max は
    # 「26 近傍で最大(タイ許容)」= 局所極大を意味する。
    local_max = maximum_filter(edt, size=3, mode="constant", cval=0.0)
    ridge_mask = mask & (edt >= local_max) & (edt > float(min_radius))
    return ridge_mask, edt


def skeletonize_vol(vol):
    """3D バイナリ voxel を細線化して 1 voxel 幅の骨格に。skimage の Lee(1994)法ラッパ。

    method='lee' は 3D 対応の位相保存細線化。塊も含めて線状の骨格へ潰す(medial *surface* が
    欲しい場合は distance_ridge を使う)。返り値は入力と同形の bool 配列。

    Args:
        vol: バイナリ voxel(bool / 0-1 の 3D)。

    Returns:
        skeleton (bool 3D): 骨格 voxel。
    """
    mask = _as_binary_volume(vol)
    if not mask.any():
        return np.zeros_like(mask)
    from skimage.morphology import skeletonize

    skel = skeletonize(mask, method="lee")
    return np.ascontiguousarray(skel).astype(bool)


def medial_axis_points(vol, min_radius=0.0):
    """medial voxel の座標と局所半径(= その点の EDT 値)を点群化。返り値 (points, radius)。

    太い部分は面状、細い部分は線状に分布する medial 点を (M,3) の座標(z,y,x)と、それぞれの
    局所半径 (M,) として返す。半径最大の点は形状の最も「内側」= 中心を指す。

    Args:
        vol: バイナリ voxel(bool / 0-1 の 3D)。
        min_radius: この半径以下の点を除外(ノイズ抑制)。

    Returns:
        points (float64, (M,3)): medial voxel 座標(z, y, x)。
        radius (float64, (M,)): 各点の EDT 値(= 局所内接半径)。
    """
    ridge_mask, edt = distance_ridge(vol, min_radius=min_radius)
    points = np.argwhere(ridge_mask).astype(np.float64)          # (M,3) in (z,y,x)
    radius = edt[ridge_mask].astype(np.float64)                   # (M,)
    return points, radius


def topology_signature(skeleton):
    """骨格の 26 近傍次数から位相記述子を作る。端点/分岐点/通常点/孤立点の個数を返す。

    各骨格 voxel について 26 近傍にある骨格 voxel 数(次数)を数え、
        次数 1  = 端点(endpoint)
        次数 2  = 通常点(骨格の途中)
        次数>=3 = 分岐点(branch)
        次数 0  = 孤立点(isolated)
    に分類する。個数は平行移動・回転(90 度)不変で、形状の位相を粗く要約する記述子になる。

    注意(honest): 26 近傍の次数は、分岐近傍で対角隣接により過大に数えられることがある(離散
    骨格の既知の性質)。端点数は各枝の末端で厳密だが、分岐点数はやや過大側に振れうる。

    Args:
        skeleton: 骨格 voxel(bool / 0-1 の 3D)。

    Returns:
        dict: endpoints, branches, normal, isolated, total(骨格 voxel 総数),
              degree_hist(次数 -> 個数)。
    """
    skel = _as_binary_volume(skeleton, name="skeleton")
    kernel = np.ones((3, 3, 3), dtype=np.int32)
    kernel[1, 1, 1] = 0
    degree = convolve(skel.astype(np.int32), kernel, mode="constant", cval=0)
    deg = degree[skel]                                            # 骨格 voxel の次数のみ
    if deg.size == 0:
        return {"endpoints": 0, "branches": 0, "normal": 0, "isolated": 0,
                "total": 0, "degree_hist": {}}
    endpoints = int(np.count_nonzero(deg == 1))
    branches = int(np.count_nonzero(deg >= 3))
    normal = int(np.count_nonzero(deg == 2))
    isolated = int(np.count_nonzero(deg == 0))
    vals, counts = np.unique(deg, return_counts=True)
    degree_hist = {int(v): int(c) for v, c in zip(vals, counts)}
    return {
        "endpoints": endpoints,
        "branches": branches,
        "normal": normal,
        "isolated": isolated,
        "total": int(deg.size),
        "degree_hist": degree_hist,
    }


def _topology_vector(sig):
    """位相記述子を、総数で正規化した [端点, 分岐, 通常, 孤立] の割合ベクトルに。"""
    total = max(sig["total"], 1)
    return np.array(
        [sig["endpoints"], sig["branches"], sig["normal"], sig["isolated"]],
        dtype=np.float64,
    ) / total


def _radius_histogram(radius, edges):
    """半径配列を共通 bin 端 edges で正規化ヒストグラム(合計 1)に。空なら一様 0。"""
    if radius.size == 0:
        return np.zeros(len(edges) - 1, dtype=np.float64)
    hist, _ = np.histogram(radius, bins=edges)
    s = hist.sum()
    if s == 0:
        return np.zeros(len(edges) - 1, dtype=np.float64)
    return hist.astype(np.float64) / s


def medial_match(vol_a, vol_b, w_topology=0.6, w_radius=0.4, n_bins=12):
    """2 つの voxel 形状の medial(位相 + 半径分布)による粗照合スコア。返り値 [0,1]。

    骨格の位相記述子(端点/分岐/通常/孤立の割合)の距離と、medial 半径分布(内接半径の
    ヒストグラム)の距離を重み付き合成し、類似度 = 1 - 距離 として返す。1 に近いほど似ている。
    平行移動・回転(90 度)に対して概ね不変で、位相ベースの初期照合(粗いふるい)に使う。

    Args:
        vol_a, vol_b: バイナリ voxel(bool / 0-1 の 3D)。
        w_topology: 位相距離の重み(既定 0.6)。
        w_radius: 半径分布距離の重み(既定 0.4)。
        n_bins: 半径ヒストグラムの bin 数。

    Returns:
        float: 類似スコア [0,1](大きいほど類似)。
    """
    if w_topology < 0 or w_radius < 0 or (w_topology + w_radius) <= 0:
        raise ValueError("weights must be non-negative and sum to > 0")

    # 位相距離: 骨格の次数割合ベクトルの L1 距離を半分にして [0,1] に収める。
    sig_a = topology_signature(skeletonize_vol(vol_a))
    sig_b = topology_signature(skeletonize_vol(vol_b))
    tv_a, tv_b = _topology_vector(sig_a), _topology_vector(sig_b)
    topo_dist = 0.5 * float(np.abs(tv_a - tv_b).sum())           # [0,1]

    # 半径分布距離: 共通 bin での全変動距離(TV = 0.5 * L1)、[0,1]。
    _, ra = medial_axis_points(vol_a)
    _, rb = medial_axis_points(vol_b)
    rmax = max(float(ra.max()) if ra.size else 0.0,
               float(rb.max()) if rb.size else 0.0)
    if rmax <= 0.0:
        radius_dist = 0.0 if (ra.size == 0 and rb.size == 0) else 1.0
    else:
        edges = np.linspace(0.0, rmax + 1e-9, n_bins + 1)
        ha = _radius_histogram(ra, edges)
        hb = _radius_histogram(rb, edges)
        radius_dist = 0.5 * float(np.abs(ha - hb).sum())         # [0,1]

    dist = (w_topology * topo_dist + w_radius * radius_dist) / (w_topology + w_radius)
    return float(1.0 - min(max(dist, 0.0), 1.0))


if __name__ == "__main__":
    # 手早い自己確認(中実球 / 中実円柱)。
    def _ball(size, r):
        zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
        c = (size - 1) / 2.0
        return ((zz - c) ** 2 + (yy - c) ** 2 + (xx - c) ** 2) <= r * r

    v = _ball(41, 12)
    pts, rad = medial_axis_points(v)
    i = int(np.argmax(rad))
    print(f"ball: medial pts={len(pts)}  max_radius={rad[i]:.2f} @ {pts[i]}  (center=20)")
    print("self-match:", round(medial_match(v, v), 3))
