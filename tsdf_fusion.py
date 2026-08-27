"""多フレーム TSDF 体積融合(KinectFusion 核)= 深度列 → 重み付き符号付き距離場 → 表面点。

各 voxel 中心を各フレームの (K,R,t) で射影し、観測深度との投影的符号付き距離
``sdf = (d_meas - d_voxel)/trunc`` を [-1,1] に切り詰め、**重み付き移動平均**で volume に
統合する(KinectFusion / Curless-Levoy 1996 の projective TSDF)。全フレーム統合後、
ゼロ交差する voxel 辺を線形補間して表面点を出す。

固有価値(既存モジュールとの差別化 — honest):
  * ``match3d.tsdf_from_depth`` は **単フレーム**の TSDF を作るだけ(重みも融合も表面抽出も
    無く、後方切り詰め=遮蔽処理も無い)。本モジュールは **複数フレームを running weight で
    融合**し、**遮蔽領域(表面より trunc 以上奥)は更新しない**(Curless-Levoy / Andy Zeng 流)
    ことで多視点の穴埋め・整合を行い、さらに **ゼロ交差表面抽出**まで担う。
  * ``fuse3d.fuse_to_voxel`` は点群スプラットの **密度/占有** voxel(符号無し)で、視線遮蔽も
    符号付き距離も持たない。本モジュールは符号付き距離場で、表面の内外が定義される。
  * ``visualhull.carve`` は **シルエット**空間彫刻(占有 bool、深度値は使わない)。本モジュールは
    **深度値そのもの**を使う密な再構成。

marching cubes は使わない(skimage 非依存): ゼロ交差 voxel 辺の線形補間で表面点を出す。
cv2/skimage は一切 import しない。numpy + 標準ライブラリのみ。

規約: ``X_cam = R X + t``、depth は正(perpendicular Z-depth)、射影は
``match3d.project_points`` と一致(``u = fx*X/Z + cx``、``v = fy*Y/Z + cy``、``d_voxel = Z_cam``)。
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

Bounds = Sequence[Sequence[float]]

__all__ = ["new_volume", "integrate", "fuse", "extract_surface_points"]


# ──────────────────────────────────────────────────────────────────────────
# 内部ヘルパ
# ──────────────────────────────────────────────────────────────────────────
def _check_bounds(bounds: Bounds) -> np.ndarray:
    """bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax)) を (3,2) 配列へ検証つき変換。"""
    b = np.asarray(bounds, dtype=np.float64)
    if b.shape != (3, 2):
        raise ValueError("bounds must be ((xmin,xmax),(ymin,ymax),(zmin,zmax)); got shape %r"
                         % (b.shape,))
    if not np.all(b[:, 1] > b[:, 0]):
        # fail-closed: 退化した(幅ゼロ/反転)bounds では voxel サイズが未定義。
        raise ValueError("bounds must be non-degenerate (max > min per axis); got %r" % (b.tolist(),))
    return b


def _axis_coords(shape: Tuple[int, int, int], bounds: Optional[Bounds]):
    """各軸の voxel 中心座標 (xs, ys, zs) と voxel サイズ (dx,dy,dz) を返す。

    bounds=None のときは grid-index フレーム(voxel (i,j,k) 中心 = (i+0.5, j+0.5, k+0.5)、
    voxel サイズ=1)。この場合 (K,R,t) は grid-index → camera を写像するものとして扱う。
    """
    rx, ry, rz = shape
    if bounds is None:
        xs = np.arange(rx, dtype=np.float64) + 0.5
        ys = np.arange(ry, dtype=np.float64) + 0.5
        zs = np.arange(rz, dtype=np.float64) + 0.5
        return (xs, ys, zs), (1.0, 1.0, 1.0)
    b = _check_bounds(bounds)
    dx = (b[0, 1] - b[0, 0]) / rx
    dy = (b[1, 1] - b[1, 0]) / ry
    dz = (b[2, 1] - b[2, 0]) / rz
    xs = b[0, 0] + (np.arange(rx, dtype=np.float64) + 0.5) * dx
    ys = b[1, 0] + (np.arange(ry, dtype=np.float64) + 0.5) * dy
    zs = b[2, 0] + (np.arange(rz, dtype=np.float64) + 0.5) * dz
    return (xs, ys, zs), (float(dx), float(dy), float(dz))


def _voxel_centers(shape: Tuple[int, int, int], bounds: Optional[Bounds]) -> np.ndarray:
    """voxel 中心の world 座標 (Nv,3)。indexing='ij'、ravel は C-order(tsdf の平坦化と一致)。"""
    (xs, ys, zs), _ = _axis_coords(shape, bounds)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)


def _as_K(K) -> Tuple[float, float, float, float]:
    K = np.asarray(K, dtype=np.float64)
    if K.shape != (3, 3):
        raise ValueError("K must be 3x3 intrinsic matrix; got shape %r" % (K.shape,))
    return float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2])


# ──────────────────────────────────────────────────────────────────────────
# 公開 API
# ──────────────────────────────────────────────────────────────────────────
def new_volume(bounds: Bounds, res: int) -> Tuple[np.ndarray, np.ndarray]:
    """空の TSDF volume を確保 = (tsdf 初期 1.0, weight 初期 0)。融合の初期状態。

    bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax))、res=一辺の voxel 数(cube: res×res×res)。
    tsdf は「観測前=表面より手前(空き空間)」を意味する +1.0 で初期化、weight=0(未観測)。
    """
    if not isinstance(res, (int, np.integer)) or res <= 0:
        raise ValueError("res must be a positive integer; got %r" % (res,))
    _check_bounds(bounds)  # 退化 bounds は早期に fail-closed
    r = int(res)
    tsdf = np.ones((r, r, r), dtype=np.float32)
    weight = np.zeros((r, r, r), dtype=np.float32)
    return tsdf, weight


def integrate(tsdf: np.ndarray, weight: np.ndarray, depth: np.ndarray,
              K, R, t, trunc: float, bounds: Optional[Bounds] = None) -> None:
    """深度 1 枚を投影的 TSDF で volume に統合(in-place、重み付き移動平均)。

    各 voxel 中心を (K,R,t) で射影(``X_cam = R X + t``, ``u = fx*X/Z+cx``)し、対応画素の
    観測深度 ``d_meas`` と voxel のカメラ深度 ``d_voxel = Z_cam`` を比較。
    ``sdf = min(1, (d_meas - d_voxel)/trunc)`` を、以下すべてを満たす voxel にのみ適用:
    画像内・``d_meas>0`` かつ有限・``(d_meas - d_voxel) >= -trunc``(表面より trunc 以上奥=
    遮蔽領域は観測不能として **更新しない**)。この valid 集合では sdf ∈ [-1,1]。
    更新: ``tsdf = (w*tsdf + sdf)/(w+1)``、``weight = w+1``(1 フレーム重み 1)。

    bounds を渡すと voxel 中心を world で解釈し (K,R,t) は world→camera。bounds=None(既定)
    では voxel 中心を grid-index フレーム((i+0.5,...))で解釈し (K,R,t) は grid→camera とする
    (``fuse`` は bounds を渡すので world 座標で融合される)。
    """
    tsdf = np.asarray(tsdf)
    weight = np.asarray(weight)
    if tsdf.shape != weight.shape or tsdf.ndim != 3:
        raise ValueError("tsdf and weight must be 3D arrays of equal shape")
    d = np.asarray(depth, dtype=np.float64)
    if d.ndim != 2:
        raise ValueError("depth must be a 2D array (H,W)")
    trunc = float(trunc)
    if not np.isfinite(trunc) or trunc <= 0:
        raise ValueError("trunc must be a positive finite scalar; got %r" % (trunc,))

    H, W = d.shape
    fx, fy, cx, cy = _as_K(K)
    Rm = np.asarray(R, dtype=np.float64)
    tv = np.asarray(t, dtype=np.float64).ravel()
    if Rm.shape != (3, 3) or tv.shape != (3,):
        raise ValueError("R must be 3x3 and t length-3")

    centers = _voxel_centers(tsdf.shape, bounds)              # (Nv,3) world (or grid) 座標
    Pc = centers @ Rm.T + tv                                  # camera 座標 (Nv,3)
    z = Pc[:, 2]
    zc = np.where(z > 0, z, 1.0)                              # z<=0 は下で除外(0 割回避のみ)
    u = fx * Pc[:, 0] / zc + cx
    v = fy * Pc[:, 1] / zc + cy
    ui = np.rint(u).astype(np.int64)
    vi = np.rint(v).astype(np.int64)

    in_img = (z > 0) & (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
    d_meas = np.zeros(centers.shape[0], dtype=np.float64)
    d_meas[in_img] = d[vi[in_img], ui[in_img]]

    diff = d_meas - z                                        # 符号付き距離(未正規化)
    valid = in_img & (d_meas > 0) & np.isfinite(d_meas) & (diff >= -trunc)
    if not np.any(valid):
        return                                               # 有効観測ゼロ = 変更なし(honest)

    sdf = np.minimum(1.0, diff / trunc)                      # valid では [-1,1](下限は valid 側で担保)

    valid3 = valid.reshape(tsdf.shape)
    sdf3 = sdf.reshape(tsdf.shape)
    w_old = weight[valid3].astype(np.float64)
    tsdf[valid3] = ((w_old * tsdf[valid3] + sdf3[valid3]) / (w_old + 1.0)).astype(tsdf.dtype)
    weight[valid3] = (w_old + 1.0).astype(weight.dtype)


def fuse(depths: Sequence[np.ndarray], Ks: Sequence, Rs: Sequence, ts: Sequence,
         bounds: Bounds, res: int, trunc: float) -> Tuple[np.ndarray, np.ndarray]:
    """深度列を new_volume + integrate で 1 つの TSDF volume に融合。返り値 (tsdf, weight)。

    各フレームの (K,R,t) は world→camera。多視点で同じ表面を観測すると重みが積算され、
    単フレームでは見えない(自己遮蔽の)面が別視点で埋まる。
    """
    n = len(depths)
    if n == 0:
        # fail-closed: フレーム 0 枚では融合対象が無い(空 volume の詐称を避ける)。
        raise ValueError("fuse requires at least one depth frame")
    if not (n == len(Ks) == len(Rs) == len(ts)):
        raise ValueError("depths/Ks/Rs/ts must have the same length; got %d/%d/%d/%d"
                         % (n, len(Ks), len(Rs), len(ts)))
    tsdf, weight = new_volume(bounds, res)
    for depth, K, R, t in zip(depths, Ks, Rs, ts):
        integrate(tsdf, weight, depth, K, R, t, trunc, bounds=bounds)
    return tsdf, weight


def extract_surface_points(tsdf: np.ndarray, weight: np.ndarray,
                           bounds: Bounds, res: int) -> np.ndarray:
    """TSDF ゼロ交差から表面点 (M,3) を抽出(marching cubes 不要、線形補間)。

    観測済み(weight>0)の隣接 voxel 対で TSDF 符号が変わる辺を、その 2 中心の間で
    ``alpha = t_a/(t_a - t_b)`` により線形補間して交点(表面点)を出す。両端とも weight>0 の
    辺のみ採用(未観測の初期値 1.0 との偽の交差を作らない=honest)。x/y/z 3 軸の全辺を走査。
    交差が無ければ空 (0,3) を返す(詐称せず honest な空返し)。
    """
    tsdf = np.asarray(tsdf, dtype=np.float64)
    weight = np.asarray(weight, dtype=np.float64)
    if tsdf.shape != weight.shape or tsdf.ndim != 3:
        raise ValueError("tsdf and weight must be 3D arrays of equal shape")
    r = int(res)
    if tsdf.shape != (r, r, r):
        raise ValueError("tsdf shape %r does not match res=%d" % (tsdf.shape, r))

    (xs, ys, zs), _ = _axis_coords(tsdf.shape, bounds)
    obs = weight > 0
    out = []

    # 各軸方向の隣接辺で符号変化(かつ両端観測済み)を探し、線形補間で交点を作る。
    for axis, coords in ((0, xs), (1, ys), (2, zs)):
        a = np.take(tsdf, np.arange(0, r - 1), axis=axis)
        b = np.take(tsdf, np.arange(1, r), axis=axis)
        oa = np.take(obs, np.arange(0, r - 1), axis=axis)
        ob = np.take(obs, np.arange(1, r), axis=axis)
        cross = oa & ob & ((a < 0) != (b < 0)) & (a != b)     # 厳密な符号変化
        idx = np.argwhere(cross)                              # (K, 3) の (i,j,k)(a 側=低 index)
        if idx.size == 0:
            continue
        ia, ja, ka = idx[:, 0], idx[:, 1], idx[:, 2]
        ta = a[ia, ja, ka]
        tb = b[ia, ja, ka]
        alpha = ta / (ta - tb)                                # 0..1: a→b のどこで 0 交差か
        pa = np.stack([xs[ia], ys[ja], zs[ka]], axis=1)       # a 側 voxel 中心(world)
        step = coords[1] - coords[0]                          # 当該軸の voxel サイズ(均一)
        pa[:, axis] = pa[:, axis] + alpha * step
        out.append(pa)

    if not out:
        return np.zeros((0, 3), dtype=np.float64)
    return np.vstack(out)
