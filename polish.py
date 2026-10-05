# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""polish — 研削・研磨・拭き取りで「削れた量」と「拭けた範囲」を画像で測る(学習なし、2026-10-05)。

物理シミュ × Fullseye 系列(柔らかい手首のペグ挿入 pegsim、失敗の分類 pegfail、膜 pegtactile、対称性 pegsym)の続き。研究所の
研削・粉砕の模倣学習(DIPCOM、arXiv:2410.19235、MIT)と、可変コンプライアンスの両腕の拭き(Comp-ACT、arXiv:2406.14990、IROS 2024、
MIT)は、接触を保つ剛性を学習で決める。ここでは学習を使わず、**削れた深さ・拭けた帯の幅・拭けた面積**を画像から読み、
外から来る式と比べる部品を作る。

外から来るもの:
  * **Preston の式**(F. W. Preston, "The theory and design of plate glass polishing machines", J. Soc. Glass Technol. 11, 214–256,
    1927 —— 原文は**未読**)。式の形は二次資料で確かめた: Shen, Feigenbaum, Suratwala ほか, "Nanoplastic removal function and the
    mechanical nature of colloidal silica slurry polishing", J. Am. Ceram. Soc. 2018(LLNL-JRNL-748089)の式 (1)
    dh/dt = k_p σ_o V_r(k_p = Preston 係数、σ_o = 圧力、V_r = 相対速度)。同じ論文の数: セリアでガラスを磨く k_p は
    2×10⁻¹³〜2×10⁻¹² m²/N、ナノ塑性の除去が支配的な時は 5×10⁻¹⁵〜1×10⁻¹³ m²/N。この二次資料は式の出典に Preston 1922
    (Trans. Opt. Soc. 23, 141)を挙げ、1927 ではない。
  * **接触圧の閉形式**: 平らな円形の工具(半径 a)は一様 p = F/(πa²)(剛な平板を仮定)。球面の工具(半径 R、複合弾性率 E*)は
    Hertz の p(r) = p0 √(1 − r²/a²)、a³ = 3FR/(4E*)、p0 = 3F/(2πa²)(Johnson 1985 §3、tacsim の hertz_sphere / hertz_pressure を
    そのまま使う)。
  * **長い直線の一筆の断面(導出)**: 速さ v で x へ進む工具の下の点が受ける除去は h(y) = k_p ∫ p |v_rel| dt。回らない工具なら
    |v_rel| dt = dx なので速さに依らず、平板: h = 2 k_p p √(a² − y²)、Hertz: h = k_p (E*/R)(a² − y²)(放物線の曲率が力に依らない)。
    どちらも 1 m 進むごとの除去体積は k_p F。角速度 ω で回る平板では |v_rel| = √((v − ωy)² + ω²x²) から
    h(y) = (k_p p / v)[c √(b² + ω²c²) + (b²/ω) asinh(ωc/|b|)] (c = √(a² − y²)、b = v − ωy)—— 進む側と戻る側で非対称。
  * **拭けた帯の幅(導出)**: 厚さ h0 の膜は h(y) ≥ h0 の所だけ消える。平板: 半幅 a √(1 − (h0/D)²)(D = 2 a k_p p)、拭ける最小の力
    F_min = π a h0/(2 k_p)。Hertz: 半幅 √(a² − h0 R/(k_p E*))、F_min = (4E*/3R)(h0 R/(k_p E*))^{3/2}。
  * **平行な一筆を持ち上げて並べた時の拭けた面積(導出)**: 半径 a、長さ L、間隔 s の N 本の和集合は
    (2a + (N − 1) min(s, 2a)) L + N π a² − (N − 1) lens(s)、lens(s) = 2a² atan2(√(4a² − s²), s) − (s/2)√(4a² − s²)
    (端の円は中心が一直線に並ぶので、隣り合う 2 つの重なりだけが効く —— 円の凸性による)。
  * **弾性床のパッドで粗さが減る速さ(導出、仮定 = Winkler の弾性床 p = k_w max(0, z − z_t)、パッドの曲げなし)**: 全面が当たる間は
    平均からのずれが exp(−k_p k_w v t) で減り、平均は k_p p̄ v t だけ下がる。山だけが当たる(部分接触)と式から外れる。

numpy 層(台帳 ``polish``、opsdrive): :func:`preston_pressure_kernel` 圧力の窓 / :func:`preston_removal_map` 軌跡と力から除去の
  深さの地図(直接の積分と FFT の畳み込みの 2 つの実装)/ :func:`preston_track_profile` 一筆の断面の閉形式 /
  :func:`wipe_band_width` 拭けた帯の幅と最小の力 / :func:`raster_wipe_area` 平行な一筆の面積の閉形式と軌跡 /
  :func:`coat_image` 残った膜の厚さ → 画像(Beer–Lambert)/ :func:`coat_thickness_from_image` 逆 / :func:`wipe_coverage`
  拭けた面積(Otsu、detect.segment_objects)/ :func:`band_width_profile` 帯の幅を列ごとに副画素で /
  :func:`removal_depth_from_heights` 前後の高さ図から削れた深さ / :func:`preston_coefficient_fit` 深さ = k_p × 滞在の地図 /
  :func:`winkler_polish_run` 弾性床のパッドで磨く時間発展 / :func:`polish_scene_mjcf`(MJCF 文字列)。
mujoco 層(facade のみ): :func:`polish_scene_build` / :func:`polish_stroke_run` / :func:`polish_scene_close`。

規約: 長さは m、力は N、圧力は Pa、時間は s、角速度は rad/s(反時計回りが正、上から見て)。地図は列 = +x、行 = −y(北が上)、画素
中心が整数で、中心の画素が原点 ((W − 1)/2, (H − 1)/2)。軌跡は (N, 2) の xy で、NaN の行は「工具を持ち上げる」区切り。``kind`` は
``"flat"``(``radius`` = 工具の半径 a)か ``"hertz"``(``radius`` = 球の半径 R、``estar`` = 複合弾性率が要る)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "preston_pressure_kernel", "preston_removal_map", "preston_track_profile", "wipe_band_width", "raster_wipe_area",
    "coat_image", "coat_thickness_from_image", "wipe_coverage", "band_width_profile", "removal_depth_from_heights",
    "preston_coefficient_fit", "winkler_polish_run", "polish_scene_mjcf",
    # mujoco が要る(facade のみ、台帳の外)
    "polish_scene_build", "polish_stroke_run", "polish_scene_close",
]

_KINDS = ("flat", "hertz")


# ======================================================================================================================
# 0. 検査の小道具
def _pos(x, name: str, op: str, allow_zero: bool = False) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x)) from None
    if not math.isfinite(v) or v < 0.0 or (v == 0.0 and not allow_zero):
        raise ValueError("%s: %s must be finite and %s 0, got %r" % (op, name, ">=" if allow_zero else ">", x))
    return v


def _kind(kind, op: str) -> str:
    if kind not in _KINDS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, _KINDS, kind))
    return kind


def _contact(force: float, radius: float, kind: str, estar, op: str) -> tuple[float, float]:
    """力 F → (接触半径 a、代表の圧力)。平板: (a, F/(πa²))。Hertz: (a, p0)(tacsim.hertz_sphere、Johnson 1985)。"""
    if kind == "flat":
        return radius, force / (math.pi * radius * radius)
    if estar is None:
        raise ValueError("%s: kind='hertz' needs estar (composite modulus, Pa)" % op)
    es = _pos(estar, "estar", op)
    import tacsim
    h = tacsim.hertz_sphere(force, radius, es)
    return h["a"], h["p0"]


def _pressure_at(r2: np.ndarray, a: float, p: float, kind: str) -> np.ndarray:
    """中心からの距離の二乗 r² の配列で圧力。平板 = 円の内側で一様、Hertz = p0 √(1 − r²/a²)。"""
    if kind == "flat":
        return np.where(r2 <= a * a, p, 0.0)
    return p * np.sqrt(np.maximum(0.0, 1.0 - r2 / (a * a)))


def _shape(shape, op: str) -> tuple[int, int]:
    try:
        h, w = (int(shape[0]), int(shape[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: shape must be (H, W), got %r" % (op, shape)) from None
    if h < 2 or w < 2:
        raise ValueError("%s: shape must be at least (2, 2), got %r" % (op, shape))
    return h, w


def _img(a, name: str, op: str, min_side: int = 2) -> np.ndarray:
    z = np.asarray(a, np.float64)
    if z.ndim != 2 or min(z.shape) < min_side:
        raise ValueError("%s: %s must be a 2-D array with sides >= %d, got shape %r" % (op, name, min_side, z.shape))
    if not np.all(np.isfinite(z)):
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return z


def _strokes(path, op: str) -> list[np.ndarray]:
    """(N, 2) の軌跡を NaN の行で区切った一筆の列に分ける(各 2 点以上)。index の列も返すため (idx, pts) の組。"""
    p = np.asarray(path, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2:
        raise ValueError("%s: path must be an (N >= 2, 2) array, got shape %r" % (op, p.shape))
    nan_row = np.isnan(p).any(axis=1)
    if np.any(~np.isfinite(p[~nan_row])):
        raise ValueError("%s: path has infinite values" % op)
    out, cur = [], []
    for i in range(len(p)):
        if nan_row[i]:
            if len(cur) >= 2:
                out.append(np.array(cur, int))
            elif len(cur) == 1:
                raise ValueError("%s: a stroke between NaN separators has only one point (index %d)" % (op, cur[0]))
            cur = []
        else:
            cur.append(i)
    if len(cur) >= 2:
        out.append(np.array(cur, int))
    elif len(cur) == 1:
        raise ValueError("%s: the last stroke has only one point" % op)
    if not out:
        raise ValueError("%s: path has no stroke of two or more finite points" % op)
    return out


def _grid_xy(h: int, w: int, res: float) -> tuple[np.ndarray, np.ndarray]:
    """画素中心の世界座標(列 = +x、行 = −y、中心の画素が原点)。"""
    x = (np.arange(w) - (w - 1) / 2.0) * res
    y = ((h - 1) / 2.0 - np.arange(h)) * res
    return x, y


# ======================================================================================================================
# 1. 圧力の窓と除去の地図
def preston_pressure_kernel(force: float, radius: float, res: float, kind: str = "flat", estar=None,
                            normalize: bool = False) -> np.ndarray:
    """工具の下の圧力 [Pa] を画素中心で標本化した窓(奇数 × 奇数、中心の画素が工具の中心)。平板は円の内側で一様 F/(πa²)、
    Hertz は p0 √(1 − r²/a²)(``radius`` = 球の半径 R、``estar`` が要る)。``normalize=True`` なら Σ p · res² = F に合わせる
    (画素で数えた円の面積の誤差を消す。FFT の畳み込みで体積を保つため)。
    **Raises** ValueError: 力・半径・画素が正でない、kind が不明、Hertz で estar が無い、接触半径が 1 画素より小さい。"""
    op = "preston_pressure_kernel"
    F = _pos(force, "force", op)
    R = _pos(radius, "radius", op)
    r_ = _pos(res, "res", op)
    k = _kind(kind, op)
    a, p = _contact(F, R, k, estar, op)
    if a < r_:
        raise ValueError("%s: res %.3g is coarser than the contact radius %.3g" % (op, r_, a))
    half = int(math.ceil(a / r_)) + 1
    o = np.arange(-half, half + 1) * r_
    r2 = o[None, :] ** 2 + o[:, None] ** 2
    ker = _pressure_at(r2, a, p, k)
    if normalize:
        s = float(ker.sum()) * r_ * r_
        if not s > 0.0:
            raise ValueError("%s: no pixel centre falls inside the contact" % op)
        ker = ker * (F / s)
    return ker


def _segment_samples(path, force, times, speed, step, op):
    """一筆ごとに中点則の小区間へ分ける: 中心 (M, 2)、長さ ds (M,)、速さ v (M,)、進む向き (M, 2)、力 (M,)。"""
    p = np.asarray(path, np.float64)
    n = len(p)
    f_arr = np.asarray(force, np.float64)
    if f_arr.ndim == 0:
        F = np.full(n, _pos(float(f_arr), "force", op))
    else:
        if f_arr.shape != (n,):
            raise ValueError("%s: force must be a scalar or have one value per path row (%d), got shape %r" % (op, n, f_arr.shape))
        F = f_arr
    if times is not None:
        t = np.asarray(times, np.float64)
        if t.shape != (n,):
            raise ValueError("%s: times must have one value per path row (%d), got shape %r" % (op, n, t.shape))
    elif speed is None:
        raise ValueError("%s: give speed (m/s) or times (s)" % op)
    else:
        v0 = _pos(speed, "speed", op)
    C, DS, V, D, FF, LAB = [], [], [], [], [], []
    for si, idx in enumerate(_strokes(p, op)):
        fi = F[idx]
        if not np.all(np.isfinite(fi)) or np.any(fi < 0.0):
            raise ValueError("%s: force must be finite and >= 0 on every stroke point" % op)
        for j in range(len(idx) - 1):
            a, b = p[idx[j]], p[idx[j + 1]]
            seg = b - a
            L = float(math.hypot(seg[0], seg[1]))
            if L == 0.0:
                continue
            if times is not None:
                dt = float(t[idx[j + 1]] - t[idx[j]])
                if not (dt > 0.0 and math.isfinite(dt)):
                    raise ValueError("%s: times must increase along each stroke (rows %d -> %d)" % (op, idx[j], idx[j + 1]))
                v = L / dt
            else:
                v = v0
            m = max(1, int(math.ceil(L / step)))
            s = (np.arange(m) + 0.5) / m
            C.append(a[None, :] + s[:, None] * seg[None, :])
            DS.append(np.full(m, L / m))
            V.append(np.full(m, v))
            D.append(np.repeat((seg / L)[None, :], m, axis=0))
            FF.append(fi[j] + s * (fi[j + 1] - fi[j]))
            LAB.append(np.full(m, si))
    if not C:
        raise ValueError("%s: every stroke has zero length" % op)
    return (np.concatenate(C), np.concatenate(DS), np.concatenate(V), np.concatenate(D), np.concatenate(FF),
            np.concatenate(LAB))


def _removal_direct(shape, res, C, DS, V, D, FF, radius, kind, estar, k_p, spin, frames=None, op="preston_removal_map"):
    """直接の積分: 小区間ごとに窓の画素で k_p p(r) |v_rel| dt を足す。``frames`` に小区間の番号を渡すと、その時点の地図の写しも返す。"""
    h, w = shape
    xs, ys = _grid_xy(h, w, res)
    out = np.zeros((h, w))
    snaps = []
    fr = set(int(i) for i in frames) if frames is not None else set()
    cache = {}
    for i in range(len(C)):
        Fi = float(FF[i])
        if Fi > 0.0:
            key = round(Fi, 12)
            if key not in cache:
                cache[key] = _contact(Fi, radius, kind, estar, op)
            a, p = cache[key]
            cx, cy = C[i]
            c0 = max(0, int(math.floor((cx - a) / res + (w - 1) / 2.0)))
            c1 = min(w - 1, int(math.ceil((cx + a) / res + (w - 1) / 2.0)))
            r0 = max(0, int(math.floor((h - 1) / 2.0 - (cy + a) / res)))
            r1 = min(h - 1, int(math.ceil((h - 1) / 2.0 - (cy - a) / res)))
            if c0 <= c1 and r0 <= r1:
                dx = xs[c0:c1 + 1][None, :] - cx
                dy = ys[r0:r1 + 1][:, None] - cy
                pr = _pressure_at(dx * dx + dy * dy, a, p, kind)
                if spin == 0.0:
                    out[r0:r1 + 1, c0:c1 + 1] += k_p * pr * DS[i]
                else:
                    vx = V[i] * D[i][0] - spin * dy
                    vy = V[i] * D[i][1] + spin * dx
                    out[r0:r1 + 1, c0:c1 + 1] += k_p * pr * np.hypot(vx, vy) * (DS[i] / V[i])
        if i in fr:
            snaps.append(out.copy())
    return out, snaps


def preston_removal_map(path, force, radius: float, k_p: float, shape=(128, 128), res: float = 1.0e-4, kind: str = "flat",
                        speed=None, times=None, spin: float = 0.0, estar=None, step=None, method: str = "direct") -> np.ndarray:
    """軌跡と押す力から、Preston の式 dh/dt = k_p p |v_rel| を積分した除去の深さの地図 [m] (形 ``shape``、画素 ``res``)。

    ``path`` (N, 2) は工具の中心の xy(NaN の行で工具を持ち上げる)、``force`` はスカラーか行ごとの値(区間の中で線形に補間)、
    ``speed`` [m/s] か ``times`` [s] (行ごと)のどちらか。``spin`` [rad/s] で工具が回ると相対速度に ω ẑ × (x − c) が足される。
    ``method="direct"`` は小区間(既定の刻み res/4)ごとに窓の画素で足す。``method="fft"`` は「軌跡の線密度の画像」と正規化した
    圧力の窓(:func:`preston_pressure_kernel`)の畳み込み —— 回らない・力が一定・速さが一定の時だけ使える第 2 の実装で、
    体積 Σ h res² = k_p F × (窓の半分だけ広げた地図の中の軌跡の長さ)を、地図の外にこぼれる分を除いて保つ。
    **Raises** ValueError: 形・数の検査、速さも時刻も無い、時刻が増えない、fft で回る / 力が変わる / 時刻で速さが変わる。"""
    op = "preston_removal_map"
    h, w = _shape(shape, op)
    r_ = _pos(res, "res", op)
    R = _pos(radius, "radius", op)
    kp = _pos(k_p, "k_p", op)
    k = _kind(kind, op)
    om = float(spin)
    if not math.isfinite(om):
        raise ValueError("%s: spin must be finite" % op)
    st = r_ / 4.0 if step is None else _pos(step, "step", op)
    if method not in ("direct", "fft"):
        raise ValueError("%s: method must be 'direct' or 'fft', got %r" % (op, method))
    C, DS, V, D, FF, _lab = _segment_samples(path, force, times, speed, st, op)
    if method == "direct":
        out, _ = _removal_direct((h, w), r_, C, DS, V, D, FF, R, k, estar, kp, om, op=op)
        return out
    if om != 0.0:
        raise ValueError("%s: method='fft' needs spin = 0 (the kernel must not depend on the travel direction)" % op)
    if np.ptp(FF) > 0.0:
        raise ValueError("%s: method='fft' needs a constant force" % op)
    if times is not None and np.ptp(V) > 1e-12 * float(np.max(V)):
        raise ValueError("%s: method='fft' needs a constant speed" % op)
    F0 = float(FF[0])
    if not F0 > 0.0:
        return np.zeros((h, w))
    ker = preston_pressure_kernel(F0, R, r_, k, estar=estar, normalize=True)
    # 軌跡の小区間の長さを双線形に画素へ置く(線密度 [m / 画素])。地図の外の工具も縁を削るので、窓の半分だけ広げた格子に置いて
    # 畳み込み、最後に切り出す。
    pad = ker.shape[0] // 2 + 1
    h_, w_ = h, w
    h, w = h_ + 2 * pad, w_ + 2 * pad
    col = C[:, 0] / r_ + (w - 1) / 2.0
    row = (h - 1) / 2.0 - C[:, 1] / r_
    c0 = np.floor(col).astype(int)
    r0 = np.floor(row).astype(int)
    fc, fr = col - c0, row - r0
    dens = np.zeros((h, w))
    for dr, dc, wt in ((0, 0, (1 - fr) * (1 - fc)), (0, 1, (1 - fr) * fc), (1, 0, fr * (1 - fc)), (1, 1, fr * fc)):
        rr, cc = r0 + dr, c0 + dc
        ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
        np.add.at(dens, (rr[ok], cc[ok]), DS[ok] * wt[ok])
    from scipy.signal import fftconvolve
    return np.maximum(0.0, kp * fftconvolve(dens, ker, mode="same"))[pad:pad + h_, pad:pad + w_]


# ======================================================================================================================
# 2. 閉形式(一筆の断面・帯の幅・面積)
def preston_track_profile(y, force: float, radius: float, k_p: float, kind: str = "flat", spin: float = 0.0, speed=None,
                          estar=None) -> np.ndarray:
    """長い直線の一筆(+x へ進む)の断面の除去の深さ h(y) [m] (y = 進む向きの左が正の横ずれ、``y`` と同じ形)。閉形式:
    平板 2 k_p p √(a² − y²)、Hertz k_p (E*/R)(a² − y²)(a は力から Hertz で)、回る平板(``spin`` = ω、``speed`` = v が要る)
    (k_p p / v)[c √(b² + ω²c²) + (b²/ω) asinh(ωc/|b|)] (c = √(a² − y²)、b = v − ωy)。|y| ≥ a は 0。
    **Raises** ValueError: 数の検査、回る時に速さが無い、Hertz で回す(閉形式が無い)。"""
    op = "preston_track_profile"
    F = _pos(force, "force", op)
    R = _pos(radius, "radius", op)
    kp = _pos(k_p, "k_p", op)
    k = _kind(kind, op)
    om = float(spin)
    yy = np.asarray(y, np.float64)
    if not np.all(np.isfinite(yy)) or not math.isfinite(om):
        raise ValueError("%s: y and spin must be finite" % op)
    a, p = _contact(F, R, k, estar, op)
    c2 = np.maximum(0.0, a * a - yy * yy)
    c = np.sqrt(c2)
    if k == "hertz":
        if om != 0.0:
            raise ValueError("%s: no closed form for a spinning Hertz tool (use preston_removal_map)" % op)
        es = float(estar)
        return kp * (es / R) * c2
    if om == 0.0:
        return 2.0 * kp * p * c
    if speed is None:
        raise ValueError("%s: a spinning tool needs speed (m/s)" % op)
    v = _pos(speed, "speed", op)
    b = v - om * yy
    w_ = abs(om)
    ab = np.abs(b)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(ab > 0.0, (b * b / w_) * np.arcsinh(w_ * c / np.where(ab > 0, ab, 1.0)), 0.0)
    return kp * p / v * (c * np.sqrt(b * b + w_ * w_ * c2) + term)


def wipe_band_width(force: float, radius: float, k_p: float, coat: float, kind: str = "flat", estar=None) -> dict:
    """厚さ ``coat`` の膜を回らない工具の直線の一筆で拭いた時、膜が消える帯の幅(閉形式)。返り ``width``(0 なら拭けない)、
    ``half_width``、``force_min``(帯ができ始める力)、``centre_depth``(中心の除去の深さ)、``a``(接触半径)。
    平板: D = 2 a k_p p、半幅 a √(1 − (h0/D)²)、F_min = π a h0/(2 k_p)。Hertz: D = k_p E* a²/R、半幅 √(a² − h0 R/(k_p E*))、
    F_min = (4E*/3R)(h0 R/(k_p E*))^{3/2}。速さに依らない(回らない時)。**Raises** ValueError: 数の検査。"""
    op = "wipe_band_width"
    F = _pos(force, "force", op)
    R = _pos(radius, "radius", op)
    kp = _pos(k_p, "k_p", op)
    h0 = _pos(coat, "coat", op)
    k = _kind(kind, op)
    a, p = _contact(F, R, k, estar, op)
    if k == "flat":
        D = 2.0 * a * kp * p
        fmin = math.pi * a * h0 / (2.0 * kp)
        half = a * math.sqrt(1.0 - (h0 / D) ** 2) if D > h0 else 0.0
    else:
        es = float(estar)
        D = kp * es * a * a / R
        g = h0 * R / (kp * es)
        fmin = 4.0 * es / (3.0 * R) * g ** 1.5
        half = math.sqrt(a * a - g) if a * a > g else 0.0
    return {"width": 2.0 * half, "half_width": half, "force_min": fmin, "centre_depth": D, "a": a, "kind": k}


def _lens(a: float, s: float) -> float:
    """半径 a の 2 円(中心間 s)の重なりの面積。acos でなく atan2。"""
    if s >= 2.0 * a:
        return 0.0
    q = math.sqrt(max(0.0, 4.0 * a * a - s * s))
    return 2.0 * a * a * math.atan2(q, s) - 0.5 * s * q


def raster_wipe_area(radius: float, length: float, pitch: float, n_strokes: int, centre=(0.0, 0.0), step=None) -> dict:
    """半径 ``radius`` の工具で、長さ ``length`` の平行な一筆(+x へ、間隔 ``pitch`` で +y へ並べ、一筆ごとに持ち上げて戻る)を
    ``n_strokes`` 本引いた時、工具が触れた面積の閉形式: (2a + (N − 1) min(s, 2a)) L + N π a² − (N − 1) lens(s)。
    返り ``area``、``rect_area``、``disc_union_area``、``lens``、``overlap_saving``(N 本の和 − 面積)、``path``((M, 2)、NaN で
    区切った軌跡、``step`` があれば各一筆をその刻みの点列に)。**Raises** ValueError: 数の検査、n_strokes < 1、面積が溢れる、
    一筆の点が 1e6 を超える。"""
    op = "raster_wipe_area"
    a = _pos(radius, "radius", op)
    L = _pos(length, "length", op)
    s = _pos(pitch, "pitch", op)
    try:
        N = int(n_strokes)
    except (TypeError, ValueError):
        raise ValueError("%s: n_strokes must be an integer" % op) from None
    if N < 1 or N != n_strokes:
        raise ValueError("%s: n_strokes must be an integer >= 1, got %r" % (op, n_strokes))
    cx, cy = float(centre[0]), float(centre[1])
    if not (math.isfinite(cx) and math.isfinite(cy)):
        raise ValueError("%s: centre must be finite" % op)
    lens = _lens(a, s)
    rect = (2.0 * a + (N - 1) * min(s, 2.0 * a)) * L
    discs = N * math.pi * a * a - (N - 1) * lens
    area = rect + discs
    single = 2.0 * a * L + math.pi * a * a
    # 有限の入力でも積が溢れる(chain_fuzz の発見 2026-10-05: 前段の ttc_from_scale が 1e300 級を渡して area = inf)。黙って inf を返さない
    if not all(math.isfinite(v) for v in (rect, discs, area, single)):
        raise ValueError("%s: the area overflows (radius %r, length %r, pitch %r, n_strokes %d)" % (op, radius, length, pitch, N))
    rows = []
    m = 1 if step is None else max(1, int(min(math.ceil(L / _pos(step, "step", op)), 2.0e6)))
    if step is not None and L / float(step) > 1.0e6:
        raise ValueError("%s: length / step = %.3g points per stroke (> 1e6)" % (op, L / float(step)))
    for i in range(N):
        y = cy + (i - (N - 1) / 2.0) * s
        xs = cx - L / 2.0 + L * np.arange(m + 1) / m
        rows.append(np.stack([xs, np.full(m + 1, y)], axis=1))
        if i < N - 1:
            rows.append(np.full((1, 2), np.nan))
    saving = N * single - area
    path = np.vstack(rows)
    # ★2026-10-05 chain_fuzz の 2 回目の発見(ttc_from_scale → raster_wipe_area): 面積の 4 項が有限でも、N 本の和(N·single)と
    # 一筆の y 座標((i − (N−1)/2)·pitch)はまだ溢れうる。区切りの NaN 以外に非有限が出たら黙って返さない
    if not (math.isfinite(saving) and np.isfinite(path[~np.isnan(path)]).all()):
        raise ValueError("%s: the stroke path or the overlap saving overflows (radius %r, length %r, pitch %r, n_strokes %d)"
                         % (op, radius, length, pitch, N))
    return {"area": area, "rect_area": rect, "disc_union_area": discs, "lens": lens, "overlap_saving": saving,
            "path": path, "n_strokes": N}


# ======================================================================================================================
# 3. 膜の画像と読み
def coat_image(depth_map, coat: float, optical_depth: float = math.log(4.0), bare: float = 0.85, noise: float = 0.0,
               seed: int = 0) -> np.ndarray:
    """除去の深さの地図 → 汚れ(膜)の残った板を真上から撮った画像 [0, 1]。残った厚さ t = clip(h0 − h, 0, h0)、明るさ
    I = bare · exp(−τ t/h0)(Beer–Lambert、τ = ``optical_depth`` は膜全体の光学的厚さ)+ 正規の雑音 ``noise``。
    **Raises** ValueError: 地図が 2-D でない・非有限、coat ≤ 0、τ ≤ 0、bare が (0, 1] の外、noise < 0。"""
    op = "coat_image"
    d = _img(depth_map, "depth_map", op)
    h0 = _pos(coat, "coat", op)
    tau = _pos(optical_depth, "optical_depth", op)
    b = _pos(bare, "bare", op)
    sg = _pos(noise, "noise", op, allow_zero=True)
    if b > 1.0:
        raise ValueError("%s: bare must be in (0, 1], got %r" % (op, bare))
    t = np.clip(h0 - d, 0.0, h0)
    img = b * np.exp(-tau * t / h0)
    if sg > 0.0:
        img = img + np.random.default_rng(int(seed)).normal(0.0, sg, img.shape)
    return np.clip(img, 0.0, 1.0)


def coat_thickness_from_image(image, coat: float, optical_depth: float = math.log(4.0), bare: float = 0.85) -> np.ndarray:
    """:func:`coat_image` の逆: t = h0 ln(bare/I)/τ を [0, h0] に切る。**Raises** ValueError: 画像の検査、数の検査。"""
    op = "coat_thickness_from_image"
    im = _img(image, "image", op)
    h0 = _pos(coat, "coat", op)
    tau = _pos(optical_depth, "optical_depth", op)
    b = _pos(bare, "bare", op)
    with np.errstate(divide="ignore"):
        t = h0 * np.log(b / np.maximum(im, 1e-12)) / tau
    return np.clip(t, 0.0, h0)


def wipe_coverage(image, res: float, threshold="otsu", coat=None, optical_depth: float = math.log(4.0), bare: float = 0.85,
                  min_area: int = 4) -> dict:
    """拭けた所(明るい = 膜が消えた所)の面積を画像から読む。2 値化と連結成分は detect.segment_objects(Otsu が既定)。
    返り ``area``(拭けた画素 × res² [m²])、``fraction``、``largest_area``、``n_regions``、``mask``、``threshold``(Otsu の
    しきい値 = 拭けた側の最小と残った側の最大の中点で推定)、``coat`` を渡せば ``residual_at_threshold``(しきい値の明るさが意味する
    残った膜の厚さ —— 読んだ帯は「除去 ≥ h0 − この厚さ」の所)。**Raises** ValueError: 画像の検査、res ≤ 0、拭けた所も残った所も
    無い(しきい値が決まらない)。"""
    op = "wipe_coverage"
    im = _img(image, "image", op)
    r_ = _pos(res, "res", op)
    import detect
    objs = detect.segment_objects(np.clip(im, 0.0, 1.0), threshold=threshold, min_area=int(min_area))
    mask = np.zeros(im.shape, bool)
    for o in objs:
        mask |= o["mask"]
    if not mask.any() or mask.all():
        raise ValueError("%s: the threshold separates nothing (all pixels on one side)" % op)
    thr = 0.5 * (float(im[mask].min()) + float(im[~mask].max())) if threshold == "otsu" else float(threshold)
    out = {"area": float(mask.sum()) * r_ * r_, "fraction": float(mask.mean()),
           "largest_area": (float(objs[0]["area"]) * r_ * r_) if objs else 0.0, "n_regions": len(objs), "mask": mask,
           "threshold": thr}
    if coat is not None:
        h0 = _pos(coat, "coat", op)
        tau = _pos(optical_depth, "optical_depth", op)
        out["residual_at_threshold"] = float(np.clip(h0 * math.log(_pos(bare, "bare", op) / max(thr, 1e-12)) / tau, 0.0, h0))
    return out


def band_width_profile(image, threshold: float, res: float, along: str = "x") -> dict:
    """直線の一筆(``along`` の向き)で拭けた帯の幅を、帯に直交する線ごとに副画素で読む: しきい値を最初に越える所と最後に越える所を
    隣の画素との線形補間で求め、その差 × res。返り ``widths``(線ごと、読めない線は NaN)、``centres``(帯の中心の位置 [m]、
    地図の座標)、``valid``、``median``。帯が 1 本である前提(複数の帯は外側どうしの幅になる)。
    **Raises** ValueError: 画像の検査、res ≤ 0、along が x / y でない、しきい値が非有限。"""
    op = "band_width_profile"
    im = _img(image, "image", op, min_side=3)
    r_ = _pos(res, "res", op)
    th = float(threshold)
    if not math.isfinite(th):
        raise ValueError("%s: threshold must be finite" % op)
    if along not in ("x", "y"):
        raise ValueError("%s: along must be 'x' or 'y', got %r" % (op, along))
    A = im if along == "x" else im.T[::-1, :]          # 行の向き = 帯に直交(上が +y)
    n_lines = A.shape[1]
    nrow = A.shape[0]
    widths = np.full(n_lines, np.nan)
    centres = np.full(n_lines, np.nan)
    for j in range(n_lines):
        col = A[:, j]
        above = np.nonzero(col >= th)[0]
        if len(above) == 0:
            continue
        i0, i1 = int(above[0]), int(above[-1])
        if i0 == 0 or i1 == nrow - 1:
            continue
        # 上の縁: (i0 − 1, i0) の間、下の縁: (i1, i1 + 1) の間
        e0 = i0 - (col[i0] - th) / (col[i0] - col[i0 - 1])
        e1 = i1 + (col[i1] - th) / (col[i1] - col[i1 + 1])
        widths[j] = (e1 - e0) * r_
        centres[j] = ((nrow - 1) / 2.0 - 0.5 * (e0 + e1)) * r_
    valid = np.isfinite(widths)
    return {"widths": widths, "centres": centres, "valid": valid,
            "median": float(np.median(widths[valid])) if valid.any() else float("nan")}


def removal_depth_from_heights(z_before, z_after, ref_mask=None, frame: float = 0.1) -> np.ndarray:
    """磨く前と後の高さ図(同じ格子に置かれていること)から削れた深さ [高さの単位、正 = 削れた]。後の図は載せ直しで傾きと高さが
    変わるので、差 z_before − z_after から「触れていない所」(``ref_mask``、無ければ外周の ``frame`` の割合の枠)で最小二乗の平面を
    引く。**Raises** ValueError: 形が違う・2-D でない・非有限、参照の画素が 3 未満、frame が (0, 0.5) の外。"""
    op = "removal_depth_from_heights"
    zb = _img(z_before, "z_before", op, min_side=3)
    za = _img(z_after, "z_after", op, min_side=3)
    if zb.shape != za.shape:
        raise ValueError("%s: shapes differ %r vs %r" % (op, zb.shape, za.shape))
    h, w = zb.shape
    if ref_mask is None:
        f = float(frame)
        if not (0.0 < f < 0.5):
            raise ValueError("%s: frame must be in (0, 0.5), got %r" % (op, frame))
        k = max(1, int(round(f * min(h, w))))
        m = np.zeros((h, w), bool)
        m[:k, :] = m[-k:, :] = True
        m[:, :k] = m[:, -k:] = True
    else:
        m = np.asarray(ref_mask, bool)
        if m.shape != zb.shape:
            raise ValueError("%s: ref_mask shape %r differs from %r" % (op, m.shape, zb.shape))
    if int(m.sum()) < 3:
        raise ValueError("%s: need at least 3 reference pixels" % op)
    d = zb - za
    rr, cc = np.nonzero(m)
    G = np.stack([np.ones(len(rr)), cc - (w - 1) / 2.0, rr - (h - 1) / 2.0], axis=1)
    coef, *_ = np.linalg.lstsq(G, d[m], rcond=None)
    R_, C_ = np.mgrid[0:h, 0:w]
    plane = coef[0] + coef[1] * (C_ - (w - 1) / 2.0) + coef[2] * (R_ - (h - 1) / 2.0)
    return d - plane


def preston_coefficient_fit(depth_map, dwell_map, mask=None) -> dict:
    """深さの地図 = k_p × 滞在の地図(``dwell_map`` = k_p = 1 で積分した ∫ p |v_rel| dt [Pa·m])を最小二乗で解き、Preston 係数を
    返す。原点を通す当てはめ ``k_p`` と、切片つき ``k_p_affine`` / ``offset``、``r2``、``rms_residual``、``n``。``mask`` が無ければ
    滞在が最大の 5 % を超える画素。**Raises** ValueError: 形が違う・非有限、画素が 3 未満、滞在が 0。"""
    op = "preston_coefficient_fit"
    d = _img(depth_map, "depth_map", op)
    g = _img(dwell_map, "dwell_map", op)
    if d.shape != g.shape:
        raise ValueError("%s: shapes differ %r vs %r" % (op, d.shape, g.shape))
    if mask is None:
        gm = float(g.max())
        if not gm > 0.0:
            raise ValueError("%s: dwell_map is zero everywhere" % op)
        m = g > 0.05 * gm
    else:
        m = np.asarray(mask, bool)
        if m.shape != d.shape:
            raise ValueError("%s: mask shape differs" % op)
    assert m.ndim == 2
    if int(m.sum()) < 3:
        raise ValueError("%s: need at least 3 pixels in the mask" % op)
    x, y = g[m], d[m]
    sxx = float(np.dot(x, x))
    if not sxx > 0.0:
        raise ValueError("%s: dwell is zero inside the mask" % op)
    k = float(np.dot(x, y)) / sxx
    G = np.stack([x, np.ones_like(x)], axis=1)
    (k2, off), *_ = np.linalg.lstsq(G, y, rcond=None)
    res_ = y - k * x
    ss = float(np.sum((y - y.mean()) ** 2))
    return {"k_p": k, "k_p_affine": float(k2), "offset": float(off), "r2": 1.0 - float(np.sum(res_ ** 2)) / ss if ss > 0 else float("nan"),
            "rms_residual": float(np.sqrt(np.mean(res_ ** 2))), "n": int(m.sum())}


# ======================================================================================================================
# 4. 弾性床のパッドで磨く(粗さの時間発展)
def _winkler_level(z: np.ndarray, target: float, zt0: float) -> float:
    """Σ max(0, z − z_t) = target を満たす z_t(区分線形・凸・減少の関数に左から Newton、有限回で厳密)。"""
    zt = zt0
    for _ in range(200):
        above = z > zt
        cnt = int(above.sum())
        if cnt == 0:                                   # 左から近づく限り起きない(f(z_t) ≥ 0 の側を保つ)
            raise ValueError("winkler_polish_run: lost the contact level (no pixel above the pad)")
        f = float(np.sum(z[above] - zt)) - target
        if f <= 1e-13 * max(target, 1e-300):
            return zt
        zt += f / cnt
    return zt


def winkler_polish_run(z, pressure: float, k_w: float, k_p: float, speed: float, duration: float, dt=None,
                       n_record: int = 50) -> dict:
    """弾性床(Winkler)のパッドを平均圧 ``pressure`` で押し、相対速度 ``speed`` で磨いた時の表面の高さ図 ``z`` の時間発展。
    各刻みでパッドの面の高さ z_t を Σ k_w max(0, z − z_t) = N p̄ から解き(当たっている所だけが圧を受ける)、Preston の式で
    z ← z − k_p v k_w max(0, z − z_t) Δt(陽解法、c Δt ≤ 0.01、c = k_p k_w v)。
    返り ``z``(最後)、``t``・``rms``(平均からのずれの rms、形の除去なし)・``mean``・``contact``(当たっている割合)を
    ``n_record`` 点、``rate_full_contact`` = c(全面が当たる間 rms は exp(−c t) で減る —— 導出、この関数は使わない)、``dt``、
    ``steps``。**Raises** ValueError: z の検査、数の検査、c Δt > 0.01。"""
    op = "winkler_polish_run"
    zz = _img(z, "z", op).copy()
    p = _pos(pressure, "pressure", op)
    kw = _pos(k_w, "k_w", op)
    kp = _pos(k_p, "k_p", op)
    v = _pos(speed, "speed", op)
    T = _pos(duration, "duration", op)
    c = kp * kw * v
    step = 0.002 / c if dt is None else _pos(dt, "dt", op)
    if c * step > 0.01 + 1e-12:
        raise ValueError("%s: c*dt = %.3g > 0.01 (explicit step too large; c = k_p k_w v = %.3g 1/s)" % (op, c * step, c))
    nrec = int(n_record)
    if nrec < 2:
        raise ValueError("%s: n_record must be >= 2" % op)
    n_steps = max(1, int(math.ceil(T / step)))
    step = T / n_steps
    rec_at = set(np.unique(np.round(np.linspace(0, n_steps, nrec)).astype(int)).tolist())
    N = zz.size
    target = N * p / kw
    zt = float(zz.mean()) - target / N
    ts, rms, mean, contact = [], [], [], []
    for i in range(n_steps + 1):
        zt = _winkler_level(zz.ravel(), target, min(zt, float(zz.mean()) - target / N))
        gap = zz - zt
        if i in rec_at:
            ts.append(i * step)
            mu = float(zz.mean())
            rms.append(float(np.sqrt(np.mean((zz - mu) ** 2))))
            mean.append(mu)
            contact.append(float(np.mean(gap > 0.0)))
        if i < n_steps:
            zz -= c * np.maximum(gap, 0.0) * step
    return {"z": zz, "t": np.array(ts), "rms": np.array(rms), "mean": np.array(mean), "contact": np.array(contact),
            "rate_full_contact": c, "dt": step, "steps": n_steps}


# ======================================================================================================================
# 5. MuJoCo の場面(工具を押し付けて動かす)
def polish_scene_mjcf(radius: float = 8.0e-3, k_z: float = 500.0, k_xy: float = 2.0e4, mass: float = 0.2,
                      friction: float = 0.3, thickness: float = 4.0e-3, timestep: float = 5.0e-4) -> str:
    """平らな板(z = 0 の平面)の上で、円柱の工具(半径 ``radius``、厚さ ``thickness``、質量 ``mass``)を x・y・z の 3 本の直動の
    関節で動かす MJCF。z は位置サーボ(ゲイン ``k_z`` [N/m] = 手首の押し付けのばね)、x・y は硬いサーボ ``k_xy``。重力あり。
    ばねの閉形式: 工具の底が板に載っている時の法線力 N = m g + k_z (q_surface − q_cmd)(q_surface = 底が z = 0 に来る関節値)。
    接触は硬めに(solref の時定数 = 4 × timestep、solimp 0.99)して、めり込みを ばねの縮みより十分小さくする(既定の柔らかい接触では
    質量 0.05 kg・5 N で 0.7 mm めり込み、手首のばねと直列になって力が 6 % 小さく出た —— 実測)。摩擦の錐は角錐(pyramidal)。
    楕円の錐 + impratio = 10 では、硬い手首(20 kN/m)で 0.1〜0.36 mm めり込んで力が 17 % 小さく出た(摩擦 0 でも同じ、実測)。
    **Raises** ValueError: 数の検査。"""
    op = "polish_scene_mjcf"
    a = _pos(radius, "radius", op)
    kz = _pos(k_z, "k_z", op)
    kxy = _pos(k_xy, "k_xy", op)
    m = _pos(mass, "mass", op)
    mu = _pos(friction, "friction", op)
    th = _pos(thickness, "thickness", op)
    ts = _pos(timestep, "timestep", op)
    cz = 2.0 * math.sqrt(kz * m)                     # z は臨界減衰
    cxy = 2.0 * math.sqrt(kxy * m)
    return """<mujoco model="polish">
  <compiler angle="radian"/>
  <option timestep="%.6g" gravity="0 0 -9.81" cone="elliptic"/>
  <visual><global offwidth="320" offheight="240"/></visual>
  <worldbody>
    <light pos="0 0 0.5" dir="0 0 -1"/>
    <geom name="plate" type="plane" size="0.2 0.2 0.01" friction="%.6g 0.005 0.0001" rgba="0.8 0.8 0.75 1"/>
    <body name="tool" pos="0 0 %.6g">
      <joint name="tx" type="slide" axis="1 0 0" damping="%.6g"/>
      <joint name="ty" type="slide" axis="0 1 0" damping="%.6g"/>
      <joint name="tz" type="slide" axis="0 0 1" damping="%.6g"/>
      <geom name="pad" type="cylinder" size="%.6g %.6g" mass="%.6g" friction="%.6g 0.005 0.0001" solref="%.6g 1" solimp="0.99 0.99 0.001"
            rgba="0.2 0.4 0.8 1"/>
    </body>
    <camera name="top" pos="0 0 0.3" xyaxes="1 0 0 0 1 0"/>
  </worldbody>
  <actuator>
    <position name="ax" joint="tx" kp="%.6g"/>
    <position name="ay" joint="ty" kp="%.6g"/>
    <position name="az" joint="tz" kp="%.6g"/>
  </actuator>
</mujoco>
""" % (ts, mu, th / 2.0, cxy, cxy, cz, a, th / 2.0, m, mu, 4.0 * ts, kxy, kxy, kz)


def polish_scene_build(radius: float = 8.0e-3, k_z: float = 500.0, k_xy: float = 2.0e4, mass: float = 0.2,
                       friction: float = 0.3, thickness: float = 4.0e-3, timestep: float = 5.0e-4) -> dict:
    """:func:`polish_scene_mjcf` を MuJoCo に読ませた場面(mujoco が要る)。返り ``model``・``data``・``params``・各 id。
    関節値 0 で工具の底が z = 0(板の面)に来る。**Raises** ValueError: 数の検査、RuntimeError: mujoco が無い。"""
    try:
        import mujoco
    except ImportError as exc:                                   # pragma: no cover
        raise RuntimeError("polish_scene_build needs mujoco") from exc
    xml = polish_scene_mjcf(radius, k_z, k_xy, mass, friction, thickness, timestep)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    return {"model": model, "data": data, "mujoco": mujoco,
            "params": {"radius": float(radius), "k_z": float(k_z), "k_xy": float(k_xy), "mass": float(mass),
                       "friction": float(friction), "thickness": float(thickness), "timestep": float(timestep)},
            "pad": mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "pad"),
            "plate": mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "plate")}


def _contact_wrench(sc) -> tuple[float, np.ndarray]:
    """工具と板の接触の法線力の和と、接線力(世界の xy)の和。"""
    mj = sc["mujoco"]
    m, d = sc["model"], sc["data"]
    fn, ft = 0.0, np.zeros(2)
    f6 = np.zeros(6)
    for i in range(d.ncon):
        con = d.contact[i]
        if {int(con.geom1), int(con.geom2)} != {sc["pad"], sc["plate"]}:
            continue
        mj.mj_contactForce(m, d, i, f6)
        frame = np.array(con.frame).reshape(3, 3)          # 行 0 = 法線、行 1・2 = 接線
        fw = f6[0] * frame[0] + f6[1] * frame[1] + f6[2] * frame[2]
        sgn = 1.0 if int(con.geom2) == sc["pad"] else -1.0  # 法線は geom1 → geom2
        fw = sgn * fw
        fn += float(fw[2])
        ft += fw[:2]
    return fn, ft


def polish_stroke_run(sc, path, z_cmd, speed: float, settle: float = 0.3, record_every: int = 4) -> dict:
    """工具を ``path`` (N, 2) の折れ線に沿って速さ ``speed`` で動かし(x・y の指令)、z の指令を ``z_cmd``(行ごと、関節値、負 =
    板より下へ押し込む)で線形に補間して押す。最初に ``settle`` 秒だけ始点で押して落ち着かせる(記録しない)。
    返り ``t``・``xy``(工具の中心の実測)・``cmd_xy``・``z``(関節値)・``z_cmd``・``normal``(接触の法線力の和、+ = 上向き)・
    ``tangent``(接線力 xy)・``speed``。力は記録の間隔(``record_every`` 刻み)の平均。**Raises** ValueError: 形・数の検査、RuntimeError: mujoco が無い。"""
    op = "polish_stroke_run"
    p = np.asarray(path, np.float64)
    zc = np.asarray(z_cmd, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2 or not np.all(np.isfinite(p)):
        raise ValueError("%s: path must be a finite (N >= 2, 2) array" % op)
    if zc.shape != (len(p),) or not np.all(np.isfinite(zc)):
        raise ValueError("%s: z_cmd must have one finite value per path row" % op)
    v = _pos(speed, "speed", op)
    st = _pos(settle, "settle", op, allow_zero=True)
    mj = sc["mujoco"]
    m, d = sc["model"], sc["data"]
    mj.mj_resetData(m, d)
    seg = np.hypot(*np.diff(p, axis=0).T)
    s_cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(s_cum[-1])
    if not total > 0.0:
        raise ValueError("%s: path has zero length" % op)
    dt = float(m.opt.timestep)
    d.qpos[:3] = [p[0, 0], p[0, 1], 0.0]
    d.ctrl[:] = [p[0, 0], p[0, 1], zc[0]]
    for _ in range(int(round(st / dt))):
        mj.mj_step(m, d)
    n = int(math.ceil(total / v / dt))
    re_ = int(record_every)
    if re_ < 1:
        raise ValueError("%s: record_every must be >= 1" % op)
    T, XY, CXY, Z, ZC, FN, FT = [], [], [], [], [], [], []
    acc_n, acc_t, acc_k = 0.0, np.zeros(2), 0
    for k in range(n + 1):
        s = min(total, k * dt * v)
        cx = float(np.interp(s, s_cum, p[:, 0]))
        cy = float(np.interp(s, s_cum, p[:, 1]))
        czv = float(np.interp(s, s_cum, zc))
        d.ctrl[:] = [cx, cy, czv]
        mj.mj_step(m, d)
        fn, ft = _contact_wrench(sc)
        acc_n += fn
        acc_t += ft
        acc_k += 1
        if k % re_ == 0:
            # 力は記録の間の平均(= 力積 / 時間)。瞬間の値は接触の細かな離れ(数十 µs)で 0 を拾う —— 除去は力の時間積分なので平均でよい
            T.append(k * dt)
            XY.append([float(d.qpos[0]), float(d.qpos[1])])
            CXY.append([cx, cy])
            Z.append(float(d.qpos[2]))
            ZC.append(czv)
            FN.append(acc_n / acc_k)
            FT.append(acc_t / acc_k)
            acc_n, acc_t, acc_k = 0.0, np.zeros(2), 0
    return {"t": np.array(T), "xy": np.array(XY), "cmd_xy": np.array(CXY), "z": np.array(Z), "z_cmd": np.array(ZC),
            "normal": np.array(FN), "tangent": np.array(FT), "speed": v}


def polish_scene_close(sc) -> None:
    """場面を手放す(MjData / MjModel の参照を切る)。2 回呼んでもよい。"""
    if isinstance(sc, dict):
        for key in ("data", "model"):
            sc.pop(key, None)
