# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""物体空間アンビエントオクルージョン(AO)— メッシュへの半球到達性で「映える」陰影を作る。

AO(ambient occlusion, 環境遮蔽)は「その表面点が周囲の環境光をどれだけ受けられるか」=
開空率(sky openness)を [0,1] で表す量だ。凸面(尾根・出っ張り)は空が広く見えるので明るく
(AO≈1=露出)、凹面(溝の底・接触部・角の谷)は周囲の面に空を遮られて暗くなる(AO→0=遮蔽)。
写実的な静止画では、この「触れ合う所・窪む所に自然に落ちる柔らかい影」が立体感を決定づける —
Lambertian のべた塗りにはこの手掛かりが無く、平坦でのっぺりして見える。

**このモジュールが計算するのは物体空間 AO**(画面空間 SSAO ではない):各頂点から
*外向き法線まわりの半球* へ多数のレイを飛ばし、``max_dist`` 以内でメッシュ自身に当たった
割合(cos 重み付き)を遮蔽率とし、``AO = 1 - 遮蔽率`` とする。これは拡散 AO の定義
``AO = 1 - (1/π)∫_Ω V(ω) cosθ dω``(V=可視性)を半球一様サンプリング + cos 重みで
モンテカルロ近似したもの。物体空間で解くと、既知形状(平面に載る球・波状の溝)に対して
「凹部 < 凸部」「深いほど暗い」という **解析的に自明な順序** を GT として検証できる。

既存レンダ op との違い(固有価値, honest):
  - ``render3d.render_mesh`` … depth / silhouette / 法線の幾何バッファ。**陰影は無い**。
    本モジュールはこれを土台(カメラ・ラスタライズ)にして AO 画像を焼き込む(再発明しない)。
  - ``match3d.render_shaded`` / ``photometric.render_lambertian`` … 法線・光源方向だけの
    Lambertian。**面の向き**しか使わないので、平面に載った球の接触影や溝の谷影は出ない
    (向きが同じなら明るさも同じ)。AO は **周囲形状への到達性** を使うので、向きが同じでも
    周りに遮蔽物があれば暗くなる — これが接触影・窪み影の正体で、両者は乗算で組み合わせる。
  - ``range_image.occlusion_edges`` … 深度不連続(遮蔽エッジ)の検出であって陰影量ではない。

限界(証明していない能力は主張しない):
  - AO は「外向き法線まわりの半球」に対して定義する。``normals`` を渡さない場合は
    面の巻き順(winding)から面積重み付き頂点法線を作るので、**巻き順が外向きに一貫** した
    メッシュを仮定する(``render3d`` / ``mesh`` と同じ前提)。一貫しない場合は ``normals`` を渡す。
  - モンテカルロ近似ゆえ ``n_dirs`` 有限のサンプリング分散が乗る(既定 48〜64 で GT の順序は
    安定して再現する)。``max_dist`` は AO の局所性(遮蔽の効く距離)を決めるパラメータで、
    これを超える遠方の面は遮蔽に数えない(物理的な falloff 相当・高速化にも効く)。
  - レイ交差はブルートフォースの Möller-Trumbore を ``max_dist`` 近傍の面へ cKDTree で
    枝刈りして行う(BVH ではない)。巨大メッシュには不向き。

Reference (public):
  * S. Zhukov, A. Iones, G. Kronin, "An Ambient Light Illumination Model", EGWR 1998
    (obscurance / ambient occlusion の原典)。
  * H. Landis, "Production-Ready Global Illumination", SIGGRAPH 2002 course
    (レイキャスト AO の実務的定式化)。
  * T. Möller, B. Trumbore, "Fast, Minimum Storage Ray/Triangle Intersection", 1997。
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

import render3d

__all__ = ["vertex_occlusion", "ambient_occlusion"]

_DET_EPS = 1e-12          # 平行レイ / 退化三角形のしきい値
_BARY_EPS = 1e-9          # 三角形カバレッジのバリセントリック許容
_GOLDEN = np.pi * (3.0 - np.sqrt(5.0))     # フィボナッチ球の黄金角


# --------------------------------------------------------------------------- #
# fail-closed 入力検証(mesh.py / render3d.py の様式を踏襲)                    #
# --------------------------------------------------------------------------- #
def _as_mesh(V, F):
    """``(V, F)`` を float64 (nv,3) 頂点 + int64 (nf,3) 面へ検証。fail-closed。"""
    Vv = np.asarray(V, np.float64)
    if Vv.ndim != 2 or Vv.shape[1] != 3:
        raise ValueError(f"vertices must be (N, 3), got shape {Vv.shape}")
    if Vv.shape[0] == 0:
        raise ValueError("mesh has no vertices")
    if not np.isfinite(Vv).all():
        raise ValueError("vertices contain non-finite values")
    Ff = np.asarray(F)
    if Ff.ndim != 2 or Ff.shape[1] != 3:
        raise ValueError(f"faces must be (M, 3) triangles, got shape {Ff.shape}")
    Ff = Ff.astype(np.int64)
    if Ff.shape[0] == 0:
        raise ValueError("mesh has no faces")
    lo, hi = int(Ff.min()), int(Ff.max())
    if lo < 0 or hi >= Vv.shape[0]:
        raise ValueError(f"face index {hi if hi >= Vv.shape[0] else lo} "
                         f"out of range for {Vv.shape[0]} vertices")
    return Vv, Ff


def _bbox_diag(Vv: np.ndarray) -> float:
    lo, hi = Vv.min(axis=0), Vv.max(axis=0)
    diag = float(np.linalg.norm(hi - lo))
    if not np.isfinite(diag) or diag <= 0.0:
        raise ValueError("mesh is degenerate (zero-extent bounding box)")
    return diag


# --------------------------------------------------------------------------- #
# 半球方向サンプリング(フィボナッチ半球・立体角一様)                          #
# --------------------------------------------------------------------------- #
def _hemisphere_dirs(n_dirs: int) -> tuple[np.ndarray, np.ndarray]:
    """局所 +z を軸とする上半球の一様(立体角)方向 ``(K,3)`` と cos 重み ``(K,)``。

    ``z = 1 - (i+0.5)/n`` を使うと z が一様 → 半球上で立体角一様。cos θ = 局所 z 成分
    なので、重み ``w = z`` を掛けた平均が拡散 AO の cos 重み積分のモンテカルロ推定になる。
    """
    n = int(n_dirs)
    if n < 8:
        raise ValueError(f"n_dirs must be >= 8 for a stable estimate, got {n}")
    i = np.arange(n, dtype=np.float64) + 0.5
    z = 1.0 - i / n                                  # (0,1] 立体角一様
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = i * _GOLDEN
    dirs = np.stack([r * np.cos(phi), r * np.sin(phi), z], axis=1)
    return dirs, z.copy()                            # 重み = cosθ = z


def _basis_from_normal(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """単位法線 ``n`` に直交する接ベクトル 2 本(数値的に安定な選び方)。"""
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    t1 = np.cross(a, n)
    t1 /= np.linalg.norm(t1) + 1e-15
    t2 = np.cross(n, t1)
    return t1, t2


# --------------------------------------------------------------------------- #
# レイ×三角形群(ベクトル化 Möller-Trumbore、K レイ vs M 面)                  #
# --------------------------------------------------------------------------- #
def _rays_hit_any(o: np.ndarray, D: np.ndarray, A: np.ndarray,
                  e1: np.ndarray, e2: np.ndarray,
                  tmin: float, tmax: float) -> np.ndarray:
    """原点 ``o`` から方向 ``D`` (K,3) の各レイが、いずれかの三角形
    ``(A, e1=B-A, e2=C-A)`` (M,3) に ``t∈(tmin,tmax)`` で当たるか ``(K,)`` bool。"""
    pvec = np.cross(D[:, None, :], e2[None, :, :])           # (K,M,3)
    det = np.einsum("md,kmd->km", e1, pvec)                  # (K,M)
    nz = np.abs(det) > _DET_EPS
    inv = np.zeros_like(det)
    inv[nz] = 1.0 / det[nz]
    tvec = o[None, :] - A                                    # (M,3)
    u = np.einsum("md,kmd->km", tvec, pvec) * inv
    qvec = np.cross(tvec, e1)                                # (M,3)
    v = np.einsum("kd,md->km", D, qvec) * inv
    t = (np.einsum("md,md->m", e2, qvec))[None, :] * inv     # (K,M)
    hit = (nz & (u >= -_BARY_EPS) & (u <= 1.0 + _BARY_EPS)
           & (v >= -_BARY_EPS) & (u + v <= 1.0 + _BARY_EPS)
           & (t > tmin) & (t < tmax))
    return hit.any(axis=1)


# --------------------------------------------------------------------------- #
# 物体空間 AO(頂点ごと)                                                       #
# --------------------------------------------------------------------------- #
def vertex_occlusion(V, F, n_dirs: int = 64, max_dist: float | None = None,
                     normals=None, eps: float | None = None) -> np.ndarray:
    """メッシュ ``(V, F)`` の各頂点のアンビエントオクルージョン ``(N,)`` を [0,1] で返す。

    ``1`` = 完全露出(周囲に遮蔽物なし)、``0`` = 完全遮蔽。各頂点で外向き法線まわりの
    半球へ ``n_dirs`` 本のレイを飛ばし、``max_dist`` 以内でメッシュ自身に当たった割合を
    cos 重みで平均して遮蔽率とし、``AO = 1 - 遮蔽率``。自分に隣接する面(頂点を共有する面)は
    自己交差を避けるため除外し、原点は法線方向へ ``eps`` だけ浮かせる。

    *max_dist* は AO の局所性(遮蔽が効く距離)。``None`` なら境界箱対角の 0.5 倍。
    *normals* を省略すると面の巻き順から面積重み付き頂点法線を作る(外向き一貫を仮定)。
    fail-closed:形状不正・退化メッシュ・非有限は ``ValueError``。"""
    Vv, Ff = _as_mesh(V, F)
    nv = Vv.shape[0]
    diag = _bbox_diag(Vv)
    md = 0.5 * diag if max_dist is None else float(max_dist)
    if not np.isfinite(md) or md <= 0.0:
        raise ValueError(f"max_dist must be positive, got {max_dist!r}")

    A = Vv[Ff[:, 0]]
    B = Vv[Ff[:, 1]]
    C = Vv[Ff[:, 2]]
    e1 = B - A
    e2 = C - A
    fnorm = np.cross(e1, e2)                          # 長さ ∝ 2*面積(面積重みを兼ねる)
    centroid = (A + B + C) / 3.0
    # 三角形の「外接半径」上限(centroid から頂点までの最大距離)→ KDTree 枝刈りの余裕。
    tri_extent = float(np.linalg.norm(
        np.stack([A - centroid, B - centroid, C - centroid], axis=0), axis=2).max())

    # 頂点法線(外向き・面積重み)
    if normals is None:
        vn = np.zeros((nv, 3), np.float64)
        for k in range(3):
            np.add.at(vn, Ff[:, k], fnorm)           # 面積重み付き集約
        mag = np.linalg.norm(vn, axis=1, keepdims=True)
        vn = np.divide(vn, mag, out=np.zeros_like(vn), where=mag > 1e-12)
    else:
        vn = np.asarray(normals, np.float64)
        if vn.shape != (nv, 3):
            raise ValueError(f"normals must be ({nv}, 3), got {vn.shape}")
        if not np.isfinite(vn).all():
            raise ValueError("normals contain non-finite values")
        mag = np.linalg.norm(vn, axis=1, keepdims=True)
        if np.any(mag < 1e-12):
            raise ValueError("normals contain a zero-length vector")
        vn = vn / mag

    tree = cKDTree(centroid)
    eps_n = 1e-3 * diag if eps is None else float(eps)
    dirs_local, wts = _hemisphere_dirs(n_dirs)
    wsum = float(wts.sum())
    query_r = md + tri_extent

    ao = np.ones(nv, np.float64)
    for i in range(nv):
        n = vn[i]
        if not np.isfinite(n).all() or np.linalg.norm(n) < 1e-9:
            continue                                 # 向き未定 → 露出とみなす(AO=1)
        cand = tree.query_ball_point(Vv[i], query_r)
        if not cand:
            continue
        cand = np.asarray(cand, dtype=np.int64)
        # 自分を含む面(隣接面)を除外 — 自己交差防止
        own = ((Ff[cand, 0] == i) | (Ff[cand, 1] == i) | (Ff[cand, 2] == i))
        cand = cand[~own]
        if cand.size == 0:
            continue
        o = Vv[i] + eps_n * n
        t1, t2 = _basis_from_normal(n)
        D = (dirs_local[:, 0:1] * t1
             + dirs_local[:, 1:2] * t2
             + dirs_local[:, 2:3] * n)               # (K,3) 世界方向
        hit = _rays_hit_any(o, D, A[cand], e1[cand], e2[cand], tmin=0.0, tmax=md)
        occ = float((wts * hit).sum() / wsum)
        ao[i] = 1.0 - occ
    return ao


# --------------------------------------------------------------------------- #
# 画面 AO(render_mesh を土台に、頂点 AO を可視面へ焼き込む)                    #
# --------------------------------------------------------------------------- #
def ambient_occlusion(V, F, pose=None, intrinsics=None, width: int = 256,
                      height: int = 256, n_dirs: int = 64,
                      max_dist: float | None = None, k: int = 3,
                      background: float = 1.0) -> np.ndarray:
    """メッシュを AO マップ画像 ``(H, W)`` [0,1] にレンダリングして返す。

    ``render3d.render_mesh`` で depth / silhouette を得て(ラスタライズと隠面消去はそれに任せ、
    再発明しない)、物体空間 :func:`vertex_occlusion` の頂点 AO を、可視画素をカメラ空間へ
    逆投影して最近傍 ``k`` 頂点の逆距離重み補間で焼き込む。物体の外(silhouette=0)は
    ``background``(既定 1.0=完全露出)。*pose* / *intrinsics* 省略時は
    ``render3d.auto_view`` が枠取りする。fail-closed 検証は下位関数に従う。"""
    Vv, Ff = _as_mesh(V, F)
    w = int(width)
    h = int(height)
    if w <= 0 or h <= 0:
        raise ValueError(f"width and height must be positive, got {w}x{h}")

    if pose is None or intrinsics is None:
        ap, aK = render3d.auto_view(Vv, margin=1.2, width=w, height=h)
    P = ap if pose is None else np.asarray(pose, np.float64)
    K = aK if intrinsics is None else np.asarray(intrinsics, np.float64)
    if P.shape != (4, 4):
        raise ValueError(f"pose must be 4x4, got {P.shape}")
    if K.shape != (3, 3):
        raise ValueError(f"intrinsics must be 3x3, got {K.shape}")

    view = render3d.render_mesh(Vv, Ff, P, K, w, h)
    depth = view["depth"]
    sil = view["silhouette"]

    ao_vert = vertex_occlusion(Vv, Ff, n_dirs=n_dirs, max_dist=max_dist)

    img = np.full((h, w), float(background), np.float64)
    ys, xs = np.where(sil > 0)
    if ys.size == 0:
        return img                                   # 何も写っていない

    z = depth[ys, xs]                                # 前方メトリック距離(正)
    fx, fy = float(K[0, 0]), float(K[1, 1])
    cx, cy = float(K[0, 2]), float(K[1, 2])
    Xc = (xs + 0.5 - cx) * z / fx
    Yc = (cy - (ys + 0.5)) * z / fy
    Zc = -z                                          # カメラは -Z を向く
    pts = np.stack([Xc, Yc, Zc], axis=1)

    Vc = Vv @ P[:3, :3].T + P[:3, 3]                 # カメラ空間の頂点
    tree = cKDTree(Vc)
    kq = int(max(1, min(k, Vc.shape[0])))
    dist, nn = tree.query(pts, k=kq)
    if kq == 1:
        img[ys, xs] = ao_vert[nn]
    else:
        wgt = 1.0 / (dist + 1e-9)
        wgt /= wgt.sum(axis=1, keepdims=True)
        img[ys, xs] = (ao_vert[nn] * wgt).sum(axis=1)
    return img
