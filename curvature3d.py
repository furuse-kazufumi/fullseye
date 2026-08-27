# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""curvature3d — 点群の主曲率・平均/ガウス曲率・shape index(局所二次曲面フィット)。

match3d.curvature_maps は voxel 場の曲率だが、ここは**非構造点群**の各点で局所 Monge パッチ
w=f(u,v) を最小二乗フィットし、第一/第二基本形式から主曲率 k1,k2 を出す(再パラメータ化に頑健)。

**符号規約と向きの限界(honest)**: 曲率の符号は法線の向きに依存する。K=k1k2 は法線反転に不変だが、
平均曲率 H・shape index・k1/k2 の符号は向き付き法線が要る。**開いた面(bowl/dome/patch)の凹/凸は
局所情報だけでは原理的に決まらない**(大域的な内外の向きが必要)。そこで:
  - `normals` 引数(視点/range image 由来の**向き付き**法線)を渡すと局所法線をそれに整合させ、
    **正しい凹/凸符号**を出す(凹球=cup → -1、凸球=cap → +1)。
  - `normals` 未指定時は近傍重心から離れる向き(凸側)へ揃えるヒューリスティクス。開面では常に凸側を
    向くため **凹/凸の符号は不定=凸マグニチュードとして報告**(bowl も dome も同符号)。「凹球→-1」は
    向き付き法線を与えたときのみ到達する。

GT: 半径 R の球 → k1=k2=1/R・K=1/R² / 円柱 → k1=1/R,k2=0・K=0 / 平面 → 0。
shape index(Koenderink)= 球(凸)+1・円柱 +0.5・鞍点 0・平面 不定(0 扱い)。凹球は向き付き法線時 -1。

用途: 把持アフォーダンス(凸/凹/鞍点判定)、表面分類、曲率異常による欠陥検出(Physical AI)。
"""
import numpy as np
from scipy.spatial import cKDTree


def _knn_idx(points, k):
    """各点の (自身含む) k+1 近傍インデックス。→ (N, k+1) int。"""
    p = np.asarray(points, float)
    k = min(k, len(p) - 1)
    tree = cKDTree(p)
    _, idx = tree.query(p, k=k + 1)
    return np.atleast_2d(idx)


def _principal_at(local, orient=None):
    """クエリ点を原点にした近傍 (m,3) → 主曲率 (k1>=k2) と法線。

    PCA で法線(最小固有ベクトル)を推定 → 接線基底で Monge 形 w=du+ev+au²+buv+cv² を
    フィット → 第一/第二基本形式の shape operator 固有値で k1,k2。

    `orient`(向き付き参照法線, 3,)を与えると PCA 法線をそれに整合(dot>0)させ、大域的な
    凹/凸の符号を正しく出す。未指定なら近傍重心から離れる向き(凸側)へ揃えるヒューリスティクス
    (開面では常に凸側=符号は凸マグニチュードで不定)。いずれも凸(法線から遠ざかる曲がり)を正。
    """
    if len(local) < 5:
        return 0.0, 0.0, np.array([0.0, 0.0, 1.0])
    C = local.T @ local
    w_eig, V = np.linalg.eigh(C)
    normal = V[:, 0]                 # 最小固有値方向 = 法線
    if orient is not None:
        # 向き付き参照法線(視点/range image 由来の大域向き)へ整合
        if np.dot(normal, orient) < 0:
            normal = -normal
    else:
        centroid = local.mean(axis=0)
        if np.dot(centroid, normal) > 0:  # 近傍の重心から離れる向き(凸側)へ
            normal = -normal
    t1 = V[:, 2] - np.dot(V[:, 2], normal) * normal
    t1 /= np.linalg.norm(t1) + 1e-12
    t2 = np.cross(normal, t1)
    u = local @ t1
    v = local @ t2
    wc = local @ normal
    A = np.stack([u, v, u * u, u * v, v * v], axis=1)
    coef, *_ = np.linalg.lstsq(A, wc, rcond=None)
    d, e, a, b, c = coef
    fx, fy, fxx, fxy, fyy = d, e, 2 * a, b, 2 * c
    denom = np.sqrt(1 + fx * fx + fy * fy)
    I1 = np.array([[1 + fx * fx, fx * fy], [fx * fy, 1 + fy * fy]])
    II = np.array([[fxx, fxy], [fxy, fyy]]) / denom
    S = np.linalg.solve(I1, II)      # shape operator
    ev = np.sort(np.linalg.eigvals(S).real)
    # 外向き法線だと凸面は負固有値 → 符号反転して凸=正、k1>=k2 を維持
    k1, k2 = -ev[0], -ev[1]
    return k1, k2, normal


def _validate_normals(normals, n):
    """向き付き参照法線を検証 → (n,3) float。fail-closed(不正形状/非有限/ゼロ長は ValueError)。"""
    nrm = np.asarray(normals, float)
    if nrm.shape != (n, 3):
        raise ValueError(f"normals must have shape ({n}, 3), got {nrm.shape}")
    if not np.all(np.isfinite(nrm)):
        raise ValueError("normals must be finite")
    if np.any(np.linalg.norm(nrm, axis=1) < 1e-12):
        raise ValueError("normals must be nonzero (each row needs an orientation)")
    return nrm


def _curvatures(points, k, normals=None):
    """全点の (k1, k2, normals)。→ (N,), (N,), (N,3)。

    normals(向き付き参照法線, (N,3))を渡すと各点の局所法線をそれへ整合させ凹/凸符号を正しく出す。
    """
    p = np.asarray(points, float)
    n = len(p)
    if normals is not None:
        normals = _validate_normals(normals, n)
    idx = _knn_idx(p, k)
    K1 = np.zeros(n)
    K2 = np.zeros(n)
    NRM = np.zeros((n, 3))
    for i in range(n):
        local = p[idx[i]] - p[i]     # クエリ点を原点に
        orient = None if normals is None else normals[i]
        K1[i], K2[i], NRM[i] = _principal_at(local, orient)
    return K1, K2, NRM


def principal_curvatures(points, k=25, normals=None):
    """各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。

    normals(向き付き参照法線, (N,3))未指定時は凸側マグニチュード(開面の凹/凸符号は不定)。
    向き付き法線を渡すと大域向きに整合し正しい符号(凹=負, 凸=正)。
    """
    K1, K2, _ = _curvatures(points, k, normals)
    return K1, K2


def mean_curvature(points, k=25, normals=None):
    """平均曲率 H=(k1+k2)/2。→ (N,)。向きに依存する量。

    normals(向き付き参照法線, (N,3))未指定時は凸側ヒューリスティクス(開面の凹/凸符号は不定)。
    向き付き法線を渡すと大域向きに整合し正しい符号を出す。
    """
    K1, K2, _ = _curvatures(points, k, normals)
    return (K1 + K2) / 2.0


def gaussian_curvature(points, k=25):
    """ガウス曲率 K=k1·k2(法線の反転に不変)。→ (N,)。"""
    K1, K2, _ = _curvatures(points, k)
    return K1 * K2


def shape_index(points, k=25, normals=None):
    """Koenderink の shape index s∈[-1,1](凸球+1・円柱+0.5・鞍点0・凹球-1)。→ (N,)。

    umbilic/平面判定は**曲率スケール相対**(絶対しきい値なし)。緩やかな凸/凹(曲率が微小でも)は
    符号=凹凸を保ち、平面はデータ全体の曲率スケールに対して相対的に 0 の点のみ s=0 とする。

    normals(向き付き参照法線, (N,3))未指定時は開面の凹/凸符号が不定(凸マグニチュードで報告)。
    向き付き法線を渡すと大域向きに整合し正しい符号(凹球=cup → -1)を出す。
    """
    K1, K2, _ = _curvatures(points, k, normals)
    ssum = K1 + K2
    diff = K1 - K2                        # k1>=k2 なので diff>=0
    mag = np.abs(K1) + np.abs(K2)         # 局所曲率の大きさ
    curv = np.sqrt((K1 ** 2 + K2 ** 2) / 2.0)  # curvedness(各点)
    scale = float(np.median(curv))        # データ全体の曲率スケール(robust)

    rel_umbilic = 1e-2                    # |k1-k2| がこの割合未満 → 臍点扱い(符号のみ)
    rel_flat = 1e-3                       # curvedness がスケールのこの割合未満 → 平面(s=0)

    s = np.zeros_like(K1)
    # 平面: データ曲率スケールに対して相対的に 0 の点のみ(scale>0 が前提。信号ゼロなら全面平面)
    if scale > 0.0:
        flat_plane = curv < rel_flat * scale
    else:
        flat_plane = np.ones_like(K1, dtype=bool)  # 曲率信号なし → 不定(平面=0)

    # 臍点(k1≈k2): |k1-k2| が曲率の大きさに対して相対的に小 → 符号 sign(k1+k2) で凹凸を保つ
    umbilic = (diff < rel_umbilic * mag) & (mag > 0.0)

    umb = umbilic & ~flat_plane          # 臍点かつ非平面 → 符号(緩くても凹凸を保存)
    s[umb] = np.sign(ssum[umb])
    general = ~umbilic & ~flat_plane     # 一般(異方性)→ Koenderink arctan
    s[general] = (2.0 / np.pi) * np.arctan(ssum[general] / diff[general])
    return s


def curvedness(points, k=25):
    """curvedness C=√((k1²+k2²)/2)(曲がりの強さ、shape index と直交な量)。→ (N,)。"""
    K1, K2, _ = _curvatures(points, k)
    return np.sqrt((K1 ** 2 + K2 ** 2) / 2.0)


def estimate_normals(points, k=25):
    """外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。"""
    _, _, NRM = _curvatures(points, k)
    return NRM
