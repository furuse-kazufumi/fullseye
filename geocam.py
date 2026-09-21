# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""geocam — 位置既知の固定カメラの向きを、写真そのものから決める(学習なし・閉形式 + 格子探索)。

動機(2026-09-21): 公共の固定カメラ(道路・気象・観光)は**位置**は公開されるが**向き**は無いか
粗い(道路の増減方向、id のハッシュ、手校正)。向きが無いと、写真を地図・DEM・3D 都市に置けない。
先行研究は 2 系統 —— (a) 太陽と空: Lalonde・Narasimhan・Efros, IJCV 2010(時刻つき画像列に太陽位置
モデルを当てはめ、焦点距離・天頂角・方位角。webcam 22 台で 3° 以内)、その前身 Jacobs ら WACV 2008。
(b) スカイライン: Baatz・Saurer・Köser・Pollefeys, ECCV 2012(DEM から描いた 360° スカイラインと
写真の稜線を照合)、Lie ら 2005(動的計画法によるスカイライン抽出)。この族はその 2 系統を
**同じ固定カメラで併用して互いに検算**できる形にする(先行研究はどちらか一方)。

規約(ここが姿勢の定義):
    * 世界座標 = ENU(x = 東, y = 北, z = 上)。方位 az は**北 0°、時計回り**(東 90°)。仰角 el は水平 0°、上が正。
    * カメラ座標 = OpenCV(x 右, y 下, z 前)。内部行列 K = (fx, fy, cx, cy)、画素は (u, v) = (列, 行)。
    * 姿勢 (yaw, pitch, roll) [度]: yaw = 光軸の方位(北 0°、時計回り)、pitch = 光軸の仰角(上が正)、
      roll = 光軸まわりの回転(0 で水平線が水平、正でカメラが右に傾く = 画面の水平線は左上がり)。
      ``R_wc = Rz(-yaw) · Rx(pitch) · Ry(roll) · B``(B = 基準姿勢: 前 = 北, 右 = 東, 下 = -上)。
    * DEM は (H, W) の標高 [m]、行 0 が北端(上 = 北)、列は東向きに増える。``cell_size`` [m/セル]。

すべて numpy + scipy(optional 依存なし)。検証失敗は ValueError(fail-closed)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "sun_position",
    "sun_pixel_position",
    "camera_orientation_from_sun",
    "sun_bloom_fit",
    "camera_orientation_from_sun_candidates",
    "dem_skyline",
    "skyline_extract",
    "render_skyline_view",
    "camera_orientation_from_skyline",
    # 補助(op ではない、__all__ には入れない): _rotation / _pose_from_rotation / _pixel_rays
]

_EARTH_RADIUS_M = 6_371_000.0
_REFRACTION_K = 0.13          # 標準的な大気屈折係数(有効半径 = R / (1 - k))


# --------------------------------------------------------------------------- #
# 姿勢と光線                                                                    #
# --------------------------------------------------------------------------- #
def _rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def _rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


#: 基準姿勢: カメラ軸(右, 下, 前)の世界座標 = (東, -上, 北)
_B = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])


def _rotation(yaw_deg, pitch_deg, roll_deg):
    """R_wc(カメラ座標 → 世界 ENU)。"""
    y, p, r = np.deg2rad([float(yaw_deg), float(pitch_deg), float(roll_deg)])
    return _rz(-y) @ _rx(p) @ _ry(r) @ _B


def _pose_from_rotation(R):
    """R_wc → (yaw, pitch, roll) [度]。``_rotation`` の逆(yaw は [0, 360))。"""
    Rp = np.asarray(R, dtype=np.float64) @ _B.T
    f = Rp @ np.array([0.0, 1.0, 0.0])
    pitch = np.degrees(np.arcsin(np.clip(f[2], -1.0, 1.0)))
    yaw = np.degrees(np.arctan2(f[0], f[1])) % 360.0
    right = Rp @ np.array([1.0, 0.0, 0.0])
    v = _rx(-np.deg2rad(pitch)) @ _rz(np.deg2rad(yaw)) @ right
    roll = np.degrees(np.arctan2(-v[2], v[0]))
    return float(yaw), float(pitch), float(roll)


def _intrinsics(K):
    k = np.asarray(K, dtype=np.float64).ravel()
    if k.shape != (4,) or not np.all(np.isfinite(k)) or k[0] <= 0 or k[1] <= 0:
        raise ValueError("K must be (fx, fy, cx, cy) with fx, fy > 0 and all finite, got %r" % (K,))
    return k


def _pixel_rays(uv, K):
    """画素 (N,2) → カメラ座標の単位光線 (N,3)。"""
    fx, fy, cx, cy = _intrinsics(K)
    uv = np.asarray(uv, dtype=np.float64)
    d = np.column_stack([(uv[:, 0] - cx) / fx, (uv[:, 1] - cy) / fy, np.ones(len(uv))])
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def _az_el(dirs_world):
    d = np.asarray(dirs_world, dtype=np.float64)
    az = np.degrees(np.arctan2(d[..., 0], d[..., 1])) % 360.0
    el = np.degrees(np.arcsin(np.clip(d[..., 2], -1.0, 1.0)))
    return az, el


def _dir_from_az_el(az_deg, el_deg):
    az, el = np.deg2rad(np.asarray(az_deg, float)), np.deg2rad(np.asarray(el_deg, float))
    return np.stack([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)], -1)


def _check_latlon(lat_deg, lon_deg):
    lat, lon = float(lat_deg), float(lon_deg)
    if not (np.isfinite(lat) and np.isfinite(lon)) or abs(lat) > 90.0 or abs(lon) > 180.0:
        raise ValueError("latitude must be within [-90, 90] and longitude within [-180, 180], got %r, %r" % (lat_deg, lon_deg))
    return lat, lon


# --------------------------------------------------------------------------- #
# 太陽                                                                          #
# --------------------------------------------------------------------------- #
def sun_position(lat_deg, lon_deg, unix_times):
    """緯度・経度・時刻(UNIX 秒、UTC)→ 太陽の方位・仰角 [度](NOAA の太陽位置アルゴリズム、Meeus 1998 の低精度式)。

    公開された閉形式(NOAA Global Monitoring Laboratory の Solar Calculator と同じ式:
    ユリウス世紀 → 平均黄経・平均近点角・中心差 → 視黄経 → 黄道傾斜 → 赤緯 と均時差 →
    時角 → 天頂角・方位角)。精度は 2000 年 ± 1 世紀で **0.01° 程度**(NOAA の記述)、
    大気屈折は仰角に足す(NOAA の区分式、水平近くで最大 0.57°)。時刻は UTC の UNIX 秒
    (1-D、float でよい)。うるう秒・ΔT は無視する(0.01° に効かない)。

    Args:
        lat_deg, lon_deg: 観測点。経度は東が正。
        unix_times: (N,) UNIX 秒(UTC)。スカラも可。

    Returns:
        table: ``azimuth_deg`` (N,)(北 0°、時計回り)/ ``elevation_deg`` (N,)(屈折込み)/
        ``elevation_true_deg`` (N,)(屈折なし)/ ``declination_deg`` / ``equation_of_time_min`` /
        ``hour_angle_deg`` / ``n``。

    真値で確かめてある性質(tests/test_geocam.py): 春分の正午に仰角 = 90 − |緯度|、
    正午の方位は北半球で 180°(南)、方位は東 → 南 → 西と単調、日の出と日の入りの
    仰角が対称、赤緯は ±23.44° に収まる。
    """
    lat, lon = _check_latlon(lat_deg, lon_deg)
    t = np.atleast_1d(np.asarray(unix_times, dtype=np.float64)).ravel()
    if t.size == 0 or not np.all(np.isfinite(t)):
        raise ValueError("unix_times must be a non-empty array of finite UNIX seconds (UTC)")
    jd = t / 86400.0 + 2440587.5
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360.0
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    Mr = np.deg2rad(M)
    C = (np.sin(Mr) * (1.914602 - T * (0.004817 + 0.000014 * T)) + np.sin(2 * Mr) * (0.019993 - 0.000101 * T)
         + np.sin(3 * Mr) * 0.000289)
    true_long = L0 + C
    omega = 125.04 - 1934.136 * T
    app_long = true_long - 0.00569 - 0.00478 * np.sin(np.deg2rad(omega))
    eps0 = 23.0 + (26.0 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60.0) / 60.0
    eps = eps0 + 0.00256 * np.cos(np.deg2rad(omega))
    decl = np.degrees(np.arcsin(np.sin(np.deg2rad(eps)) * np.sin(np.deg2rad(app_long))))
    y = np.tan(np.deg2rad(eps / 2.0)) ** 2
    L0r, er = np.deg2rad(L0), e
    eot = 4.0 * np.degrees(y * np.sin(2 * L0r) - 2 * er * np.sin(Mr) + 4 * er * y * np.sin(Mr) * np.cos(2 * L0r)
                           - 0.5 * y * y * np.sin(4 * L0r) - 1.25 * er * er * np.sin(2 * Mr))
    minutes_utc = (t % 86400.0) / 60.0
    true_solar = (minutes_utc + eot + 4.0 * lon) % 1440.0
    ha = true_solar / 4.0 - 180.0
    ha = np.where(ha < -180.0, ha + 360.0, ha)
    latr, dr, hr = np.deg2rad(lat), np.deg2rad(decl), np.deg2rad(ha)
    cosz = np.sin(latr) * np.sin(dr) + np.cos(latr) * np.cos(dr) * np.cos(hr)
    zen = np.degrees(np.arccos(np.clip(cosz, -1.0, 1.0)))
    el_true = 90.0 - zen
    # 方位(NOAA): 北 0°、時計回り
    denom = np.cos(latr) * np.sin(np.deg2rad(zen))
    with np.errstate(divide="ignore", invalid="ignore"):
        cosaz = (np.sin(latr) * np.cos(np.deg2rad(zen)) - np.sin(dr)) / denom
    az = np.degrees(np.arccos(np.clip(cosaz, -1.0, 1.0)))
    az = np.where(ha > 0.0, (az + 180.0) % 360.0, (540.0 - az) % 360.0)
    az = np.where(denom == 0.0, 0.0, az)                       # 天頂・極では方位が定義できない
    # 屈折(NOAA の区分式、角度は度)
    ref = np.zeros_like(el_true)
    hi = el_true > 85.0
    mid = (el_true > 5.0) & ~hi
    low = (el_true > -0.575) & ~hi & ~mid
    below = el_true <= -0.575
    te = np.tan(np.deg2rad(np.where(mid, el_true, 45.0)))
    ref = np.where(mid, 58.1 / te - 0.07 / te ** 3 + 0.000086 / te ** 5, ref)
    h = np.where(low, el_true, 0.0)
    ref = np.where(low, 1735.0 + h * (-518.2 + h * (103.4 + h * (-12.79 + h * 0.711))), ref)
    ref = np.where(below, -20.774 / np.tan(np.deg2rad(np.where(below, el_true, -1.0))), ref)
    ref = ref / 3600.0
    return {"azimuth_deg": az, "elevation_deg": el_true + ref, "elevation_true_deg": el_true,
            "declination_deg": decl, "equation_of_time_min": eot, "hour_angle_deg": ha, "n": int(t.size)}


def sun_pixel_position(image, threshold=0.98, min_area=4):
    """画像の中の太陽(センサを**飽和**させる円盤)の重心 → keypoints (1, 2) = (u, v)。

    前提は「太陽はセンサを飽和させ、雲や雪は飽和の手前で止まる」。値が ``threshold``(絶対値、
    画像は 0〜1)以上の画素を 8 近傍で連結し、**最大の塊**の輝度重心を返す。塊が ``min_area`` 未満、
    または飽和画素が無ければ「太陽が写っていない」として ValueError(黙って雲の反射を返さない —— 太陽が
    山に隠れた時刻の写真で、雲を太陽と読んで姿勢を汚さないための門)。**画像の最大値に対する比では
    ない**(比にすると、太陽の無い写真で一番明るい雲が必ず「太陽」になる)。夜景の人工光源や
    太陽の水面反射は飽和しうるので、その場面では使えない。塊は**詰まった丸**であること(充填率 ≥ 0.4、
    縦横比 ≤ 2.5)—— 露出過多で空の帯が飽和した写真は細長い塊になり、拒否される。

    Args:
        image: (H, W) float、0〜1(範囲外は ValueError)。
        threshold: 飽和とみなす絶対値(既定 0.98)。
        min_area: 塊の最小画素数。
    Returns:
        keypoints (1, 2) float: (u, v)。
    """
    from scipy import ndimage

    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or a.size == 0 or not np.isfinite(a).all():
        raise ValueError("image must be a finite 2-D array, got shape %r" % (a.shape,))
    thr = float(threshold)
    if not (0.0 < thr <= 1.0):
        raise ValueError("threshold must be in (0, 1], got %r" % (threshold,))
    if float(a.min()) < 0.0 or float(a.max()) > 1.0:
        raise ValueError("image must be in [0, 1] (saturation is an absolute level), got %.3g..%.3g" % (float(a.min()), float(a.max())))
    if float(a.max()) <= float(a.min()):
        raise ValueError("image is constant — there is no sun to find")
    mask = a >= thr
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        raise ValueError("no saturated pixel (>= %.2f) — no sun disc in this image" % thr)
    sizes = ndimage.sum(mask, lab, index=np.arange(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < int(min_area):
        raise ValueError("brightest blob has %d pixels < min_area %d — no sun disc in this image" % (int(sizes[k - 1]), int(min_area)))
    # 円盤らしさ: 飽和した雑音の筋や空の帯は細長く疎、太陽は詰まった丸
    ys, xs = np.nonzero(lab == k)
    hh, ww = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
    fill = float(sizes[k - 1]) / float(hh * ww)
    if fill < 0.4 or max(hh, ww) > 2.5 * min(hh, ww):
        raise ValueError("largest saturated blob is not a compact disc (fill %.2f, box %dx%d) — a saturated sky band or a "
                         "streak, not the sun" % (fill, hh, ww))
    w = np.where(lab == k, a, 0.0)
    cy, cx = ndimage.center_of_mass(w)
    return np.array([[float(cx), float(cy)]], dtype=np.float64)


def camera_orientation_from_sun(sun_pixels, unix_times, lat_deg, lon_deg, K):
    """時刻つきの太陽の画素位置 ≥ 2 点 → カメラの (yaw, pitch, roll)(Wahba 問題の SVD 解 = Kabsch)。

    各観測で、画素 → カメラ座標の光線 d_c(K から)、時刻 → 世界の太陽方向 s_w(``sun_position``、
    **屈折込み**の仰角を使う: カメラが見るのは見かけの太陽)。``R = argmin Σ |R d_c − s_w|²`` を
    SVD で閉形式に解き(Kabsch 1976 / Markley 1988)、``(yaw, pitch, roll)`` に分解する。

    2 点で一意に決まる(2 本の方向が張る面が要る)。観測が 1 点、または全部が同じ方向(共線)なら
    ValueError —— 例えば同じ時刻の 2 枚、あるいは正午だけを何日も。太陽は 1 日で方位が大きく
    動くので、**同じ日の朝と夕の 2 枚**があれば足りる。

    Args:
        sun_pixels: (N, 2) の (u, v)。``sun_pixel_position`` の出力を積んだもの。
        unix_times: (N,) UNIX 秒(UTC)。
        lat_deg, lon_deg: カメラの位置。
        K: (fx, fy, cx, cy)。
    Returns:
        table: ``yaw_deg`` / ``pitch_deg`` / ``roll_deg`` / ``residual_deg``(光線と太陽方向の
        角度残差の RMS)/ ``max_residual_deg`` / ``n`` / ``condition``(観測方向の張る面の広さ =
        2 番目の特異値、0 に近いほど不定)。
    """
    uv = np.asarray(sun_pixels, dtype=np.float64)
    t = np.atleast_1d(np.asarray(unix_times, dtype=np.float64)).ravel()
    if uv.ndim != 2 or uv.shape[1] != 2 or not np.isfinite(uv).all():
        raise ValueError("sun_pixels must be a finite (N, 2) array of (u, v), got shape %r" % (uv.shape,))
    if len(uv) != len(t):
        raise ValueError("sun_pixels has %d rows but unix_times has %d" % (len(uv), len(t)))
    if len(uv) < 2:
        raise ValueError("at least 2 sun observations at different times are needed to fix a rotation, got %d" % len(uv))
    sun = sun_position(lat_deg, lon_deg, t)
    # 高い所から見る地平線は 0° より下に沈む(1,000 m で約 1°)ので、拒むのは明らかな夜(−3° 未満)だけ
    if np.any(sun["elevation_true_deg"] < -3.0):
        raise ValueError("the sun is below the horizon at %d of the given times — a camera cannot see it" % int(np.sum(sun["elevation_true_deg"] < -3.0)))
    s_w = _dir_from_az_el(sun["azimuth_deg"], sun["elevation_deg"])
    d_c = _pixel_rays(uv, K)
    H = d_c.T @ s_w                                                    # (3,3)
    U, S, Vt = np.linalg.svd(H)
    if S[1] < 1e-6 * max(S[0], 1e-12) or S[1] < 1e-3:
        raise ValueError("sun directions are collinear (second singular value %.2g) — observations at "
                         "different times of day are needed" % float(S[1]))
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T                                                 # R d_c ≈ s_w
    yaw, pitch, roll = _pose_from_rotation(R)
    res = np.degrees(np.arccos(np.clip(np.sum((d_c @ R.T) * s_w, axis=1), -1.0, 1.0)))
    return {"yaw_deg": yaw, "pitch_deg": pitch, "roll_deg": roll,
            "residual_deg": float(np.sqrt(np.mean(res ** 2))), "max_residual_deg": float(res.max()),
            "n": int(len(uv)), "condition": float(S[1] / S[0])}


def sun_bloom_fit(image, threshold=0.97, ignore_top_rows=0, min_area=30, max_area_frac=0.15, min_rim_fraction=0.3):
    """実写の太陽 = センサを飽和させる**ブルーム**(円盤より大きい、露出で大きさが変わる、画像の縁や文字の帯で切れる)。
    最大の飽和塊の**縁**に円を当てて中心を返す → table。重心は塊が切れると切れた側の反対へ偏る(実測 15 px)ので、
    切れた縁(画像の外周と ``ignore_top_rows`` の帯に触れる画素)を捨てた残りの弧に代数的最小二乗(Kåsa 1976)で円を当てる。

    ``sun_pixel_position`` は「詰まった小さな円盤」を前提にした合成向けの門で、実写の道路カメラでは局名の白い
    文字・標識・白い車を太陽と読む(Fintraffic 天候カメラで 24/24 が誤検出、2026-09-21)。この op は**太陽と決めない**:
    円の中心と半径・残差・切れの有無を返し、太陽かどうかは時刻どおりに動くかで決める
    (``camera_orientation_from_sun_candidates``)。

    Args:
        image: (H, W) float、0〜1。
        threshold: 飽和とみなす絶対値。
        ignore_top_rows: 上端の何行を無視するか(局名などの文字の帯)。
        min_area: 塊の最小画素数。
        max_area_frac: 塊の最大面積(画像に対する比)—— 空全体が飛んだ写真を拒む。
        min_rim_fraction: 切れていない縁が円周の何割以上要るか(これ未満は「切れすぎ」で ValueError)。
    Returns:
        table: ``u`` / ``v``(円の中心)/ ``r``(半径 px)/ ``rms_px``(縁の半径残差)/ ``area``(塊の画素数)/
        ``clipped``(1 = 縁のどこかが切れている)/ ``rim_fraction`` / ``centroid_u`` / ``centroid_v``(比較用の重心)。
    """
    from scipy import ndimage

    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or a.size == 0 or not np.isfinite(a).all():
        raise ValueError("image must be a finite 2-D array, got shape %r" % (a.shape,))
    if float(a.min()) < 0.0 or float(a.max()) > 1.0:
        raise ValueError("image must be in [0, 1] (saturation is an absolute level), got %.3g..%.3g" % (float(a.min()), float(a.max())))
    thr = float(threshold)
    if not (0.0 < thr <= 1.0):
        raise ValueError("threshold must be in (0, 1], got %r" % (threshold,))
    top = int(ignore_top_rows)
    if top < 0 or top >= a.shape[0] - 2:
        raise ValueError("ignore_top_rows must be in [0, H-2), got %r" % (ignore_top_rows,))
    H, W = a.shape
    mask = a >= thr
    mask[:top, :] = False
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        raise ValueError("no saturated pixel (>= %.2f) — no bloom in this image" % thr)
    sizes = ndimage.sum(mask, lab, index=np.arange(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    area = float(sizes[k - 1])
    if area < int(min_area):
        raise ValueError("largest saturated blob has %d pixels < min_area %d" % (int(area), int(min_area)))
    if area > float(max_area_frac) * H * W:
        raise ValueError("largest saturated blob covers %.1f%% of the image (> %.1f%%) — the sky is blown out, not a sun bloom"
                         % (100.0 * area / (H * W), 100.0 * float(max_area_frac)))
    blob = lab == k
    rim = blob & ~ndimage.binary_erosion(blob, structure=np.ones((3, 3)), border_value=0)
    vs, us = np.nonzero(rim)
    on_cut = (vs <= top) | (vs >= H - 1) | (us <= 0) | (us >= W - 1)
    clipped = bool(on_cut.any())
    vs, us = vs[~on_cut].astype(np.float64), us[~on_cut].astype(np.float64)
    if len(us) < 8:
        raise ValueError("only %d rim pixels survive the cut lines — the bloom is almost entirely clipped" % len(us))
    M = np.column_stack([us, vs, np.ones_like(us)])
    rhs = -(us ** 2 + vs ** 2)
    (ca, cb, cc), *_ = np.linalg.lstsq(M, rhs, rcond=None)
    cu, cv = -ca / 2.0, -cb / 2.0
    r2 = cu * cu + cv * cv - cc
    if not np.isfinite(r2) or r2 <= 0.0:
        raise ValueError("circle fit to the bloom rim is degenerate (the rim is a straight edge)")
    r = float(np.sqrt(r2))
    rms = float(np.std(np.hypot(us - cu, vs - cv) - r))
    rim_fraction = float(min(1.0, len(us) / max(2.0 * np.pi * r, 1.0)))
    if rim_fraction < float(min_rim_fraction):
        raise ValueError("only %.0f%% of the rim is unclipped (< %.0f%%) — the centre is not constrained"
                         % (100.0 * rim_fraction, 100.0 * float(min_rim_fraction)))
    ys, xs = np.nonzero(blob)
    return {"u": float(cu), "v": float(cv), "r": r, "rms_px": rms, "area": area, "clipped": float(clipped),
            "rim_fraction": rim_fraction, "centroid_u": float(xs.mean()), "centroid_v": float(ys.mean())}


def camera_orientation_from_sun_candidates(candidates, frame_index, unix_times, lat_deg, lon_deg, shape, K=None,
                                           hfov_range_deg=(25.0, 120.0), tol_px=20.0, roll_max_deg=12.0,
                                           pitch_range_deg=(-40.0, 0.0), min_dt=1800.0, max_pairs=600, seed=0):
    """フレームごとに複数ある「明るい塊」の候補(太陽・白い車・標識・文字が混じる)から、**時刻どおりに動く 1 本**を
    RANSAC で選び、(yaw, pitch, roll) と焦点距離を同時に決める → table。固定カメラでは太陽だけが太陽の速さで動く
    ので、見た目で太陽を決めずに動きで決める(Fintraffic 天候カメラでは見た目の門が 24/24 誤検出だった、2026-09-21)。

    仮説 = 時刻差 ≥ ``min_dt`` の 2 フレームから候補を 1 つずつ → ``camera_orientation_from_sun`` と同じ Wahba の
    2 点解。**道路カメラの事前知識**(|roll| ≤ ``roll_max_deg``、pitch が ``pitch_range_deg``、水平画角が
    ``hfov_range_deg``)を満たさない仮説は捨てる —— 自由度 4(回転 3 + 焦点距離)に対して候補が多いと、偶然の 3 点で
    非物理な姿勢が通るため。票 = 予測位置から ``tol_px`` 以内に候補があるフレーム数(地平線下の時刻は投票しない)。実写のブルーム中心は 5〜13 px ぶれる(雲・露出)ので既定 20 px。最良仮説のインライアで焦点距離を
    1 次元最適化し、回転を全点で引き直す(2 回)。

    **濡れた路面に映った太陽の反射も太陽の速さで動く**(鏡像)ので、動きだけでは区別できない。反射は画像の下側(路面)に
    あるから、それを太陽として当てはめると「カメラが上を向く」姿勢(pitch > 0)になる —— 既定の ``pitch_range_deg`` の上限 0 は
    そのための門(道路カメラは上を向かない)。上を向くカメラなら広げること。独立な検算(車線の消失点の仰角 ≈ 0)も勧める。

    ``K`` を渡せばそれを使う(焦点距離は探索しない)。``K=None`` なら主点は画像中心、``fx = fy = f`` を
    ``hfov_range_deg`` の範囲で探索する —— 公開カメラは内部パラメータが無いのが普通。

    Args:
        candidates: (N, 2) の (u, v)。全フレームの候補を積んだもの(``sun_bloom_fit`` や ``sun_pixel_position`` の出力)。
        frame_index: (N,) 各候補がどのフレームか(``unix_times`` の添字、整数値)。
        unix_times: (F,) 各フレームの UNIX 秒(UTC)。
        lat_deg, lon_deg: カメラの位置。
        shape: (H, W)。
        K: (fx, fy, cx, cy) か None。
    Returns:
        table: ``yaw_deg`` / ``pitch_deg`` / ``roll_deg`` / ``f_px`` / ``hfov_deg`` / ``K``(4,)/ ``inlier``(N,、1 = 採用)/
        ``n_inliers`` / ``n_frames`` / ``n_frames_with_candidates`` / ``residual_deg``(採用点の角度残差 RMS)/
        ``max_residual_deg`` / ``residual_px`` / ``loo_px``(1 点抜き予測誤差の平均)/ ``loo_max_px`` / ``span_h``
        (採用点の時間幅)/ ``n_hypotheses``(事前知識を通った仮説の数)/ ``at_prior_bound``(1 = 答えが事前知識の縁に張り付いている: 信用しない)。
    Raises:
        ValueError: 候補が 2 フレーム未満、事前知識を通る仮説が無い、インライアが 3 未満。
    """
    uv = np.asarray(candidates, dtype=np.float64)
    fi = np.atleast_1d(np.asarray(frame_index, dtype=np.float64)).ravel()
    t = np.atleast_1d(np.asarray(unix_times, dtype=np.float64)).ravel()
    if uv.ndim != 2 or uv.shape[1] < 2 or not np.isfinite(uv).all():
        raise ValueError("candidates must be a finite (N, 2) array of (u, v), got shape %r" % (uv.shape,))
    uv = uv[:, :2]
    if len(fi) != len(uv):
        raise ValueError("frame_index has %d entries but candidates has %d rows" % (len(fi), len(uv)))
    if len(t) < 2 or not np.isfinite(t).all():
        raise ValueError("unix_times must hold at least 2 finite frame times, got %d" % len(t))
    if not np.isfinite(fi).all() or np.any(fi < 0) or np.any(fi >= len(t)) or np.any(fi != np.round(fi)):
        raise ValueError("frame_index must be integers in [0, %d)" % len(t))
    fi = fi.astype(int)
    try:
        H, W = int(shape[0]), int(shape[1])
    except Exception:  # noqa: BLE001
        raise ValueError("shape must be (H, W), got %r" % (shape,))
    if H < 2 or W < 2:
        raise ValueError("shape must be at least 2x2, got %r" % (shape,))
    _check_latlon(lat_deg, lon_deg)
    lo, hi = float(hfov_range_deg[0]), float(hfov_range_deg[1])
    if not (0.0 < lo < hi < 180.0):
        raise ValueError("hfov_range_deg must satisfy 0 < lo < hi < 180, got %r" % (hfov_range_deg,))
    sun = sun_position(lat_deg, lon_deg, t)
    s_w = _dir_from_az_el(sun["azimuth_deg"], sun["elevation_deg"])
    F, N = len(t), len(uv)
    per_frame = [np.nonzero(fi == k)[0] for k in range(F)]
    # 地平線下(−3° 未満)の時刻の候補は投票させない —— カメラが見ているのは太陽ではない
    have = [k for k in range(F) if len(per_frame[k]) and sun["elevation_true_deg"][k] >= -3.0]
    if len(have) < 2:
        raise ValueError("candidates are present in only %d frame(s) — at least 2 frames at different times are needed" % len(have))
    if K is None:
        f_hi = W / (2.0 * np.tan(np.radians(lo / 2.0)))
        f_lo = W / (2.0 * np.tan(np.radians(hi / 2.0)))
        f_grid = np.exp(np.linspace(np.log(f_lo), np.log(f_hi), 7))
        Ks = [(float(f), float(f), W / 2.0, H / 2.0) for f in f_grid]
    else:
        fx, fy, cx, cy = _intrinsics(K)
        Ks = [(fx, fy, cx, cy)]
    tol = float(tol_px)
    rmax, (pmin, pmax) = float(roll_max_deg), (float(pitch_range_deg[0]), float(pitch_range_deg[1]))

    def _plausible(R, Kc):
        yaw, pitch, roll = _pose_from_rotation(R)
        hfov = 2.0 * np.degrees(np.arctan(W / (2.0 * Kc[0])))
        return abs(roll) <= rmax and pmin <= pitch <= pmax and lo <= hfov <= hi

    def _kabsch(d_c, sw):
        Hm = d_c.T @ sw
        U, S, Vt = np.linalg.svd(Hm)
        if S[1] < 1e-3:
            return None
        D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
        return Vt.T @ D @ U.T

    def _project(R, Kc):
        c = s_w @ R                                                   # 世界 → カメラ
        ok = c[:, 2] > 0.05
        p = np.full((F, 2), np.nan)
        p[ok, 0] = Kc[2] + Kc[0] * c[ok, 0] / c[ok, 2]
        p[ok, 1] = Kc[3] + Kc[1] * c[ok, 1] / c[ok, 2]
        return p

    def _vote(R, Kc):
        p = _project(R, Kc)
        inl, err = [], 0.0
        for k in have:
            if np.isnan(p[k, 0]):
                continue
            idx = per_frame[k]
            d = np.hypot(uv[idx, 0] - p[k, 0], uv[idx, 1] - p[k, 1])
            m = int(np.argmin(d))
            if d[m] <= tol:
                inl.append(idx[m])
                err += d[m]
        return inl, err

    rng = np.random.default_rng(int(seed))
    pairs = [(i, j) for a, i in enumerate(have) for j in have[a + 1:] if abs(t[j] - t[i]) >= float(min_dt)]
    if not pairs:
        raise ValueError("no two frames with candidates are at least min_dt=%.0f s apart" % float(min_dt))
    if len(pairs) > int(max_pairs):
        pairs = [pairs[q] for q in rng.choice(len(pairs), int(max_pairs), replace=False)]
    best, n_hyp = None, 0
    for Kc in Ks:
        for i, j in pairs:
            for ia in per_frame[i]:
                for ib in per_frame[j]:
                    R = _kabsch(_pixel_rays(uv[[ia, ib]], Kc), s_w[[i, j]])
                    if R is None or not _plausible(R, Kc):
                        continue
                    n_hyp += 1
                    inl, err = _vote(R, Kc)
                    score = (len(inl), -err)
                    if best is None or score > best[0]:
                        best = (score, Kc, inl)
    if best is None:
        raise ValueError("no two-point hypothesis satisfies the priors (|roll| <= %.0f, pitch in [%.0f, %.0f], hfov in [%.0f, %.0f])"
                         % (rmax, pmin, pmax, lo, hi))
    _, Kc, inl = best
    if len(inl) < 3:
        raise ValueError("best hypothesis has only %d supporting frames (< 3) — no consistent sun track among the candidates" % len(inl))

    from scipy.optimize import minimize_scalar

    f = Kc[0]
    for _ in range(2):
        idx = np.array(inl)
        if K is None:
            def _resid(ff):
                Kt = (ff, ff, W / 2.0, H / 2.0)
                R = _kabsch(_pixel_rays(uv[idx], Kt), s_w[fi[idx]])
                if R is None:
                    return 1e9
                p = _project(R, Kt)[fi[idx]]
                return float(np.mean(np.hypot(p[:, 0] - uv[idx, 0], p[:, 1] - uv[idx, 1])))
            f = float(minimize_scalar(_resid, bounds=(0.6 * f, 1.7 * f), method="bounded").x)
            Kc = (f, f, W / 2.0, H / 2.0)
        R = _kabsch(_pixel_rays(uv[idx], Kc), s_w[fi[idx]])
        if R is None:
            raise ValueError("the supporting sun directions became collinear during refinement")
        inl, _ = _vote(R, Kc)
        if len(inl) < 3:
            raise ValueError("fewer than 3 frames survive refinement — no consistent sun track among the candidates")
    idx = np.array(inl)
    fit = camera_orientation_from_sun(uv[idx], t[fi[idx]], lat_deg, lon_deg, Kc)
    R = _rotation(fit["yaw_deg"], fit["pitch_deg"], fit["roll_deg"])
    if not _plausible(R, Kc):
        # 仮説は事前知識の中で選んだが、焦点距離の最適化と全点の当て直しで外へ出た = 候補列が太陽の軌跡ではない
        raise ValueError("the refined pose leaves the priors (yaw %.1f, pitch %.1f, roll %.1f, hfov %.1f) — the supporting candidates "
                         "are not a sun track (widen roll_max_deg / pitch_range_deg / hfov_range_deg only if the camera really is like that)"
                         % (fit["yaw_deg"], fit["pitch_deg"], fit["roll_deg"], 2.0 * np.degrees(np.arctan(W / (2.0 * Kc[0])))))
    p = _project(R, Kc)[fi[idx]]
    px = np.hypot(p[:, 0] - uv[idx, 0], p[:, 1] - uv[idx, 1])
    loo = []
    for q in range(len(idx)):
        keep = np.arange(len(idx)) != q
        Rq = _kabsch(_pixel_rays(uv[idx[keep]], Kc), s_w[fi[idx[keep]]])
        if Rq is None:
            continue
        pq = _project(Rq, Kc)[fi[idx[q]]]
        loo.append(float(np.hypot(pq[0] - uv[idx[q], 0], pq[1] - uv[idx[q], 1])))
    inlier = np.zeros(N)
    inlier[idx] = 1.0
    hfov = 2.0 * np.degrees(np.arctan(W / (2.0 * Kc[0])))
    # 事前知識の縁に張り付いた答えは「縁が無ければもっと外へ行った」印 —— 偽の軌跡(両日の別々の塊など)がよくここへ来る
    at_bound = (abs(abs(fit["roll_deg"]) - rmax) < 1.0 or abs(fit["pitch_deg"] - pmin) < 1.0 or abs(fit["pitch_deg"] - pmax) < 1.0
                or (K is None and (abs(hfov - lo) < 2.0 or abs(hfov - hi) < 2.0)))
    return {"yaw_deg": fit["yaw_deg"], "pitch_deg": fit["pitch_deg"], "roll_deg": fit["roll_deg"], "f_px": float(Kc[0]), "at_prior_bound": float(at_bound),
            "hfov_deg": float(hfov), "K": np.array(Kc, dtype=np.float64), "inlier": inlier, "n_inliers": int(len(idx)),
            "n_frames": int(F), "n_frames_with_candidates": int(len(have)), "residual_deg": fit["residual_deg"],
            "max_residual_deg": fit["max_residual_deg"], "residual_px": float(px.mean()),
            "loo_px": float(np.mean(loo)) if loo else float("nan"), "loo_max_px": float(np.max(loo)) if loo else float("nan"),
            "span_h": float((t[fi[idx]].max() - t[fi[idx]].min()) / 3600.0), "n_hypotheses": int(n_hyp)}


# --------------------------------------------------------------------------- #
# スカイライン                                                                  #
# --------------------------------------------------------------------------- #
def _dem_check(dem, cell_size):
    z = np.asarray(dem, dtype=np.float64)
    if z.ndim != 2 or z.shape[0] < 3 or z.shape[1] < 3 or not np.isfinite(z).all():
        raise ValueError("dem must be a finite 2-D array of at least 3x3 cells, got shape %r" % (z.shape,))
    cs = float(cell_size)
    if not np.isfinite(cs) or cs <= 0.0:
        raise ValueError("cell_size must be a positive number of metres per cell, got %r" % (cell_size,))
    return z, cs


def dem_skyline(dem, cell_size, observer_rc, eye_height=1.5, az_step_deg=1.0, max_distance=None,
                earth_curvature=True):
    """DEM の 1 点から見た**全方位のスカイライン**(方位ごとの地平線仰角)→ table。

    ``dem_horizon_angle`` は「全セル × 1 方位」、これは「1 点 × 全方位」—— 固定カメラの向きを
    決めるのに要るのは後者。各方位へ ``cell_size / 2`` 刻みで視線を進め(標高は双一次補間)、
    ``atan((z_j − z_0 − drop(d)) / d)`` の最大値をその方位の仰角にする。``drop(d) = d² / (2 R_eff)``
    は地球の丸みと大気屈折(有効半径 R / (1 − 0.13))で遠くの山が沈む分。視線が DEM の外に
    出たらそこで止める(``max_distance`` でも止まる)。**DEM の外側**は「DEM の最低標高の平面が
    地平線まで続く」と仮定し、仰角の下限を地平線の沈み ``−sqrt(2 h / R_eff)``(h = 観測点の
    最低標高からの高さ)にする —— 有限の DEM の端でたまたま低い点を見て、実際には地球の丸みで
    見えない −7° のような「穴」を空にしないため(``horizon_dip_deg`` に返す)。

    Args:
        dem: (H, W) 標高 [m]。行 0 が北端。
        cell_size: [m/セル]。
        observer_rc: 観測点 (row, col)。float 可(セルの中に立てる)。
        eye_height: 地面からのカメラ高さ [m]。
        az_step_deg: 方位の刻み [度]。
        max_distance: 視線の最大距離 [m](None = DEM の端まで)。
        earth_curvature: False なら平らな地球。
    Returns:
        table: ``azimuth_deg`` (M,) / ``elevation_deg`` (M,) / ``distance_m`` (M,)(仰角を決めた
        地点までの距離)/ ``observer_elevation_m`` / ``horizon_dip_deg`` / ``n``。方位は 0 以上
        360 未満、昇順。
    """
    from scipy.ndimage import map_coordinates

    z, cs = _dem_check(dem, cell_size)
    r0, c0 = float(observer_rc[0]), float(observer_rc[1])
    H, W = z.shape
    if not (0.0 <= r0 <= H - 1 and 0.0 <= c0 <= W - 1):
        raise ValueError("observer_rc %r is outside the DEM %r" % (observer_rc, z.shape))
    step = float(az_step_deg)
    if not np.isfinite(step) or step <= 0.0 or step > 90.0:
        raise ValueError("az_step_deg must be in (0, 90], got %r" % (az_step_deg,))
    eh = float(eye_height)
    if not np.isfinite(eh) or eh < 0.0:
        raise ValueError("eye_height must be a finite value >= 0, got %r" % (eye_height,))
    z0 = float(map_coordinates(z, [[r0], [c0]], order=1, mode="nearest")[0]) + eh
    az = np.arange(0.0, 360.0, step)
    ds = cs / 2.0
    # 端までの距離の上限(全方位で同じ長さの視線を切って、DEM の外は捨てる)
    dmax = float(max(H, W)) * cs * 1.5
    if max_distance is not None:
        md = float(max_distance)
        if not np.isfinite(md) or md <= 0.0:
            raise ValueError("max_distance must be a positive distance in metres, got %r" % (max_distance,))
        dmax = min(dmax, md)
    d = np.arange(ds, dmax + ds, ds)
    azr = np.deg2rad(az)
    # 北 = -行, 東 = +列
    rows = r0 - np.outer(np.cos(azr), d) / cs
    cols = c0 + np.outer(np.sin(azr), d) / cs
    inside = (rows >= 0) & (rows <= H - 1) & (cols >= 0) & (cols <= W - 1)
    zz = map_coordinates(z, [rows.ravel(), cols.ravel()], order=1, mode="nearest").reshape(rows.shape)
    drop = d ** 2 / (2.0 * _EARTH_RADIUS_M / (1.0 - _REFRACTION_K)) if earth_curvature else 0.0
    ang = np.degrees(np.arctan2(zz - z0 - drop, d[None, :]))
    ang = np.where(inside, ang, -np.inf)
    k = np.argmax(ang, axis=1)
    el = ang[np.arange(len(az)), k]
    r_eff = _EARTH_RADIUS_M / (1.0 - _REFRACTION_K) if earth_curvature else np.inf
    dip = float(np.degrees(np.sqrt(2.0 * max(z0 - float(z.min()), 0.0) / r_eff))) if np.isfinite(r_eff) else 0.0
    el = np.where(np.isfinite(el), el, -dip)                           # 観測点が DEM の端ならその方位は地平線
    el = np.maximum(el, -dip)                                          # DEM の外は最低標高の平面 → 地平線の沈みが下限
    return {"azimuth_deg": az, "elevation_deg": el, "distance_m": d[k],
            "observer_elevation_m": z0, "horizon_dip_deg": dip, "n": int(len(az))}


def skyline_extract(image, sky_is_bright=True, smooth=1.5, max_jump=3, jump_penalty=0.5):
    """写真から**列ごとの空と地形の境界の行**を動的計画法で 1 本抜く → signal (W,)。

    Lie・Lin・Hsu 2005(*Pattern Recognition*: 航法のための頑健なスカイライン抽出)と同じ考え:
    垂直方向の明るさの変化(空が上で明るければ ``I[v−1] − I[v+1]`` が正)を「境界らしさ」にし、
    隣の列から行が ``max_jump`` 以上飛ばない連続な経路のうちコストが最小のものを選ぶ
    (``jump_penalty`` × 行の飛び)。雲や建物の縦の縁で局所的に強い応答が出ても、経路の
    連続性が本物の稜線を残す。

    Args:
        image: (H, W) float。RGB なら先に灰色にする。
        sky_is_bright: 空が地形より明るい(昼)。夜景・逆光で反転するなら False。
        smooth: 縦方向の Gaussian σ [画素](雑音)。0 で無効。
        max_jump: 隣の列で許す行の飛び [画素]。
        jump_penalty: 飛び 1 画素あたりのコスト(境界らしさは 0〜1 に正規化してある)。
    Returns:
        signal (W,) float: 列ごとの境界の行(0 が最上段)。**空しか写っていない・地形しか
        写っていない**画像では境界の応答が弱く、経路の平均コストが 0 に近いので ValueError
        で止める(黙って雑音の線を返さない)。
    """
    from scipy.ndimage import gaussian_filter1d

    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or a.shape[0] < 5 or a.shape[1] < 2 or not np.isfinite(a).all():
        raise ValueError("image must be a finite 2-D array of at least 5 rows and 2 columns, got shape %r" % (a.shape,))
    mj = int(max_jump)
    if mj < 0:
        raise ValueError("max_jump must be >= 0")
    jp = float(jump_penalty)
    if not np.isfinite(jp) or jp < 0.0:
        raise ValueError("jump_penalty must be a finite value >= 0")
    if float(smooth) > 0.0:
        a = gaussian_filter1d(a, float(smooth), axis=0, mode="nearest")
    g = np.zeros_like(a)
    g[1:-1] = a[:-2] - a[2:]
    if not sky_is_bright:
        g = -g
    scale = float(np.abs(g).max())
    if scale <= 0.0:
        raise ValueError("the image has no vertical intensity change — no skyline to extract")
    edge = np.clip(g / scale, 0.0, 1.0)                                 # 境界らしさ 0〜1
    cost = 1.0 - edge
    H, W = cost.shape
    acc = cost[:, 0].copy()
    back = np.zeros((H, W), dtype=np.int32)
    rows = np.arange(H)
    for u in range(1, W):
        best = np.full(H, np.inf)
        arg = np.zeros(H, dtype=np.int32)
        for j in range(-mj, mj + 1):
            src = rows + j
            ok = (src >= 0) & (src < H)
            cand = np.full(H, np.inf)
            cand[ok] = acc[src[ok]] + jp * abs(j)
            better = cand < best
            best[better] = cand[better]
            arg[better] = src[better]
        acc = best + cost[:, u]
        back[:, u] = arg
    path = np.zeros(W, dtype=np.int32)
    path[-1] = int(np.argmin(acc))
    for u in range(W - 1, 0, -1):
        path[u - 1] = back[path[u], u]
    strength = float(edge[path, np.arange(W)].mean())
    if strength < 0.05:
        raise ValueError("the best path has mean edge strength %.3f (< 0.05) — the image shows no sky/terrain boundary" % strength)
    return path.astype(np.float64)


def _skyline_interp(sky_table):
    az = np.asarray(sky_table["azimuth_deg"], dtype=np.float64)
    el = np.asarray(sky_table["elevation_deg"], dtype=np.float64)
    if az.ndim != 1 or az.shape != el.shape or len(az) < 4 or not np.isfinite(az).all() or not np.isfinite(el).all():
        raise ValueError("skyline table must have finite 1-D azimuth_deg / elevation_deg of equal length >= 4")
    order = np.argsort(az)
    az, el = az[order], el[order]
    azp = np.concatenate([az[-1:] - 360.0, az, az[:1] + 360.0])
    elp = np.concatenate([el[-1:], el, el[:1]])

    def f(q):
        return np.interp(np.asarray(q, float) % 360.0, azp, elp)
    return f


def render_skyline_view(sky_table, K, shape, yaw_deg, pitch_deg, roll_deg):
    """スカイライン table と姿勢から、その向きのカメラが見る**空のマスク**(H, W)を描く → image2d(0/1)。

    各画素の光線を世界へ回し、その方位のスカイライン仰角より上なら空(1)、下なら地形(0)。
    合成の写真づくり(PoC)と、推定した姿勢を写真に重ねて目で確かめる図に使う。
    ``camera_orientation_from_skyline`` の予測と同じ幾何なので、**描いて → 抜いて → 当てる**の
    往復が閉じる(テストの真値)。

    Args:
        sky_table: ``dem_skyline`` の出力(``azimuth_deg`` / ``elevation_deg``)。
        K: (fx, fy, cx, cy)。shape: (H, W)。
        yaw_deg, pitch_deg, roll_deg: 姿勢(モジュール冒頭の規約)。
    Returns:
        image2d (H, W) float {0, 1}: 1 = 空。
    """
    f = _skyline_interp(sky_table)
    H, W = int(shape[0]), int(shape[1])
    if H < 2 or W < 2:
        raise ValueError("shape must be at least 2x2, got %r" % (shape,))
    R = _rotation(yaw_deg, pitch_deg, roll_deg)
    vv, uu = np.mgrid[0:H, 0:W]
    d = _pixel_rays(np.column_stack([uu.ravel(), vv.ravel()]), K) @ R.T
    az, el = _az_el(d)
    return (el > f(az)).astype(np.float64).reshape(H, W)


def camera_orientation_from_skyline(skyline_rows, K, sky_table, yaw_step_deg=1.0, pitch_range=(-15.0, 15.0),
                                    roll_range=(-10.0, 10.0), coarse_step_deg=2.5):
    """写真のスカイライン(列ごとの行)と DEM のスカイラインから (yaw, pitch, roll) を決める → table。

    写真の境界画素 (u, v) をカメラ光線にし、仮の姿勢で世界へ回すと、各列は (方位, 仰角) の点になる。
    その仰角と、DEM のスカイラインをその方位で引いた仰角の差の RMS が姿勢のコスト。yaw を
    ``yaw_step_deg`` 刻みで一周、pitch・roll を ``coarse_step_deg`` 刻みで格子探索し、最小の点から
    Nelder–Mead で連続値に詰める(scipy)。Baatz ら 2012 のスカイライン照合を、位置既知・
    1 台のカメラに絞った形。

    **曖昧さを返す**: yaw ごとの最良コストの曲線(``yaw_profile_deg`` / ``yaw_profile_residual_deg``)
    と、最良と 2 番目の谷の差 ``margin_deg``(2 番目の谷 = 最良から 20° 以上離れた最小)。平地・
    対称な尾根・半円しか写らない写真では谷が複数あり、margin が小さい。**margin が
    ``coarse`` の残差程度なら向きは決まっていない**と読む(黙って 1 つを返さない: ``ambiguous``)。

    Args:
        skyline_rows: (W,) ``skyline_extract`` の出力(列ごとの行)。
        K: (fx, fy, cx, cy)。
        sky_table: ``dem_skyline`` の出力。
        yaw_step_deg / coarse_step_deg: 粗い格子の刻み。pitch_range / roll_range: 探索範囲 [度]。
    Returns:
        table: ``yaw_deg`` / ``pitch_deg`` / ``roll_deg`` / ``residual_deg``(仰角残差 RMS)/
        ``margin_deg`` / ``runner_up_yaw_deg`` / ``ambiguous``(bool)/ ``yaw_profile_deg`` (M,) /
        ``yaw_profile_residual_deg`` (M,) / ``n_columns``。
    """
    from scipy.optimize import minimize

    rows = np.asarray(skyline_rows, dtype=np.float64).ravel()
    if rows.size < 8 or not np.isfinite(rows).all():
        raise ValueError("skyline_rows must be a finite 1-D array with at least 8 columns, got %r" % (rows.shape,))
    f = _skyline_interp(sky_table)
    ys = float(yaw_step_deg)
    cs_ = float(coarse_step_deg)
    if not (0.0 < ys <= 30.0) or not (0.0 < cs_ <= 30.0):
        raise ValueError("yaw_step_deg and coarse_step_deg must be in (0, 30]")
    pr, rr = (float(pitch_range[0]), float(pitch_range[1])), (float(roll_range[0]), float(roll_range[1]))
    if pr[0] > pr[1] or rr[0] > rr[1]:
        raise ValueError("pitch_range / roll_range must be (lo, hi) with lo <= hi")
    uv = np.column_stack([np.arange(rows.size, dtype=np.float64), rows])
    d_c = _pixel_rays(uv, K)

    def cost(yaw, pitch, roll):
        d = d_c @ _rotation(yaw, pitch, roll).T
        az, el = _az_el(d)
        return float(np.sqrt(np.mean((el - f(az)) ** 2)))

    yaws = np.arange(0.0, 360.0, ys)
    pitches = np.arange(pr[0], pr[1] + 1e-9, cs_) if pr[1] > pr[0] else np.array([pr[0]])
    rolls = np.arange(rr[0], rr[1] + 1e-9, cs_) if rr[1] > rr[0] else np.array([rr[0]])
    profile = np.full(len(yaws), np.inf)
    best_pr = [None] * len(yaws)
    for i, y in enumerate(yaws):
        for p in pitches:
            for r in rolls:
                c = cost(y, p, r)
                if c < profile[i]:
                    profile[i], best_pr[i] = c, (p, r)
    i0 = int(np.argmin(profile))
    p0, r0 = best_pr[i0]
    x0 = np.array([yaws[i0], p0, r0])
    res = minimize(lambda x: cost(*x), x0, method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-6, "maxiter": 400})
    yaw, pitch, roll = float(res.x[0]) % 360.0, float(res.x[1]), float(res.x[2])
    best = float(res.fun)
    # 2 番目の谷: 最良から 20° 以上離れた yaw の最小
    far = np.abs((yaws - yaws[i0] + 180.0) % 360.0 - 180.0) >= 20.0
    runner = float(profile[far].min()) if far.any() else float("inf")
    runner_yaw = float(yaws[far][np.argmin(profile[far])]) if far.any() else float("nan")
    margin = runner - float(profile[i0])
    ambiguous = bool(margin < max(2.0 * best, 0.25))
    return {"yaw_deg": yaw, "pitch_deg": pitch, "roll_deg": roll, "residual_deg": best,
            "margin_deg": float(margin), "runner_up_yaw_deg": runner_yaw, "ambiguous": ambiguous,
            "yaw_profile_deg": yaws, "yaw_profile_residual_deg": profile, "n_columns": int(rows.size)}
