# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""太陽と天気(太陽の位置・影・逆光のまぶしさ・霧・雨・夜の前照灯)を教習所の世界に入れ、「見えてから止まれるか」を測る。

## 何を作るか

これまでの車載カメラ(driveworld.world_camera)は、光の向きが固定(カメラ系で与える)で、明るさは面の色 × Lambert の陰影
だけだった。ここでは **物理の単位(輝度 cd/m²・照度 lx)** で世界を照らし直す:

* **太陽**: 日時と緯度経度から太陽の高度・方位(NOAA の太陽位置の式 = Meeus "Astronomical Algorithms" の低精度版)。
  直達光は大気の通り道(空気の量 = Kasten–Young)で弱まり(Meinel の経験式)、影は太陽から見た深度画像(シャドウマップ)で落とす。
* **空の明るさ**: 太陽の高度で決まる(薄明の照度の表を対数で補間 —— 概略値、下の「仮定」)。雲量で直達を減らし散乱を増やす。
* **逆光のまぶしさ**: 太陽とカメラの視線の角 θ で、レンズ・目の中の散乱が光の幕(光幕輝度)を重ねる。
  Stiles–Holladay: L_v = 10 E_glare / θ²(θ は度、E_glare = 目の位置での太陽の照度 lx)。光幕は色が白いので、灯火の色度を
  灰色へ引き寄せる —— 信号の色の読みが落ちる。
* **霧**: Koschmieder の法則 L(d) = L₀ e^{−βd} + L_h (1 − e^{−βd})(L_h = 地平線の空の輝度 = 大気光)。気象光学距離
  MOR = −ln(0.05)/β ≈ 2.996/β(WMO: コントラスト 5 %)、Koschmieder の視程 3.912/β(コントラスト 2 %)。
* **霧の濃さを画像から測る**(Hautière ら 2006 の考え方): 平らな路面を写した縦の輝度の曲線 L(v) は、距離 d = λ/(v − v_h)
  (λ = カメラの高さ × 焦点距離 / cos²(俯角)、v_h = 地平線の行)を Koschmieder に入れた形になり、その **変曲点** v_i で
  β = 2 (v_i − v_h) / λ(= 2 / d_i)。導出: L = L_h + (L₀ − L_h) e^{−βλ/u}(u = v − v_h)の 2 階微分が 0 になるのは u = βλ/2。
* **雨**: 路面の摩擦係数が下がる(停止距離 = drivelong の閉形式に μ を入れる)。濡れた路面は暗くなり、灯火が鏡に映る
  (路面を鏡とした灯火の鏡像を投影する —— 幾何は厳密、映り方(ぼけ・反射率)は仮定)。雨筋は見た目だけ(仮定)。
* **夜**: 灯火(信号)は自分で光る(周りの照明に依らない輝度)。前照灯は配光(光度 cd の角度分布)から照度 E = I cos i / r²
  を路面と物体に与える。前照灯の影は持たない。

## 真値(門)になるもの

1. 太陽の位置: 国立天文台 暦計算室の日の出入り・南中の時刻と方位・高度(公表値)、および別の低精度の式(天体暦の
   簡略式)と 0.01° の桁で一致(第 2 実装、tests)。
2. 影の長さ = 高さ × cot(高度)(棒の影の先端を、描いた画像のシャドウマップから測る)。
3. 霧: 描いた画像の輝度が距離で Koschmieder に従う / 変曲点の閉形式で β を画像から戻す。
4. 見えてから止まれる速さ ``sight_stop_speed``: 停止距離の閉形式 = 見える距離 を v について解く(k = 0 は 2 次方程式の根、
   k > 0 は二分法)。drivelong.stopping_distance_grade に戻して一致。
5. 逆光: 灯火の色度が検出の許容(balltrack の chroma の color_tol)を割る光幕の閾値を、画素の式から先に出し、
   描いた画像の読みがその両側で変わる。

## 仮定(出典の確かさを分けて書く)

* 大気外の太陽放射 1361 W/m²(太陽定数、Kopp & Lean 2011)、発光効率 105 lm/W で照度に(仮定、晴天の日射の典型値)。
  直達の減衰 = Meinel 0.7^{AM^0.678}(経験式)、空気の量 AM = Kasten & Young 1989。
* 晴天の散乱光(水平面)と薄明の照度: 高度 0° で 400 lx、−6° で 3 lx、−12° で 0.008 lx、−18° で 0.001 lx を対数で補間、
  高度 > 0 では 400 + 16000 sin(h) lx(概略値 —— 仮定。薄明の照度は文献で幅がある)。
* 灯火の輝度 10000 cd/m²(LED 信号の典型の桁、仮定)。前照灯の配光(最大光度 すれ違い 15000 cd・走行 60000 cd、
  ガウス形 + すれ違いの上の遮光)は仮定(保安基準は「前方 40 m / 100 m の障害物を確認できる」性能で与え、配光の数字では与えない)。
* カメラの露出: 画面の輝度の中央値を 0.3 に写す自動露出(倍率の上限 1 = 1 cd/m² で 1)。車載の HDR カメラとして
  色の比を保つ階調の圧縮(:func:`tone_map`)—— 明るい灯火も色度は保たれ、白く飛ばない(仮定)。
* 光幕の式は人の目の散乱の経験式で、カメラのレンズの散乱をこれで代用している(仮定)。

## 世界の向き

世界の +x = 東、+y = 北、+z = 上 を既定とする(``north_yaw`` で回せる)。太陽の方位は北から時計回り(北 0°・東 90°)。
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "julian_day", "sun_at", "sun_events", "sun_vector", "sun_illuminance",
    "koschmieder", "mor_from_beta", "beta_from_mor", "road_row_distance", "fog_beta_from_profile",
    "veiling_luminance", "veil_chroma_limit", "sight_stop_speed", "env_params", "tone_map", "env_render",
]

SOLAR_CONSTANT = 1361.0              # W/m²(Kopp & Lean 2011)
LUMINOUS_EFFICACY = 105.0            # lm/W(仮定: 晴天の直達日射の典型)
H0_SUNRISE = -0.8333                 # 日の出入りの太陽の中心の高度 [度](大気差 34′ + 視半径 16′)
_TWILIGHT = ((-18.0, 0.001), (-12.0, 0.008), (-6.0, 3.0), (0.0, 400.0))   # (高度 度, 散乱照度 lx) —— 仮定(上の docstring)


# ---- 引数検査(fail-closed) ------------------------------------------------------------------------
def _finite(v, name: str, op: str) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if not math.isfinite(f):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return f


def _positive(v, name: str, op: str) -> float:
    f = _finite(v, name, op)
    if f <= 0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    return f


def _nonneg(v, name: str, op: str) -> float:
    f = _finite(v, name, op)
    if f < 0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    return f


def _latlon(lat, lon, op: str) -> Tuple[float, float]:
    la = _finite(lat, "lat", op)
    lo = _finite(lon, "lon", op)
    if not -90.0 <= la <= 90.0:
        raise ValueError("%s: lat must be in [-90, 90], got %r" % (op, lat))
    if not -180.0 <= lo <= 360.0:
        raise ValueError("%s: lon must be in [-180, 360], got %r" % (op, lon))
    return la, lo


# ─────────────────────────────── 太陽 ───────────────────────────────────

def julian_day(when) -> float:
    """ユリウス日(UT)。``when`` = タイムゾーンつきの datetime(UTC に直す)、または数(そのままユリウス日)。

    素朴な(tzinfo の無い)datetime は **拒否**する(地方時と UTC を取り違えると太陽が 9 時間ずれる)。"""
    op = "julian_day"
    if isinstance(when, datetime):
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError("%s: naive datetime is ambiguous; give tzinfo (e.g. timezone(timedelta(hours=9)))" % op)
        u = when.astimezone(timezone.utc)
        epoch = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)          # J2000.0 = JD 2451545.0
        return 2451545.0 + (u - epoch).total_seconds() / 86400.0
    return _finite(when, "when", op)


def sun_at(when, lat: float, lon: float, *, refraction: bool = True) -> Dict[str, float]:
    """日時(タイムゾーンつき datetime かユリウス日)の太陽の高度・方位。式は :func:`geocam.sun_position`(NOAA の太陽位置の式
    = Meeus "Astronomical Algorithms" 第 25 章の低精度版、NOAA の大気差)をそのまま使い、日時の受け方と地球–太陽の距離を足す。

    Returns
    -------
    dict : ``elevation``(度、``refraction`` なら大気差つきの見かけ)、``elevation_geometric``、``azimuth``(北から時計回り 度)、
    ``declination``、``eq_time``(均時差 分)、``hour_angle``(度)、``jd``、``distance_au``、``semidiameter``(度)。

    NOAA が述べる精度は、日の出入りの時刻で緯度 ±72° 以内 1 分以内(1800〜2100 年)。

    **Raises** ``ValueError``: 素朴な datetime・範囲外の緯度経度。"""
    import geocam
    op = "sun_at"
    la, lo = _latlon(lat, lon, op)
    if lo > 180.0:
        lo -= 360.0
    jd = julian_day(when)
    g = geocam.sun_position(la, lo, (jd - 2440587.5) * 86400.0)
    T = (jd - 2451545.0) / 36525.0
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    Mr = math.radians(M)
    C = (math.sin(Mr) * (1.914602 - T * (0.004817 + 0.000014 * T)) + math.sin(2 * Mr) * (0.019993 - 0.000101 * T)
         + math.sin(3 * Mr) * 0.000289)
    dist = 1.000001018 * (1.0 - e * e) / (1.0 + e * math.cos(math.radians(M + C)))     # 地球と太陽の距離 [au]
    el_g = float(g["elevation_true_deg"][0])
    return {"elevation": float(g["elevation_deg"][0]) if refraction else el_g, "elevation_geometric": el_g,
            "azimuth": float(g["azimuth_deg"][0]), "declination": float(g["declination_deg"][0]),
            "eq_time": float(g["equation_of_time_min"][0]), "hour_angle": float(g["hour_angle_deg"][0]), "jd": jd,
            "distance_au": dist, "semidiameter": 959.63 / 3600.0 / dist}


def sun_events(year: int, month: int, day: int, lat: float, lon: float, tz_hours: float = 9.0,
               *, h0: float = H0_SUNRISE) -> Dict[str, object]:
    """その日(地方の暦日)の日の出・南中・日の入りの時刻と、日の出入りの方位・南中の高度。

    日の出入り = 太陽の中心の **幾何の** 高度が ``h0``(既定 −0.8333° = 大気差 34′ + 視半径 16′、上辺が地平線に接する)を
    横切る時刻。``h0="naoj"`` で国立天文台 暦計算室の定義(太陽の上辺が視地平線、地平大気差 35′8″、視半径は距離から)。
    南中 = 時角 0。どちらも sun_at を時刻について解く(二分法、1e-6 日 ≈ 0.1 秒まで)。

    Returns
    -------
    dict : ``sunrise`` / ``transit`` / ``sunset``(タイムゾーンつき datetime、日の出入りが無ければ None)、
    ``sunrise_azimuth`` / ``sunset_azimuth``(度)、``transit_altitude``(度、大気差なしの幾何の高度と、``transit_altitude_apparent``)。"""
    op = "sun_events"
    la, lo = _latlon(lat, lon, op)
    tzh = _finite(tz_hours, "tz_hours", op)
    naoj = isinstance(h0, str)
    if naoj and h0 != "naoj":
        raise ValueError("%s: h0 must be a number or 'naoj'" % op)
    h0v = 0.0 if naoj else _finite(h0, "h0", op)
    tz = timezone(timedelta(hours=tzh))
    t0 = datetime(int(year), int(month), int(day), tzinfo=tz)
    jd0 = julian_day(t0)

    def elev(jd):
        sp = sun_at(jd, la, lo, refraction=False)
        if naoj:                                   # 暦計算室: 上辺が視地平線、地平大気差 35′8″(標高 0 m)
            return sp["elevation_geometric"] + sp["semidiameter"] + (35.0 / 60.0 + 8.0 / 3600.0)
        return sp["elevation_geometric"] - h0v

    def ha(jd):
        return sun_at(jd, la, lo, refraction=False)["hour_angle"]

    def to_dt(jd):
        return t0 + timedelta(days=jd - jd0)

    grid = jd0 + np.linspace(0.0, 1.0, 97)                  # 15 分おきに符号の変わり目を探す
    hs = np.array([ha(j) for j in grid])
    es = np.array([elev(j) for j in grid])

    def bisect(f, a, b):
        fa = f(a)
        for _ in range(80):
            m = 0.5 * (a + b)
            fm = f(m)
            if (fm > 0) == (fa > 0):
                a, fa = m, fm
            else:
                b = m
            if b - a < 1e-7:
                break
        return 0.5 * (a + b)

    transit = None
    for i in range(len(grid) - 1):
        if hs[i] < 0.0 <= hs[i + 1] and hs[i + 1] - hs[i] < 180.0:
            transit = bisect(ha, grid[i], grid[i + 1])
            break
    rise = sett = None
    for i in range(len(grid) - 1):
        if es[i] < 0.0 <= es[i + 1] and rise is None:
            rise = bisect(elev, grid[i], grid[i + 1])
        if es[i] >= 0.0 > es[i + 1] and sett is None:
            sett = bisect(elev, grid[i], grid[i + 1])
    out = {"sunrise": to_dt(rise) if rise is not None else None,
           "transit": to_dt(transit) if transit is not None else None,
           "sunset": to_dt(sett) if sett is not None else None,
           "sunrise_azimuth": sun_at(rise, la, lo, refraction=False)["azimuth"] if rise is not None else None,
           "sunset_azimuth": sun_at(sett, la, lo, refraction=False)["azimuth"] if sett is not None else None}
    if transit is not None:
        sp = sun_at(transit, la, lo, refraction=True)
        out["transit_altitude"] = sp["elevation_geometric"]
        out["transit_altitude_apparent"] = sp["elevation"]
    else:
        out["transit_altitude"] = out["transit_altitude_apparent"] = None
    return out


def sun_vector(elevation: float, azimuth: float, north_yaw: float = 90.0) -> np.ndarray:
    """太陽の方向の単位ベクトル(世界系、地面から太陽へ向く)。

    ``north_yaw`` = 世界の +x から反時計回りに測った北の向き [度](既定 90° = +y が北、+x が東)。方位は北から時計回り。"""
    op = "sun_vector"
    el = math.radians(_finite(elevation, "elevation", op))
    az = math.radians(_finite(azimuth, "azimuth", op))
    ny = math.radians(_finite(north_yaw, "north_yaw", op))
    # 方位 az(北から東へ)→ 世界の yaw = north_yaw − az
    yaw = ny - az
    return np.array([math.cos(el) * math.cos(yaw), math.cos(el) * math.sin(yaw), math.sin(el)])


def sun_illuminance(elevation: float, cloud: float = 0.0) -> Dict[str, float]:
    """晴天(雲量 ``cloud`` ∈ [0, 1])の太陽の照度 [lx]: ``direct_normal``(太陽に正対する面)・``diffuse``(水平面の散乱)・``air_mass``。

    直達 = 1361 W/m² × 0.7^{AM^0.678}(Meinel)× 105 lm/W × (1 − cloud)、AM = Kasten & Young 1989
    1 / (sin h + 0.50572 (h + 6.07995°)^{−1.6364})。散乱 = 薄明の表(高度 ≤ 0)/ 400 + 16000 sin h(高度 > 0)に
    雲で (1 + 0.5 cloud) を掛ける —— 仮定(モジュールの docstring)。"""
    op = "sun_illuminance"
    h = _finite(elevation, "elevation", op)
    cl = _finite(cloud, "cloud", op)
    if not 0.0 <= cl <= 1.0:
        raise ValueError("%s: cloud must be in [0, 1], got %r" % (op, cloud))
    if h > 0.0:
        am = 1.0 / (math.sin(math.radians(h)) + 0.50572 * (h + 6.07995) ** -1.6364)
        dn = SOLAR_CONSTANT * 0.7 ** (am ** 0.678) * LUMINOUS_EFFICACY * (1.0 - cl)
        diff = 400.0 + 16000.0 * math.sin(math.radians(h))
    else:
        am = math.inf
        dn = 0.0
        hs = [p[0] for p in _TWILIGHT]
        ls = [math.log(p[1]) for p in _TWILIGHT]
        diff = math.exp(float(np.interp(h, hs, ls, left=ls[0], right=ls[-1])))
    return {"direct_normal": dn, "diffuse": diff * (1.0 + 0.5 * cl), "air_mass": am}


# ─────────────────────────────── 霧 ───────────────────────────────────

def koschmieder(L0, L_h, beta: float, d):
    """Koschmieder の法則: 距離 d の物体の見かけの輝度 L = L₀ e^{−βd} + L_h (1 − e^{−βd})(配列可)。"""
    op = "koschmieder"
    b = _nonneg(beta, "beta", op)
    d = np.asarray(d, np.float64)
    if np.any(~np.isfinite(d)) or np.any(d < 0):
        raise ValueError("%s: d must be finite and >= 0" % op)
    t = np.exp(-b * d)
    return np.asarray(L0, np.float64) * t + np.asarray(L_h, np.float64) * (1.0 - t)


def mor_from_beta(beta: float, contrast: float = 0.05) -> float:
    """減衰係数 β [1/m] → 視程 = −ln(contrast)/β。既定 0.05 = WMO の気象光学距離(MOR ≈ 2.996/β)、0.02 = Koschmieder(3.912/β)。"""
    op = "mor_from_beta"
    b = _positive(beta, "beta", op)
    c = _finite(contrast, "contrast", op)
    if not 0.0 < c < 1.0:
        raise ValueError("%s: contrast must be in (0, 1), got %r" % (op, contrast))
    return -math.log(c) / b


def beta_from_mor(mor: float, contrast: float = 0.05) -> float:
    """視程 → 減衰係数 β = −ln(contrast)/視程(:func:`mor_from_beta` の逆)。"""
    op = "beta_from_mor"
    m = _positive(mor, "mor", op)
    c = _finite(contrast, "contrast", op)
    if not 0.0 < c < 1.0:
        raise ValueError("%s: contrast must be in (0, 1), got %r" % (op, contrast))
    return -math.log(c) / m


def road_row_distance(rows, horizon_row: float, focal: float, cam_height: float, pitch: float = 0.0) -> np.ndarray:
    """平らな路面の上の行 → カメラから路面の点までの水平距離(厳密)。地平線より上の行は ``inf``。

    俯角 α(下向き +、ラジアン)のピンホール: 地平線の行 v_h = c_y − f tan α、路面の水平距離 d の点の行は
    v − v_h = f H (1 + tan²α) / (d + H tan α) —— よって d = λ/(v − v_h) − H tan α、λ = f H / cos²α
    (Hautière ら 2006 の λ/(v − v_h) は第 1 項だけの形)。行は下向きが +。"""
    op = "road_row_distance"
    vh = _finite(horizon_row, "horizon_row", op)
    f = _positive(focal, "focal", op)
    Hc = _positive(cam_height, "cam_height", op)
    a = _finite(pitch, "pitch", op)
    lam = f * Hc / math.cos(a) ** 2
    v = np.asarray(rows, np.float64)
    u = v - vh
    with np.errstate(divide="ignore", invalid="ignore"):
        d = lam / np.where(u > 0, u, 1.0) - Hc * math.tan(a)
    return np.where(u > 0, d, np.inf)


def fog_beta_from_profile(rows, luminance, horizon_row: float, focal: float, cam_height: float, pitch: float = 0.0, *,
                          method: str = "fit", slant: bool = True, beta_range=(1e-4, 0.5), n_grid: int = 400) -> Dict[str, float]:
    """路面の縦の輝度の曲線から霧の減衰係数 β を測る(Hautière ら 2006 の考え方)。

    ``method="fit"``(既定): 各行の路面までの距離(:func:`road_row_distance`、``slant=True`` で視線の長さ √(d² + H²))に
    Koschmieder L = L_h + (L₀ − L_h) e^{−β r} を当てる(β は対数格子 + 黄金分割、各 β で L₀・L_h は線形最小二乗)。
    ``method="inflection"``: 曲線を 5 行の移動平均で均し、2 階差分が符号を変える行 v_i から β = 2 (v_i − v_h)/λ
    (λ = f H / cos²α。距離を λ/(v − v_h) と近似したときの厳密な変曲点: L = L_h + (L₀ − L_h) e^{−βλ/u} の 2 階微分は u = βλ/2 で 0)。
    返り値にはどちらも入る: ``beta``(選んだ方)・``beta_fit``・``beta_inflection``(見つからなければ nan)・``L0``・``L_h``・
    ``rms``・``mor``(2.996/β)。

    **Raises** ``ValueError``: 長さ違い・地平線より下の点が 5 未満・method が不正。"""
    op = "fog_beta_from_profile"
    if method not in ("fit", "inflection"):
        raise ValueError("%s: method must be 'fit' or 'inflection'" % op)
    v = np.asarray(rows, np.float64).ravel()
    L = np.asarray(luminance, np.float64).ravel()
    if v.shape != L.shape:
        raise ValueError("%s: rows and luminance must have the same length" % op)
    vh = _finite(horizon_row, "horizon_row", op)
    f = _positive(focal, "focal", op)
    Hc = _positive(cam_height, "cam_height", op)
    a = _finite(pitch, "pitch", op)
    lam = f * Hc / math.cos(a) ** 2
    ok = np.isfinite(v) & np.isfinite(L) & (v > vh + 0.5)
    v, L = v[ok], L[ok]
    if len(v) < 5:
        raise ValueError("%s: need >= 5 finite rows below the horizon, got %d" % (op, len(v)))
    order = np.argsort(v)
    v, L = v[order], L[order]
    d = road_row_distance(v, vh, f, Hc, a)
    r = np.sqrt(d * d + Hc * Hc) if slant else d

    def solve(b):
        t = np.exp(-b * r)
        A = np.stack([t, 1.0 - t], axis=1)
        coef, *_ = np.linalg.lstsq(A, L, rcond=None)
        res = A @ coef - L
        return float(np.sqrt(np.mean(res * res))), coef

    lo, hi = (_positive(beta_range[0], "beta_range[0]", op), _positive(beta_range[1], "beta_range[1]", op))
    grid = np.geomspace(lo, hi, int(n_grid))
    errs = np.array([solve(b)[0] for b in grid])
    i = int(np.argmin(errs))
    aa, cc = grid[max(0, i - 1)], grid[min(len(grid) - 1, i + 1)]
    gr = (math.sqrt(5) - 1) / 2
    x1, x2 = cc - gr * (cc - aa), aa + gr * (cc - aa)
    f1, f2 = solve(x1)[0], solve(x2)[0]
    for _ in range(200):
        if f1 < f2:
            cc, x2, f2 = x2, x1, f1
            x1 = cc - gr * (cc - aa)
            f1 = solve(x1)[0]
        else:
            aa, x1, f1 = x1, x2, f2
            x2 = aa + gr * (cc - aa)
            f2 = solve(x2)[0]
        if cc - aa < 1e-13 * max(1.0, cc):
            break
    b_fit = 0.5 * (aa + cc)
    rms, coef = solve(b_fit)
    b_inf = float("nan")
    if len(v) >= 9:
        k = 5
        Ls = np.convolve(L, np.ones(k) / k, mode="valid")
        vs = v[k // 2: len(v) - k // 2]
        d2 = np.diff(Ls, 2)
        sgn = np.sign(d2)
        idx = np.where(sgn[:-1] * sgn[1:] < 0)[0]
        if len(idx):
            j = idx[np.argmax(np.abs(d2[idx] - d2[idx + 1]))]
            w = d2[j] / (d2[j] - d2[j + 1])
            vi = vs[j + 1] + w * (vs[j + 2] - vs[j + 1])
            b_inf = 2.0 * (vi - vh) / lam
    beta = b_fit if method == "fit" else b_inf
    return {"beta": float(beta), "beta_fit": float(b_fit), "beta_inflection": float(b_inf), "L0": float(coef[0]),
            "L_h": float(coef[1]), "rms": rms, "mor": (2.995732273553991 / beta) if beta and beta > 0 else float("nan")}


# ─────────────────────────────── まぶしさ ───────────────────────────────────

def veiling_luminance(E_glare, theta_deg, *, model: str = "stiles_holladay", age: float = 40.0, p: float = 0.5):
    """減能グレアの光幕輝度 L_v [cd/m²](配列可)。E_glare = 目の位置での光源の照度 [lx]、θ = 光源と視線の角 [度]。

    ``model="stiles_holladay"``: L_v = 10 E / θ²(θ は 1°〜30° 程度で使われる経験式)。
    ``model="cie"``: CIE 146:2002 の一般式 L_v/E = 10/θ³ + (5/θ² + 0.1 p/θ)(1 + (age/62.5)⁴) + 0.0025 p
    (p = 目の色素の係数、既定 0.5)。θ ≤ 0 は拒否(光源そのものは光幕でなく像)。"""
    op = "veiling_luminance"
    if model not in ("stiles_holladay", "cie"):
        raise ValueError("%s: model must be 'stiles_holladay' or 'cie'" % op)
    E = np.asarray(E_glare, np.float64)
    th = np.asarray(theta_deg, np.float64)
    if np.any(~np.isfinite(E)) or np.any(E < 0):
        raise ValueError("%s: E_glare must be finite and >= 0" % op)
    if np.any(~np.isfinite(th)) or np.any(th <= 0):
        raise ValueError("%s: theta_deg must be finite and > 0" % op)
    if model == "stiles_holladay":
        return 10.0 * E / th ** 2
    a = _nonneg(age, "age", op)
    pp = _nonneg(p, "p", op)
    return E * (10.0 / th ** 3 + (5.0 / th ** 2 + 0.1 * pp / th) * (1.0 + (a / 62.5) ** 4) + 0.0025 * pp)


def veil_chroma_limit(color, luminance: float, tol: float = 0.15) -> float:
    """色 ``color``(RGB の比)で輝度 ``luminance`` の灯火に白い光(光幕・霧の大気光)W を足したとき、色度の距離
    |(c L + W·1)/|c L + W·1| − c/|c||(balltrack.ball_detect の chroma と同じ量)が ``tol`` に達する W* [cd/m²]。

    距離は W に単調に増える(W → ∞ で灰色 (1,1,1)/√3 との距離に漸近)。漸近値が tol 以下なら ``inf``(どれだけ白を足しても
    色は読める)。二分法で相対 1e-12。使い道: 逆光の閾値 θ* = √(10 E_glare / W*)(Stiles–Holladay)、霧の中で色が読める距離
    d* = ln(1 + W*/L_h)/β(灯火 c L e^{−βd} + 大気光 L_h (1 − e^{−βd}) の色度は c L + L_h (e^{βd} − 1)·1 と同じ)。"""
    op = "veil_chroma_limit"
    c = np.asarray(color, np.float64).reshape(-1)
    if c.shape != (3,) or np.any(~np.isfinite(c)) or np.any(c < 0) or c.sum() <= 0:
        raise ValueError("%s: color must be 3 finite non-negative numbers (not all 0)" % op)
    L = _positive(luminance, "luminance", op)
    t = _positive(tol, "tol", op)
    ch = c / np.linalg.norm(c)

    def dist(W):
        v = c * L + W
        return float(np.linalg.norm(v / np.linalg.norm(v) - ch))
    if np.linalg.norm(np.ones(3) / math.sqrt(3.0) - ch) <= t:
        return math.inf
    lo, hi = 0.0, L
    while dist(hi) < t:
        hi *= 2.0
    for _ in range(300):
        m = 0.5 * (lo + hi)
        if dist(m) < t:
            lo = m
        else:
            hi = m
        if hi - lo <= 1e-12 * hi:
            break
    return 0.5 * (lo + hi)


# ─────────────────────────────── 見えてから止まれるか ───────────────────────────────────

def sight_stop_speed(sight: float, reaction: float, brake: float, theta: float = 0.0, c_rr: float = 0.0,
                     k: float = 0.0, g: float = 9.80665) -> float:
    """見える距離 ``sight`` の中で止まれる最大の速さ v*: drivelong.stopping_distance_grade(v*) = sight。

    k = 0 では v ρ + v²/(2A) = D の正の根 v* = A (√(ρ² + 2D/A) − ρ)(A = brake + g sin θ + c_rr g cos θ)。
    k > 0 は停止距離が v に単調なので二分法(1e-12)。A ≤ 0(下りで制動が負ける)なら 0。"""
    op = "sight_stop_speed"
    D = _nonneg(sight, "sight", op)
    rho = _nonneg(reaction, "reaction", op)
    b = _nonneg(brake, "brake", op)
    th = _finite(theta, "theta", op)
    crr = _nonneg(c_rr, "c_rr", op)
    kk = _nonneg(k, "k", op)
    A = b + g * math.sin(th) + crr * g * math.cos(th)
    if A <= 0.0 or D == 0.0:
        return 0.0
    if kk == 0.0:
        return A * (math.sqrt(rho * rho + 2.0 * D / A) - rho)

    def dist(v):
        return v * rho + math.log1p(kk * v * v / A) / (2.0 * kk)
    lo, hi = 0.0, A * (math.sqrt(rho * rho + 2.0 * D / A) - rho) * 2.0 + 1.0
    while dist(hi) < D:
        hi *= 2.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if dist(m) < D:
            lo = m
        else:
            hi = m
        if hi - lo < 1e-12:
            break
    return 0.5 * (lo + hi)


# ─────────────────────────────── 描画 ───────────────────────────────────

def env_params(when=None, lat: float = 35.6581, lon: float = 139.7414, *, sun=None, cloud: float = 0.0,
               fog_mor: Optional[float] = None, rain: float = 0.0, headlamps: str = "off", north_yaw: float = 90.0,
               lamp_luminance: float = 10000.0, exposure: Optional[float] = None, max_gain: float = 1.0,
               glare_model: str = "stiles_holladay", fog_layer: float = 100.0, seed: int = 0) -> Dict[str, object]:
    """描画の条件をまとめる(:func:`env_render` に渡す)。

    ``when`` + 緯度経度(既定 = 東京の暦計算室の代表点)から太陽を出す。``sun=(elevation, azimuth)`` で直接与えてもよい。
    ``fog_mor`` = 気象光学距離 [m](None で霧なし)、``rain`` ∈ [0, 1](0 = 乾き。濡れた路面・雨筋の強さ)、
    ``headlamps`` ∈ {"off", "low", "high"}、``exposure`` = 固定の露出(輝度 → 画素値の倍率。None で自動)、
    ``max_gain`` = 自動露出の倍率の上限(暗い夜に雑に明るくしない)。"""
    op = "env_params"
    if sun is None:
        if when is None:
            raise ValueError("%s: give when (+ lat/lon) or sun=(elevation, azimuth)" % op)
        sp = sun_at(when, lat, lon)
        el, az = sp["elevation"], sp["azimuth"]
    else:
        el, az = _finite(sun[0], "sun[0]", op), _finite(sun[1], "sun[1]", op)
    if headlamps not in ("off", "low", "high"):
        raise ValueError("%s: headlamps must be 'off', 'low' or 'high'" % op)
    r = _finite(rain, "rain", op)
    if not 0.0 <= r <= 1.0:
        raise ValueError("%s: rain must be in [0, 1]" % op)
    ill = sun_illuminance(el, cloud)
    beta = 0.0 if fog_mor is None else beta_from_mor(fog_mor)
    # 霧の層(厚さ fog_layer)を斜めに通る直達は e^{−β H / sin h} で弱まる(仮定: 一様な層)
    if beta > 0 and el > 0:
        ill["direct_normal"] *= math.exp(-beta * _positive(fog_layer, "fog_layer", op) / max(math.sin(math.radians(el)), 1e-3))
    return {"sun_elevation": el, "sun_azimuth": az, "sun_dir": sun_vector(el, az, north_yaw),
            "direct_normal": ill["direct_normal"], "diffuse": ill["diffuse"], "cloud": float(cloud), "beta": beta,
            "fog_mor": fog_mor, "rain": r, "headlamps": headlamps, "lamp_luminance": _positive(lamp_luminance, "lamp_luminance", op),
            "exposure": None if exposure is None else _positive(exposure, "exposure", op),
            "max_gain": _positive(max_gain, "max_gain", op), "glare_model": glare_model, "seed": int(seed)}


def _emissive_faces(world) -> np.ndarray:
    """点いている灯火の面(信号機の lamp_faces のうち state の色)と、world["face_emission"](任意)の面。"""
    em = np.zeros(len(world["F"]), bool)
    for obj in world["objects"]:
        lf = obj.get("lamp_faces")
        if lf and obj.get("state") in lf:
            f0, f1 = lf[obj["state"]]
            em[f0:f1] = True
    extra = world.get("face_emission")
    if extra is not None:
        em |= np.asarray(extra, bool)
    return em


def _pixel_rays(pose, K, W, H):
    """各画素の視線(世界系の単位ベクトル (H,W,3))とカメラの位置。"""
    R = np.asarray(pose, np.float64)[:3, :3]
    t = np.asarray(pose, np.float64)[:3, 3]
    cols, rows = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
    x = (cols - K[0, 2]) / K[0, 0]
    y = (K[1, 2] - rows) / K[1, 1]
    dc = np.stack([x, y, -np.ones_like(x)], axis=-1)
    dw = dc @ R                                          # R^T d(行ベクトルなので d @ R)
    dw /= np.linalg.norm(dw, axis=-1, keepdims=True)
    eye = -R.T @ t
    return dw, eye


def _shadow_map(V, F, sun_dir, bounds, res: int = 1024):
    """太陽から見た深度画像(ほぼ平行投影: 遠くから狭い画角で撮る)。返り値 = (pose, K, depth, res)。"""
    import render3d
    lo, hi = bounds
    c = 0.5 * (lo + hi)
    rad = 0.5 * float(np.linalg.norm(hi - lo)) + 1.0
    dist = 4000.0
    eye = c + sun_dir * dist
    up = (0.0, 0.0, 1.0) if abs(sun_dir[2]) < 0.99 else (0.0, 1.0, 0.0)
    pose = render3d.look_at(eye, c, up)
    fov = 2.0 * math.degrees(math.atan(rad / dist))
    K = render3d.intrinsics_from_fov(fov, res, res)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=res, height=res)
    return pose, K, np.asarray(out["depth"], np.float64), res


def _headlamp_intensity(mode: str, h_deg, v_deg):
    """前照灯 1 灯の光度 [cd](仮定の配光)。h = 左右の角、v = 上下の角(上が +)。"""
    if mode == "high":
        return 60000.0 * np.exp(-(h_deg / 9.0) ** 2 - (v_deg / 4.0) ** 2)
    base = 15000.0 * np.exp(-(h_deg / 14.0) ** 2 - ((v_deg + 1.2) / 2.0) ** 2)
    return np.where(v_deg > -0.57, base * 0.03, base)            # すれ違い: 水平の少し下で上を切る(遮光)


def tone_map(radiance, exposure: float):
    """HDR カメラの色を保つ階調の圧縮: m = 各画素の最大チャンネル × exposure、表示 = 輝度 × exposure × (1 + m/4)/(1 + m)
    —— m ≪ 1 では線形、明るい所は 1 に漸近(色の比 = 色度は変えない。飽和で灯火が白くならない、仮定: 車載の HDR カメラ)。"""
    op = "tone_map"
    k = _positive(exposure, "exposure", op)
    r = np.asarray(radiance, np.float64)
    if r.ndim < 1 or r.shape[-1] != 3:
        raise ValueError("%s: radiance must be (..., 3)" % op)
    m = np.max(r, axis=-1, keepdims=True) * k
    scale = k * (1.0 + m / 4.0) / (1.0 + m)
    out = r * scale
    mx = np.max(out, axis=-1, keepdims=True)
    return np.where(mx > 1.0, out / np.maximum(mx, 1e-300), out)


def env_render(world: dict, pose, K, width: int = 640, height: int = 400, env: Optional[dict] = None, *,
               ego=None, ego_pose=None, shadows: bool = True, shadow_cache: Optional[dict] = None,
               shadow_res: int = 1024) -> Dict[str, np.ndarray]:
    """太陽・空・影・灯火・前照灯・霧・雨・まぶしさを物理の単位で描く。

    Returns
    -------
    dict : ``color``(カメラの線形 RGB [0,1]、:func:`tone_map` で圧縮 —— 画像処理はこれを読む)、``display``(sRGB に符号化した
    表示用、図だけに使う)、``radiance``(RGB の輝度 cd/m²、線形)、``depth``・``label``・
    ``face``(driveworld.world_camera と同じ)、``shadow``(bool、太陽の影の画素)、``exposure``(使った倍率)、
    ``veil``(光幕輝度 cd/m² (H,W))、``illuminance``(面の照度 lx (H,W))。

    ``ego_pose=(x, y, yaw)`` = 前照灯を付ける自車の姿勢(前端 2.25 m・左右 ±0.6 m・高さ 0.65 m に 2 灯)。
    ``shadow_cache`` に dict を渡すと太陽のシャドウマップを使い回す(太陽と世界が変わらない間)。"""
    import render3d
    op = "env_render"
    if env is None:
        raise ValueError("%s: env is required (use env_params)" % op)
    W, H = int(width), int(height)
    K = np.asarray(K, np.float64)
    pose = np.asarray(pose, np.float64)
    V, F, C, Lb = world["V"], world["F"], world["face_color"], world["face_label"]
    em = _emissive_faces(world)
    if ego is not None:
        Ve, Fe, Ce = ego
        F = np.vstack([F, np.asarray(Fe, np.int64) + len(V)])
        V = np.vstack([V, np.asarray(Ve, np.float64)])
        C = np.vstack([C, np.asarray(Ce, np.float64)])
        Lb = np.concatenate([Lb, np.full(len(Fe), 2, np.int64)])
        em = np.concatenate([em, np.zeros(len(Fe), bool)])
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=W, height=H, attributes=True)
    face = np.array(out["face"])
    depth = np.array(out["depth"], np.float64)
    R = pose[:3, :3]
    n_w = np.asarray(out["normals"], np.float64) @ R                 # カメラ系 → 世界系
    rays, eye = _pixel_rays(pose, K, W, H)
    # render3d は頂点の 1 つでもカメラの後ろにある三角形を落とす → 足元の大きな地面の三角形が抜けて空になる。
    # 地面(world["objects"] の "ground" = z = 0 の平面)は解析的に交わりを取って埋める。
    g_obj = [o for o in world["objects"] if o.get("name") == "ground"]
    if g_obj:
        gf0, gf1 = g_obj[0]["faces"]
        gv = world["V"][world["F"][gf0:gf1]].reshape(-1, 3)
        gx0, gy0 = gv[:, 0].min(), gv[:, 1].min()
        gx1, gy1 = gv[:, 0].max(), gv[:, 1].max()
        down = (face < 0) & (rays[..., 2] < -1e-9)
        tg = np.where(down, -eye[2] / np.where(down, rays[..., 2], -1.0), np.inf)
        Pg = eye + rays * np.where(np.isfinite(tg), tg, 0.0)[..., None]
        fill = down & (Pg[..., 0] >= gx0) & (Pg[..., 0] <= gx1) & (Pg[..., 1] >= gy0) & (Pg[..., 1] <= gy1)
        face[fill] = gf0
        cz_ = -(rays @ R.T)[..., 2]
        depth[fill] = (tg * cz_)[fill]
        n_w[fill] = np.array([0.0, 0.0, 1.0])
    hit = face >= 0
    # 視線と逆向きの法線に揃える(両面)
    flip = np.sum(n_w * rays, axis=-1) > 0
    n_w[flip] *= -1.0
    # 画素の世界の点(カメラの −Z 方向の深度 → 視線の長さ = depth / cos)
    cz = -(rays @ R.T)[..., 2]
    rng = np.where(hit, depth / np.maximum(cz, 1e-9), np.inf)
    P = eye + rays * np.where(hit, rng, 0.0)[..., None]
    s = np.asarray(env["sun_dir"], np.float64)
    E_dn, E_diff = float(env["direct_normal"]), float(env["diffuse"])
    # ---- 影(太陽のシャドウマップ)
    shadow = np.zeros((H, W), bool)
    cos_i = np.clip(n_w @ s, 0.0, None)
    if shadows and E_dn > 0 and s[2] > 0:
        key = (tuple(np.round(s, 9)), V.shape, float(V.sum()), int(shadow_res))
        if shadow_cache is not None and shadow_cache.get("key") == key:
            sp, sK, sd, sres = shadow_cache["map"]
        else:
            lo, hi = V.min(axis=0), V.max(axis=0)
            sp, sK, sd, sres = _shadow_map(V, F, s, (lo, hi), int(shadow_res))
            if shadow_cache is not None:
                shadow_cache["key"] = key
                shadow_cache["map"] = (sp, sK, sd, sres)
        Pc = P[hit] @ sp[:3, :3].T + sp[:3, 3]
        dz = -Pc[:, 2]
        cc = np.rint(sK[0, 0] * Pc[:, 0] / dz + sK[0, 2]).astype(np.int64)
        rr = np.rint(sK[1, 2] - sK[1, 1] * Pc[:, 1] / dz).astype(np.int64)
        inside = (cc >= 0) & (cc < sres) & (rr >= 0) & (rr < sres)
        occl = np.zeros(len(dz), bool)
        dmap = sd[np.clip(rr, 0, sres - 1), np.clip(cc, 0, sres - 1)]
        texel = 2.0 * 4000.0 / sK[0, 0]                                  # シャドウマップ 1 画素の幅 [m]
        # 傾きに比例する偏り(slope-scaled bias): 太陽に対して寝た面ほど、1 画素の中で深度が tan(入射角) 倍変わる
        ci = np.clip(cos_i[hit], 0.05, 1.0)
        bias = 0.05 + texel * (1.0 + np.sqrt(1.0 - ci * ci) / ci)
        occl[inside] = np.isfinite(dmap[inside]) & (dmap[inside] < dz[inside] - bias[inside])
        shadow[hit] = occl
    E = E_diff * (0.5 + 0.5 * np.clip(n_w[..., 2], -1, 1)) + E_dn * cos_i * (~shadow)   # 散乱は空の見える割合(上向き面 1、壁 0.5)
    # ---- 前照灯
    hl = env.get("headlamps", "off")
    if hl != "off" and ego_pose is not None:
        x0, y0, yaw = (float(v) for v in ego_pose)
        cy, sy = math.cos(yaw), math.sin(yaw)
        for side in (-0.6, 0.6):
            L0 = np.array([x0 + 2.25 * cy - side * sy, y0 + 2.25 * sy + side * cy, 0.65])
            dv = P - L0
            r2 = np.sum(dv * dv, axis=-1)
            r = np.sqrt(np.maximum(r2, 1e-9))
            u = dv / r[..., None]
            fwd = u[..., 0] * cy + u[..., 1] * sy
            lat = -u[..., 0] * sy + u[..., 1] * cy
            h_deg = np.degrees(np.arctan2(lat, np.maximum(fwd, 1e-9)))
            v_deg = np.degrees(np.arcsin(np.clip(u[..., 2], -1, 1)))
            I = np.where(fwd > 0, _headlamp_intensity(hl, h_deg, v_deg), 0.0)
            inc = np.clip(-np.sum(n_w * u, axis=-1), 0.0, None)
            E = E + np.where(hit, I * inc / np.maximum(r2, 1e-6), 0.0)
    albedo = np.zeros((H, W, 3))
    albedo[hit] = C[face[hit]]
    rain = float(env.get("rain", 0.0))
    if rain > 0:
        wet = hit & (Lb[np.where(hit, face, 0)] == 0) if Lb.max() >= 0 else hit   # 路面(ラベル 0)を暗く
        albedo[wet] *= (1.0 - 0.4 * rain)
    rad = albedo * (E / math.pi)[..., None]
    emis = hit & em[np.where(hit, face, 0)]
    Llamp = float(env["lamp_luminance"])
    rad[emis] = C[face[emis]] * Llamp
    # ---- 空(地平線は明るく、天頂は青い)
    sky_hit = ~hit
    # 地平線の空の輝度 L_h = 2 E_diff/π(晴天の地平線は天頂より明るい; 係数は仮定)、天頂へ 0.5 倍まで下がる
    L_h = 2.0 * E_diff / math.pi if E_diff > 0 else 0.0
    elev_ray = np.clip(rays[..., 2], 0.0, 1.0)
    sky_col = np.array([0.62, 0.75, 0.92]) if env.get("cloud", 0.0) < 0.5 else np.array([0.80, 0.82, 0.85])
    sky = (L_h * (1.0 - 0.5 * np.sqrt(elev_ray)))[..., None] * (sky_col / sky_col.max())
    rad[sky_hit] = sky[sky_hit]
    # 太陽の円盤(視半径 0.267°)
    cos_sun = rays @ s
    disc = sky_hit & (cos_sun > math.cos(math.radians(0.267)))
    if E_dn > 0 and s[2] > 0:
        L_disc = E_dn / (math.pi * math.radians(0.267) ** 2)
        rad[disc] = np.array([1.0, 0.97, 0.9]) * L_disc
    # ---- 霧(Koschmieder、距離は視線の長さ)
    beta = float(env.get("beta", 0.0))
    if beta > 0:
        t = np.where(hit, np.exp(-beta * np.where(hit, rng, 0.0)), 0.0)
        airlight = L_h * np.ones(3)
        rad = rad * t[..., None] + airlight * (1.0 - t)[..., None]
    # ---- 雨: 路面に映る灯火(路面 z = 0 を鏡にした灯火の鏡像を投影)+ 雨筋
    if rain > 0:
        rng_ = np.random.default_rng(int(env.get("seed", 0)))
        # 灯火ごと(点いている面のまとまり)に 1 つの鏡像
        groups = []
        for obj in world["objects"]:
            lf = obj.get("lamp_faces")
            if lf and obj.get("state") in lf:
                groups.append(lf[obj["state"]])
        lamp_f = np.array([g0 for g0, _ in groups], np.int64)
        if len(lamp_f):
            cent = np.array([V[F[g0:g1]].reshape(-1, 3).mean(axis=0) for g0, g1 in groups])
            mir = cent * np.array([1.0, 1.0, -1.0])
            Pc = mir @ R.T + pose[:3, 3]
            dz = -Pc[:, 2]
            ok = dz > 0.5
            col = np.where(ok, K[0, 0] * Pc[:, 0] / np.where(ok, dz, 1) + K[0, 2], -1e9)
            row = np.where(ok, K[1, 2] - K[1, 1] * Pc[:, 1] / np.where(ok, dz, 1), -1e9)
            refl = 0.25 * rain * Llamp
            road_px = hit & (Lb[np.where(hit, face, 0)] == 0)
            for c_, r_, f_ in zip(col[ok], row[ok], lamp_f[ok]):
                # 濡れた路面の鏡像は縦に伸びる(路面の細かい凹凸で縦にぼける —— 形は仮定、位置は鏡の幾何で厳密)
                c0_, c1_ = max(0, int(c_) - 6), min(W, int(c_) + 7)
                r0_, r1_ = max(0, int(r_) - 30), min(H, int(r_) + 31)
                if c0_ >= c1_ or r0_ >= r1_:
                    continue
                yy, xx = np.mgrid[r0_:r1_, c0_:c1_]
                g = np.exp(-0.5 * ((xx - c_) / 1.5) ** 2 - 0.5 * ((yy - r_) / 8.0) ** 2)
                g = np.where(road_px[r0_:r1_, c0_:c1_], g, 0.0)
                rad[r0_:r1_, c0_:c1_] += (refl * C[f_])[None, None, :] * g[..., None]
        n_str = int(600 * rain * (W * H) / (640 * 400))
        streak = np.zeros((H, W))
        x0 = rng_.uniform(0, W, n_str)
        y0 = rng_.uniform(0, H, n_str)
        ln = rng_.uniform(8, 20, n_str)
        kk = np.arange(20)
        yy_ = (y0[:, None] + kk[None, :]).astype(np.int64)
        xx_ = (x0[:, None] + 0.15 * kk[None, :]).astype(np.int64)
        okk = (kk[None, :] < ln[:, None]) & (yy_ >= 0) & (yy_ < H) & (xx_ >= 0) & (xx_ < W)
        np.add.at(streak, (yy_[okk], xx_[okk]), 0.25)
        rad = rad * (1 - np.clip(streak, 0, 0.6))[..., None] + (np.clip(streak, 0, 0.6) * (L_h * 1.3 + 1e-3))[..., None]
    # ---- まぶしさ(光幕): 太陽が空にある間、視線との角 θ で L_v = 10 E_glare / θ²
    veil = np.zeros((H, W))
    if E_dn > 0 and s[2] > 0:
        th = np.degrees(np.arccos(np.clip(cos_sun, -1, 1)))
        th = np.maximum(th, 0.5)
        veil = np.where(th < 90.0, veiling_luminance(E_dn, th, model=env.get("glare_model", "stiles_holladay")), 0.0)
        rad = rad + veil[..., None]
    lum = rad @ np.array([0.2126, 0.7152, 0.0722])
    if env.get("exposure") is not None:
        k_exp = float(env["exposure"])
    else:
        k_exp = min(0.3 / max(float(np.median(lum)), 1e-9), float(env["max_gain"]))
    color = tone_map(rad, k_exp)
    label = np.full((H, W), -1, np.int64)
    label[hit] = Lb[face[hit]]
    return {"color": color, "display": np.where(color <= 0.0031308, 12.92 * color, 1.055 * np.power(np.maximum(color, 0.0031308), 1 / 2.4) - 0.055),
            "radiance": rad, "depth": depth, "label": label, "face": face, "shadow": shadow,
            "exposure": k_exp, "veil": veil, "illuminance": np.where(hit, E, 0.0), "range": rng}
