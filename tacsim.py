# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacsim — 視触覚センサ(弾性膜 + カメラ、retrographic sensing)の合成と逆算を、接触力学の閉形式で門にする(2026-10-04)。

物理シミュ × Fullseye 系列の第 2 弾。真値は外から来る —— **弾性接触の閉形式**と**フォトメトリックステレオの閉形式**:
  * Hertz 球接触(K. L. Johnson, *Contact Mechanics*, CUP 1985, DOI 10.1017/CBO9781139171731, §3・§4.2。教科書、標準の結果):
      a³ = 3FR/(4E*)、δ = a²/R、p(r) = p0 √(1 − r²/a²)、p0 = 3F/(2πa²) = 2E*a/(πR)、F = (4/3) E* √R δ^{3/2}。
    半空間の表面変位(ゲル膜がへこむ形 = カメラが撮る高さ場):
      内側 r ≤ a: ū_z(r) = δ − r²/(2R)(球面にならう)
      外側 r > a: ū_z(r) = (1/πR)[(2a² − r²) arcsin(a/r) + a r √(1 − a²/r²)] (Johnson 式 3.42a)
      r = a で値 δ/2・傾き −a/R ともに連続。外側の傾きは **導出**: dū_z/dr = (2/πR)[a √(1 − a²/r²) − r arcsin(a/r)]。
  * Hertz 線接触(円柱、Johnson §4.2): b² = 4(F/L)R/(πE*)、p0 = 2(F/L)/(πb)。
  * フォトメトリックステレオ(R. J. Woodham, Opt. Eng. 19(1), 139-144, 1980, DOI 10.1117/12.7972479): 既知 3 光源 I = L N → N = L⁻¹ I。
  * 法線 → 高さ(R. T. Frankot, R. Chellappa, IEEE TPAMI 10(4), 439-451, 1988, DOI 10.1109/34.3909): FFT の最小二乗積分。
  * 弾性膜 + 色つき多方向照明で 1 枚の画像から法線を読む原理(M. K. Johnson, E. H. Adelson, "Retrographic sensing for the
    measurement of surface texture and shape", CVPR 2009, DOI 10.1109/CVPR.2009.5206534)。
  * 直近の大変形解(T. Mu ほか, "A scaling law for large-deformation contact in soft materials", arXiv:2509.18581, 2025)は
    本モジュールの小変形 Hertz の先 —— :mod:`tacdome` に実装した(式 (3) の 1 次の係数は活字と違う、tacdome の docstring)。

被験者(第 2 実装 = Fullseye の既存 op): :mod:`photometric` の ``photometric_stereo`` / ``integrate_normals`` / ``surface_normals`` /
``render_lambertian`` / ``normals_to_gradients``、:func:`measure.fit_circle`。``tac_*``(backends_tactile、単画像の擬似参照)は別物。

op(台帳 ``tacsim``、opsdrive、全部 numpy):
  閉形式: :func:`combined_modulus` / :func:`hertz_sphere` / :func:`hertz_force` / :func:`hertz_cylinder` / :func:`hertz_surface_uz` /
  :func:`hertz_pressure`。合成: :func:`membrane_indent_sphere`(Hertz の高さ場 + 解析法線)/ :func:`membrane_indent_shape`
  (球・円柱・直線エッジ・スタンプの幾何学的な押し込み h = −max(0, d − z_ind)、弾性の裾なし)/ :func:`membrane_lights` /
  :func:`membrane_render_rgb`(3 色照明 → RGB)。逆算: :func:`membrane_recover`(RGB → 法線 → 高さ)/
  :func:`contact_radius_ring`(方位角ごとの |∇h| 副画素ピーク → 円、模型なし)/ :func:`contact_radius_fit`(法線の半径スロープ分布に
  Hertz のスロープ模型を 1 パラメータ a で当てる)/ :func:`membrane_delta_from_normals`(半径スロープの 1D 積分 + Boussinesq 遠方場の裾)。

試作で踏んだこと(正直に): (1) |∇h| のしきい値リングは Hertz の a より 9 % 内側に出た —— 内側は r/R で緩やかに増え外側は
√ で急に落ちる非対称なカスプなので、帯の重心が内側へ寄る。方位角ごとの副画素ピークで直す。(2) FFT 積分は深い局所のへこみの
振幅を減衰させ、有限窓では遠方場 ū_z ~ F/(πE*r) の裾(r = 4.5 mm で δ の 8 %)が 0 でないので、δ を高さの差で読むと過小になる。
スロープを使う経路(contact_radius_fit / membrane_delta_from_normals)は積分を通らない。(3) 平坦域は方位対称で光源仰角の較正ずれに
鈍感(誤差 0)で、ずれは斜面にだけ出る。

規約: 長さ m、力 N、角 rad(引数名に _deg が付くものだけ度)。画素ピッチ pitch [m/px]。高さ h はへこむ向きが負(h = −ū_z)。
法線は :mod:`photometric` と同じ (−∂h/∂x, −∂h/∂y, 1)/|·|、x = 列・y = 行。E* は複合弾性率 1/E* = (1−ν1²)/E1 + (1−ν2²)/E2。
"""
from __future__ import annotations

import math

import numpy as np

import measure as _fsmeasure
import photometric as _ph

__all__ = [
    "combined_modulus", "hertz_sphere", "hertz_force", "hertz_cylinder", "hertz_surface_uz", "hertz_pressure",
    "membrane_indent_sphere", "membrane_indent_shape", "membrane_lights", "membrane_render_rgb",
    "membrane_recover", "contact_radius_ring", "contact_radius_fit", "contact_radius_fit_pixelwise", "membrane_delta_from_normals",
    "SHAPES",
]

#: :func:`membrane_indent_shape` が作れる押し込み形状
SHAPES = ("sphere", "cylinder", "edge", "stamp")


# ----------------------------------------------------------------------------------------------------------------------
# 閉形式(外部真値)
def combined_modulus(E1: float, nu1: float, E2: float | None = None, nu2: float = 0.0) -> float:
    """複合弾性率 E*: 1/E* = (1 − ν1²)/E1 + (1 − ν2²)/E2(Johnson 1985 式 4.9)。``E2=None`` は剛体の押し込み子(第 2 項 0)。

    **Raises** ``ValueError``: E ≤ 0、|ν| ≥ 1(Poisson 比は (−1, 0.5] が物理的だが上限は見ない)。"""
    E1, nu1 = float(E1), float(nu1)
    if not (E1 > 0.0) or not (abs(nu1) < 1.0):
        raise ValueError("combined_modulus: need E1 > 0 and |nu1| < 1, got E1=%r nu1=%r" % (E1, nu1))
    inv = (1.0 - nu1 * nu1) / E1
    if E2 is not None:
        E2, nu2 = float(E2), float(nu2)
        if not (E2 > 0.0) or not (abs(nu2) < 1.0):
            raise ValueError("combined_modulus: need E2 > 0 and |nu2| < 1, got E2=%r nu2=%r" % (E2, nu2))
        inv += (1.0 - nu2 * nu2) / E2
    return 1.0 / inv


def hertz_sphere(F: float, R: float, Estar: float) -> dict:
    """剛体球(半径 R)を弾性半空間(複合弾性率 E*)に荷重 F で押し込む Hertz 接触の閉形式(Johnson 1985 §3)。

    返り: ``a``(接触半径 = (3FR/4E*)^{1/3})、``delta``(押し込み = a²/R)、``p0``(最大圧 = 3F/(2πa²))、``pm``(平均圧 = F/(πa²)
    = (2/3)p0)と入力 ``F``・``R``・``Estar``。**Raises** ``ValueError``: いずれかが ≤ 0 または非有限。"""
    F, R, Estar = float(F), float(R), float(Estar)
    if not (F > 0.0 and R > 0.0 and Estar > 0.0) or not all(math.isfinite(v) for v in (F, R, Estar)):
        raise ValueError("hertz_sphere: F, R, Estar must be finite and > 0, got %r %r %r" % (F, R, Estar))
    a = (3.0 * F * R / (4.0 * Estar)) ** (1.0 / 3.0)
    return {"a": a, "delta": a * a / R, "p0": 3.0 * F / (2.0 * math.pi * a * a), "pm": F / (math.pi * a * a),
            "F": F, "R": R, "Estar": Estar}


def hertz_force(R: float, Estar: float, a: float | None = None, delta: float | None = None) -> float:
    """Hertz の逆算: 接触半径 a か押し込み δ のどちらか一方から荷重 F。F = 4E*a³/(3R) = (4/3) E* √R δ^{3/2}。

    **Raises** ``ValueError``: a と δ の両方(または両方なし)、値が ≤ 0。"""
    R, Estar = float(R), float(Estar)
    if not (R > 0.0 and Estar > 0.0):
        raise ValueError("hertz_force: R and Estar must be > 0")
    if (a is None) == (delta is None):
        raise ValueError("hertz_force: give exactly one of a= or delta=")
    if a is not None:
        a = float(a)
        if not (a > 0.0):
            raise ValueError("hertz_force: a must be > 0, got %r" % a)
        return 4.0 * Estar * a ** 3 / (3.0 * R)
    delta = float(delta)
    if not (delta > 0.0):
        raise ValueError("hertz_force: delta must be > 0, got %r" % delta)
    return (4.0 / 3.0) * Estar * math.sqrt(R) * delta ** 1.5


def hertz_cylinder(F_per_L: float, R: float, Estar: float) -> dict:
    """円柱(半径 R)を弾性半空間に線荷重 F/L で押す線接触(Johnson 1985 §4.2): 接触半幅 b = √(4(F/L)R/(πE*))、p0 = 2(F/L)/(πb)。

    返り: ``b``、``p0``、``pm`` = (F/L)/(2b) = (π/4)p0、入力。2-D の押し込み δ は対数的で参照点に依存するため返さない。
    **Raises** ``ValueError``: ≤ 0。"""
    P, R, Estar = float(F_per_L), float(R), float(Estar)
    if not (P > 0.0 and R > 0.0 and Estar > 0.0):
        raise ValueError("hertz_cylinder: F_per_L, R, Estar must be > 0")
    b = math.sqrt(4.0 * P * R / (math.pi * Estar))
    return {"b": b, "p0": 2.0 * P / (math.pi * b), "pm": P / (2.0 * b), "F_per_L": P, "R": R, "Estar": Estar}


def hertz_surface_uz(r, a: float, delta: float, R: float) -> np.ndarray:
    """Hertz 球接触の半空間表面の法線変位 ū_z(r)(沈む量 ≥ 0、r と同じ形の配列)。

    内側 r ≤ a: δ − r²/(2R)。外側: (1/πR)[(2a² − r²) arcsin(a/r) + a r √(1 − a²/r²)] (Johnson 式 3.42a)。r = a で δ/2 に連続。
    **Raises** ``ValueError``: a, δ, R ≤ 0、a² と Rδ が 1 % 以上食い違う(Hertz でない組)。"""
    a, delta, R = float(a), float(delta), float(R)
    if not (a > 0.0 and delta > 0.0 and R > 0.0):
        raise ValueError("hertz_surface_uz: a, delta, R must be > 0")
    if abs(a * a - R * delta) > 0.01 * R * delta:
        raise ValueError("hertz_surface_uz: a² = %.3e but R·δ = %.3e (not a Hertz pair)" % (a * a, R * delta))
    r = np.abs(np.asarray(r, np.float64))
    uz = np.empty_like(r)
    inside = r <= a
    uz[inside] = delta - r[inside] ** 2 / (2.0 * R)
    ro = r[~inside]
    with np.errstate(invalid="ignore", divide="ignore"):
        s = a / ro
        uz[~inside] = ((2.0 * a * a - ro * ro) * np.arcsin(s) + a * ro * np.sqrt(np.maximum(0.0, 1.0 - s * s))) / (math.pi * R)
    return uz


def _hertz_slope(r, a: float, R: float) -> np.ndarray:
    """Hertz のへこみ h = −ū_z の半径方向の傾き dh/dr ≥ 0: 内側 r/R、外側 (2/πR)[r arcsin(a/r) − a √(1 − a²/r²)] (導出)。"""
    r = np.abs(np.asarray(r, np.float64))
    out = np.empty_like(r)
    inside = r <= a
    out[inside] = r[inside] / R
    ro = r[~inside]
    with np.errstate(invalid="ignore", divide="ignore"):
        s = a / ro
        out[~inside] = (2.0 / (math.pi * R)) * (ro * np.arcsin(s) - a * np.sqrt(np.maximum(0.0, 1.0 - s * s)))
    return out


def hertz_pressure(r, a: float, p0: float) -> np.ndarray:
    """Hertz の接触圧 p(r) = p0 √(1 − r²/a²)(r < a)、外は 0。r と同じ形。**Raises** ``ValueError``: a, p0 ≤ 0。"""
    a, p0 = float(a), float(p0)
    if not (a > 0.0 and p0 > 0.0):
        raise ValueError("hertz_pressure: a and p0 must be > 0")
    r = np.abs(np.asarray(r, np.float64))
    out = np.zeros_like(r)
    inside = r < a
    out[inside] = p0 * np.sqrt(np.maximum(0.0, 1.0 - (r[inside] / a) ** 2))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 合成(高さ場 → 法線 → 3 色照明の RGB)
def _grid(n: int, fov: float):
    """n×n の画素中心座標 (X, Y)[m] (中心が原点)、半径 r、画素ピッチ pitch[m/px]。"""
    n = int(n)
    if n < 16:
        raise ValueError("tacsim: n must be >= 16, got %r" % n)
    fov = float(fov)
    if not (fov > 0.0):
        raise ValueError("tacsim: fov must be > 0")
    pitch = fov / n
    c = (np.arange(n) - (n - 1) / 2.0) * pitch
    X, Y = np.meshgrid(c, c)
    return X, Y, np.hypot(X, Y), pitch


def membrane_indent_sphere(hz: dict, n: int = 256, fov: float = 16.0e-3) -> dict:
    """球押し込みのゲル膜の高さ場 h(x, y) = −ū_z(r)[m] (:func:`hertz_sphere` の表から)と解析的な法線。

    ``n`` 画素四方、視野 ``fov`` [m] (画素ピッチ fov/n)。法線は ū_z の半径微分を中心差分(刻み pitch/4)で取り
    (−∂h/∂x, −∂h/∂y, 1)/|·|。返り: ``h``(n, n)、``normals``(n, n, 3)、``pitch``、``X``・``Y``・``r``(n, n)、``contact``(r < a の bool)、
    ``hz``。窓は接触半径の 5 倍以上ないと遠方場の裾で高さの基準が沈む(**Raises** ``ValueError``: fov < 5a、hz に a/delta/R が無い)。"""
    if not isinstance(hz, dict) or not all(k in hz for k in ("a", "delta", "R")):
        raise ValueError("membrane_indent_sphere: hz must be the dict from hertz_sphere()")
    a, delta, R = float(hz["a"]), float(hz["delta"]), float(hz["R"])
    X, Y, r, pitch = _grid(n, fov)
    if float(fov) < 5.0 * a:
        raise ValueError("membrane_indent_sphere: fov=%.4g m is < 5a=%.4g m (window too small)" % (fov, 5.0 * a))
    uz = hertz_surface_uz(r, a, delta, R)
    dr = 0.25 * pitch
    duz = (hertz_surface_uz(r + dr, a, delta, R) - hertz_surface_uz(np.maximum(r - dr, 0.0), a, delta, R)) / (2.0 * dr)
    with np.errstate(invalid="ignore", divide="ignore"):
        inv_r = np.where(r > 1e-12, 1.0 / np.maximum(r, 1e-15), 0.0)
    hx = -duz * X * inv_r
    hy = -duz * Y * inv_r
    nrm = np.stack([-hx, -hy, np.ones_like(hx)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return {"h": -uz, "normals": nrm, "pitch": pitch, "X": X, "Y": Y, "r": r, "contact": r < a, "hz": dict(hz)}


def _box_dist(X, Y, cx, cy, hx, hy):
    """軸平行な箱 [cx±hx]×[cy±hy] の外側距離(内側は 0)。"""
    dx = np.maximum(np.abs(X - cx) - hx, 0.0)
    dy = np.maximum(np.abs(Y - cy) - hy, 0.0)
    return np.hypot(dx, dy)


def membrane_indent_shape(shape: str, depth: float, n: int = 128, fov: float = 6.0e-3, R: float = 3.0e-3,
                          edge_deg: float = 30.0, tip_radius: float = 0.3e-3, size: float = 2.0e-3) -> dict:
    """既知形状の剛体を深さ ``depth`` だけ押し込んだゲル膜の高さ場を**幾何学的な追従**で作る: h = −max(0, depth − z_ind(x, y))。

    弾性の裾(Hertz の外側解)は入れない —— 球は :func:`membrane_indent_sphere` が Hertz で正確に作るので、こちらは
    円柱・直線エッジ・スタンプのように閉形式の裾が無い形を**同じ流儀で**並べるための道具。``shape``:
    ``"sphere"``(半径 R の球冠 z = R − √(R² − r²))、``"cylinder"``(軸は y、z = R − √(R² − x²))、``"edge"``(直線エッジ:
    先端半径 tip_radius で丸めた角 edge_deg のくさび z = (√(x² + ρ²) − ρ) tan α)、``"stamp"``(一辺 size の "F" 字の平らなスタンプ、
    外側は距離 × tan 60° で立ち上がる)。法線は :func:`photometric.surface_normals`(h/pitch)で取る(第 2 実装)。
    返り: ``h``・``normals``・``pitch``・``X``・``Y``・``contact``(z_ind < depth)・``z_ind``。
    **Raises** ``ValueError``: 未知の shape、depth ≤ 0、球・円柱で depth ≥ R。"""
    shape = str(shape)
    if shape not in SHAPES:
        raise ValueError("membrane_indent_shape: shape must be one of %s, got %r" % (SHAPES, shape))
    depth, R = float(depth), float(R)
    if not (depth > 0.0):
        raise ValueError("membrane_indent_shape: depth must be > 0")
    X, Y, r, pitch = _grid(n, fov)
    if shape in ("sphere", "cylinder"):
        if not (0.0 < depth < R):
            raise ValueError("membrane_indent_shape: need 0 < depth < R for %s" % shape)
        q = r if shape == "sphere" else np.abs(X)
        z_ind = R - np.sqrt(np.maximum(R * R - q * q, 0.0))
        z_ind = np.where(q < R, z_ind, R + (q - R))             # 赤道の外は円柱面で続ける(影響なし)
    elif shape == "edge":
        rho = float(tip_radius)
        if not (rho > 0.0) or not (0.0 < float(edge_deg) < 90.0):
            raise ValueError("membrane_indent_shape: edge needs tip_radius > 0 and 0 < edge_deg < 90")
        z_ind = (np.sqrt(X * X + rho * rho) - rho) * math.tan(math.radians(float(edge_deg)))
    else:                                                           # "stamp": 平らな F 字 + 外側は 60° で立ち上がる
        s = float(size)
        if not (s > 0.0):
            raise ValueError("membrane_indent_shape: stamp needs size > 0")
        w = s / 7.0
        d = np.minimum.reduce([
            _box_dist(X, Y, -s / 2 + w, 0.0, w, s / 2),            # 縦棒
            _box_dist(X, Y, 0.0, -s / 2 + w, s / 2, w),            # 上の横棒(y は下向きが正なので負側が上)
            _box_dist(X, Y, -w, 0.0, s / 2 - 2 * w, w),            # 中の横棒
        ])
        z_ind = d * math.tan(math.radians(60.0))
    h = -np.maximum(0.0, depth - z_ind)
    normals = np.asarray(_ph.surface_normals(h / pitch), np.float64)
    return {"h": h, "normals": normals, "pitch": pitch, "X": X, "Y": Y, "contact": z_ind < depth, "z_ind": z_ind,
            "shape": shape, "depth": depth}


def membrane_lights(elev_deg: float = 55.0, azimuths_deg=(90.0, 210.0, 330.0)) -> np.ndarray:
    """多方向の色つき照明の単位方向ベクトル (N, 3)(行 k が色チャネル k の光源、既定は方位 90/210/330°・仰角 55° の 3 灯)。

    **Raises** ``ValueError``: 仰角が (0°, 90°] の外、光源が 3 灯未満、3 灯が同一平面(rank < 3 でフォトメトリックステレオが解けない)。"""
    e = math.radians(float(elev_deg))
    if not (0.0 < float(elev_deg) <= 90.0):
        raise ValueError("membrane_lights: elev_deg must be in (0, 90], got %r" % elev_deg)
    az = [math.radians(float(v)) for v in azimuths_deg]
    if len(az) < 3:
        raise ValueError("membrane_lights: need >= 3 lights, got %d" % len(az))
    L = np.array([[math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)] for a in az], np.float64)
    if np.linalg.matrix_rank(L) < 3:
        raise ValueError("membrane_lights: light directions are coplanar (rank < 3)")
    return L


def membrane_render_rgb(normals, lights, albedo: float = 1.0, ambient: float = 0.03, noise: float = 0.0, seed: int = 0) -> np.ndarray:
    """法線場 (H, W, 3) + 光源 (3, 3) → 視触覚センサ風の RGB (H, W, 3) float。チャネル k = 光源 k の Lambertian 像
    albedo·(max(N·L_k, 0) + ambient)(:func:`photometric.render_lambertian` を 3 回、第 2 実装)。``noise`` > 0 なら正規乱数を足す。

    **Raises** ``ValueError``: normals が (H, W, 3) でない、lights が (3, 3) でない、noise < 0。"""
    nrm = np.asarray(normals, np.float64)
    L = np.asarray(lights, np.float64)
    if nrm.ndim != 3 or nrm.shape[2] != 3:
        raise ValueError("membrane_render_rgb: normals must be (H, W, 3)")
    if L.shape != (3, 3):
        raise ValueError("membrane_render_rgb: lights must be (3, 3) (one row per colour channel)")
    if float(noise) < 0.0:
        raise ValueError("membrane_render_rgb: noise must be >= 0")
    rgb = np.stack([np.asarray(_ph.render_lambertian(nrm, float(albedo), L[k], ambient=float(ambient)), np.float64)
                    for k in range(3)], axis=-1)
    if float(noise) > 0.0:
        rgb = rgb + np.random.default_rng(int(seed)).normal(0.0, float(noise), rgb.shape)
    return rgb


# ----------------------------------------------------------------------------------------------------------------------
# 逆算
def membrane_recover(rgb, lights, pitch: float, ambient: float = 0.0, albedo: float = 1.0) -> dict:
    """視触覚 RGB (H, W, 3) → 3 チャネルを 3 光源の像として :func:`photometric.photometric_stereo`(lit_only)で法線 →
    :func:`photometric.integrate_normals`(Frankot-Chellappa)で高さ(画素単位 × pitch = m)。

    ``ambient``・``albedo`` は較正値: 像から albedo·ambient を引いてから解く(合成 albedo·(N·L + ambient) の ambient 項を
    Woodham の線形模型は持たないので、引かないと法線が z 側へ寄り、傾きが ambient/sin(仰角) ≈ 3.7 %(0.03/0.82)系統的に
    小さく出る —— 実機の参照フレーム較正に当たる。試作で δ が 3.5 % 低かった原因)。
    返り: ``normals``(H, W, 3)、``albedo``(H, W)、``height``(H, W)[m、平均 0 の相対値]、``pitch``。
    **Raises** ``ValueError``: rgb が (H, W, 3) でない、pitch ≤ 0、ambient < 0。"""
    img = np.asarray(rgb, np.float64)
    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError("membrane_recover: rgb must be (H, W, 3)")
    pitch = float(pitch)
    if not (pitch > 0.0):
        raise ValueError("membrane_recover: pitch must be > 0")
    if float(ambient) < 0.0:
        raise ValueError("membrane_recover: ambient must be >= 0")
    L = np.asarray(lights, np.float64)
    img = np.maximum(img - float(albedo) * float(ambient), 0.0)
    normals, albedo = _ph.photometric_stereo(np.moveaxis(img, -1, 0), L, lit_only=True)
    z_px = _ph.integrate_normals(normals)
    return {"normals": np.asarray(normals, np.float64), "albedo": np.asarray(albedo, np.float64),
            "height": np.asarray(z_px, np.float64) * pitch, "pitch": pitch}


def _indent_centre(h) -> tuple[float, float]:
    """へこみの中心 (cy, cx)[px]: 最深点の半分より深い画素の、深さで重み付けした重心。"""
    h = np.asarray(h, np.float64)
    hmin = float(h.min())
    if not (hmin < 0.0):
        raise ValueError("tacsim: height field has no indentation (min >= 0)")
    w = np.where(h < 0.5 * hmin, -h, 0.0)
    yy, xx = np.mgrid[0:h.shape[0], 0:h.shape[1]]
    s = float(w.sum())
    return float((w * yy).sum() / s), float((w * xx).sum() / s)


def _bilinear(img, y, x):
    """(H, W) 画像を実数座標 (y, x) で双線形補間(外は最寄りの縁)。"""
    H, W = img.shape
    y = np.clip(np.asarray(y, np.float64), 0.0, H - 1.0)
    x = np.clip(np.asarray(x, np.float64), 0.0, W - 1.0)
    y0 = np.clip(np.floor(y).astype(int), 0, H - 2)
    x0 = np.clip(np.floor(x).astype(int), 0, W - 2)
    fy, fx = y - y0, x - x0
    return (img[y0, x0] * (1 - fy) * (1 - fx) + img[y0 + 1, x0] * fy * (1 - fx)
            + img[y0, x0 + 1] * (1 - fy) * fx + img[y0 + 1, x0 + 1] * fy * fx)


def contact_radius_ring(h, pitch: float, n_az: int = 72, step_px: float = 0.25, r_max_px: float | None = None) -> dict:
    """高さ場から接触半径 a を**模型なし**で読む: 接触縁 r = a は半径方向の傾き |∂h/∂r| が最大になる輪(Hertz では内側 r/R で
    増え、外側は √ で急に落ちるカスプ)。方位角 ``n_az`` 本の半径線に沿って |∇h| を ``step_px`` 刻みで双線形補間し、各線の
    ピークを放物線補間で副画素化 → 72 点に :func:`measure.fit_circle`(第 2 実装)と半径の中央値。

    返り: ``a``(中央値 × pitch)[m]、``a_circle``(円当てはめの半径 × pitch)、``r_px``・``cy``・``cx``・``rms_px``(円)、
    ``radii_px``(方位角ごとのピーク半径)、``centre``(重心 (cy, cx))、``bias_px_per_a``(分解能の限界の目安 = −0.7 px / a、
    双線形補間がカスプを約 1 px 平滑するので a が 14 px なら −5 %、21 px なら −3 % 内側に出る —— 実測値、模型なしの代償)。
    しきい値の帯の重心(試作 v1)が 9 % 内側に寄った反省から、帯でなくピーク位置を使い、半径方向の傾きは h の双線形標本の
    1 px スパン差分(np.gradient の 2 px より平滑が少ない)で取る。
    **Raises** ``ValueError``: へこみが無い、pitch ≤ 0。"""
    h = np.asarray(h, np.float64)
    pitch = float(pitch)
    if not (pitch > 0.0):
        raise ValueError("contact_radius_ring: pitch must be > 0")
    cy, cx = _indent_centre(h)
    H, W = h.shape
    rmax = float(r_max_px) if r_max_px is not None else 0.5 * min(cy, cx, H - 1 - cy, W - 1 - cx)
    rs = np.arange(1.0, rmax, float(step_px))
    phis = np.linspace(0.0, 2.0 * math.pi, int(n_az), endpoint=False)
    radii, pts = [], []
    for ph in phis:
        sy, sx = math.sin(ph), math.cos(ph)
        prof = _bilinear(h, cy + (rs + 0.5) * sy, cx + (rs + 0.5) * sx) - _bilinear(h, cy + (rs - 0.5) * sy, cx + (rs - 0.5) * sx)
        k = int(np.argmax(prof))
        rk = rs[k]
        if 0 < k < len(rs) - 1:
            y0, y1, y2 = prof[k - 1], prof[k], prof[k + 1]
            den = y0 - 2.0 * y1 + y2
            if abs(den) > 1e-18:
                rk = rs[k] + 0.5 * (y0 - y2) / den * float(step_px)
        radii.append(rk)
        pts.append((cy + rk * math.sin(ph), cx + rk * math.cos(ph)))
    radii = np.asarray(radii)
    circ = _fsmeasure.fit_circle(np.asarray(pts))
    return {"a": float(np.median(radii)) * pitch, "a_circle": circ["r"] * pitch, "r_px": circ["r"], "cy": circ["cy"],
            "cx": circ["cx"], "rms_px": circ["rms"], "radii_px": radii, "centre": (cy, cx), "bias_px_per_a": -0.7}


def _radial_slope_profile(normals, X, Y, centre_xy, pitch: float):
    """法線 → 勾配 (p, q) = (∂h/∂x, ∂h/∂y)(photometric.normals_to_gradients)→ 中心まわりの半径方向成分を半径ビン(幅 pitch)で平均。
    返り: r_bin(中央)[m]、s̄(r)、個数。"""
    p, q = _ph.normals_to_gradients(normals)
    dx = X - centre_xy[0]
    dy = Y - centre_xy[1]
    r = np.hypot(dx, dy)
    with np.errstate(invalid="ignore", divide="ignore"):
        s_r = np.where(r > 1e-12, (p * dx + q * dy) / np.maximum(r, 1e-15), 0.0)
    rmax = float(min(np.abs(X).max(), np.abs(Y).max()))          # 四隅を除いた円の中まで
    nb = int(rmax / pitch)
    idx = np.clip((r / (rmax / nb)).astype(int), 0, nb)
    prof = np.zeros(nb + 1)
    cnt = np.zeros(nb + 1)
    np.add.at(prof, idx.ravel(), s_r.ravel())
    np.add.at(cnt, idx.ravel(), 1.0)
    prof = prof[:nb]
    cnt = cnt[:nb]
    prof = np.where(cnt > 0, prof / np.maximum(cnt, 1), 0.0)
    r_bin = (np.arange(nb) + 0.5) * (rmax / nb)
    return r_bin, prof, cnt


def contact_radius_fit(normals, X, Y, R: float, pitch: float, centre_xy=None) -> dict:
    """法線場の**半径方向スロープ分布**に Hertz のスロープ模型 dh/dr(r; a) を 1 パラメータ a で当てて接触半径を読む。

    模型: 内側 r/R、外側 (2/πR)[r arcsin(a/r) − a √(1 − a²/r²)] (導出、r = a で a/R に連続)。高さの積分を通らないので
    FFT 積分の振幅減衰・有限窓の遠方場・高さの基準(オフセット)の影響を受けない。a は [0.2, 3] × 粗い初期値の格子で SSE
    (ビンの個数で重み)を最小化し、放物線で副格子に詰める。``centre_xy`` は (x, y)[m]、省略なら法線から高さを積分して重心。
    返り: ``a``、``delta`` = a²/R、``rms``(スロープの残差)、``r``・``slope``・``model``(分布)、``centre_xy``。
    **Raises** ``ValueError``: R, pitch ≤ 0、形が合わない。"""
    nrm = np.asarray(normals, np.float64)
    X = np.asarray(X, np.float64)
    Y = np.asarray(Y, np.float64)
    R, pitch = float(R), float(pitch)
    if not (R > 0.0 and pitch > 0.0):
        raise ValueError("contact_radius_fit: R and pitch must be > 0")
    if nrm.ndim != 3 or nrm.shape[:2] != X.shape or X.shape != Y.shape:
        raise ValueError("contact_radius_fit: normals (H, W, 3) and X, Y (H, W) must agree")
    if centre_xy is None:
        cy, cx = _indent_centre(np.asarray(_ph.integrate_normals(nrm), np.float64))
        centre_xy = (float(_bilinear(X, cy, cx)), float(_bilinear(Y, cy, cx)))
    r_bin, prof, cnt = _radial_slope_profile(nrm, X, Y, centre_xy, pitch)
    w = cnt / max(1.0, float(cnt.max()))
    k0 = int(np.argmax(prof))
    a0 = max(r_bin[k0], 2.0 * pitch)

    def sse(a):
        return float(np.sum(w * (prof - _hertz_slope(r_bin, a, R)) ** 2))

    grid = a0 * np.linspace(0.2, 3.0, 281)
    vals = np.array([sse(a) for a in grid])
    k = int(np.argmin(vals))
    a_best = grid[k]
    if 0 < k < len(grid) - 1:
        y0, y1, y2 = vals[k - 1], vals[k], vals[k + 1]
        den = y0 - 2.0 * y1 + y2
        if den > 1e-30:
            a_best = grid[k] + 0.5 * (y0 - y2) / den * (grid[1] - grid[0])
    model = _hertz_slope(r_bin, a_best, R)
    return {"a": float(a_best), "delta": float(a_best * a_best / R), "rms": float(np.sqrt(np.sum(w * (prof - model) ** 2) / w.sum())),
            "r": r_bin, "slope": prof, "model": model, "centre_xy": centre_xy}


def contact_radius_fit_pixelwise(normals, X, Y, R: float, a0: float, centre_xy=(0.0, 0.0), r_max_over_a: float = 2.5,
                                 excl_px: float = 1.5) -> dict:
    """接触半径を**画素ごと**の半径方向スロープに Hertz のスロープ模型 dh/dr(r; a) を連続の a で当てて読む(:func:`contact_radius_fit`
    のビンを使わない版。``a0`` はその粗い値)。

    :func:`contact_radius_fit` は半径ビン(幅 = 画素ピッチ)の平均に当てるので、a が画素ピッチをまたぐたびに偏りの符号が変わる
    (P = 3.5 / 4.0 / 4.5 N で −0.04 / +0.31 / −0.02 %)。P の値そのものは 0.3 % で十分でも、2 枚の差(把持の 2 本指の F_x = P_L − P_R)
    では P̂ の**傾き** dP̂/dP が効き、ビン版は傾きを 40 % 狂わせた(pegtactile の PoC で測った)。ここでは r < ``r_max_over_a``·a0 の
    画素をそのまま使い、縁 r ≈ a0 の ±``excl_px`` 画素は捨てる —— スロープは r = a で微分が不連続(外側に平方根の尖り)で、
    画素と縁の位置関係で値が揺れ、残すと a が画素ピッチの周期で揺れる。SSE(a) を黄金分割(初期区間 [0.8, 1.2]·a0、40 回)で最小化。
    ``centre_xy`` は既知の中心 (x, y)、単位 m。返り ``a``・``delta`` = a²/R・``rms``(スロープの残差)・``n``(使った画素数)。
    **Raises** ``ValueError``: R, a0 ≤ 0、形が合わない、使える画素が 16 未満。"""
    nrm = np.asarray(normals, np.float64)
    X = np.asarray(X, np.float64)
    Y = np.asarray(Y, np.float64)
    R, a0 = float(R), float(a0)
    if not (R > 0.0 and a0 > 0.0):
        raise ValueError("contact_radius_fit_pixelwise: R and a0 must be > 0")
    if nrm.ndim != 3 or nrm.shape[:2] != X.shape or X.shape != Y.shape or X.shape[1] < 2:
        raise ValueError("contact_radius_fit_pixelwise: normals (H, W, 3) and X, Y (H, W) must agree")
    p, q = _ph.normals_to_gradients(nrm)
    dx = X - float(centre_xy[0])
    dy = Y - float(centre_xy[1])
    r = np.hypot(dx, dy)
    pitch = float(abs(X[0, 1] - X[0, 0]))
    sel = (r > 1e-12) & (r < float(r_max_over_a) * a0) & (np.abs(r - a0) > float(excl_px) * pitch)
    if int(sel.sum()) < 16:
        raise ValueError("contact_radius_fit_pixelwise: only %d usable pixels (need >= 16)" % int(sel.sum()))
    s_r = (p[sel] * dx[sel] + q[sel] * dy[sel]) / r[sel]
    rs = r[sel]

    def sse(a):
        return float(np.sum((s_r - _hertz_slope(rs, a, R)) ** 2))

    lo, hi = 0.8 * a0, 1.2 * a0
    g = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = hi - g * (hi - lo), lo + g * (hi - lo)
    fc, fd = sse(c), sse(d)
    for _ in range(40):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - g * (hi - lo)
            fc = sse(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + g * (hi - lo)
            fd = sse(d)
    a = 0.5 * (lo + hi)
    return {"a": float(a), "delta": float(a * a / R), "rms": float(np.sqrt(sse(a) / rs.size)), "n": int(rs.size)}


def membrane_delta_from_normals(normals, X, Y, pitch: float, tail: str = "boussinesq", centre_xy=None) -> float:
    """中心の沈み込み δ を法線場から: 半径方向スロープ s̄(r) を中心から窓の端まで 1D 積分(∫ s̄ dr = ū_z(0) − ū_z(r_max))し、
    ``tail="boussinesq"`` なら遠方場 ū_z ≈ C/r(点荷重の Boussinesq 解、Johnson §3.2)から残りの裾 ū_z(r_max) = r_max · s̄(r_max)
    を足す(窓の端の最後の 3 ビンの中央値)。``tail="none"`` は裾なし(有限窓の過小評価をそのまま返す —— 間違いの量を測るため)。

    高さの FFT 積分を通らないので振幅の減衰を受けない。返り: δ [m]。**Raises** ``ValueError``: 未知の tail、pitch ≤ 0。"""
    if tail not in ("boussinesq", "none"):
        raise ValueError("membrane_delta_from_normals: tail must be 'boussinesq' | 'none', got %r" % (tail,))
    nrm = np.asarray(normals, np.float64)
    X = np.asarray(X, np.float64)
    Y = np.asarray(Y, np.float64)
    pitch = float(pitch)
    if not (pitch > 0.0):
        raise ValueError("membrane_delta_from_normals: pitch must be > 0")
    if centre_xy is None:
        cy, cx = _indent_centre(np.asarray(_ph.integrate_normals(nrm), np.float64))
        centre_xy = (float(_bilinear(X, cy, cx)), float(_bilinear(Y, cy, cx)))
    r_bin, prof, _ = _radial_slope_profile(nrm, X, Y, centre_xy, pitch)
    dr = float(r_bin[1] - r_bin[0]) if len(r_bin) > 1 else pitch
    delta = float(np.sum(prof) * dr)
    if tail == "boussinesq":
        delta += float(np.median(r_bin[-3:] * prof[-3:]))
    return delta
