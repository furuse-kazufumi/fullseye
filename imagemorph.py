# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imagemorph — 対応点(ランドマーク)駆動の2D画像ワープとモーフ。

2枚の画像 A, B と、それぞれの上の対応点(目・鼻・口・輪郭など)を与えると、
特徴を幾何的に「中間形状」へ合わせてからクロスディゾルブすることで、
**単純な半透明合成では得られない「本物の中間画像」**を作る(Beier & Neely,
"Feature-Based Image Metamorphosis", SIGGRAPH 1992 のメッシュ・モーフ流)。

なぜ α ブレンドだけでは駄目か:
    目や鼻の位置がズレたまま 2 枚を重ねると、特徴が二重像(ゴースト)になる。
    先に **ワープで特徴位置を揃える**(A の目と B の目を中間位置へ動かす)ことで、
    ブレンド後も特徴が 1 つに重なり、顔なら「2 人の中間の顔」に見える。

提供する汎用op(顔専用ではない — 登録・データ拡張・テンプレート整列・医用位置
合わせにも効く):
    warp_piecewise_affine(img, src_pts, dst_pts)  区分アフィン(Delaunay 三角形)
    warp_tps_image(img, src_pts, dst_pts, lam)     薄板スプライン(TPS, 滑らか)
    blend(a, b, alpha)                             クロスディゾルブ
    morph(imgA, imgB, ptsA, ptsB, alpha, method)   2 枚のモーフ(warp + dissolve)
    morph_sequence(imgA, imgB, ptsA, ptsB, n)      α を 0→1 に振ったモーフ列

規約(既存 flow.warp_by_flow / deformreg.warp_by_field と同じ):
    画像は (H, W) か (H, W, C)、値域 [0, 1] の float。ワープは**逆写像**
    (out[p] = img[f(p)])で穴が空かない(Wolberg, *Digital Image Warping*, 1990,
    Sec. 3.5)。点は (N, 2) の (x, y) ピクセル座標。

★★ 座標順の落とし穴(2026-09-02 に明文化)★★
    このモジュール(``morph`` / ``morph_sequence`` / ``warp_piecewise_affine`` /
    ``warp_tps_image`` / ``add_frame_corners``)の点は **(x, y) = (列, 行)**。
    いっぽう **XLD 輪郭 (``contour["cs"][i]``) と ``fourierdesc.from_xld`` は
    (row, col) = (行, 列)** で、順序が **逆** である。

    両者とも (N,2) の float 配列なので、(row, col) をそのまま渡しても
    **例外は出ない**。出るのは「それらしく見えるが間違った」モーフ
    モーフ。
    実測(96x96、円盤 A(30,30) -> B(62,66)、12 点の対応点、alpha=0.5): 同じ対応点で affine と TPS を掛けたときの平均差が、(row,col) を渡すと **0.00488**、正しく (x,y) に直すと **0.00260** —— 座標順を間違えると 2 つの補間法が別々の場所へワープするので食い違いが約 1.9 倍に開く。
    **黙って間違う**型の事故なので、
    XLD 側から点を持ってくるときは必ず列を入れ替えること::

        pts_xy = np.asarray(fourierdesc.from_xld(contour))[:, ::-1]   # (row,col) -> (x,y)
        out    = imagemorph.morph(A, B, ptsA_xy, pts_xy, 0.5)
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial import Delaunay

__all__ = [
    "warp_piecewise_affine",
    "warp_tps_image",
    "blend",
    "morph",
    "morph_sequence",
    "add_frame_corners",
]


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _as_image(img, name="img"):
    a = np.asarray(img, dtype=np.float64)
    if a.ndim not in (2, 3):
        raise ValueError(f"{name} must be (H,W) or (H,W,C) (got: {a.shape})")
    if a.size == 0 or a.shape[0] == 0 or a.shape[1] == 0:
        raise ValueError(f"{name} is empty")
    if not np.all(np.isfinite(a)):
        a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0)
    return a


def _as_pts(p, name):
    a = np.asarray(p, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(f"{name} must be (N,2) (x,y) coordinates (got: {a.shape})")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} contains non-finite values")
    return a


def _sample(img, xs, ys, order=1):
    """img を浮動小数座標 (xs, ys) で逆写像サンプル(端はクランプ)。

    xs, ys は出力と同形の (H,W)。返りは img と同 shape・[0,1] にクリップ。
    """
    H, W = img.shape[:2]
    coords = np.stack([ys.ravel(), xs.ravel()], axis=0)  # map_coordinates は [row, col]
    if img.ndim == 3:
        chans = [
            map_coordinates(img[..., c], coords, order=order, mode="nearest").reshape(H, W)
            for c in range(img.shape[2])
        ]
        out = np.stack(chans, axis=-1)
    else:
        out = map_coordinates(img, coords, order=order, mode="nearest").reshape(H, W)
    return np.clip(out, 0.0, 1.0)


def add_frame_corners(pts, shape):
    """点群に画像の四隅(+辺の中点)を固定点として足す。

    ワープの三角形分割が画像全体を覆い、凸包の外側にできる穴を防ぐための定番処置。
    src/dst の両方に同じ順序で足せば、四隅は「動かない対応点」として働く。
    """
    p = _as_pts(pts, "pts")
    H, W = shape[:2]
    x1, y1 = 0.0, 0.0
    x2, y2 = float(W - 1), float(H - 1)
    xm, ym = x2 / 2.0, y2 / 2.0
    frame = np.array(
        [[x1, y1], [xm, y1], [x2, y1],
         [x1, ym], [x2, ym],
         [x1, y2], [xm, y2], [x2, y2]],
        dtype=np.float64,
    )
    return np.vstack([p, frame])


# --------------------------------------------------------------------------- #
# 1) 区分アフィン(Delaunay 三角形)ワープ                                     #
# --------------------------------------------------------------------------- #
def warp_piecewise_affine(img, src_pts, dst_pts, order=1):
    """img の src_pts にある内容を dst_pts へ動かす区分アフィンワープ。

    dst_pts を Delaunay 三角形分割し、各出力画素が属す三角形の重心座標を求め、
    同じ重心座標で src_pts 側の対応三角形へ写して逆写像サンプルする。凸包の外側
    (三角形に属さない画素)は恒等(元位置)でサンプルするため、四隅を対応点に含める
    (:func:`add_frame_corners`)と穴なく画像全体を覆える。

    引数:
        img: (H,W) か (H,W,C)、[0,1]。
        src_pts, dst_pts: (K,2) の (x,y)。同数・同順の対応点。
        order: 補間次数(1=バイリニア)。

    返り値: img と同 shape・[0,1] の float64。
    """
    a = _as_image(img, "img")
    src = _as_pts(src_pts, "src_pts")
    dst = _as_pts(dst_pts, "dst_pts")
    if src.shape[0] != dst.shape[0]:
        raise ValueError(f"src_pts and dst_pts have mismatched point counts ({src.shape[0]} vs {dst.shape[0]})")
    if src.shape[0] < 3:
        raise ValueError(f"triangulation needs at least 3 corresponding points (got: {src.shape[0]})")

    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    grid = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(np.float64)  # (N,2) (x,y)

    tri = Delaunay(dst)
    simplex = tri.find_simplex(grid)  # (N,) 属す三角形 id、外側は -1
    inside = simplex >= 0

    source = grid.copy()  # 外側は恒等(元位置)
    if np.any(inside):
        s = simplex[inside]
        T = tri.transform[s]              # (M,3,2)
        b2 = np.einsum("nij,nj->ni", T[:, :2, :], grid[inside] - T[:, 2, :])  # (M,2)
        bary = np.column_stack([b2, 1.0 - b2.sum(axis=1)])  # (M,3) 重心座標
        verts = tri.simplices[s]          # (M,3) 対応点 index
        src_tri = src[verts]              # (M,3,2)
        source[inside] = np.einsum("nk,nkd->nd", bary, src_tri)  # (M,2)

    xs = source[:, 0].reshape(H, W)
    ys = source[:, 1].reshape(H, W)
    return _sample(a, xs, ys, order=order)


# --------------------------------------------------------------------------- #
# 2) 薄板スプライン(TPS)画像ワープ                                          #
# --------------------------------------------------------------------------- #
def _tps_kernel_2d(r):
    """2D TPS の放射基底 U(r) = r² · log r(U(0)=0)。"""
    r = np.asarray(r, dtype=np.float64)
    out = np.zeros_like(r)
    nz = r > 1e-12
    out[nz] = (r[nz] ** 2) * np.log(r[nz])
    return out


def _pairwise_dist(a, b):
    d = a[:, None, :] - b[None, :, :]
    return np.sqrt(np.maximum(np.einsum("ijk,ijk->ij", d, d), 0.0))


def _tps_fit_2d(src, dst, lam=0.0):
    """src → dst を写す 2D TPS を制御点対応から当てはめる(鞍点系の最小二乗)。"""
    p = _as_pts(src, "src")
    v = _as_pts(dst, "dst")
    n = p.shape[0]
    if n < 3:
        raise ValueError(f"2D TPS needs at least 3 control points (got: {n})")
    if lam < 0:
        raise ValueError(f"lam must be non-negative (got: {lam})")
    K = _tps_kernel_2d(_pairwise_dist(p, p))
    if lam > 0:
        K = K + lam * np.eye(n)
    P = np.hstack([np.ones((n, 1)), p])          # [1, x, y]  (n,3)
    L = np.zeros((n + 3, n + 3), dtype=np.float64)
    L[:n, :n] = K
    L[:n, n:] = P
    L[n:, :n] = P.T
    Y = np.zeros((n + 3, 2), dtype=np.float64)
    Y[:n, :] = v
    params, *_ = np.linalg.lstsq(L, Y, rcond=None)
    return {"ctrl": p, "w": params[:n, :], "a": params[n:, :], "lam": float(lam)}


def _tps_eval(model, pts):
    ctrl = model["ctrl"]
    U = _tps_kernel_2d(_pairwise_dist(pts, ctrl))
    Phi = np.hstack([np.ones((pts.shape[0], 1)), pts])
    return Phi @ model["a"] + U @ model["w"]


def warp_tps_image(img, src_pts, dst_pts, lam=0.0, order=1):
    """薄板スプラインで img の src_pts を dst_pts へ動かす滑らかなワープ。

    出力座標 → 入力座標の逆写像 TPS(dst→src)を当てはめ、出力全格子で評価して
    サンプルする。lam=0 なら制御点上で厳密に対応(特徴が正しく着地)、lam>0 で
    変形を平滑化。区分アフィンより滑らかだが、全画素×制御点のカーネル評価コスト。

    引数・返り値は :func:`warp_piecewise_affine` と同じ。
    """
    a = _as_image(img, "img")
    src = _as_pts(src_pts, "src_pts")
    dst = _as_pts(dst_pts, "dst_pts")
    if src.shape[0] != dst.shape[0]:
        raise ValueError(f"src_pts and dst_pts have mismatched point counts ({src.shape[0]} vs {dst.shape[0]})")

    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    grid = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(np.float64)  # (N,2)

    inv = _tps_fit_2d(dst, src, lam=lam)         # 出力(dst)座標 → 入力(src)座標
    source = _tps_eval(inv, grid)                # (N,2)
    xs = source[:, 0].reshape(H, W)
    ys = source[:, 1].reshape(H, W)
    return _sample(a, xs, ys, order=order)


# --------------------------------------------------------------------------- #
# 3) ブレンドとモーフ                                                          #
# --------------------------------------------------------------------------- #
def blend(a, b, alpha):
    """クロスディゾルブ (1-alpha)·a + alpha·b(a,b は同 shape・[0,1])。"""
    A = _as_image(a, "a")
    B = _as_image(b, "b")
    if A.shape != B.shape:
        raise ValueError(f"a and b have mismatched shapes ({A.shape} vs {B.shape})")
    t = float(np.clip(alpha, 0.0, 1.0))
    return np.clip((1.0 - t) * A + t * B, 0.0, 1.0)


def _warp(img, src_pts, dst_pts, method, lam):
    if method == "affine":
        return warp_piecewise_affine(img, src_pts, dst_pts)
    if method == "tps":
        return warp_tps_image(img, src_pts, dst_pts, lam=lam)
    raise ValueError(f"method must be 'affine' or 'tps' (got: {method!r})")


def morph(imgA, imgB, ptsA, ptsB, alpha, method="affine", lam=0.0, with_corners=True):
    """2 枚の画像 A, B を対応点でモーフし、比率 alpha の中間画像を作る。

    手順(Beier–Neely 流のメッシュ・モーフ):
        1. 中間形状 mid = (1-alpha)·ptsA + alpha·ptsB を作る。
        2. A を ptsA→mid へ、B を ptsB→mid へワープ(両者の特徴を mid に揃える)。
        3. warp(A), warp(B) を alpha でクロスディゾルブ。
    alpha=0 で A、alpha=1 で B に一致する。単純な blend(A,B,alpha) と違い、
    目・鼻などの特徴が二重像にならず 1 つに重なる(=「本物の中間」)。

    引数:
        imgA, imgB: (H,W[,C])、同 shape、[0,1]。
        ptsA, ptsB: (K,2) の (x,y)。A と B の対応点(同数・同順)。
        alpha: 合成比率 [0,1]。
        method: "affine"(区分アフィン, 速い)か "tps"(滑らか)。
        lam: TPS の平滑化係数(method="tps" のとき)。
        with_corners: True で四隅を固定点に足し、端の穴を防ぐ。

    返り値: (H,W[,C]) の中間画像([0,1])。
    """
    A = _as_image(imgA, "imgA")
    B = _as_image(imgB, "imgB")
    if A.shape != B.shape:
        raise ValueError(f"imgA and imgB have mismatched shapes ({A.shape} vs {B.shape})")
    pa = _as_pts(ptsA, "ptsA")
    pb = _as_pts(ptsB, "ptsB")
    if pa.shape != pb.shape:
        raise ValueError(f"ptsA and ptsB have mismatched point counts ({pa.shape[0]} vs {pb.shape[0]})")
    if with_corners:
        pa = add_frame_corners(pa, A.shape)
        pb = add_frame_corners(pb, B.shape)

    t = float(np.clip(alpha, 0.0, 1.0))
    mid = (1.0 - t) * pa + t * pb
    wa = _warp(A, pa, mid, method, lam)
    wb = _warp(B, pb, mid, method, lam)
    return np.clip((1.0 - t) * wa + t * wb, 0.0, 1.0)


def morph_sequence(imgA, imgB, ptsA, ptsB, n=7, method="affine", lam=0.0, with_corners=True):
    """alpha を 0→1 に n 段で振ったモーフ列(A から B へ滑らかに変わる各フレーム)。

    返り値: 長さ n の list。先頭が A、末尾が B に一致する。
    """
    if n < 2:
        raise ValueError(f"n must be >= 2 (got: {n})")
    alphas = np.linspace(0.0, 1.0, int(n))
    return [
        morph(imgA, imgB, ptsA, ptsB, a, method=method, lam=lam, with_corners=with_corners)
        for a in alphas
    ]
