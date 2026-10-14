# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""deflectometry — 位相計測デフレクトメトリ(PMD)。光沢面に映した縞の歪みから面の傾きを測る。

塗装面・カバーガラス・鏡面研磨品の外観検査の定番。面の前に画面(液晶)を置き、位相シフト縞を
表示して、その**鏡像**をカメラで撮る。面が傾くと鏡像の縞がずれるので、位相から「画面のどの点が
映ったか」が分かり、カメラの視線と画面の点の二等分方向が面の法線になる。高さでなく**傾き**を
直接測るので、深さ数 µm・直径数 mm の凹みでも傾きは 1e-3 rad の桁で、画面までの距離 d が
てこになって画面上では mm の桁のずれになる(反射は角度を 2 倍にする)。

内容(6 op、numpy + scipy):
  装置      `deflectometry_rig`(カメラ・画面・視野の幾何を 1 つの表に)
  画面      `deflectometry_screen_pattern`(画面に出す位相シフト縞・一様光・ソフトボックス)
  順方向    `deflectometry_render`(高さ場 → カメラが撮る縞の鏡像。拡散成分・散乱・ガラスの裏面反射・
            ピントの位置・雑音・量子化を物理の式で入れる)
  逆方向    `deflectometry_phase_to_slope`(画面の絶対位相 2 枚 → 面の格子上の法線マップ)
  微分      `slope_to_curvature`(法線マップ → 平均曲率 / ガウス曲率 / ラプラシアン。積分しない)
  感度      `deflectometry_sensitivity`(撮る前に最小検出傾き・高さと傾きの不定性の係数を閉形式で)

既存資産との棲み分け(再実装せず import して合成):
  * 鏡面反射と法線の復元 = `match3d.reflect` / `match3d.normal_from_reflection`
    (n ∝ 反射 − 入射。後者は「デフレクトメトリの要」として以前から置いてあった単体の式)。
  * 屈折と Fresnel = `glassmirror.refract_rays`(光線ごとに全反射を判定)/
    `glassmirror.fresnel_dielectric`(ガラスの表面と裏面の反射率)。
  * 縞の復号 = `fringe.wrapped_phase` / `fringe.modulation` / `fringe.absolute_phase`
    (本 op の縞は `fringe.synthesize_fringes` と同じ符号規約 I = a + b cos(φ − δ_n))。
  * 法線 → 勾配 = `photometric.normals_to_gradients`、勾配 → 高さ = `photometric.integrate_normals`
    (Frankot–Chellappa)。デフレクトメトリの出力を既存の法線マップの語彙で返すので、そのまま流れる。
  * 高さ場からの曲率 = `demops.dem_curvature`(DEM 用、高さを受ける)。こちらの `slope_to_curvature`
    は**傾きを受ける** —— デフレクトメトリは傾きを測るので、曲率は 1 回微分で出て積分が要らない。

幾何(`deflectometry_rig` の座標系、単位 mm):
  面は z = h(x, y)(公称 z = 0)、x は画像の列方向、y は行方向、+z が上。入射面は x-z 面で、
  カメラ(ピンホール)は C = L(−sin θ, 0, cos θ) から原点を見る。画面は公称の正反射方向
  r0 = (sin θ, 0, cos θ) 上の距離 d に、r0 と直交して置く。画面の座標 u は e_u = (cos θ, 0, −sin θ)、
  v は e_v = (0, 1, 0) 方向で、画面の中心が u = v = 0。縞の位相は φ = 2π u / 周期。

閉形式の感度(`deflectometry_sensitivity`):
  * 面の法線が入射面内で α 傾くと反射光は 2α 曲がり、画面上で 2 d α ずれる。直交方向は
    2 d β cos θ。よって画面の座標の不確かさ σ_u から σ_p = σ_u / (2d)、σ_q = σ_u / (2 d cos θ)。
  * N ステップ位相シフトの位相雑音 σ_φ = √(2/N) σ_I / b(b = 縞の振幅、σ_I = 画素の雑音)、
    σ_u = 周期 · σ_φ / 2π。「画面の画素ピッチ / (2d)」は縞を使わない(画素を数える)場合の目安で、
    位相シフトは補間でこれを大きく下回る。
  * 高さと傾きの不定性: 面が Δz 高いと、同じ画素は視線上で手前の点を見ていて、同じ画面の点が
    映るには法線が Δz sin θ / d だけ傾いていればよい —— 1 台のカメラと 1 枚の画面では、
    高さを知らずに傾きは決まらない(PMD の既知の不定性。Knauer ら 2004)。

来歴(公開文献): Knauer, Kaminski & Häusler, *Proc. SPIE* 5457, 366 (2004)(位相計測デフレクトメトリの
原典)/ Wu ら, *Opt. Eng.* 54(6), 064103 (2015)(PMD の位相誤差: 雑音・画面の非線形・非テレセントリック)/
Frankot & Chellappa, *IEEE PAMI* 10(4), 439 (1988)(勾配の積分)/ Wang, Cossairt & Willomitzer,
*Optica* 12 (2025)(偏光と PMD の融合で不定性を解く)。

★正直な制約:
  * カメラはピンホール + 薄レンズのぼけ(錯乱円)、画面は平面で輝度は角度に依らない。画面の画素の
    格子(スクリーンドア)と液晶の階調の非線形は入れない(位相誤差の主因の 1 つ。Wu ら 2015)。
  * 拡散成分は「画面の平均輝度を一様に足す」近似。ざらつきの散乱は鏡面ローブのガウスの広がりとして
    縞の振幅を落とす(縞の位相は動かさない)。
  * ガラスの裏面は平らで表と平行(厚さ一定)。裏面の反射は 1 回だけ(多重反射は R² の桁で落とす)。
  * ピントのぼけ: 画面側は縞に一様円板の MTF(位相が反転し得る)、面側は画像を円板で畳み込む近似。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import fringe
import glassmirror
import match3d
import photometric

__all__ = [
    "deflectometry_rig",
    "deflectometry_screen_pattern",
    "deflectometry_render",
    "deflectometry_phase_to_slope",
    "slope_to_curvature",
    "deflectometry_sensitivity",
]

#: 台帳(opsspecular の deflectometry 族)に載せる op の正本。
DEFLECTOMETRY = list(__all__)

#: 画面の縞の明るさ(平均 a、振幅 b)。0 と 1 に触れない余白を残す —— 雑音で飽和すると位相が偏る。
FRINGE_MEAN = 0.5
FRINGE_AMPLITUDE = 0.45

_KINDS = ("fringe", "uniform", "softbox")


# --------------------------------------------------------------------------- #
# 検証の小道具                                                                  #
# --------------------------------------------------------------------------- #
def _num(x, name, op, lo=None, hi=None, lo_open=False):
    """有限の実数スカラーへ(bool・文字列・配列は拒否)。範囲外は ValueError。"""
    if isinstance(x, (bool, np.bool_)) or isinstance(x, str):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, x))
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, type(x).__name__)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (v <= lo if lo_open else v < lo):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and v > hi:
        raise ValueError("%s: %s must be <= %g, got %g" % (op, name, hi, v))
    return v


def _field2d(a, name, op, allow_nan=False):
    """2-D の有限な実数配列(空・3-D・NaN は拒否。allow_nan なら NaN は通す)。"""
    if a is None:
        raise ValueError("%s: %s must not be None" % (op, name))
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D array, got shape %s" % (op, name, arr.shape))
    if arr.size == 0 or min(arr.shape) < 2:
        raise ValueError("%s: %s must be at least 2 x 2, got shape %s" % (op, name, arr.shape))
    bad = ~np.isfinite(arr)
    if allow_nan:
        bad &= ~np.isnan(arr)
    if bad.any():
        raise ValueError("%s: %s contains %s values" % (op, name, "infinite" if allow_nan else "non-finite"))
    return arr


def _check_rig(rig, op):
    """rig が None なら既定の装置、dict なら鍵と値を検める(知らない鍵・欠けた鍵は拒否)。"""
    if rig is None:
        return deflectometry_rig()
    if not isinstance(rig, dict):
        raise ValueError("%s: rig must be a dict from deflectometry_rig(), got %s" % (op, type(rig).__name__))
    missing = [k for k in _RIG_KEYS if k not in rig]
    if missing:
        raise ValueError("%s: rig is missing keys %s (build it with deflectometry_rig())" % (op, missing))
    # 値を作り直して突き合わせる: 手で書き換えた rig(C だけ動かした等)は幾何が食い違うので拒否する
    fresh = deflectometry_rig(rig["incidence_deg"], rig["camera_distance_mm"], rig["screen_distance_mm"],
                              rig["field_mm"], rig["aperture_mm"], rig["screen_size_mm"], rig["screen_pixel_mm"])
    for k in ("camera", "screen_center", "screen_normal", "e_u", "e_v", "forward", "right", "down"):
        if not np.allclose(np.asarray(rig[k], float), fresh[k], atol=1e-9):
            raise ValueError("%s: rig[%r] is inconsistent with its scalar parameters (rebuild it with "
                             "deflectometry_rig() instead of editing vectors by hand)" % (op, k))
    return fresh


_RIG_KEYS = ("incidence_deg", "camera_distance_mm", "screen_distance_mm", "field_mm", "aperture_mm",
             "screen_size_mm", "screen_pixel_mm")


# --------------------------------------------------------------------------- #
# 1. 装置                                                                       #
# --------------------------------------------------------------------------- #
def deflectometry_rig(incidence_deg=20.0, camera_distance_mm=400.0, screen_distance_mm=300.0,
                      field_mm=40.0, aperture_mm=4.0, screen_size_mm=(520.0, 320.0),
                      screen_pixel_mm=0.27):
    """デフレクトメトリの装置(カメラ・画面・視野)の幾何を 1 つの表(dict)にする。

    入射面は x-z 面。カメラ(ピンホール)は面の中心から ``camera_distance_mm`` = L 離れ、法線から
    ``incidence_deg`` = θ 傾いた位置 C = L(−sin θ, 0, cos θ) から原点を見る。画面は公称の正反射方向
    r0 = (sin θ, 0, cos θ) 上の距離 ``screen_distance_mm`` = d に、r0 と直交して置く。
    ``field_mm`` は測る面の正方形の一辺(高さ場の格子はこの視野に張る。縦横比は高さ場の形に従う)。
    ``aperture_mm`` はレンズの開口の直径(ピントのぼけの錯乱円に効く。0 = ピンホール)。
    ``screen_size_mm`` は画面の (幅 u, 高さ v)、``screen_pixel_mm`` は画面の画素ピッチ
    (24 型 WUXGA でおよそ 0.27 mm)。

    返り値: dict。スカラーの入力 7 つに加え、ベクトル ``camera``(C)、``screen_center``、
    ``screen_normal``(面へ向く)、``e_u`` / ``e_v``(画面の座標軸)、``forward`` / ``right`` /
    ``down``(カメラの光軸と、画像の列・行の方向)。他の op はこの dict を ``rig=`` で受け、
    手で書き換えたベクトルはスカラーと食い違うとして拒否する(fail-closed)。

    Raises: ``ValueError`` —— 入射角が [0, 80] 度の外、距離・視野・画面の大きさ・画素ピッチが
    正でない、開口が負、値が数でない・有限でない、画面の大きさが 2 つの数でない。
    """
    op = "deflectometry_rig"
    th = _num(incidence_deg, "incidence_deg", op, 0.0, 80.0)
    L = _num(camera_distance_mm, "camera_distance_mm", op, 0.0, lo_open=True)
    d = _num(screen_distance_mm, "screen_distance_mm", op, 0.0, lo_open=True)
    fld = _num(field_mm, "field_mm", op, 0.0, lo_open=True)
    ap = _num(aperture_mm, "aperture_mm", op, 0.0)
    if isinstance(screen_size_mm, (str, bytes)) or np.ndim(screen_size_mm) != 1 or len(screen_size_mm) != 2:
        raise ValueError("%s: screen_size_mm must be (width_u, height_v), got %r" % (op, screen_size_mm))
    sw = _num(screen_size_mm[0], "screen_size_mm[0]", op, 0.0, lo_open=True)
    sh = _num(screen_size_mm[1], "screen_size_mm[1]", op, 0.0, lo_open=True)
    sp = _num(screen_pixel_mm, "screen_pixel_mm", op, 0.0, lo_open=True)
    if fld >= L:
        raise ValueError("%s: field_mm (%g) must be smaller than camera_distance_mm (%g)" % (op, fld, L))
    t = math.radians(th)
    s, c = math.sin(t), math.cos(t)
    r0 = np.array([s, 0.0, c])
    return {
        "incidence_deg": th, "camera_distance_mm": L, "screen_distance_mm": d, "field_mm": fld,
        "aperture_mm": ap, "screen_size_mm": (sw, sh), "screen_pixel_mm": sp,
        "camera": np.array([-L * s, 0.0, L * c]),
        "screen_center": d * r0,
        "screen_normal": -r0,
        "e_u": np.array([c, 0.0, -s]),
        "e_v": np.array([0.0, 1.0, 0.0]),
        "forward": np.array([s, 0.0, -c]),
        "right": np.array([c, 0.0, s]),
        "down": np.array([0.0, 1.0, 0.0]),
    }


def _grid(rig, shape):
    """高さ場の格子(視野の中心が原点)。→ (X (W,), Y (H,), 格子間隔 [mm])。"""
    H, W = shape
    spacing = rig["field_mm"] / (W - 1)
    X = (np.arange(W) - (W - 1) / 2.0) * spacing
    Y = (np.arange(H) - (H - 1) / 2.0) * spacing
    return X, Y, spacing


def _camera(rig, shape):
    """画素 → 視線。焦点距離は視野の四隅が画像に収まるように選ぶ(縦横とも 2 % の余白)。"""
    H, W = shape
    X, Y, _ = _grid(rig, shape)
    C = rig["camera"]
    corners = np.array([[x, y, 0.0] for x in (X[0], X[-1]) for y in (Y[0], Y[-1])]) - C
    zc = corners @ rig["forward"]
    uc = np.abs(corners @ rig["right"] / zc).max()
    vc = np.abs(corners @ rig["down"] / zc).max()
    f_px = 0.98 * min((W - 1) / (2.0 * uc), (H - 1) / (2.0 * vc))
    return f_px, (W - 1) / 2.0, (H - 1) / 2.0


def _rays(rig, shape):
    """各画素の視線の単位ベクトル (H, W, 3)。"""
    H, W = shape
    f_px, cx, cy = _camera(rig, shape)
    cols, rows = np.meshgrid(np.arange(W, dtype=float), np.arange(H, dtype=float))
    d = (rig["forward"][None, None, :] + ((cols - cx) / f_px)[..., None] * rig["right"]
         + ((rows - cy) / f_px)[..., None] * rig["down"])
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def _project(rig, shape, P):
    """3-D 点 (..., 3) → 画素 (列, 行)。"""
    f_px, cx, cy = _camera(rig, shape)
    q = P - rig["camera"]
    z = q @ rig["forward"]
    return f_px * (q @ rig["right"]) / z + cx, f_px * (q @ rig["down"]) / z + cy


def _sample(field, rig, x, y):
    """高さ場の格子上の量を、世界座標 (x, y) で双線形に読む(視野の外は縁の値を延ばす)。

    ★視野の外を 0 で埋めると、余白の画素(焦点距離は 2 % の余白を残す)が平らな面を見て、
    縁の格子点の位相の補間に混ざる —— 傾いた平面の縁 1 行で傾きが 0 に引かれた(実測)。"""
    X, Y, spacing = _grid(rig, field.shape)
    j = (x - X[0]) / spacing
    i = (y - Y[0]) / spacing
    return ndimage.map_coordinates(field, [i.ravel(), j.ravel()], order=1, mode="nearest").reshape(x.shape)


def _hit_screen(rig, P, r):
    """点 P から方向 r の光線を画面の平面に当てる。→ (u, v, 距離)。画面に向かわない光線は NaN。"""
    ns = rig["screen_normal"]
    den = r @ ns
    with np.errstate(divide="ignore", invalid="ignore"):
        t = ((rig["screen_center"] - P) @ ns) / den
    t = np.where((den < -1e-12) & (t > 0), t, np.nan)
    S = P + t[..., None] * r
    q = S - rig["screen_center"]
    return q @ rig["e_u"], q @ rig["e_v"], t


def _screen_intensity(u, v, rig, kind, period, delta):
    """画面の輝度(画面の外は 0 = 黒)。``fringe`` は a + b cos(2πu/周期 − δ)。"""
    sw, sh = rig["screen_size_mm"]
    inside = (np.abs(u) <= sw / 2.0) & (np.abs(v) <= sh / 2.0)
    if kind == "fringe":
        val = FRINGE_MEAN + FRINGE_AMPLITUDE * np.cos(2.0 * np.pi * u / period - delta)
    elif kind == "uniform":
        val = np.full(np.shape(u), 0.8)
    else:  # softbox: 片側から光る大きな面光源(輝度が画面の端へ向けてゆるやかに落ちる)
        val = 0.75 + 0.2 * np.clip(u / (sw / 2.0), -1.0, 1.0)
    return np.where(inside, np.nan_to_num(val), 0.0)


def _screen_mean(kind):
    return FRINGE_MEAN if kind == "fringe" else (0.8 if kind == "uniform" else 0.75)


# --------------------------------------------------------------------------- #
# 2. 画面のパターン                                                             #
# --------------------------------------------------------------------------- #
def deflectometry_screen_pattern(rig=None, period_mm=10.0, n_steps=4, direction="x", kind="fringe",
                                 max_side_px=1024):
    """画面に表示するパターン(画面の画素の格子)。→ 画像のリスト(各 (行, 列)、値 [0, 1])。

    ``kind="fringe"``: 位相シフト縞 I_n = a + b cos(2π s / ``period_mm`` − 2πn/N)(a = 0.5、b = 0.45、
    s は ``direction`` が ``"x"`` なら画面の u、``"y"`` なら v、中心が 0)を ``n_steps`` = N 枚。
    ``fringe.wrapped_phase`` で復号すると位相 2π s / 周期 がそのまま戻る(同じ符号規約)。
    ``"uniform"``: 一様な白(0.8)1 枚。``"softbox"``: 片側から明るい大きな面光源 1 枚
    (0.75 + 0.2 u / 半幅)—— どちらも「縞を使わない普通の撮り方」の比較用。
    画面の画素数は ``screen_size_mm / screen_pixel_mm``。図のために長辺を ``max_side_px`` 画素まで
    間引く(値は各画素の中心で評価するので間引いても縞の位相は正しい)。
    `deflectometry_render` は同じ輝度の式を連続の座標で評価する(画面の画素の格子は入れない)。

    Raises: ``ValueError`` —— 周期が正でない、N < 3(縞のとき)、方向が x / y でない、kind が
    fringe / uniform / softbox でない、max_side_px < 8、rig が不正。
    """
    op = "deflectometry_screen_pattern"
    rig = _check_rig(rig, op)
    period = _num(period_mm, "period_mm", op, 0.0, lo_open=True)
    if kind not in _KINDS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, _KINDS, kind))
    if direction not in ("x", "y"):
        raise ValueError("%s: direction must be 'x' or 'y', got %r" % (op, direction))
    if isinstance(n_steps, bool) or not isinstance(n_steps, (int, np.integer)) or (kind == "fringe" and n_steps < 3):
        raise ValueError("%s: n_steps must be an integer >= 3 for fringes, got %r" % (op, n_steps))
    if isinstance(max_side_px, bool) or not isinstance(max_side_px, (int, np.integer)) or max_side_px < 8:
        raise ValueError("%s: max_side_px must be an integer >= 8, got %r" % (op, max_side_px))
    sw, sh = rig["screen_size_mm"]
    nu = int(round(sw / rig["screen_pixel_mm"]))
    nv = int(round(sh / rig["screen_pixel_mm"]))
    step = max(1, int(math.ceil(max(nu, nv) / max_side_px)))
    u = (np.arange(0, nu, step) + 0.5) * rig["screen_pixel_mm"] - sw / 2.0
    v = (np.arange(0, nv, step) + 0.5) * rig["screen_pixel_mm"] - sh / 2.0
    U, V = np.meshgrid(u, v)
    s = U if direction == "x" else V
    if kind != "fringe":
        return [_screen_intensity(U, V, rig, kind, period, 0.0)]
    out = []
    for n in range(int(n_steps)):
        val = FRINGE_MEAN + FRINGE_AMPLITUDE * np.cos(2.0 * np.pi * s / period - 2.0 * np.pi * n / n_steps)
        out.append(val)
    return out


# --------------------------------------------------------------------------- #
# 3. 順方向: 高さ場 → カメラの画像                                              #
# --------------------------------------------------------------------------- #
def _trace(height, rig, slope_x=None, slope_y=None, back_thickness_mm=None, refractive_index=1.52,
           origins=None, rays=None):
    """光線を追う。→ dict(表面の点・法線・画面の座標・距離・裏面の経路と重み)。

    既定は各画素の主光線(ピンホール C から)。``origins`` / ``rays`` (H, W, 3) を渡すと、レンズの
    開口上の別の点から出る光線を追う(ピントのぼけの開口積分に使う)。"""
    H, W = height.shape
    _, _, spacing = _grid(rig, height.shape)
    if slope_x is None or slope_y is None:
        gy, gx = np.gradient(height, spacing)
        slope_x = gx if slope_x is None else slope_x
        slope_y = gy if slope_y is None else slope_y
    C = rig["camera"] if origins is None else origins
    r = _rays(rig, (H, W)) if rays is None else rays
    # 視線と面 z = h(x, y) の交点: z = 0 から始めて固定点反復(h は µm〜mm の桁なので 6 回で十分)
    t = -C[..., 2] / r[..., 2]
    for _ in range(6):
        P = C + t[..., None] * r
        z = _sample(height, rig, P[..., 0], P[..., 1])
        t = (z - C[..., 2]) / r[..., 2]
    P = C + t[..., None] * r
    p = _sample(slope_x, rig, P[..., 0], P[..., 1])
    q = _sample(slope_y, rig, P[..., 0], P[..., 1])
    n = np.stack([-p, -q, np.ones_like(p)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    refl = match3d.reflect(r, n)
    u1, v1, d1 = _hit_screen(rig, P, refl)
    out = {"P": P, "n": n, "ray": r, "u": u1, "v": v1, "dist_screen": d1,
           "dist_camera": np.linalg.norm(P - C, axis=-1)}
    cos_i = np.clip(-np.sum(r * n, axis=-1), 0.0, 1.0)
    R1 = glassmirror.fresnel_dielectric(cos_i, 1.0, refractive_index)
    out["w_front"] = R1
    if back_thickness_mm is not None:
        tb = float(back_thickness_mm)
        rt, _ = glassmirror.refract_rays(r, n, 1.0, refractive_index)          # 表面で屈折して中へ
        s = (P[..., 2] + tb) / np.maximum(-rt[..., 2], 1e-12)                  # 裏面 z = −t まで
        Pb = P + s[..., None] * rt
        rb = rt * np.array([1.0, 1.0, -1.0])                                     # 平らな裏面で反射
        cos_b = np.clip(-rt[..., 2], 0.0, 1.0)
        Rb = glassmirror.fresnel_dielectric(cos_b, refractive_index, 1.0)
        # 表面へ戻る(z = h の交点を反復で)
        s2 = (0.0 - Pb[..., 2]) / rb[..., 2]
        for _ in range(4):
            Pe = Pb + s2[..., None] * rb
            ze = _sample(height, rig, Pe[..., 0], Pe[..., 1])
            s2 = (ze - Pb[..., 2]) / rb[..., 2]
        Pe = Pb + s2[..., None] * rb
        pe = _sample(slope_x, rig, Pe[..., 0], Pe[..., 1])
        qe = _sample(slope_y, rig, Pe[..., 0], Pe[..., 1])
        ne = np.stack([-pe, -qe, np.ones_like(pe)], axis=-1)
        ne /= np.linalg.norm(ne, axis=-1, keepdims=True)
        ro, tir = glassmirror.refract_rays(rb, -ne, refractive_index, 1.0)      # 中から外へ(入射側の法線は −n)
        cos_e = np.clip(np.sum(rb * ne, axis=-1), 0.0, 1.0)
        Te = 1.0 - glassmirror.fresnel_dielectric(cos_e, refractive_index, 1.0)
        u2, v2, d2 = _hit_screen(rig, Pe, ro)
        w2 = (1.0 - R1) * Rb * Te * (~tir)
        out.update({"u_back": u2, "v_back": v2, "dist_back": d2, "w_back": w2})
    return out


def _aperture_points(k):
    """開口の円板(半径 1)上の k 点(Vogel の螺旋 = 面積が等しい)。→ (k, 2)。"""
    i = np.arange(k) + 0.5
    rad = np.sqrt(i / k)
    ang = i * math.pi * (3.0 - math.sqrt(5.0))
    return np.stack([rad * np.cos(ang), rad * np.sin(ang)], axis=1)


def _disk_mtf(c_over_p):
    """直径 c の一様円板の MTF を周波数 1/p で: 2 J1(πc/p) / (πc/p)(負 = 縞の位相が反転)。"""
    from scipy.special import j1
    x = np.pi * np.asarray(c_over_p, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(x > 1e-9, 2.0 * j1(x) / np.where(x > 1e-9, x, 1.0), 1.0)
    return m


def _focus_alpha(focus, op):
    if isinstance(focus, str):
        if focus == "surface":
            return 0.0
        if focus == "screen":
            return 1.0
        raise ValueError("%s: focus must be 'surface', 'screen' or a number in [0, 1], got %r" % (op, focus))
    return _num(focus, "focus", op, 0.0, 1.0)


def deflectometry_render(height, rig=None, period_mm=10.0, n_steps=4, direction="x", kind="fringe",
                         slope_x=None, slope_y=None, diffuse_fraction=0.0, scatter_rad=0.0,
                         back_thickness_mm=None, refractive_index=1.52, focus="surface",
                         aperture_samples=None, noise_sigma=0.0, bits=None, seed=0):
    """高さ場 → カメラが撮る「画面の鏡像」(順方向のシミュレーション)。→ 画像のリスト(各 (H, W)、[0, 1])。

    ``height`` (H, W) [mm] は ``rig`` の視野(一辺 ``field_mm``、格子間隔 field / (W − 1))に張った面の高さ。
    カメラの画像も (H, W) で、視野の四隅が収まる焦点距離を選ぶ(画素と面の格子は斜めから見るので
    1 対 1 ではない —— `deflectometry_phase_to_slope` が投影して読み直す)。各画素の視線を面に当て
    (z = h の交点を反復で)、法線で鏡面反射して(`match3d.reflect`)画面に当て、画面の輝度
    (`deflectometry_screen_pattern` と同じ式)を読む。``kind="fringe"`` なら ``n_steps`` 枚、
    それ以外は 1 枚。

    傾きは ``slope_x`` = ∂h/∂x、``slope_y`` = ∂h/∂y を渡せば解析値を使い(真値を厳密にするため)、
    省略すると ``height`` の中心差分。

    物理の効果(どれも既定は「理想の鏡」):
      * ``diffuse_fraction`` = k_d ∈ [0, 1): 面の拡散成分。I = (1 − k_d)·鏡面 + k_d·画面の平均輝度。
        縞の振幅が (1 − k_d) 倍に落ち、位相の雑音は 1 / (1 − k_d) 倍になる(ざらついた塗装)。
      * ``scatter_rad``: 鏡面ローブの広がり(面の法線の標準偏差 [rad])。反射光は 2 倍広がり、画面上で
        σ = 2·scatter·(面から画面の距離)のガウスで縞がぼける → 振幅 exp(−2π²σ²/周期²)。
      * ``back_thickness_mm`` / ``refractive_index``: 透明板(カバーガラス)の裏面反射。表で屈折
        (`glassmirror.refract_rays`)→ 平らな裏面で反射 → 表から出る光が、ずれた画面の点を映す。
        重みは Fresnel(`glassmirror.fresnel_dielectric`)。カメラの露出は表と裏の和で正規化する。
      * ``focus``: ``"surface"``(面にピント)/ ``"screen"``(画面の虚像 = 主光線に沿って L + d にピント)/
        0〜1 の数(その間の比 D_f = L + α d)。開口 ``rig["aperture_mm"]`` = A の薄レンズで、距離 D の物体の
        錯乱円の直径は A·|D − D_f| / D_f。面にピント(α = 0)で開口積分を指定しないときは、面の 1 点から出た
        光が画面上で直径 A·d/L の円板に広がるだけなので、縞に一様円板の MTF 2 J1(πc/p) / (πc/p) を掛ける
        (閉形式、負なら位相が反転)。それ以外は**開口積分**: 開口上の ``aperture_samples`` 点(既定 16、
        Vogel の螺旋)から、主光線上のピントの点へ向かう光線を 1 本ずつ面に当てて反射させ、画面の輝度を
        平均する —— 画面側のぼけ(縞の振幅)と面側のぼけ(面の傾きの平均 = 凹みがぼける)が同時に出る。
        ★2026-10-15: 初版は面側のぼけを「画像を円板で畳み込む」近似にしていて、画面にピントを合わせても
        縞の振幅が 0.59 倍に落ちた(縞そのものまでぼかしていた)。画面に合っていれば縞はくっきりで、ぼける
        のは縞を曲げる面の傾きのほう —— 開口積分に直した。
      * ``noise_sigma``(画素の加法ガウス雑音、[0, 1] の単位)と ``bits``(量子化、例 8)。``seed`` で再現。

    画面の外に当たる画素は 0(黒)。``fringe.modulation`` で低い変調の画素を除くこと。

    Raises: ``ValueError`` —— ``height`` が 2-D の有限な配列でない(2 × 2 未満も)、傾きの形が違う・
    有限でない、周期が正でない、N < 3、方向・kind・focus が不正、k_d が [0, 1) の外、散乱が負、
    板厚が正でない、屈折率が 1 以下、雑音が負、bits が 1〜16 の整数でない、aperture_samples が
    1〜256 の整数でも None でもない、rig が不正。
    """
    op = "deflectometry_render"
    rig = _check_rig(rig, op)
    h = _field2d(height, "height", op)
    sx = None if slope_x is None else _field2d(slope_x, "slope_x", op)
    sy = None if slope_y is None else _field2d(slope_y, "slope_y", op)
    for nm, a in (("slope_x", sx), ("slope_y", sy)):
        if a is not None and a.shape != h.shape:
            raise ValueError("%s: %s shape %s does not match height %s" % (op, nm, a.shape, h.shape))
    period = _num(period_mm, "period_mm", op, 0.0, lo_open=True)
    if kind not in _KINDS:
        raise ValueError("%s: kind must be one of %s, got %r" % (op, _KINDS, kind))
    if direction not in ("x", "y"):
        raise ValueError("%s: direction must be 'x' or 'y', got %r" % (op, direction))
    if isinstance(n_steps, bool) or not isinstance(n_steps, (int, np.integer)) or (kind == "fringe" and n_steps < 3):
        raise ValueError("%s: n_steps must be an integer >= 3 for fringes, got %r" % (op, n_steps))
    kd = _num(diffuse_fraction, "diffuse_fraction", op, 0.0)
    if kd >= 1.0:
        raise ValueError("%s: diffuse_fraction must be < 1 (1 = no mirror at all, nothing to measure), got %g"
                         % (op, kd))
    sc = _num(scatter_rad, "scatter_rad", op, 0.0)
    nidx = _num(refractive_index, "refractive_index", op, 1.0, lo_open=True)
    if back_thickness_mm is not None:
        _num(back_thickness_mm, "back_thickness_mm", op, 0.0, lo_open=True)
    alpha = _focus_alpha(focus, op)
    if aperture_samples is not None and (isinstance(aperture_samples, bool)
                                         or not isinstance(aperture_samples, (int, np.integer))
                                         or not 1 <= aperture_samples <= 256):
        raise ValueError("%s: aperture_samples must be None or an integer in 1..256, got %r"
                         % (op, aperture_samples))
    sig = _num(noise_sigma, "noise_sigma", op, 0.0)
    if bits is not None and (isinstance(bits, bool) or not isinstance(bits, (int, np.integer)) or not 1 <= bits <= 16):
        raise ValueError("%s: bits must be None or an integer in 1..16, got %r" % (op, bits))

    tr = _trace(h, rig, sx, sy, back_thickness_mm, nidx)
    A = rig["aperture_mm"]
    nimg = int(n_steps) if kind == "fringe" else 1
    mean_lum = _screen_mean(kind)
    deltas = [2.0 * np.pi * k / nimg if kind == "fringe" else 0.0 for k in range(nimg)]

    def _shade(t, screen_mtf):
        """1 回の光線追跡の結果 → 各位相シフトの鏡面の輝度(表と裏の重みで正規化)。"""
        paths = [(t["u"], t["v"], t["w_front"], t["dist_screen"])]
        if back_thickness_mm is not None:
            paths.append((t["u_back"], t["v_back"], t["w_back"], t["dist_back"]))
        wsum = sum(np.nan_to_num(w) for _, _, w, _ in paths)
        wsum = np.where(wsum > 0, wsum, 1.0)
        res = []
        for delta in deltas:
            spec = np.zeros(h.shape)
            for u, v, w, dist in paths:
                uu = np.nan_to_num(u, nan=1e9)
                vv = np.nan_to_num(v, nan=1e9)
                base = _screen_intensity(uu, vv, rig, kind, period, delta)
                if kind == "fringe":
                    s_ = uu if direction == "x" else vv
                    sigma_s = 2.0 * sc * np.nan_to_num(dist)
                    m = np.exp(-2.0 * np.pi ** 2 * sigma_s ** 2 / period ** 2) * screen_mtf
                    base = np.where(base > 0, FRINGE_MEAN + FRINGE_AMPLITUDE * m
                                    * np.cos(2.0 * np.pi * s_ / period - delta), 0.0)
                spec += np.nan_to_num(w) * base
            res.append(spec / wsum)
        return res

    if A == 0.0 or (alpha == 0.0 and aperture_samples is None):
        # 面にピント: 面の 1 点の光は画面上で直径 A·d/L の円板に広がる → 縞に円板の MTF(閉形式)
        c_screen = A * np.nan_to_num(tr["dist_screen"]) / tr["dist_camera"]
        specs = _shade(tr, _disk_mtf(c_screen / period))
    else:
        # 開口積分: 主光線上のピントの点 F へ、開口の各点から光線を引いて追う
        Lp = tr["dist_camera"]
        dp = np.nan_to_num(tr["dist_screen"], nan=rig["screen_distance_mm"])
        F = rig["camera"] + (Lp + alpha * dp)[..., None] * tr["ray"]
        k = 16 if aperture_samples is None else int(aperture_samples)
        specs = [np.zeros(h.shape) for _ in deltas]
        for a, b in _aperture_points(k) * (A / 2.0):
            O = rig["camera"] + a * rig["right"] + b * rig["down"]
            r_ = F - O
            r_ /= np.linalg.norm(r_, axis=-1, keepdims=True)
            t_ = _trace(h, rig, sx, sy, back_thickness_mm, nidx, origins=np.broadcast_to(O, F.shape), rays=r_)
            for i, sp_ in enumerate(_shade(t_, 1.0)):
                specs[i] += sp_ / k
    imgs = [(1.0 - kd) * sp_ + kd * mean_lum for sp_ in specs]
    rng = np.random.default_rng(seed)
    out = []
    for im in imgs:
        if sig > 0:
            im = im + rng.normal(0.0, sig, im.shape)
        im = np.clip(im, 0.0, 1.0)
        if bits is not None:
            levels = 2 ** int(bits) - 1
            im = np.round(im * levels) / levels
        out.append(im)
    return out


# --------------------------------------------------------------------------- #
# 4. 逆方向: 位相 → 法線                                                        #
# --------------------------------------------------------------------------- #
def deflectometry_phase_to_slope(phase_x, phase_y, rig=None, period_mm=10.0, z_ref=0.0):
    """画面の絶対位相 2 枚(u 方向・v 方向の縞)→ 面の格子上の法線マップ (H, W, 3)。

    ``phase_x`` / ``phase_y``: カメラの画素ごとの**絶対**位相 [rad] (次数を確定したもの。
    `fringe.absolute_phase` で粗い縞から決める)。画面の座標は u = φ_x·周期 / 2π、v = φ_y·周期 / 2π
    (画面の中心が 0)。NaN の画素は無効。

    面の格子(`deflectometry_render` と同じ、視野の中心が原点、間隔 field / (W − 1))の各点
    P = (x, y, ``z_ref``) をカメラに投影して位相を双線形に読み、画面の点 S を出して、
    入射 S→P と反射 P→C から法線を `match3d.normal_from_reflection` で作る(n ∝ 反射 − 入射)。
    返り値は ``photometric`` と同じ規約(+z が上、x が列、y が行)なので、そのまま
    `photometric.integrate_normals`(高さへ)や `slope_to_curvature`(曲率へ)に流せる。
    位相が NaN・視野の外の点は NaN。

    ★高さと傾きの不定性: 面の高さを ``z_ref``(数か (H, W) の配列)と仮定して法線を出す。本当の面が
    Δz ずれていると、法線は Δz sin θ / d だけ(視野の中心で)傾いて出る —— 1 台のカメラと 1 枚の
    画面では分けられない(`deflectometry_sensitivity` が係数を返す)。局所の凹みの形はほぼ影響を
    受けないが、面全体の傾きと曲がりは位置の不確かさに引きずられる。

    Raises: ``ValueError`` —— 位相が 2-D でない・形が違う・無限大を含む、周期が正でない、
    ``z_ref`` が有限でない・形が違う、rig が不正。
    """
    op = "deflectometry_phase_to_slope"
    rig = _check_rig(rig, op)
    px = _field2d(phase_x, "phase_x", op, allow_nan=True)
    py = _field2d(phase_y, "phase_y", op, allow_nan=True)
    if px.shape != py.shape:
        raise ValueError("%s: phase_x %s and phase_y %s must have the same shape" % (op, px.shape, py.shape))
    period = _num(period_mm, "period_mm", op, 0.0, lo_open=True)
    z = np.asarray(z_ref, dtype=np.float64)
    if z.ndim == 0:
        z = np.full(px.shape, _num(z_ref, "z_ref", op))
    elif z.shape != px.shape or not np.all(np.isfinite(z)):
        raise ValueError("%s: z_ref must be a finite number or a finite array of shape %s, got shape %s"
                         % (op, px.shape, z.shape))
    X, Y, _ = _grid(rig, px.shape)
    XX, YY = np.meshgrid(X, Y)
    P = np.stack([XX, YY, z], axis=-1)
    col, row = _project(rig, px.shape, P)
    coords = [row.ravel(), col.ravel()]
    # NaN を含む双線形は近傍の NaN を広げる: 値と有効の重みを別に読んで、無効が混じった点は NaN
    valid = (np.isfinite(px) & np.isfinite(py)).astype(float)
    ax = ndimage.map_coordinates(np.nan_to_num(px), coords, order=1, mode="constant", cval=0.0)
    ay = ndimage.map_coordinates(np.nan_to_num(py), coords, order=1, mode="constant", cval=0.0)
    w = ndimage.map_coordinates(valid, coords, order=1, mode="constant", cval=0.0)
    ok = (w > 1.0 - 1e-9).reshape(px.shape)
    u = (ax.reshape(px.shape)) * period / (2.0 * np.pi)
    v = (ay.reshape(px.shape)) * period / (2.0 * np.pi)
    S = rig["screen_center"] + u[..., None] * rig["e_u"] + v[..., None] * rig["e_v"]
    n = match3d.normal_from_reflection(P - S, rig["camera"] - P)
    if np.mean(n[..., 2]) < 0:      # 全体の符号判定が面の外向き(+z)と逆なら返す
        n = -n
    return np.where(ok[..., None], n, np.nan)


# --------------------------------------------------------------------------- #
# 5. 傾き → 曲率                                                                #
# --------------------------------------------------------------------------- #
def slope_to_curvature(normals, spacing=1.0, kind="mean", sigma_px=0.0):
    """法線マップ (H, W, 3) → 曲率の地図 (H, W)。傾きを 1 回微分するだけで、高さへ積分しない。

    傾き p = ∂z/∂x、q = ∂z/∂y を `photometric.normals_to_gradients` で取り、``spacing``
    (格子間隔、例 mm)で中心差分して z_xx = ∂p/∂x、z_yy = ∂q/∂y、z_xy = (∂p/∂y + ∂q/∂x) / 2。
    ``kind``:
      * ``"mean"`` —— 平均曲率 H = ((1 + q²) z_xx − 2pq z_xy + (1 + p²) z_yy) / (2 (1 + p² + q²)^{3/2})。
      * ``"gaussian"`` —— ガウス曲率 K = (z_xx z_yy − z_xy²) / (1 + p² + q²)²。
      * ``"laplacian"`` —— z_xx + z_yy(小さな傾きでの 2H)。
    単位は 1 / (spacing の単位)。符号: 上に開いた椀(凹み、z = r² / 2R)が**正**(H = 1/R)。
    ``sigma_px`` > 0 なら微分の前に傾きをガウスで均す(微分は雑音を持ち上げる)。NaN の画素は
    重みつきの均しで避け、出力でも NaN。

    デフレクトメトリが曲率で欠陥を見る理由: 凹み・うねりは高さでは µm でも曲率は大きく、しかも
    面全体の傾きと一定の傾きの誤差(高さと傾きの不定性で出るもの)は微分で消える。

    Raises: ``ValueError`` —— 法線が (H, W, 3) でない・2 × 2 未満・無限大を含む・z 成分が正でない
    (面の外向きでない)、spacing が正でない、kind が mean / gaussian / laplacian でない、sigma が負。
    """
    op = "slope_to_curvature"
    n = np.asarray(normals, dtype=np.float64)
    if n.ndim != 3 or n.shape[2] != 3:
        raise ValueError("%s: normals must be an (H, W, 3) normal map, got shape %s" % (op, n.shape))
    if min(n.shape[:2]) < 2:
        raise ValueError("%s: normals must be at least 2 x 2, got shape %s" % (op, n.shape))
    if np.isinf(n).any():
        raise ValueError("%s: normals contain infinite values" % op)
    finite = np.all(np.isfinite(n), axis=-1)
    if np.any(n[..., 2][finite] <= 0):
        raise ValueError("%s: every normal must face +z (n_z > 0); slopes are undefined otherwise" % op)
    h = _num(spacing, "spacing", op, 0.0, lo_open=True)
    if kind not in ("mean", "gaussian", "laplacian"):
        raise ValueError("%s: kind must be 'mean', 'gaussian' or 'laplacian', got %r" % (op, kind))
    sg = _num(sigma_px, "sigma_px", op, 0.0)
    p, q = photometric.normals_to_gradients(np.where(finite[..., None], n, [0.0, 0.0, 1.0]))
    if sg > 0:
        wgt = ndimage.gaussian_filter(finite.astype(float), sg)
        wsafe = np.where(wgt > 1e-12, wgt, 1.0)
        p = ndimage.gaussian_filter(np.where(finite, p, 0.0), sg) / wsafe
        q = ndimage.gaussian_filter(np.where(finite, q, 0.0), sg) / wsafe
    py_, px_ = np.gradient(p, h)
    qy_, qx_ = np.gradient(q, h)
    zxx, zyy, zxy = px_, qy_, 0.5 * (py_ + qx_)
    g = 1.0 + p * p + q * q
    if kind == "mean":
        k = ((1.0 + q * q) * zxx - 2.0 * p * q * zxy + (1.0 + p * p) * zyy) / (2.0 * g ** 1.5)
    elif kind == "gaussian":
        k = (zxx * zyy - zxy * zxy) / (g * g)
    else:
        k = zxx + zyy
    # 無効画素とその隣(中心差分が無効画素を読んだところ)は NaN
    bad = ~finite
    if bad.any():
        bad = ndimage.binary_dilation(bad, structure=np.ones((3, 3), bool))
    return np.where(bad, np.nan, k)


# --------------------------------------------------------------------------- #
# 6. 撮る前の感度                                                               #
# --------------------------------------------------------------------------- #
def deflectometry_sensitivity(rig=None, period_mm=10.0, n_steps=4, noise_sigma=0.004, fringe_amplitude=None,
                              bits=8, diffuse_fraction=0.0):
    """撮る前に、最小検出傾き・高さと傾きの不定性の係数・ピントのぼけを閉形式で出す。→ dict。

    返す鍵(角度は rad、長さは mm):
      * ``slope_pixel_bound`` —— 画面の画素ピッチ / (2d)。縞を使わず画面の画素を数えるときの傾きの刻み。
      * ``phase_noise_rad`` —— N ステップの位相雑音 √(2/N)·σ / b。σ は画素の雑音(``bits`` の量子化
        1/(2^bits − 1)/√12 を 2 乗和で足す)、b は縞の振幅(既定 0.45·(1 − k_d)·|M|、M は面にピントの
        ときの画面側の錯乱円 A·d/L の円板の MTF = `deflectometry_render` の既定と同じ条件。★初版は M を
        忘れていて、実測の位相雑音が閉形式の 1.12 倍に出た —— 内訳を追って直した)。
      * ``fringe_amplitude`` —— 上で使った b。
      * ``screen_noise_mm`` —— 画面の座標の雑音 周期·σ_φ / 2π。
      * ``slope_noise_x`` / ``slope_noise_y`` —— σ_u / (2d) と σ_u / (2 d cos θ)(入射面内と直交方向)。
      * ``height_slope_coupling`` —— 面が 1 mm ずれたときの見かけの傾き sin θ / d [rad/mm]。
      * ``blur_screen_focus_surface_mm`` / ``blur_surface_focus_screen_mm`` —— 面にピントを合わせたときの
        画面側の錯乱円 A·d / L と、画面にピントを合わせたときの面側の錯乱円 A·d / (L + d)。
      * ``contrast_focus_surface`` —— 面にピントのとき縞の振幅に掛かる円板の MTF。

    Raises: ``ValueError`` —— 周期・振幅が正でない、N < 3、雑音が負、bits が 1〜16 の整数でも None
    でもない、k_d が [0, 1) の外、ぼけで縞が消える(MTF がちょうど 0)、rig が不正。
    """
    op = "deflectometry_sensitivity"
    rig = _check_rig(rig, op)
    period = _num(period_mm, "period_mm", op, 0.0, lo_open=True)
    if isinstance(n_steps, bool) or not isinstance(n_steps, (int, np.integer)) or n_steps < 3:
        raise ValueError("%s: n_steps must be an integer >= 3, got %r" % (op, n_steps))
    sig = _num(noise_sigma, "noise_sigma", op, 0.0)
    kd = _num(diffuse_fraction, "diffuse_fraction", op, 0.0)
    if kd >= 1.0:
        raise ValueError("%s: diffuse_fraction must be < 1, got %g" % (op, kd))
    if bits is not None and (isinstance(bits, bool) or not isinstance(bits, (int, np.integer)) or not 1 <= bits <= 16):
        raise ValueError("%s: bits must be None or an integer in 1..16, got %r" % (op, bits))
    d = rig["screen_distance_mm"]
    L = rig["camera_distance_mm"]
    th = math.radians(rig["incidence_deg"])
    A = rig["aperture_mm"]
    contrast = float(_disk_mtf(A * d / L / period))
    if fringe_amplitude is None:
        b = FRINGE_AMPLITUDE * (1.0 - kd) * abs(contrast)
    else:
        b = _num(fringe_amplitude, "fringe_amplitude", op, 0.0, lo_open=True)
    if b <= 1e-12:
        raise ValueError("%s: the fringe vanishes (contrast %.3g at aperture %g mm, period %g mm): "
                         "there is no phase to measure" % (op, contrast, A, period))
    q = 0.0 if bits is None else 1.0 / (2 ** int(bits) - 1) / math.sqrt(12.0)
    sig_eff = math.hypot(sig, q)
    sphi = math.sqrt(2.0 / n_steps) * sig_eff / b
    su = period * sphi / (2.0 * math.pi)
    blur_screen = A * d / L
    return {
        "slope_pixel_bound": rig["screen_pixel_mm"] / (2.0 * d),
        "phase_noise_rad": sphi,
        "pixel_noise_effective": sig_eff,
        "screen_noise_mm": su,
        "slope_noise_x": su / (2.0 * d),
        "slope_noise_y": su / (2.0 * d * math.cos(th)),
        "height_slope_coupling": math.sin(th) / d,
        "blur_screen_focus_surface_mm": blur_screen,
        "blur_surface_focus_screen_mm": A * d / (L + d),
        "contrast_focus_surface": contrast,
        "fringe_amplitude": b,
    }
