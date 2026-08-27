"""spherical_proj — 回転式 LiDAR の球面/円柱レンジ画像(点群 ⇄ レンジ画像)。

Velodyne/Ouster のような**回転式(spinning)LiDAR** は、水平に 360° 回りながら
複数のレーザ層(beam)で縦方向を掃く。その 1 スイープを自然に格子化したものが
**球面レンジ画像**: 行 = 仰角(elevation, レーザ層)、列 = 方位角(azimuth, 回転角)、
画素値 = センサ原点からの range(距離)。全方位(水平 360°)を 1 枚に畳み込むのが要点で、
畳み込み CNN・占有格子・地面除去などの下流をそのまま 2D 画像処理に落とせる。

固有価値(既存との棲み分け, honest):
  * :mod:`range_image` は depth camera の **organized 深度**(前方視錐台・格子は画素そのもの)。
    こちらは**センサを中心にした全方位**の角度格子で、水平 360° の巻き(azimuth wrap)を扱う。
    range_image は透視/正射の逆投影、本モジュールは球面(方位×仰角)/円柱(方位×z)の投影。
  * :mod:`pointcloud` / :mod:`scene_flow3d` は**非構造点群**をそのまま扱う。本モジュールは
    点群を**角度格子へ整列(organize)**する橋渡しで、その逆(格子→点群)も閉形式で戻す。
  * :func:`evis_fullseye_bridge.pseudo_lidar_rays` は水平面内の**平面 2D** スキャン(z を持たない)。
    本モジュールは仰角/ z を持つ**3 次元**のレンジ画像。

フレーム規約:
  * センサは原点。x = 前方, y = 左, z = 上(右手系)。
  * 方位角 azimuth φ = atan2(y, x) ∈ (-π, π]。列は φ を全周 [-π, π) に等分し、
    **列 0 = φ=-π(後方 -x 側)**、**中央列 h_res//2 = φ=0(前方 +x)**、列は反時計回りに増加。
  * 仰角 elevation θ = atan2(z, hypot(x, y)) ∈ [-90°, 90°]。v_fov=(v_min, v_max)[度] の帯のみ採用。
    **行 0 = 帯の上端(θ=v_max, 上)**、**行 v_res-1 = 帯の下端(θ=v_min, 下)**(画像同様に上が小さい行)。
  * 各ビンは中心角で代表する(逆投影はビン中心へ戻す)。近い点優先(同セルは最小 range を残す)。

限界(self_reported):
  * 角度量子化: 逆投影はビン中心角へ戻すため、元点との位置誤差は最大およそ「半セル角 × range」。
    セル内の補間はしない(sub-cell 精度なし)。
  * 単一リターン: 同一セルに複数点が来たら最小 range のみ残し、奥/遮蔽点は捨てる
    (単一リターン LiDAR として物理的には正しいが、奥の形状は失われる)。
  * 単スイープ剛体前提: ego-motion による歪み補正(deskew)はしない。
  * FOV 外(v_fov / z_range 外)・原点上(r=0)・z 軸上(円柱で ρ=0)・非有限座標の点は落とす(honest に drop)。
  * 円柱投影の画素値は**水平半径 ρ = hypot(x, y)**(z 軸からの距離)であって slant range r ではない。
    円柱上の点が一定値になる自然な不変量のため(球面は slant range r を格納)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["project_spherical", "unproject_spherical", "project_cylindrical"]


def _validate_res(h_res: int, v_res: int) -> None:
    """分解能が正の整数かを検査(fail-closed)。"""
    if int(h_res) <= 0 or int(v_res) <= 0:
        raise ValueError(f"resolution must be positive, got h_res={h_res}, v_res={v_res}")


def _validate_fov(v_fov) -> tuple[float, float]:
    """v_fov=(min,max)[度] を検査して (v_min, v_max) を返す(min<max 必須, fail-closed)。"""
    v_min, v_max = float(v_fov[0]), float(v_fov[1])
    if not (v_min < v_max):
        raise ValueError(f"v_fov must be (v_min, v_max) with v_min < v_max, got {v_fov}")
    return v_min, v_max


def _as_points(points) -> np.ndarray:
    """(N,3) の点群配列に整形(不正形状は fail-closed)。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points must be (N, 3), got shape {P.shape}")
    return P


def _azimuth_columns(x: np.ndarray, y: np.ndarray, h_res: int) -> np.ndarray:
    """方位角 → 列インデックス。φ=atan2(y,x)∈(-π,π] を [0,h_res) に等分。列 h_res//2=前方(+x)。"""
    az = np.arctan2(y, x)                      # (-π, π]
    frac = (az + np.pi) / (2.0 * np.pi)        # [0, 1]
    col = np.floor(frac * h_res).astype(np.int64)
    return np.clip(col, 0, h_res - 1)


def project_spherical(points, h_res: int = 1024, v_res: int = 64,
                      v_fov=(-25.0, 15.0)) -> np.ndarray:
    """回転式 LiDAR の球面レンジ画像へ投影 (v_res, h_res)。空セル=0, 近い点優先(最小 range)。

    各点を方位角(列)× 仰角(行)ビンへ落とし、センサ原点からの range(slant distance)を書く。
    v_fov=(v_min,v_max)[度] の仰角帯の外側、原点上(r=0)、非有限座標の点は落とす(honest drop)。
    空/全 drop の場合は全ゼロ画像を返す(=何も見えていない、honest)。
    """
    _validate_res(h_res, v_res)
    v_min, v_max = _validate_fov(v_fov)
    h_res, v_res = int(h_res), int(v_res)
    P = _as_points(points)

    img = np.zeros((v_res, h_res), dtype=np.float64)
    if P.shape[0] == 0:
        return img

    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    r = np.sqrt(x * x + y * y + z * z)
    horiz = np.hypot(x, y)
    # 仰角[度]。r=0 の点は方向が未定義なので後で drop する。
    with np.errstate(invalid="ignore", divide="ignore"):
        el_deg = np.degrees(np.arctan2(z, horiz))

    keep = np.isfinite(r) & (r > 0.0) & np.isfinite(el_deg)
    keep &= (el_deg >= v_min) & (el_deg <= v_max)
    if not np.any(keep):
        return img

    xk, yk, rk, elk = x[keep], y[keep], r[keep], el_deg[keep]
    col = _azimuth_columns(xk, yk, h_res)

    # 仰角 → 行。row 0 = 上端(θ=v_max)。ビンは中心角で代表。
    el_norm = (elk - v_min) / (v_max - v_min)          # [0, 1]
    row_from_bottom = np.clip(np.floor(el_norm * v_res).astype(np.int64), 0, v_res - 1)
    row = (v_res - 1) - row_from_bottom

    # 近い点優先: 同セルは最小 range。flat index 上で np.minimum.at。
    flat = row * h_res + col
    acc = np.full(v_res * h_res, np.inf, dtype=np.float64)
    np.minimum.at(acc, flat, rk)
    acc[~np.isfinite(acc)] = 0.0
    return acc.reshape(v_res, h_res)


def unproject_spherical(range_img, v_fov=(-25.0, 15.0)) -> np.ndarray:
    """球面レンジ画像 → 3D 点 (M, 3)。range>0 のセルのみをビン中心角で逆投影。

    :func:`project_spherical` の逆。行/列からビン**中心**の (elevation, azimuth) を復元し、
    格納 range を slant distance として球面 → 直交座標へ戻す。空(全 0)なら (0, 3) を返す。
    """
    v_min, v_max = _validate_fov(v_fov)
    R = np.asarray(range_img, dtype=np.float64)
    if R.ndim != 2:
        raise ValueError(f"range_img must be a 2D (v_res, h_res) image, got shape {R.shape}")
    v_res, h_res = R.shape
    if v_res <= 0 or h_res <= 0:
        raise ValueError(f"range_img must have positive dimensions, got {R.shape}")

    rows, cols = np.nonzero(R > 0.0)
    if rows.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    rng = R[rows, cols]

    # 列 → 方位角(ビン中心)。project の frac=(az+π)/2π, col=floor(frac*h_res) の逆(中心 +0.5)。
    az = (cols + 0.5) / h_res * (2.0 * np.pi) - np.pi
    # 行 → 仰角[度](ビン中心)。row = (v_res-1) - row_from_bottom の逆。
    row_from_bottom = (v_res - 1) - rows
    el_norm = (row_from_bottom + 0.5) / v_res
    el = np.radians(v_min + el_norm * (v_max - v_min))

    ce = np.cos(el)
    x = rng * ce * np.cos(az)
    y = rng * ce * np.sin(az)
    z = rng * np.sin(el)
    return np.stack([x, y, z], axis=1)


def project_cylindrical(points, h_res: int = 1024, z_bins: int = 64,
                        z_range=None) -> np.ndarray:
    """円柱レンジ画像へ投影 (z_bins, h_res)。方位角(列)× z(行)、画素=水平半径 ρ=hypot(x,y)。

    球面投影が仰角で層を切るのに対し、円柱投影は**高さ z を等間隔に切る**(壁/柱/回廊の展開に向く)。
    画素値は z 軸からの水平距離 ρ(円柱上の点が一定になる自然な不変量)。空セル=0, 近い点優先(最小 ρ)。
    z_range=(z_min,z_max) 未指定なら点群の [z.min, z.max] を採用。z 幅ゼロは fail-closed(ValueError)。
    行 0 = 上端(z=z_max)。z_range 外、z 軸上(ρ=0)、非有限座標の点は落とす。
    """
    _validate_res(h_res, z_bins)
    h_res, z_bins = int(h_res), int(z_bins)
    P = _as_points(points)

    img = np.zeros((z_bins, h_res), dtype=np.float64)
    if P.shape[0] == 0:
        if z_range is None:
            return img
        # 明示 z_range が与えられていれば妥当性だけは検査(fail-closed)。
        z_min, z_max = float(z_range[0]), float(z_range[1])
        if not (z_min < z_max):
            raise ValueError(f"z_range must be (z_min, z_max) with z_min < z_max, got {z_range}")
        return img

    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    rho = np.hypot(x, y)

    if z_range is None:
        finite_z = z[np.isfinite(z)]
        if finite_z.size == 0:
            return img
        z_min, z_max = float(finite_z.min()), float(finite_z.max())
        if not (z_min < z_max):
            # 全点が同じ z(平坦)→ 高さ方向のビン割りが縮退。詐称せず fail-closed。
            raise ValueError(
                "cannot infer z_range: all points share z="
                f"{z_min!r} (zero z-extent). Pass an explicit z_range=(z_min, z_max)."
            )
    else:
        z_min, z_max = float(z_range[0]), float(z_range[1])
        if not (z_min < z_max):
            raise ValueError(f"z_range must be (z_min, z_max) with z_min < z_max, got {z_range}")

    keep = np.isfinite(rho) & (rho > 0.0) & np.isfinite(z)
    keep &= (z >= z_min) & (z <= z_max)
    if not np.any(keep):
        return img

    xk, yk, zk, rhok = x[keep], y[keep], z[keep], rho[keep]
    col = _azimuth_columns(xk, yk, h_res)

    z_norm = (zk - z_min) / (z_max - z_min)                 # [0, 1]
    row_from_bottom = np.clip(np.floor(z_norm * z_bins).astype(np.int64), 0, z_bins - 1)
    row = (z_bins - 1) - row_from_bottom

    flat = row * h_res + col
    acc = np.full(z_bins * h_res, np.inf, dtype=np.float64)
    np.minimum.at(acc, flat, rhok)
    acc[~np.isfinite(acc)] = 0.0
    return acc.reshape(z_bins, h_res)
