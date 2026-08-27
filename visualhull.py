"""多視点シルエットからの空間彫刻(visual hull / space carving)で voxel 占有を復元する。

Physical AI 向けの「形が先、テクスチャは後」の 3-D 再構成プリミティブ。既知の
校正済みカメラ群 ``(K, R, t)`` で撮ったオブジェクトのシルエット(前景マスク)だけ
から、その物体を必ず内包する凸でない体積(visual hull)を voxel 集合として彫り出す。
学習モデルも深度センサも要らず、幾何と集合演算だけで動く — 掴む対象の当たり判定、
occupancy grid の初期化、bin-pick の粗い体積推定などに使える下地。

原理(Laurentini 1994, "The Visual Hull Concept for Silhouette-Based Image
Understanding", PAMI): 各カメラのシルエットは 3-D 空間で視錐(visual cone)を張る。
物体は必ずすべての視錐の内側にあるので、視錐の **共通部分** が物体を上位集合として
覆う。ここではその共通部分を、bounding box を ``res^3`` に離散化した voxel 中心を
全カメラへ射影し「すべてのシルエット内に落ちる voxel だけ残す」空間彫刻で求める。

性質(honest):
- visual hull は連続空間では物体の **上位集合**(superset)。凹みのうちどのカメラ
  からも遮蔽で見えない窪みは埋まったまま残る(silhouette からは復元不能)。
- 凸物体(球・軸整列箱)は十分な視点数で hull ≈ 物体になり tight。
- カメラ 1 台では視錐そのもの(奥行き方向へ伸びる錐台)しか制約できず全く tight でない。
- 離散化(pixel 格子 + voxel 格子)で境界に約 1 セルの誤差が出る。recall(物体 voxel
  を取りこぼさない)を守るため、シルエットは「pixel 中心が覆われる」ではなく「pixel が
  少しでも物体に触れる」= 被覆(coverage)意味で 1 画素太らせる(下記 ``dilate``)。

射影規約(camera.py と同一, OpenCV スタイル): ``X_cam = R @ X_world + t``、
``u_hom = K @ X_cam``、``pixel = u_hom[:2] / u_hom[2]``、depth ``= X_cam[z] > 0`` のみ有効。
"""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
from scipy import ndimage

__all__ = ["synthesize_silhouette", "carve", "visual_hull", "look_at"]

Bounds = Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]


# --- small validators ------------------------------------------------------- #
def _as_pts3(a) -> np.ndarray:
    a = np.asarray(a, np.float64)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError("expected (N, 3) points, got shape %r" % (a.shape,))
    return a


def _as_K(K) -> np.ndarray:
    K = np.asarray(K, np.float64)
    if K.shape != (3, 3):
        raise ValueError("intrinsic matrix K must be 3x3, got %r" % (K.shape,))
    return K


def _as_R(R) -> np.ndarray:
    R = np.asarray(R, np.float64)
    if R.shape != (3, 3):
        raise ValueError("rotation R must be 3x3, got %r" % (R.shape,))
    return R


def _as_t(t) -> np.ndarray:
    t = np.asarray(t, np.float64).ravel()
    if t.size != 3:
        raise ValueError("translation t must have 3 elements, got %d" % t.size)
    return t


def _project(points: np.ndarray, K: np.ndarray, R: np.ndarray,
             t: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """World points (N,3) -> (pixel_uv (N,2) float, depth (N,) camera-frame Z)."""
    Xc = points @ R.T + t                       # X_cam = R X + t  (row-vector form)
    depth = Xc[:, 2]
    uvw = Xc @ K.T                              # homogeneous pixel = K X_cam
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = uvw[:, :2] / uvw[:, 2:3]
    return uv, depth


# --- public API ------------------------------------------------------------- #
def synthesize_silhouette(points, K, R, t, size: Tuple[int, int],
                          *, fill: bool = True, dilate: int = 1) -> np.ndarray:
    """3-D 点群を (K,R,t) カメラへ射影し占有画素 True のシルエット(H,W bool)を返す。

    GT 生成用。``points`` (N,3) を ``X_cam = R X + t`` で射影し、depth>0 かつ画像内に
    落ちた画素を True にする。疎な点群では射影像に穴が空くため、既定で穴埋め
    (``fill``, scipy.ndimage.binary_fill_holes)して中身の詰まった前景マスクにする。
    さらに ``dilate`` 画素だけ膨張させ「pixel が少しでも物体に触れれば前景」という
    被覆(coverage)意味のシルエットにする — これが visual hull の recall(物体 voxel を
    取りこぼさない)を離散化誤差の下でも保証するための保守側の丸め。

    Parameters
    ----------
    points : (N, 3) array_like  ワールド座標の点群(物体表面/内部のサンプル)。
    K : (3, 3)  内部パラメータ。
    R, t : (3, 3), (3,)  ワールド->カメラの回転・並進。
    size : (H, W)  出力画像サイズ。
    fill : bool  射影像の穴を埋めて solid にする(既定 True)。
    dilate : int  被覆マージンとして膨張させる画素数(既定 1、0 で無効)。

    Returns
    -------
    (H, W) bool ndarray  前景 True のシルエット。
    """
    P = _as_pts3(points)
    K = _as_K(K)
    R = _as_R(R)
    t = _as_t(t)
    H, W = int(size[0]), int(size[1])
    if H <= 0 or W <= 0:
        raise ValueError("size must be positive, got %r" % (size,))

    sil = np.zeros((H, W), dtype=bool)
    if P.shape[0] == 0:
        return sil

    uv, depth = _project(P, K, R, t)
    valid = depth > 0                                  # 前方の点のみ
    if not np.any(valid):
        return sil
    # nearest-pixel: 連続座標 (u,v) を整数画素中心へ丸める
    px = np.rint(uv[valid]).astype(np.int64)
    u = px[:, 0]
    v = px[:, 1]
    inside = (u >= 0) & (u < W) & (v >= 0) & (v < H)
    sil[v[inside], u[inside]] = True

    if fill:
        sil = ndimage.binary_fill_holes(sil)
    if dilate and dilate > 0:
        sil = ndimage.binary_dilation(sil, iterations=int(dilate))
    return sil


def carve(silhouettes: Sequence[np.ndarray], Ks: Sequence[np.ndarray],
          Rs: Sequence[np.ndarray], ts: Sequence[np.ndarray],
          bounds: Bounds, res: int) -> np.ndarray:
    """bounds を res^3 voxel に離散化し、全シルエット内に射影される voxel を残す(空間彫刻)。

    各 voxel 中心を全カメラ ``m`` に ``X_cam = R_m X + t_m`` で射影し、depth>0・画像内・
    ``silhouettes[m]`` が前景、を **すべて** 満たす voxel だけ keep する(視錐の共通部分)。
    シルエット/カメラは長さ M のリスト。

    Parameters
    ----------
    silhouettes : list of (H, W) bool array  各カメラの前景マスク(M 個)。
    Ks, Rs, ts : list  各カメラの内部パラメータ・回転・並進(各 M 個)。
    bounds : ((xmin,xmax),(ymin,ymax),(zmin,zmax))  彫刻する直方体領域。
    res : int  各軸の voxel 分割数(voxel 総数 = res^3)。

    Returns
    -------
    (res, res, res) bool ndarray  占有 voxel。indexing='ij' で軸は (x, y, z)。
        ``vox[i,j,k]`` の中心は ``(xmin+(i+.5)dx, ymin+(j+.5)dy, zmin+(k+.5)dz)``。
    """
    M = len(silhouettes)
    if not (M == len(Ks) == len(Rs) == len(ts)):
        raise ValueError("silhouettes/Ks/Rs/ts must have the same length")
    if res <= 0:
        raise ValueError("res must be positive, got %r" % (res,))
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bounds
    if not (xmax > xmin and ymax > ymin and zmax > zmin):
        raise ValueError("bounds must be non-degenerate (max > min per axis)")

    # voxel 中心(セル中心。境界に張り付かないよう +0.5 オフセット)
    xs = xmin + (np.arange(res) + 0.5) * (xmax - xmin) / res
    ys = ymin + (np.arange(res) + 0.5) * (ymax - ymin) / res
    zs = zmin + (np.arange(res) + 0.5) * (zmax - zmin) / res
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    centers = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)   # (res^3, 3)

    occ = np.ones(centers.shape[0], dtype=bool)
    if M == 0:
        # 制約カメラなし: bounds 全体が hull(全 voxel keep)
        return occ.reshape(res, res, res)

    for sil, K, R, t in zip(silhouettes, Ks, Rs, ts):
        sil = np.asarray(sil, dtype=bool)
        H, W = sil.shape
        uv, depth = _project(centers, _as_K(K), _as_R(R), _as_t(t))
        keep = np.zeros(centers.shape[0], dtype=bool)
        front = depth > 0                                  # カメラ後方は視錐外 -> 彫り取る
        if np.any(front):
            px = np.rint(uv[front]).astype(np.int64)
            u = px[:, 0]
            v = px[:, 1]
            inb = (u >= 0) & (u < W) & (v >= 0) & (v < H)
            idx = np.nonzero(front)[0][inb]
            in_sil = sil[v[inb], u[inb]]
            keep[idx[in_sil]] = True
        occ &= keep                                        # 視錐の共通部分(AND)

    return occ.reshape(res, res, res)


def visual_hull(silhouettes: Sequence[np.ndarray], Ks: Sequence[np.ndarray],
                Rs: Sequence[np.ndarray], ts: Sequence[np.ndarray],
                bounds: Bounds, res: int) -> np.ndarray:
    """多視点シルエットの visual hull を voxel 占有として返す(:func:`carve` の別名)。"""
    return carve(silhouettes, Ks, Rs, ts, bounds, res)


# --- convenience: multi-view GT 生成用のカメラ姿勢 --------------------------- #
def look_at(eye, target=(0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0)) -> Tuple[np.ndarray, np.ndarray]:
    """視点 eye から target を見る OpenCV カメラの (R, t) を作る(X_cam = R X + t)。

    カメラは +Z 前方・+X 右・+Y 下(OpenCV)。``R`` の行が world 座標で表したカメラ軸、
    ``t = -R @ eye``(カメラ中心が eye)。上方向 ``up`` が視線とほぼ平行なときは
    代替軸に切り替えて退化を避ける。多視点 GT シルエット生成の補助。

    Returns
    -------
    (R (3,3), t (3,))
    """
    eye = np.asarray(eye, np.float64).ravel()
    target = np.asarray(target, np.float64).ravel()
    up = np.asarray(up, np.float64).ravel()
    f = target - eye
    nf = np.linalg.norm(f)
    if nf < 1e-12:
        raise ValueError("eye and target coincide")
    f = f / nf                                             # camera +Z (forward)
    if abs(float(f @ (up / np.linalg.norm(up)))) > 0.999:  # up ∥ 視線 -> 退化回避
        up = np.array([1.0, 0.0, 0.0]) if abs(f[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up)                                     # camera +X (right)
    r = r / np.linalg.norm(r)
    d = np.cross(f, r)                                     # camera +Y (down) = f × r
    R = np.stack([r, d, f], axis=0)                        # rows = camera axes in world
    t = -R @ eye
    return R, t
