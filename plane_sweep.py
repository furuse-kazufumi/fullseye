# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""plane_sweep — 2視点 plane-sweep stereo(平面掃引で密な深度を推定)。

twoview が疎な対応点から相対姿勢を復元し、bundle3d が多視点を最適化するのに対し、
plane_sweep は**姿勢既知の 2 枚**から**密な深度マップ**を作る MVS(Multi-View Stereo)の初歩。
基準カメラの視錐台を候補深度で切る一連のフロント平行平面(法線 n=[0,0,1])を仮定し、各深度平面が
誘導する homography で source 画像を reference へワープ、photo-consistency(輝度差)が最小の深度を
画素ごとに選ぶ(winner-take-all)。

原理: 基準カメラを [I|0]、source を [R|t] とする。平面 n^T X = d 上の 3D 点は
X_src = (R + t n^T / d) X_ref を満たすので、画素対応は homography
H = K (R + t n^T / d) K^{-1}(ref 画素 → src 画素)で表せる。ref 画素 p を depth d と仮定して
src を H p で採り、|I_ref(p) - I_src(H p)| が小さいほどその深度が正しい。真の深度で 3D 点が平面上に
乗り、ワープが一致してコストが最小になる。フロント平行掃引でも、傾いた面の各画素の真の Z(その ray が
面と交わる深度)で平面が点を通過するため、窓なし(window=1)なら傾斜面の per-pixel 深度も厳密に復元。

規約: 画像は (H,W) grayscale の float 配列。K は 3x3 共通内部行列。R,t は source の基準に対する姿勢
(P_src = K[R|t])。depth_candidates は基準カメラ座標での正の深度列。深度は winner-take-all(近傍候補への
量子化誤差 ~ 候補間隔)。fail-closed: 空・非 2D・shape 不一致・非正深度・特異 K は明示 raise。

GT 検証 = 合成テクスチャ平面(既知深度)を 2 視点でレンダ → plane_sweep_depth がその深度を復元
(相対誤差 < 数%)。フロント平行/傾斜面の両方。

用途: 姿勢既知ステレオの密深度、terrain heightmap / point cloud の前段、多視点再構成の初期化
(Physical AI の空間認識)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["plane_homography", "warp_by_plane", "cost_volume", "plane_sweep_depth"]


def _check_image(img: np.ndarray, name: str) -> np.ndarray:
    """2D float 画像を検証して返す(fail-closed)。"""
    a = np.asarray(img, dtype=float)
    if a.ndim != 2:
        raise ValueError(f"{name} must be 2D grayscale (ndim={a.ndim})")
    if a.size == 0:
        raise ValueError(f"{name} is empty")
    return a


def plane_homography(K: np.ndarray, R: np.ndarray, t: np.ndarray, depth: float,
                     normal=(0.0, 0.0, 1.0)) -> np.ndarray:
    """平面 n^T X = depth が誘導する homography H(ref 画素 → src 画素)。→ (3,3)。

    H = K (R + t n^T / depth) K^{-1}。基準カメラ [I|0]、source [R|t]。depth<=0 は raise。
    """
    K = np.asarray(K, float)
    R = np.asarray(R, float)
    t = np.asarray(t, float).reshape(3)
    n = np.asarray(normal, float).reshape(3)
    if K.shape != (3, 3) or R.shape != (3, 3):
        raise ValueError("K,R must be 3x3")
    if not np.isfinite(depth) or depth <= 0:
        raise ValueError(f"depth must be a positive finite value (depth={depth})")
    try:
        Kinv = np.linalg.inv(K)
    except np.linalg.LinAlgError as e:
        raise ValueError("K is singular (no inverse)") from e
    return K @ (R + np.outer(t, n) / depth) @ Kinv


def warp_by_plane(img: np.ndarray, H: np.ndarray, order: int = 1,
                  cval: float = np.nan) -> np.ndarray:
    """homography H で img を逆ワープ。→ out[y,x] = img(H·(x,y,1))(bilinear)。

    H は出力(ref)画素 → 入力(src)画素の写像。視野外は cval(既定 NaN)。
    """
    a = _check_image(img, "img")
    H = np.asarray(H, float)
    if H.shape != (3, 3):
        raise ValueError("H must be 3x3")
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    ones = np.ones_like(xx, dtype=float)
    p = np.stack([xx.ravel(), yy.ravel(), ones.ravel()], axis=0)  # (3, h*w)
    q = H @ p
    z = q[2]
    # z≈0(無限遠)は視野外扱い
    bad = np.abs(z) < 1e-12
    z_safe = np.where(bad, 1.0, z)
    sx = q[0] / z_safe
    sy = q[1] / z_safe
    # map_coordinates は (row, col) = (sy, sx) 順
    coords = np.stack([sy, sx], axis=0)
    out = ndimage.map_coordinates(a, coords, order=order, mode="constant",
                                  cval=cval, prefilter=False)
    out = out.reshape(h, w)
    if bad.any():
        out.ravel()[bad] = cval
    return out


def cost_volume(img_ref: np.ndarray, img_src: np.ndarray, K: np.ndarray,
                R: np.ndarray, t: np.ndarray, depth_candidates,
                window: int = 1, normal=(0.0, 0.0, 1.0),
                invalid_cost: float = np.inf) -> np.ndarray:
    """各候補深度で src を ref へワープし photo-consistency コストを積む。→ (D,H,W)。

    コスト = |I_ref - warp(I_src)|、window>1 なら box 集約(SAD)。視野外画素は invalid_cost。
    """
    ref = _check_image(img_ref, "img_ref")
    src = _check_image(img_src, "img_src")
    if ref.shape != src.shape:
        raise ValueError(f"img_ref and img_src shape mismatch {ref.shape} vs {src.shape}")
    depths = np.asarray(depth_candidates, dtype=float).ravel()
    if depths.size == 0:
        raise ValueError("depth_candidates is empty")
    if not np.all(np.isfinite(depths)) or np.any(depths <= 0):
        raise ValueError("depth_candidates must contain only positive finite values")
    if int(window) < 1:
        raise ValueError("window must be at least 1")
    window = int(window)

    h, w = ref.shape
    vol = np.empty((depths.size, h, w), dtype=float)
    for i, d in enumerate(depths):
        H = plane_homography(K, R, t, d, normal=normal)
        warped = warp_by_plane(src, H, order=1, cval=np.nan)
        cost = np.abs(ref - warped)
        invalid = ~np.isfinite(cost)
        if window > 1:
            # 視野外を 0 で埋めて box 和、有効画素数で正規化(端/視野外を honest に扱う)
            filled = np.where(invalid, 0.0, cost)
            valid = (~invalid).astype(float)
            ksum = ndimage.uniform_filter(filled, size=window, mode="constant",
                                          cval=0.0) * (window * window)
            cnt = ndimage.uniform_filter(valid, size=window, mode="constant",
                                         cval=0.0) * (window * window)
            with np.errstate(invalid="ignore", divide="ignore"):
                # cnt は窓内の有効画素数(整数)。uniform_filter の分離和で ~1e-16 の丸め残差が
                # 乗るため cnt>0 だと全無効窓(真の cnt=0)が finite/負の捏造コストを得て argmin を
                # 汚す。有効 1 画素で cnt≈1 なので整数境界 0.5 でガード(丸め残差は 0.5 未満)。
                cost = np.where(cnt >= 0.5, ksum / np.maximum(cnt, 1.0), np.inf)
        else:
            cost = np.where(invalid, invalid_cost, cost)
        vol[i] = cost
    return vol


def plane_sweep_depth(img_ref: np.ndarray, img_src: np.ndarray, K: np.ndarray,
                      R: np.ndarray, t: np.ndarray, depth_candidates,
                      window: int = 1, normal=(0.0, 0.0, 1.0)) -> np.ndarray:
    """plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。

    各深度平面で src を ref へワープし、photo-consistency 最小の候補深度を画素ごとに選ぶ
    (winner-take-all)。全候補で視野外の画素は NaN。fail-closed(空/非 2D/shape 不一致/非正深度)。
    """
    depths = np.asarray(depth_candidates, dtype=float).ravel()
    vol = cost_volume(img_ref, img_src, K, R, t, depths, window=window, normal=normal)
    idx = np.argmin(vol, axis=0)
    depth = depths[idx]
    # 全候補で無効(∞)の画素は NaN
    all_invalid = ~np.any(np.isfinite(vol), axis=0)
    if all_invalid.any():
        depth = depth.astype(float)
        depth[all_invalid] = np.nan
    return depth
