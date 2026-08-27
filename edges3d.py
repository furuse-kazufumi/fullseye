"""edges3d — 3D エッジ抽出(2D Canny / LoG のボリューム版)。

グレー voxel(3D numpy float、軸順 (D,H,W) = (depth, height, width))を入力に、
検出・照合の前処理として使えるエッジ場を計算する。2D の Canny / Laplacian-of-Gaussian
をそのまま 3 次元へ拡張したもので、すべて numpy + scipy.ndimage の閉形式(torch 不要)。

提供する関数:
    gradient3d(vol, sigma)          ガウス平滑後の中心差分勾配 → (gmag, gvec)
    canny3d(vol, low, high, sigma)  3D 非最大抑制 + ヒステリシス → 薄い(1 voxel)エッジ mask
    log_zero_crossings(vol, sigma)  LoG のゼロ交差 → エッジ mask
    link_edges(edge_mask)           26 近傍連結成分ラベリング → (labels, n)
    edge_points(edge_mask)          エッジ点群化 → (M,3) 座標(下流の chamfer / Hough へ)

軸・成分の規約:
    gvec[..., 0] = ∂I/∂axis0 (depth 方向), [..., 1] = axis1 (height), [..., 2] = axis2 (width)。
    edge_points が返す座標も (axis0, axis1, axis2) = (z, y, x) の順。

差別化: match3d.sobel3d は勾配「場」を返すだけで NMS もヒステリシスもない。ここは 2D Canny と
同じく方向に沿った非最大抑制で境界を 1 voxel に細線化し、二閾値ヒステリシスで断片化を抑える。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_laplace, label, map_coordinates


# --------------------------------------------------------------------------- #
# 入力検証                                                                     #
# --------------------------------------------------------------------------- #
def _check_vol(vol) -> np.ndarray:
    """3D の実数 voxel であることを検証し float64 配列にして返す。"""
    arr = np.asarray(vol, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(f"vol は 3 次元(D,H,W)である必要があります: ndim={arr.ndim}, shape={arr.shape}")
    if arr.size == 0:
        raise ValueError("vol が空です(size=0)")
    if not np.all(np.isfinite(arr)):
        raise ValueError("vol に NaN/Inf が含まれています。前処理で除去してください")
    return arr


def _check_mask(edge_mask) -> np.ndarray:
    """3D の bool mask に正規化する。"""
    arr = np.asarray(edge_mask)
    if arr.ndim != 3:
        raise ValueError(f"edge_mask は 3 次元である必要があります: ndim={arr.ndim}, shape={arr.shape}")
    return arr.astype(bool)


# --------------------------------------------------------------------------- #
# 1. 勾配場                                                                    #
# --------------------------------------------------------------------------- #
def gradient3d(vol, sigma: float = 1.0):
    """ガウス平滑後の中心差分勾配を計算する。

    Parameters
    ----------
    vol : (D,H,W) array
        グレー voxel。
    sigma : float
        ガウス平滑の標準偏差(voxel 単位)。0 で平滑なし(生の中心差分)。

    Returns
    -------
    gmag : (D,H,W) float64
        勾配の大きさ ||∇I||。
    gvec : (D,H,W,3) float64
        勾配ベクトル。成分は (∂/∂axis0, ∂/∂axis1, ∂/∂axis2) = (depth, height, width)。

    Notes
    -----
    平滑には scipy.ndimage.gaussian_filter(mode="nearest")、微分には np.gradient(spacing=1)
    を用いる。np.gradient は内部が中心差分、境界のみ片側差分。
    """
    arr = _check_vol(vol)
    if sigma < 0:
        raise ValueError(f"sigma は非負である必要があります: {sigma}")
    smoothed = gaussian_filter(arr, sigma=sigma, mode="nearest") if sigma > 0 else arr
    # np.gradient は各軸ごとの偏微分を list で返す(axis0, axis1, axis2)。
    g0, g1, g2 = np.gradient(smoothed)
    gvec = np.stack([g0, g1, g2], axis=-1)
    gmag = np.sqrt(g0 * g0 + g1 * g1 + g2 * g2)
    return gmag, gvec


# --------------------------------------------------------------------------- #
# 2. 3D Canny(NMS + ヒステリシス)                                            #
# --------------------------------------------------------------------------- #
def _nms3d(gmag: np.ndarray, gvec: np.ndarray) -> np.ndarray:
    """勾配方向に沿った 3D 非最大抑制。前後 2 点を三線形補間で比較し局所最大のみ残す。

    対称なリッジ(偶数幅)で 2 voxel 残るのを避けるため、後方は狭義・前方は広義比較にして
    タイを片側へ寄せ、1 voxel に細線化する。
    """
    D, H, W = gmag.shape
    eps = 1e-12
    unit = gvec / (gmag[..., None] + eps)  # 単位勾配方向(gmag≈0 の voxel は ~0 ベクトル)

    zz, yy, xx = np.indices((D, H, W), dtype=np.float64)
    uz, uy, ux = unit[..., 0], unit[..., 1], unit[..., 2]

    fwd = np.stack([zz + uz, yy + uy, xx + ux], axis=0)   # 勾配方向へ +1 step
    bwd = np.stack([zz - uz, yy - uy, xx - ux], axis=0)   # 勾配方向へ -1 step
    g_fwd = map_coordinates(gmag, fwd, order=1, mode="nearest")
    g_bwd = map_coordinates(gmag, bwd, order=1, mode="nearest")

    # 後方は狭義(>)、前方は広義(>=)。対称ピークのタイを後方側 1 voxel に寄せる。
    keep = (gmag > g_bwd) & (gmag >= g_fwd) & (gmag > 0.0)
    return keep


def _hysteresis(nms_keep: np.ndarray, gmag: np.ndarray, low: float, high: float) -> np.ndarray:
    """二閾値ヒステリシス。high 種を含む low 連結成分(26 近傍)のみ残す。"""
    weak = nms_keep & (gmag >= low)
    strong = nms_keep & (gmag >= high)
    if not strong.any():
        return np.zeros_like(nms_keep, dtype=bool)
    structure = np.ones((3, 3, 3), dtype=int)  # 26 連結
    labels, _ = label(weak, structure=structure)
    # strong voxel が属するラベル集合を取り、その連結成分だけ残す。
    keep_labels = np.unique(labels[strong])
    keep_labels = keep_labels[keep_labels != 0]
    return np.isin(labels, keep_labels)


def canny3d(vol, low: float, high: float, sigma: float = 1.0) -> np.ndarray:
    """3D Canny エッジ検出(非最大抑制 + ヒステリシス)。

    Parameters
    ----------
    vol : (D,H,W) array
        グレー voxel。
    low, high : float
        ヒステリシスの下限 / 上限閾値(勾配の大きさに対して)。0 <= low <= high, high > 0。
    sigma : float
        平滑の標準偏差。

    Returns
    -------
    edge_mask : (D,H,W) bool
        1 voxel に細線化されたエッジ。

    Notes
    -----
    (1) gradient3d で平滑勾配を得る → (2) 勾配方向に沿った NMS(三線形補間)で局所最大を残し
    → (3) high 閾値を種に low 閾値で 26 連結を伸長。閾値は絶対値なので、対象に応じて
    gmag.max() のスケールで与えるとロバスト。
    """
    if not (np.isfinite(low) and np.isfinite(high)):
        raise ValueError(f"low/high は有限値である必要があります: low={low}, high={high}")
    if low < 0:
        raise ValueError(f"low は非負である必要があります: {low}")
    if high <= 0:
        raise ValueError(f"high は正である必要があります: {high}")
    if low > high:
        raise ValueError(f"low <= high である必要があります: low={low}, high={high}")

    gmag, gvec = gradient3d(vol, sigma=sigma)
    nms_keep = _nms3d(gmag, gvec)
    return _hysteresis(nms_keep, gmag, low, high)


# --------------------------------------------------------------------------- #
# 3. LoG ゼロ交差                                                              #
# --------------------------------------------------------------------------- #
def log_zero_crossings(vol, sigma: float = 1.5, rel_thresh: float = 1e-3) -> np.ndarray:
    """Laplacian-of-Gaussian のゼロ交差エッジ。

    Parameters
    ----------
    vol : (D,H,W) array
        グレー voxel。
    sigma : float
        LoG の標準偏差(> 0)。
    rel_thresh : float
        平坦部の数値ノイズによる偽交差を抑える相対閾値。交差ペアの LoG 差 |a-b| が
        rel_thresh * max|L| を超える場合のみ採用する。

    Returns
    -------
    edge_mask : (D,H,W) bool
        符号が変化する隣接ペアのうち |LoG| が小さい側(ゼロにより近い側)を立てた mask。

    Notes
    -----
    各軸方向に二種類のゼロ交差を検出する:
    (1) 格子間交差 — 隣接ペア (a,b) の符号積 a*b < 0(両側とも非ゼロで符号反転)。厚みを
        抑えるためペアのうち |LoG| が小さい側 1 voxel に割り当てる。
    (2) 格子整列交差 — 中央 voxel が厳密ゼロ(L==0)で両隣が異符号(符号がその voxel で
        ゼロを通過)する場合。SDF 風の格子に整列した面で LoG がちょうど格子点上で 0 に
        なる真のエッジは a*b が常に 0 となり (1) では取りこぼすため、当該 voxel を交差
        として立てる。定数ゼロ領域は両隣も 0 で Lm*Lp==0 となり除外される(誤検出しない)。
    いずれも平坦部の数値ノイズは相対閾値(rel_thresh * max|L|)で抑制する。
    """
    arr = _check_vol(vol)
    if sigma <= 0:
        raise ValueError(f"sigma は正である必要があります: {sigma}")

    L = gaussian_laplace(arr, sigma=sigma, mode="nearest")
    scale = float(np.abs(L).max())
    edges = np.zeros(L.shape, dtype=bool)
    if scale == 0.0:
        return edges  # 完全平坦 → エッジなし
    tol = rel_thresh * scale

    for axis in range(3):
        sl_a = [slice(None)] * 3
        sl_b = [slice(None)] * 3
        sl_a[axis] = slice(0, -1)
        sl_b[axis] = slice(1, None)
        a = L[tuple(sl_a)]
        b = L[tuple(sl_b)]
        cross = (a * b < 0.0) & (np.abs(a - b) > tol)  # 格子間: 厳密な符号反転かつ有意な変化
        # ゼロに近い側(|.| が小さい側)へ割り当て → 薄いエッジ
        pick_a = cross & (np.abs(a) <= np.abs(b))
        pick_b = cross & (np.abs(b) < np.abs(a))
        edges[tuple(sl_a)] |= pick_a
        edges[tuple(sl_b)] |= pick_b

        # 格子整列: 中央 voxel が厳密ゼロで両隣が異符号(符号がゼロを通過)する交差。
        # a*b<0 では常に 0 積となり取りこぼすため、当該 voxel を直接立てる。定数ゼロ領域は
        # 隣も 0 → Lm*Lp==0 で除外、数値ノイズは |Lm - Lp| > tol で抑制。
        if L.shape[axis] >= 3:
            sl_c = [slice(None)] * 3  # 中央 i
            sl_m = [slice(None)] * 3  # i-1
            sl_p = [slice(None)] * 3  # i+1
            sl_c[axis] = slice(1, -1)
            sl_m[axis] = slice(0, -2)
            sl_p[axis] = slice(2, None)
            Lc = L[tuple(sl_c)]
            Lm = L[tuple(sl_m)]
            Lp = L[tuple(sl_p)]
            on_grid = (Lc == 0.0) & (Lm * Lp < 0.0) & (np.abs(Lm - Lp) > tol)
            edges[tuple(sl_c)] |= on_grid

    return edges


# --------------------------------------------------------------------------- #
# 4. エッジの連結(26 近傍ラベリング)                                         #
# --------------------------------------------------------------------------- #
def link_edges(edge_mask):
    """エッジ mask を 26 近傍で連結成分ラベリングする。

    Parameters
    ----------
    edge_mask : (D,H,W) bool

    Returns
    -------
    labels : (D,H,W) int
        各 voxel の成分ラベル(背景 = 0、成分 = 1..n)。
    n : int
        連結成分数。

    Notes
    -----
    26 連結(3x3x3 の全近傍)。断片化したエッジ片を 1 本の曲線 / 閉曲面としてまとめ、
    下流の Hough / chamfer で成分単位に扱えるようにする。
    """
    mask = _check_mask(edge_mask)
    structure = np.ones((3, 3, 3), dtype=int)  # 26 連結
    labels, n = label(mask, structure=structure)
    return labels, int(n)


# --------------------------------------------------------------------------- #
# 5. エッジ点群化                                                              #
# --------------------------------------------------------------------------- #
def edge_points(edge_mask) -> np.ndarray:
    """エッジ mask を (M,3) の座標点群にする(下流の chamfer / Hough 用)。

    Parameters
    ----------
    edge_mask : (D,H,W) bool

    Returns
    -------
    pts : (M,3) float64
        エッジ voxel の座標(axis0, axis1, axis2) = (z, y, x)。M = エッジ voxel 数。
        エッジが無ければ shape (0,3) を返す。
    """
    mask = _check_mask(edge_mask)
    pts = np.argwhere(mask)  # (M,3) int
    if pts.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    return pts.astype(np.float64)


if __name__ == "__main__":
    # 中実立方体でのセルフデモ。
    D = H = W = 32
    v = np.zeros((D, H, W), dtype=np.float64)
    v[8:24, 8:24, 8:24] = 1.0
    gmag, _ = gradient3d(v, sigma=1.0)
    hi, lo = 0.3 * gmag.max(), 0.1 * gmag.max()
    e = canny3d(v, lo, hi, sigma=1.0)
    z = log_zero_crossings(v, sigma=1.5)
    labels, n = link_edges(e)
    pts = edge_points(e)
    print(f"canny3d edges={int(e.sum())}  thick(gmag>=low)={int((gmag >= lo).sum())}  "
          f"components={n}  points={pts.shape}")
    print(f"log zero-crossings={int(z.sum())}")
