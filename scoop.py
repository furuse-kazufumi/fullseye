# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粉体のすくいと注ぎを画像で測る —— すくった量(側面像の輪郭 → 体積 → 粒の数)と、傾けて注いだときの流量
(流れの幅と速さ)を規則だけで、学習なし(2026-10-05)。

物理シミュ × Fullseye 系列で granular(山の安息角・体積・Beverloo 排出)の続き。先行研究の粉体計量
(Kadokawa, Hamaya, Tanaka, IROS 2023, doi 10.1109/iros55552.2023.10342463)は秤の質量だけを観測に使う。ここは
**スプーンの中と注ぎの流れを横から見て** 量と流量を読む側を埋める。外から来る真値:

- スプーンの幾何(閉形式): 球冠の椀(縁の半径 ``a``、深さ ``h``)のすり切り体積 ``V = π h (3a² + h²) / 6``、
  深さ ``y`` まで満たした体積 ``π y² (3R − y) / 3``(``R = (a² + h²) / 2h``)、山盛り分は縁を底面とする安息角 φ の
  円錐 ``(π/3) a³ tan φ``。
- 流れの粒の数(Boolean 模型 = 位置が独立な円板の和の被覆率 ``c = 1 − exp(−n π r²)``、Matheron の確率幾何の
  標準結果): 被覆率から面密度 ``n = −ln(1 − c) / (π r²)`` を逆に解く(素朴な ``c / (π r²)`` は重なりで数え落とす)。
- 自由落下 ``v(s) = √(v₀² + 2 g s)``(流量の連続 = どの高さでも同じ粒の数 / 秒)。
- 傾けた器から出る量(**自分の導出**、前の口に壁の無い器 = 粉の前面が口から安息角 φ の斜面): 保持断面
  ``A(θ) = ∫₀ᴸ min(h₀, x tan(φ − θ)) dx``(床に沿って口から ``x``、床に垂直な高さ、奥壁は床に垂直)。granular の
  ``spoon_tilt_critical`` / ``spoon_tilt_dispense`` は ``tan φ − tan θ`` と書く小角の近似で、初めの量を ``L h₀``
  (口まで平らに満ちた形)に取る —— 2 つは θ = 10 度・φ = 30 度で楔の傾きが 10 % 違う。MuJoCo の口の開いた樋の出た割合に
  φ と深さを当てはめると口の楔が RMS 0.023、小角の近似 0.038(PoC の門; φ は当てはめで独立でない、奥の平らな層が流れて
  薄くなる挙動はどちらの模型にも無い)。
- 第 2 実装(MuJoCo 3.x、optional): granular と同じ剛体球の場面の作法で、球冠の椀を薄板で張った ``scoop_scene_mjcf``
  と、口が開いた樋を傾ける ``pour_scene_mjcf``(どちらも文字列だけで mujoco 不要、台帳に載る)。走らせる
  :func:`scoop_mujoco_fill` / :func:`scoop_mujoco_pour` は mujoco が要るので facade だけ(台帳の外)。

座標の約束: 画像は ``(H, W)`` の float で **行 0 が上**、側面像は「粉の被覆率」(0 = 背景、1 = 粉)。椀の軸は鉛直
(画像の列に平行)。長さの単位は呼び手が揃える(閉形式は単位を持たない)。角度は度。失敗はすべて ``ValueError``。

**mg 級は秤に譲る**: 画像の体積の不確かさは見えている表面積 × (縁の 0.5 画素と粒の半径)で、:func:`scoop_image_limit`
がその目安と「画像で足りるか、秤か」を返す(granular の docstring の規律)。粒が少ない(椀の半径 / 粒径 ≲ 5)と
輪郭が粒の凹凸そのものになり、体積と粒の数の換算が崩れる —— PoC の「壊れる場所」の門。

読めなかった一次情報(正直に): 傾けた孔・口からの排出の実験式(Sheldon & Durian 2010 ほか)は **未読** で、傾き角への
依存は上の楔の導出と MuJoCo だけで確かめた。Beverloo の式は granular の ``beverloo_rate`` をそのまま使い、口の流れの
層を等価直径に置き換えた **桁の照合** に留める(式は底の円孔のもの)。
"""
from __future__ import annotations

import math
import warnings

import numpy as np

import granular as _G
import pivops

__all__ = [
    "spoon_bowl_volume", "scoop_synth_side", "revolution_volume_side", "two_view_volume", "scoop_volume_read",
    "scoop_count", "scoop_image_limit",
    "tilt_wedge_retained", "tilt_pour_rate", "tilted_surface_read",
    "stream_synth", "stream_areal_density", "stream_flux_read",
    "scoop_scene_mjcf", "pour_scene_mjcf",
    "scoop_mujoco_fill", "scoop_mujoco_pour",
]

G_STD = _G.G_STD


# ----------------------------------------------------------------------------------------------
# 引数の検査(fail-closed)—— granular と同じ作法
# ----------------------------------------------------------------------------------------------
def _pos(v, name):
    return _G._pos(v, name)


def _nonneg(v, name):
    return _G._nonneg(v, name)


def _angle(v, name, lo=0.0, hi=90.0):
    return _G._angle(v, name, lo, hi)


def _image(a, name):
    return _G._image(a, name)


def _choice(v, name, allowed):
    return _G._choice(v, name, allowed)


def _coverage(a, name):
    x = _image(a, name)
    if x.min() < -1e-9 or x.max() > 1.0 + 1e-9:
        raise ValueError("%s must be a coverage image in [0, 1], got [%g, %g]" % (name, x.min(), x.max()))
    return np.clip(x, 0.0, 1.0)


def _frac(v, name):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number in [0, 1], got %r" % (name, v))
    if isinstance(v, bool) or not math.isfinite(f) or not (0.0 <= f <= 1.0):
        raise ValueError("%s must be a number in [0, 1], got %r" % (name, v))
    return f


# ----------------------------------------------------------------------------------------------
# スプーンの幾何(閉形式)
# ----------------------------------------------------------------------------------------------
def spoon_bowl_volume(a: float, h: float, *, fill_depth: float | None = None, phi_deg: float | None = None) -> dict:
    """球冠の椀(縁の半径 ``a``、深さ ``h``)の閉形式 —— すり切り・途中まで・山盛り。

    球の半径 ``R = (a² + h²) / (2h)``、すり切り ``V_struck = π h (3a² + h²) / 6``。``fill_depth = y`` を与えると底から
    ``y`` まで平らに満たした体積 ``V_fill = π y² (3R − y) / 3``(``y = h`` で ``V_struck`` に一致する恒等式)。
    ``phi_deg`` を与えると縁を底面とする安息角 φ の円錐(山盛りの上限)``V_heap = (π/3) a³ tan φ``、高さ ``a tan φ``、
    ``V_heaped = V_struck + V_heap``、山盛り / すり切りの比。
    返り: ``R``, ``V_struck``, ``V_fill``(与えたとき)、``V_heap`` / ``H_heap`` / ``V_heaped`` / ``heaped_ratio``(φ を与えたとき)。
    **Raises** ``ValueError``: ``a``・``h`` が ≤ 0、``h > a``(半球より深い椀は縁が最も広い所でなく、側面から上だけを
    見る :func:`scoop_volume_read` の前提が崩れる)、``fill_depth`` が ``(0, h]`` の外、φ が (0, 90) の外。"""
    a, h = _pos(a, "a"), _pos(h, "h")
    if h > a:
        raise ValueError("spoon_bowl_volume: h = %g > a = %g (deeper than a hemisphere)" % (h, a))
    R = (a * a + h * h) / (2.0 * h)
    out = {"R": R, "V_struck": math.pi * h * (3.0 * a * a + h * h) / 6.0, "a": a, "h": h}
    if fill_depth is not None:
        y = _pos(fill_depth, "fill_depth")
        if y > h * (1.0 + 1e-12):
            raise ValueError("fill_depth %g exceeds the bowl depth %g" % (y, h))
        out["V_fill"] = math.pi * y * y * (3.0 * R - y) / 3.0
        out["fill_depth"] = y
    if phi_deg is not None:
        phi = _angle(phi_deg, "phi_deg")
        t = math.tan(math.radians(phi))
        out.update({"V_heap": math.pi / 3.0 * a ** 3 * t, "H_heap": a * t, "phi_deg": phi})
        out["V_heaped"] = out["V_struck"] + out["V_heap"]
        out["heaped_ratio"] = out["V_heaped"] / out["V_struck"]
    return out


def _bowl_radius_at(z, R, h):
    """底から高さ ``z`` での椀の内側の半径(球冠、``0 ≤ z ≤ h``)。"""
    return np.sqrt(np.clip(R * R - (R - z) ** 2, 0.0, None)) * ((z >= 0.0) & (z <= h))


def scoop_synth_side(a_px: float, h_px: float, *, fill: float = 1.0, heap_frac: float = 0.0, phi_deg: float = 30.0,
                     pitch: float = 1e-4, margin_px: int = 10, supersample: int = 8, noise: float = 0.0,
                     seed: int | None = None) -> dict:
    """球冠の椀の中の粉を横から見た被覆率を合成する(軸対称、真値は閉形式)。

    - ``fill`` ∈ (0, 1]: 底からの深さの割合 ``y = fill·h`` まで平らに満たす(``heap_frac`` > 0 なら 1 であること)。
    - ``heap_frac`` ∈ [0, 1]: すり切りの上に、底面の半径 ``b = heap_frac·a``・安息角 φ の円錐(真ん中に注いで育つ山)。
    - 返り: ``side``(透明な椀 = 中身が全部見える被覆率)、``side_above``(縁より上だけ = 金属の椀を横から見た像)、
      ``rim_row``(縁の高さの行境界: 行 ``rim_row`` から下が縁より下)、``axis_col``(軸の列座標、画素の端が整数)、
      ``truth``(``V`` [m³] 閉形式、``V_struck``, ``V_heap``, ``fill``, ``heap_frac``, ``phi_deg``)、``pitch``。
    合成と :func:`revolution_volume_side` は同じ軸対称の模型なので、雑音なしの往復は **配管の検査**(独立な被験者は
    :func:`two_view_volume` の楕円の山と MuJoCo の球)。**Raises** ``ValueError``: 範囲外、``fill < 1`` で山を載せた。"""
    a, h = _pos(a_px, "a_px"), _pos(h_px, "h_px")
    f, hf = _frac(fill, "fill"), _frac(heap_frac, "heap_frac")
    if f <= 0.0:
        raise ValueError("fill must be > 0")
    if hf > 0.0 and f < 1.0:
        raise ValueError("a heap needs a full bowl (fill = 1), got fill = %g" % f)
    phi = _angle(phi_deg, "phi_deg")
    geo = spoon_bowl_volume(a, h, fill_depth=f * h)
    R = geo["R"]
    t = math.tan(math.radians(phi))
    b = hf * a
    Hb = b * t
    p = _pos(pitch, "pitch")
    ss = int(supersample)
    if ss < 1:
        raise ValueError("supersample must be >= 1")
    m = int(margin_px)
    cols = int(math.ceil(2.0 * a)) + 2 * m
    rows = int(math.ceil(h + Hb)) + 2 * m
    axis = cols / 2.0
    z_rim_from_top = m + math.ceil(Hb)                 # 縁の行境界(整数にそろえる: 上だけの像を切りやすい)
    zb = z_rim_from_top + h                            # 底の高さ(上からの距離 [px])
    xs = (np.arange(cols * ss) + 0.5) / ss - axis
    zs = (np.arange(rows * ss) + 0.5) / ss              # 上からの距離
    Z = zb - zs[:, None]                               # 底からの高さ
    rbowl = np.where((Z >= 0.0) & (Z <= f * h), _bowl_radius_at(Z, R, h), 0.0)
    rheap = np.where((Z > h) & (Z <= h + Hb), (h + Hb - Z) / t, 0.0) if hf > 0.0 else np.zeros_like(Z)
    rad = np.maximum(rbowl, rheap)
    inside = np.abs(xs[None, :]) <= rad
    side = inside.reshape(rows, ss, cols, ss).mean(axis=(1, 3))
    if noise > 0.0:
        rng = np.random.default_rng(seed)
        side = np.clip(side + rng.uniform(-noise, noise, side.shape), 0.0, 1.0)
    above = side.copy()
    above[int(z_rim_from_top):] = 0.0
    V_heap = math.pi / 3.0 * b * b * Hb
    V = geo["V_fill"] + V_heap
    truth = {"V": V * p ** 3, "V_struck": geo["V_struck"] * p ** 3, "V_heap": V_heap * p ** 3, "fill": f, "heap_frac": hf,
             "phi_deg": phi, "a_px": a, "h_px": h, "R_px": R}
    return {"side": side, "side_above": above, "rim_row": int(z_rim_from_top), "axis_col": axis, "truth": truth, "pitch": p}


# ----------------------------------------------------------------------------------------------
# 側面像 → 体積(回転体の円板積分 / 2 方向の楕円)
# ----------------------------------------------------------------------------------------------
def _row_widths(a):
    """行ごとの幅 [px] (被覆率の行和 = 副画素)と重心の列座標(画素の端が整数)。"""
    w = a.sum(axis=1)
    cols = np.arange(a.shape[1]) + 0.5
    with np.errstate(invalid="ignore", divide="ignore"):
        cen = np.where(w > 0.0, (a * cols[None, :]).sum(axis=1) / np.where(w > 0.0, w, 1.0), np.nan)
    return w, cen


def _shift4(m, op):
    """4 近傍のずらしで 1 画素の収縮(op = np.logical_and)/ 膨張(np.logical_or)。"""
    out = m.copy()
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.zeros_like(m)
        rs = slice(max(dr, 0), m.shape[0] + min(dr, 0))
        rd = slice(max(-dr, 0), m.shape[0] + min(-dr, 0))
        cs = slice(max(dc, 0), m.shape[1] + min(dc, 0))
        cd = slice(max(-dc, 0), m.shape[1] + min(-dc, 0))
        sh[rd, cd] = m[rs, cs]
        out = op(out, sh)
    return out


def _clean_coverage(a, threshold=0.5):
    """被覆率の雑音を物の外と内で消す: しきい値の領域を 1 画素収縮した内側は 1、1 画素膨張した外側は 0、間の縁の画素は
    そのまま。[0, 1] に切った一様雑音は内側で平均を下げ外側で上げる(granular の列和法の罠と同じ)ので、体積を被覆率の
    線形和で測る前に通す。"""
    m = a >= float(threshold)
    deep = _shift4(m, np.logical_and)
    near = _shift4(m, np.logical_or)
    return np.where(deep, 1.0, np.where(near, a, 0.0))


def _row_fill_fraction(a):
    """行ごとの縦の満ち具合(平らな粉面が行の途中を横切ると、その行の被覆率は弦の内側で一様に f)。内側(左右の隣も
    正の画素)の中央値、内側が 3 画素未満なら行の最大値。空の行は 1。"""
    f = np.ones(a.shape[0])
    pos = a > 0.0
    inner = pos & np.roll(pos, 1, axis=1) & np.roll(pos, -1, axis=1)
    inner[:, 0] = False
    inner[:, -1] = False
    for i in range(a.shape[0]):
        v = a[i, inner[i]]
        if v.size >= 3:
            f[i] = float(np.median(v))
        elif pos[i].any():
            f[i] = float(a[i].max())
    return np.clip(f, 1e-6, 1.0)


def revolution_volume_side(side, pitch: float, *, axis_col: float | None = None, threshold: float = 0.5) -> dict:
    """側面像 1 枚から軸対称を仮定した体積 —— Pappus の形 ``V = π Σ |x − x_axis| c(x, z) pitch³``(``c`` = 被覆率、
    ``x`` = 画素の中心の列)。

    被覆率に **線形** なので、平らな粉面が行の途中を横切る行でも偏らない(行ごとの幅を直径にした円板の和
    ``Σ π (w/2)²`` は、満ち具合 ``f`` の行を ``f²`` で数えて 1.5 % 低く出た、実測)。雑音は先に物の外と内で消す
    (``_clean_coverage``)。軸 ``axis_col``(画素の端が整数)を与えなければ被覆率の重心の列。行ごとの重心に直線を
    当てて軸の傾き ``axis_tilt_deg``(atan2)も返す(傾いた椀は体積が増える; 判定は呼び手)。
    返り: ``V`` [pitch の単位の 3 乗]、``V_px``、``V_discs``(円板の和、比較用)、``radius_px``(行ごとの半幅)、``axis_col``、
    ``axis_tilt_deg``、``rows_used``、``height_px``。
    **Raises** ``ValueError``: 被覆率でない / 粉が写っていない / 左右の縁に触れている(切れている)。"""
    a = _coverage(side, "side")
    p = _pos(pitch, "pitch")
    if not np.any(a >= float(threshold)):
        raise ValueError("revolution_volume_side: nothing in view (no pixel >= threshold)")
    if np.any(a[:, 0] > 0.5) or np.any(a[:, -1] > 0.5):
        raise ValueError("revolution_volume_side: the object touches the left/right edge (truncated)")
    c = _clean_coverage(a, threshold)
    w, cen = _row_widths(c)
    use = w > 0.0
    rows_used = np.flatnonzero(use)
    cols = np.arange(c.shape[1]) + 0.5
    ax = float(np.sum(c * cols[None, :]) / np.sum(c)) if axis_col is None else float(axis_col)
    Vpx = float(math.pi * np.sum(c * np.abs(cols - ax)[None, :]))
    tilt = 0.0
    if rows_used.size >= 3:
        f = np.polyfit(rows_used.astype(float), cen[use], 1)
        tilt = math.degrees(math.atan2(f[0], 1.0))
    return {"V": Vpx * p ** 3, "V_px": Vpx, "V_discs": float(np.sum(math.pi * (w / 2.0) ** 2)) * p ** 3, "radius_px": w / 2.0,
            "rows_used": int(rows_used.size), "axis_col": ax, "axis_tilt_deg": tilt,
            "height_px": float(rows_used[-1] - rows_used[0] + 1) if rows_used.size else 0.0}


def two_view_volume(side_a, side_b, pitch: float, *, threshold: float = 0.5) -> dict:
    """直交する 2 方向の側面像から体積 —— 行ごとの 2 つの弦 ``W_a``・``W_b`` を軸とする楕円の和
    ``V = Σ f π (W_a/2)(W_b/2) pitch³``。

    断面が楕円(軸対称でない山、縦長の盛り)なら厳密で、片方だけの回転体の仮定は楕円の扁平さの比で外れる(PoC で
    1.6 : 1 の楕円錐が片方だと −38 % / +60 %)。行の満ち具合 ``f``(平らな面が行の途中を横切る行、像 a で読む)で弦を
    ``W = w / f`` に直してから掛ける(幅の積は ``f²`` で数え落とすため)。雑音は先に消す。2 枚は同じ高さの刻み(同じ行が
    同じ高さ)であること。返り: ``V``、``V_a`` / ``V_b``(片方だけの回転体、Pappus)、``ellipticity``(弦の比の中央値
    max/min)。**Raises** ``ValueError``: 行数が違う / 被覆率でない / 空。"""
    A = _coverage(side_a, "side_a")
    B = _coverage(side_b, "side_b")
    if A.shape[0] != B.shape[0]:
        raise ValueError("two_view_volume: the two views must share the row grid, got %d and %d rows" % (A.shape[0], B.shape[0]))
    p = _pos(pitch, "pitch")
    if not (np.any(A >= threshold) and np.any(B >= threshold)):
        raise ValueError("two_view_volume: an empty view")
    Ac, Bc = _clean_coverage(A, threshold), _clean_coverage(B, threshold)
    wa, wb = Ac.sum(axis=1), Bc.sum(axis=1)
    f = _row_fill_fraction(Ac)
    Vpx = float(np.sum(math.pi * wa * wb / (4.0 * f)))
    both = (wa > 1.0) & (wb > 1.0)
    ell = float(np.median(np.maximum(wa[both], wb[both]) / np.minimum(wa[both], wb[both]))) if both.any() else float("nan")
    return {"V": Vpx * p ** 3, "V_px": Vpx, "V_a": revolution_volume_side(A, p, threshold=threshold)["V"],
            "V_b": revolution_volume_side(B, p, threshold=threshold)["V"], "ellipticity": ell}


def scoop_volume_read(side, rim_row: int, a_px: float, h_px: float, pitch: float, *, opaque: bool = True,
                      assume_level: bool = False, heap_min_frac: float = 0.005, level_tol: float = 0.01,
                      rim_full_frac: float = 0.95, fit_angle: bool = True) -> dict:
    """スプーンの側面像からすくった体積を読む。

    - ``opaque=True``(金属の椀): 縁より下は見えないので、縁より上の山を :func:`revolution_volume_side` で測り、
      すり切りの閉形式(:func:`spoon_bowl_volume`)に足す ``V = V_struck + V_above``。縁より上に何も無いと、すり切りか
      足りないかを側面から区別できない —— ``assume_level=True`` でなければ ``ValueError``(黙ってすり切りと言わない)。
    - ``opaque=False``(透明な椀・断面の像): 全体を Pappus の形で積分し、すり切りの ``1 − level_tol`` に満たなければ
      ``under`` として深さを閉形式 ``V_fill(y)`` の逆(二分法)で返す(平らな粉面を仮定)。
    - ``fit_angle``: 山が十分大きければ(左右 8 点以上)縁を地面とみなして granular の ``repose_angle_silhouette`` で
      山の斜面の角を読む(安息角との照合用、小さな山では ``None``)。
    返り: ``V``, ``V_struck``, ``V_above``, ``state``(``heaped`` / ``level`` / ``under``)、``heap_angle_deg``、
    ``heap_base_frac``(縁の行の山の幅 / 縁の直径)、``rim_full``(``heap_base_frac ≥ rim_full_frac``: 山の裾が縁まで届いている =
    椀が縁まで満ちている見込み。届いていない「山になりかけ」は縁の際が満ちきらず、不透明の読みは閉形式の分だけ多く出る ——
    MuJoCo で 0.90 のとき +9 %、0.99 のとき +1 %)、``axis_col``、``fill_depth_px``(透明のとき)。
    **Raises** ``ValueError``: ``rim_row`` が像の外 / 縁より上が空で ``assume_level`` でない(不透明のとき)/ 引数の範囲。"""
    a = _coverage(side, "side")
    level_tol = _nonneg(level_tol, "level_tol")
    rr = int(rim_row)
    if not (1 <= rr < a.shape[0]):
        raise ValueError("rim_row %r outside the image (1..%d)" % (rim_row, a.shape[0] - 1))
    geo = spoon_bowl_volume(a_px, h_px)
    p = _pos(pitch, "pitch")
    hm = _nonneg(heap_min_frac, "heap_min_frac")
    up = a[:rr]
    V_above_px = revolution_volume_side(up, 1.0)["V_px"] if np.any(up >= 0.5) else 0.0
    heaped = V_above_px > hm * geo["V_struck"]
    out = {"V_struck": geo["V_struck"] * p ** 3, "V_above": V_above_px * p ** 3, "heap_angle_deg": None,
           "heap_base_frac": None, "rim_full": None, "axis_col": None, "fill_depth_px": None}
    if heaped:
        w, cen = _row_widths(up)
        out["heap_base_frac"] = float(w[-1] / (2.0 * geo["a"]))
        out["rim_full"] = out["heap_base_frac"] >= rim_full_frac
        out["axis_col"] = float(np.nanmean(cen[w > 0]))
        if fit_angle:
            try:
                s = _G.repose_angle_silhouette(np.vstack([np.zeros((2, up.shape[1])), up]), toe_frac=0.1, apex_frac=0.2)
                out["heap_angle_deg"] = s["phi_deg"]
            except ValueError:
                out["heap_angle_deg"] = None
    if opaque:
        if not heaped and not assume_level:
            raise ValueError("scoop_volume_read: nothing above the rim — a side view of an opaque bowl cannot tell a level "
                             "scoop from an under-filled one (pass assume_level=True, or use a top view / the scale)")
        out["V"] = out["V_struck"] + (out["V_above"] if heaped else 0.0)
        out["state"] = "heaped" if heaped else "level"
        return out
    whole = revolution_volume_side(a, p)
    out["V"] = whole["V"]
    out["axis_col"] = whole["axis_col"] if out["axis_col"] is None else out["axis_col"]
    if heaped:
        out["state"] = "heaped"
        out["fill_depth_px"] = geo["h"]
        return out
    Vpx = whole["V_px"]
    if Vpx >= geo["V_struck"] * (1.0 - level_tol):
        out["state"], out["fill_depth_px"] = "level", geo["h"]
        return out
    lo, hi = 0.0, geo["h"]                                    # V_fill(y) は単調 → 二分法で深さ
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if spoon_bowl_volume(geo["a"], geo["h"], fill_depth=max(mid, 1e-12))["V_fill"] < Vpx:
            lo = mid
        else:
            hi = mid
    out["state"], out["fill_depth_px"] = "under", 0.5 * (lo + hi)
    return out


# ----------------------------------------------------------------------------------------------
# 体積 → 粒の数・質量 / 画像で足りるか(秤に譲る規律)
# ----------------------------------------------------------------------------------------------
def scoop_count(volume: float, radius: float, packing: float, *, density: float | None = None) -> dict:
    """体積と充填率から粒の数 ``N = V ν / ((4/3) π r³)``(``density`` を与えれば質量 ``N m_p`` とかさ密度 ``ν ρ_p``)。

    ``packing`` ν は **較正値**(同じ粒・同じ測り方で、数の分かった 1 回から ``N v_p / V_img`` を取る): 側面の輪郭は
    粒の外側の包絡なので、ν は充填そのものより小さく出る(包絡の分の体積を含む)。
    **Raises** ``ValueError``: 体積 < 0、半径 ≤ 0、ν が (0, 1] の外。"""
    V = _nonneg(volume, "volume")
    r = _pos(radius, "radius")
    nu = _pos(packing, "packing")
    if nu > 1.0:
        raise ValueError("packing must be in (0, 1], got %r" % packing)
    vp = 4.0 / 3.0 * math.pi * r ** 3
    out = {"N": V * nu / vp, "v_particle": vp, "packing": nu}
    if density is not None:
        rho = _pos(density, "density")
        out.update({"mass": out["N"] * vp * rho, "bulk_density": nu * rho, "m_particle": vp * rho})
    return out


def scoop_image_limit(a: float, pitch: float, radius: float, bulk_density: float, *, h: float | None = None,
                      phi_deg: float = 30.0, edge_px: float = 0.5, grain_frac: float = 0.25, min_a_over_d: float = 5.0,
                      target_mass: float | None = None, rel_tol: float = 0.05) -> dict:
    """山盛りのスプーンを側面像で量るときの不確かさの目安と「画像で足りるか、秤か」(**規則**、目安)。

    模型: 体積の誤差 ≈ 見える表面積 ``S`` × 境界の不確かさ ``e = edge_px·pitch + grain_frac·r``(縁の画素と、輪郭が粒の
    外側の包絡になる分のうち較正で消えない残り)。``S`` は山の円錐の側面 ``π a √(a² + H²)``(``H = a tan φ``)、体積は山盛りの
    閉形式(``h`` を与えなければ ``a/2``)。``grain_frac = 0.25`` は MuJoCo の剛体球(半径 2 mm、縁の半径 30 mm、充填率を
    1 回で較正)で 3 つの量 × 2 seed の数の誤差が 4.3 % 以内だった上限から逆算した 0.15 に余裕を見た値(PoC)。
    **粒が少ないと線形の外挿より速く崩れる**(半径 3.5 mm、縁の半径 / 粒径 4.3 で 9.5 %)ので、``a / d < min_a_over_d``
    は誤差によらず ``scale`` を返す。
    返り: ``sigma_V``、``sigma_mass = ρ_b σ_V``、``rel_err = σ_V / V``、``a_over_d``(縁の半径 / 粒径)、``a_min``(``rel_tol`` を
    満たす最小の縁の半径 —— 誤差は ``e / a`` に比例)、``verdict``(``image`` / ``scale``)、``reason``。``target_mass`` を
    与えると、同じ形の椀をその質量に合わせて縮めたときの相対誤差 ``rel_err_target`` で判定する。
    **Raises** ``ValueError``: 引数の範囲。"""
    a = _pos(a, "a")
    p = _pos(pitch, "pitch")
    r = _pos(radius, "radius")
    rb = _pos(bulk_density, "bulk_density")
    hh = _pos(h, "h") if h is not None else 0.5 * a
    e_px = _nonneg(edge_px, "edge_px")
    gf = _nonneg(grain_frac, "grain_frac")
    tol = _pos(rel_tol, "rel_tol")
    amin_d = _nonneg(min_a_over_d, "min_a_over_d")
    geo = spoon_bowl_volume(a, hh, phi_deg=phi_deg)
    e = e_px * p + gf * r

    def _rel(aa):
        k = aa / a
        Vg = geo["V_heaped"] * k ** 3
        S = math.pi * aa * math.sqrt(aa * aa + (geo["H_heap"] * k) ** 2)
        return S * e / Vg, S

    rel, S = _rel(a)
    out = {"sigma_V": S * e, "sigma_mass": rb * S * e, "rel_err": rel, "a_over_d": a / (2.0 * r), "V_heaped": geo["V_heaped"],
           "a_min": a * rel / tol, "surface": S, "boundary": e}
    aa = a
    if target_mass is not None:
        m = _pos(target_mass, "target_mass")
        aa = a * (m / (rb * geo["V_heaped"])) ** (1.0 / 3.0)
        out["a_for_target"] = aa
        out["rel_err_target"] = _rel(aa)[0]
        rel = out["rel_err_target"]
    if aa / (2.0 * r) < amin_d:
        out["verdict"], out["reason"] = "scale", "too few grains across the bowl (a/d = %.1f < %g)" % (aa / (2.0 * r), amin_d)
    elif rel > tol:
        out["verdict"], out["reason"] = "scale", "relative error %.3f > %g" % (rel, tol)
    else:
        out["verdict"], out["reason"] = "image", "relative error %.3f <= %g" % (rel, tol)
    return out


# ----------------------------------------------------------------------------------------------
# 傾けて注ぐ(口の開いた器、準静的)—— 自分の導出
# ----------------------------------------------------------------------------------------------
def _wedge_area(t, L, cap):
    """``∫₀ᴸ min(cap, x t) dx``(``t ≤ 0`` で 0)。"""
    if t <= 0.0:
        return 0.0
    xk = cap / t
    if xk >= L:
        return 0.5 * L * L * t
    return cap * L - 0.5 * cap * cap / t


def tilt_wedge_retained(theta_deg: float, phi_deg: float, L: float, h0: float) -> dict:
    """口に壁の無い器(床の長さ ``L``、奥壁は床に垂直で十分高い)に深さ ``h0`` で平らに盛った粉を、口を下げて θ 傾けた
    ときに残る量(2 次元断面、準静的、**自分の導出**)。

    口の前面は初めから安息角 φ の斜面(口に壁が無いので垂直の崖は立たない)。傾けると口を通る斜面は水平から φ を
    保ち、床から見ると ``φ − θ``。奥の平らな面は床に平行のまま(``θ < φ`` で安定)。保持断面
    ``A(θ) = ∫₀ᴸ min(h₀, x tan(φ − θ)) dx``、出た割合 ``F = 1 − A(θ) / A(0)``。出始めは θ = 0⁺(前面の楔からすぐ
    こぼれる)、斜面が奥壁に届く角 ``θ_b = φ − atan(h₀ / L)``、θ ≥ φ で全部出る。
    参考に granular の小角の近似(``tan φ − tan θ``、初めの量 ``L h₀``)の割合 ``F_small_angle`` と ``theta_c_small_angle_deg``
    も返す(MuJoCo でどちらが合うかを比べるため)。
    返り: ``A``, ``A0``, ``fraction``, ``theta_back_deg``, ``F_small_angle``, ``theta_c_small_angle_deg``。
    **Raises** ``ValueError``: θ が [0, 90) の外、φ が (0, 90) の外、``L``・``h0`` が ≤ 0。"""
    th = _nonneg(theta_deg, "theta_deg")
    if th >= 90.0:
        raise ValueError("theta_deg must be < 90, got %r" % theta_deg)
    phi = _angle(phi_deg, "phi_deg")
    L, h0 = _pos(L, "L"), _pos(h0, "h0")
    A0 = _wedge_area(math.tan(math.radians(phi)), L, h0)
    A = _wedge_area(math.tan(math.radians(phi - th)), L, h0) if th < phi else 0.0
    small = _G.spoon_tilt_dispense(th, phi, L, h0)
    return {"A": A, "A0": A0, "fraction": 1.0 - A / A0, "theta_back_deg": phi - math.degrees(math.atan2(h0, L)),
            "F_small_angle": small["fraction"], "theta_c_small_angle_deg": small["theta_c_deg"]}


def tilt_pour_rate(theta_deg: float, omega_deg_s: float, phi_deg: float, L: float, h0: float, B: float,
                   bulk_density: float) -> dict:
    """:func:`tilt_wedge_retained` の器を角速度 ω で傾けたときの準静的な流量 ``W = ρ_b B (−dA/dθ) ω`` [kg/s]
    (供給で決まる流量: 口の通す力より遅く傾けている限り、流量は傾ける速さで決まる)。

    ``dA/dθ``: 斜面が奥に届く前(``x_k = h₀ / t < L``)は ``−h₀² sec²(φ−θ) / (2 t²)``、届いた後は ``−½ L² sec²(φ−θ)``
    (``t = tan(φ − θ)``)。θ = 0 では ``h₀² / (2 sin² φ)``(前面の斜面の長さ ``h₀ / sin φ`` の楔)。
    返り: ``rate`` [kg/s]、``rate_area``(``−dA/dθ·ω`` [m²/s])、``fraction``(出た割合)、``theta_back_deg``。
    **Raises** ``ValueError``: 引数の範囲(ω ≤ 0 を含む)。"""
    w = _pos(omega_deg_s, "omega_deg_s")
    B, rb = _pos(B, "B"), _pos(bulk_density, "bulk_density")
    ret = tilt_wedge_retained(theta_deg, phi_deg, L, h0)
    th, phi = float(theta_deg), float(phi_deg)
    if th >= phi:
        dA = 0.0
    else:
        t = math.tan(math.radians(phi - th))
        sec2 = 1.0 + t * t
        xk = h0 / t
        dA = (0.5 * L * L * sec2) if xk >= L else (h0 * h0 * sec2 / (2.0 * t * t))
    rate_area = dA * math.radians(w)
    return {"rate": rb * B * rate_area, "rate_area": rate_area, "fraction": ret["fraction"], "theta_back_deg": ret["theta_back_deg"]}


def tilted_surface_read(side, lip_row: float, lip_col: float, theta_deg: float, L_px: float, *, wall_px: float | None = None,
                        threshold: float = 0.5, shell_px: float = 0.0, smooth_px: int = 1) -> dict:
    """傾いた器を横から見た像(被覆率)から、器に残る粉の断面積と奥の平らな面の高さを読む。

    器の座標: 口(``lip_row``, ``lip_col``、画素の端が整数)を原点に、床に沿って奥へ ``x``(口を下げて θ 傾けた床 = 画像の
    右上がり)、床に垂直に ``y``。``0 ≤ x ≤ L_px``・``0 ≤ y ≤ wall_px``(None = ``L_px``)の中の被覆率の和が断面積 [px²]
    (口の外の流れは数えない)。粒の側面像の輪郭は粒の外側の包絡なので、自由表面に沿って厚さ約 1 粒半径の殻が
    余分に入る —— ``shell_px``(粒の半径 [px] を渡す)× 自由表面の長さ(器の中の各列の粉面を ``smooth_px`` 列で
    移動平均した折れ線の長さ)を引いた ``area_corrected`` も返す。奥の平らな面の高さ ``plateau_px`` = 器の後ろ半分の
    粉面の床からの高さの中央値(楔の模型ではここは θ < θ_b の間変わらない; 実際の層は流れて薄くなる —— PoC で見る)。
    返り: ``area_px``, ``area_corrected``, ``surface_len_px``, ``plateau_px``(後ろ半分に粉面が無ければ None)。
    **Raises** ``ValueError``: 被覆率でない / 器の中が空 / 引数の範囲。"""
    a = _coverage(side, "side")
    th = _nonneg(theta_deg, "theta_deg")
    if th >= 90.0:
        raise ValueError("theta_deg must be < 90")
    L = _pos(L_px, "L_px")
    W = _pos(wall_px, "wall_px") if wall_px is not None else L
    shell = _nonneg(shell_px, "shell_px")
    k = int(smooth_px)
    if k < 1:
        raise ValueError("smooth_px must be >= 1")
    rows, cols = a.shape
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    yy, xx = np.mgrid[0:rows, 0:cols].astype(np.float64) + 0.5
    dx, up = xx - float(lip_col), float(lip_row) - yy          # 右へ、上へ
    xf = dx * c + up * s
    yf = -dx * s + up * c
    # 床と奥壁の側は 1 px 広げる(床を斜めに横切る画素の中心で切ると、床に接した粉の縁の画素を系統的に落とす:
    # 床の長さあたり 0.125 px²、θ = 24 度で −0.6 %、実測)。口の側(x < 0 = 流れ)は広げない
    inside = (xf >= 0.0) & (xf <= L + 1.0) & (yf >= -1.0) & (yf <= W)
    area = float(np.sum(a * inside))
    if area <= 0.0:
        raise ValueError("tilted_surface_read: nothing inside the container")
    m = (a >= float(threshold)) & inside
    js = np.flatnonzero(m.any(axis=0))
    assert len(js) >= 1
    first = np.array([np.flatnonzero(m[:, j])[0] for j in js], dtype=np.float64)
    top = first + 1.0 - a[first.astype(int), js]                 # 縁の画素の被覆率で副画素(上端からの位置)
    if k > 1 and top.size > k:
        top_s = np.convolve(np.pad(top, k // 2, mode="edge"), np.ones(k) / k, mode="valid")[:top.size]
    else:
        top_s = top
    ell = float(np.sum(np.hypot(np.diff(js.astype(float)), np.diff(top_s)))) if top.size > 1 else 0.0
    tdx, tup = js + 0.5 - float(lip_col), float(lip_row) - top
    txf, tyf = tdx * c + tup * s, -tdx * s + tup * c
    back = (txf >= 0.5 * L) & (txf <= L)
    return {"area_px": area, "area_corrected": area - shell * ell, "surface_len_px": ell,
            "plateau_px": float(np.median(tyf[back])) if back.any() else None}


# ----------------------------------------------------------------------------------------------
# 注ぎの流れ: 合成、Boolean 模型の逆、PIV と合わせた流量
# ----------------------------------------------------------------------------------------------
def stream_synth(flux: float, radius: float, width: float, *, v0: float = 0.3, s0: float = 0.02, rows: int = 192,
                 cols: int = 64, pitch: float = 0.5e-3, dt: float = 1.5e-3, n_frames: int = 16, supersample: int = 4,
                 seed: int | None = 0) -> dict:
    """口から落ちる粉の流れ(横から見た薄い帯)の被覆率のコマ列を合成する。

    粒は Poisson 過程(率 ``flux`` [個/s])で口を離れ、横位置は幅 ``width`` に一様、初速 ``v0`` で自由落下
    ``s = v₀ τ + ½ g τ²``(口からの落下距離 ``s``)。画像の行 0 は ``s = s0``、1 画素 ``pitch``。半径 ``radius`` の円板の和
    (副標本 ``supersample``² の被覆率)。位置が独立なので被覆率は Boolean 模型に従う —— 合成器はその式を使わない
    (:func:`stream_areal_density` の独立な被験者)。
    返り: ``frames``(``n_frames`` 枚)、``dt``、``pitch``、``s_rows``(行中心の落下距離)、``truth``(``flux``、
    ``crossings``(行中心の各高さを ``[0, n_frames·dt)`` に横切った実数の個数 / 時間 = 実現した流量)、``v``(行中心の
    自由落下の速さ)、``radius_px``)。**Raises** ``ValueError``: 引数の範囲。"""
    q, r, w = _pos(flux, "flux"), _pos(radius, "radius"), _pos(width, "width")
    v0, s0 = _nonneg(v0, "v0"), _nonneg(s0, "s0")
    p, dtt = _pos(pitch, "pitch"), _pos(dt, "dt")
    nr, nc, nf, ss = int(rows), int(cols), int(n_frames), int(supersample)
    if nr < 8 or nc < 8 or nf < 2 or ss < 1:
        raise ValueError("stream_synth: need rows, cols >= 8, n_frames >= 2, supersample >= 1")
    if w + 2 * r > nc * p:
        raise ValueError("stream_synth: stream width %g exceeds the image width %g" % (w + 2 * r, nc * p))
    rng = np.random.default_rng(seed)
    T = nf * dtt
    smax = s0 + nr * p + 2 * r
    travel = (-v0 + math.sqrt(v0 * v0 + 2 * G_STD * smax)) / G_STD
    t_lo = -travel - 2 * dtt
    n = int(rng.poisson(q * (T - t_lo)))
    tr = rng.uniform(t_lo, T, n)
    xr = rng.uniform(-w / 2, w / 2, n)
    pp = p / ss
    kk = int(math.ceil(r / pp))
    frames = []
    for k in range(nf):
        tau = k * dtt - tr
        m = tau > 0
        s = v0 * tau[m] + 0.5 * G_STD * tau[m] ** 2
        img = np.zeros((nr * ss, nc * ss), dtype=bool)
        for xi, si in zip(xr[m], s):
            i0, j0 = int((si - s0) / pp), int((xi + nc * p / 2) / pp)
            if i0 + kk < 0 or i0 - kk >= nr * ss:
                continue
            ii, jj = np.mgrid[max(i0 - kk, 0):min(i0 + kk + 1, nr * ss), max(j0 - kk, 0):min(j0 + kk + 1, nc * ss)]
            img[ii, jj] |= ((s0 + (ii + 0.5) * pp) - si) ** 2 + (((jj + 0.5) * pp - nc * p / 2) - xi) ** 2 <= r * r
        frames.append(img.reshape(nr, ss, nc, ss).mean(axis=(1, 3)))
    s_rows = s0 + (np.arange(nr) + 0.5) * p
    # 実現した流量: 各行中心の高さを [0, T) に横切った粒(横切る時刻 τ_s = 落下時間)
    tau_s = (-v0 + np.sqrt(v0 * v0 + 2 * G_STD * s_rows)) / G_STD
    tc = tr[None, :] + tau_s[:, None]
    crossings = ((tc >= 0.0) & (tc < T)).sum(axis=1) / T
    truth = {"flux": q, "crossings": crossings, "v": np.sqrt(v0 * v0 + 2 * G_STD * s_rows), "radius_px": r / p, "width": w,
             "n_particles": n}
    return {"frames": frames, "dt": dtt, "pitch": p, "s_rows": s_rows, "truth": truth}


def stream_areal_density(coverage, radius_px: float, *, c_max: float = 0.95, mode: str = "raise") -> np.ndarray:
    """被覆率から粒の中心の面密度 [個 / px²] を Boolean 模型で逆に解く ``n = −ln(1 − c) / (π r²)``。

    独立に置いた半径 ``r`` の円板の和の被覆率は ``c = 1 − exp(−n π r²)``(重なりを数え落とさない)。素朴な
    ``c / (π r²)`` は c = 0.8 で 2 倍近く数え落とす(PoC の門)。c が 1 に近いと逆は発散する(厚い流れは向こうが
    見えない): ``mode="raise"`` は ``c ≥ c_max`` の画素があれば ``ValueError``、``"clip"`` は ``c_max`` に切る(下限の推定に
    なる)。粒の位置が独立でない密な流れ(口の近く、粒が接している)では模型が外れる —— 限界。
    **Raises** ``ValueError``: 被覆率でない / 飽和(``mode="raise"``)/ 綴り違い。"""
    c = np.asarray(coverage, dtype=np.float64)
    if c.ndim not in (1, 2) or c.size == 0 or not np.all(np.isfinite(c)):
        raise ValueError("coverage must be a finite 1-D or 2-D array")
    if c.min() < -1e-9 or c.max() > 1.0 + 1e-9:
        raise ValueError("coverage must be in [0, 1]")
    r = _pos(radius_px, "radius_px")
    cm = _pos(c_max, "c_max")
    if cm >= 1.0:
        raise ValueError("c_max must be < 1")
    _choice(mode, "mode", ("raise", "clip"))
    if mode == "raise" and np.any(c >= cm):
        raise ValueError("stream_areal_density: %d pixels have coverage >= %g (saturated, too dense to count through)"
                         % (int(np.sum(c >= cm)), cm))
    c = np.clip(c, 0.0, cm)
    return -np.log1p(-c) / (math.pi * r * r)


def stream_flux_read(frames, dt: float, radius_px: float, *, band_rows=None, band_px: int = 9, window: int = 32,
                     particle_mass: float | None = None, c_max: float = 0.95, min_valid: float = 0.3,
                     min_crossings: float = 30.0) -> dict:
    """流れのコマ列から流量 [個/s] (と質量流量)を読む —— 速さは PIV(``pivops.piv_cross_correlate`` の全コマ対の中央値)、
    粒の線密度は時間平均の被覆率の Boolean 模型の逆(:func:`stream_areal_density`)を横に積分した ``λ``、流量 ``λ v``。

    ``band_rows`` = 測る行の中心の列(None なら PIV の窓の行中心を全部)。各帯は ``band_px`` 行の平均。速さは流れの
    向き(行が増える向き)の成分を、PIV の窓の行の間で線形に補間し、列は被覆率の重みで平均する。
    返り: ``rows``、``v_px``(px/コマ)、``v``(px/s)、``lam``(個/px)、``flux``(個/s)、``flux_naive``(素朴な ``c/(πr²)``)、
    ``flux_mean``、``flux_spread``(帯の間の (max − min)/平均 = 流量の連続の検査)、``mass_flux``(``particle_mass`` を与えたとき)、
    ``valid_fraction``(PIV の有限な窓の割合)、``c_max_seen``、``n_crossed_est``(記録の間に各帯を横切った粒の推定数
    ``flux·T``)、``rel_err_poisson``(``1/√n``、粒の数え上げの揺らぎ)、``reliable``(全帯で ``n ≥ min_crossings``)。
    粒が少ないと流量は数え上げの揺らぎそのもの(1 帯を横切る粒が 2 個なら ±70 %)—— ``reliable=False`` で知らせる。
    **Raises** ``ValueError``: コマが 2 未満 / 形が揃わない / PIV の有限な窓が ``min_valid`` 未満(粒が少なすぎて速さが
    読めない —— 壊れる場所)/ 帯が像の外 / 飽和。"""
    fr = [np.asarray(f, dtype=np.float64) for f in frames]
    if len(fr) < 2:
        raise ValueError("stream_flux_read: need >= 2 frames")
    sh = fr[0].shape
    if any(f.shape != sh for f in fr):
        raise ValueError("stream_flux_read: frames must share one shape")
    F = np.stack([_coverage(f, "frame") for f in fr])
    dtt = _pos(dt, "dt")
    r = _pos(radius_px, "radius_px")
    vs, valid = [], []
    info = None
    for k in range(len(fr) - 1):
        f, info = pivops.piv_cross_correlate(fr[k], fr[k + 1], window=int(window), overlap=0.5)
        vs.append(f[0])
        valid.append(info["valid_fraction"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # 粒の無い窓は全コマ nan(数えるのは下の vf)
        V = np.nanmedian(np.stack(vs), axis=0)
    vf = float(np.mean(np.isfinite(V)))
    if vf < _frac(min_valid, "min_valid"):
        raise ValueError("stream_flux_read: only %.2f of the PIV windows are finite (too few particles to read a speed)" % vf)
    wr, wc = info["rows"], info["cols"]
    mean_cov = F.mean(axis=0)
    hb = int(band_px) // 2
    rows = np.asarray(wr if band_rows is None else band_rows, dtype=np.float64).ravel()
    assert len(rows) >= 1
    out_v, out_lam, out_naive = [], [], []
    for rw in rows:
        i0, i1 = int(round(rw)) - hb, int(round(rw)) + hb + 1
        if i0 < 0 or i1 > sh[0]:
            raise ValueError("band around row %g leaves the image" % rw)
        band = mean_cov[i0:i1].mean(axis=0)
        n = stream_areal_density(band, r, c_max=c_max)
        out_lam.append(float(n.sum()))
        out_naive.append(float(band.sum() / (math.pi * r * r)))
        # 窓の列ごとの速さを被覆率で重み付け、行で線形補間
        wcol = np.array([band[max(int(c - window / 2), 0):int(c + window / 2) + 1].sum() for c in wc])
        vrow = []
        for i in range(V.shape[0]):
            ok = np.isfinite(V[i]) & (wcol > 0)
            vrow.append(float(np.sum(V[i][ok] * wcol[ok]) / np.sum(wcol[ok])) if ok.any() else np.nan)
        vrow = np.asarray(vrow)
        okr = np.isfinite(vrow)
        if okr.sum() < 1:
            raise ValueError("no finite PIV speed near row %g" % rw)
        out_v.append(float(np.interp(rw, wr[okr], vrow[okr])))
    v_px = np.asarray(out_v)
    lam = np.asarray(out_lam)
    flux = lam * v_px / dtt
    flux_naive = np.asarray(out_naive) * v_px / dtt
    fm = float(flux.mean())
    T = (len(fr) - 1) * dtt
    n_cross = flux * T
    with np.errstate(divide="ignore"):
        rel_p = np.where(n_cross > 0, 1.0 / np.sqrt(np.maximum(n_cross, 1e-300)), np.inf)
    out = {"rows": rows, "v_px": v_px, "v": v_px / dtt, "lam": lam, "flux": flux, "flux_naive": flux_naive, "flux_mean": fm,
           "n_crossed_est": n_cross, "rel_err_poisson": rel_p, "reliable": bool(np.all(n_cross >= min_crossings)),
           "flux_spread": float((flux.max() - flux.min()) / fm) if fm > 0 else float("nan"), "valid_fraction": vf,
           "c_max_seen": float(mean_cov.max())}
    if particle_mass is not None:
        out["mass_flux"] = fm * _pos(particle_mass, "particle_mass")
    return out


# ----------------------------------------------------------------------------------------------
# 第 2 実装: MuJoCo の場面(文字列だけ、mujoco 不要)
# ----------------------------------------------------------------------------------------------
def _sphere_lines(pts, r, density, mu_slide, mu_roll, condim):
    return "\n".join('<body pos="%.5f %.5f %.5f"><freejoint/><geom type="sphere" size="%.5f" density="%.1f" '
                     'friction="%.4f 0.005 %.6f" condim="%d"/></body>' % (x, y, z, r, density, mu_slide, mu_roll * r, int(condim))
                     for x, y, z in pts)


def _header(ts, cone, solver, iters, tc, extra=""):
    return ('<mujoco><option timestep="%g" gravity="0 0 -9.80665" integrator="implicitfast" cone="%s" solver="%s" iterations="%d" '
            'noslip_iterations="0"/>%s\n<default><geom solref="%.4f 1" solimp="0.95 0.99 0.001"/></default>\n'
            % (ts, cone, solver, int(iters), extra, tc))


def scoop_scene_mjcf(n_spheres: int = 500, radius: float = 0.002, *, a: float = 0.03, h: float = 0.012, rim_height: float = 0.10,
                     mu_slide: float = 0.16, mu_roll: float = 0.09, density: float = 2500.0, bowl_mu: float = 0.5,
                     tile: float = 0.006, drop_gap: float = 0.0003, timestep: float = 1.5e-3, contact_tc: float = 0.006,
                     solver_iterations: int = 50, solver: str = "CG", cone: str = "elliptic", condim: int = 6, seed: int = 0) -> dict:
    """球冠の椀(縁の半径 ``a``、深さ ``h``、縁の高さ ``rim_height``)を薄板のタイルで張り、真上から剛体球を
    ``n_spheres`` 個を椀の中から格子で積んで放す場面の MJCF 文字列(**mujoco 不要**、台帳に載る)。

    椀は内面が球(半径 ``R = (a² + h²) / 2h``)に接する厚さ 2 mm の板を、緯度の輪ごとに方位で並べる(``tile`` = 板の
    目安の辺、隙間ができないよう 1.35 倍に重ねる)。球は底から千鳥の格子で層に積み(椀の内面から ``r + drop_gap``
    離す)、縁より上は縁の円柱の中に積む —— 放すと縁より上の柱が崩れて山になり、あふれた球は縁から転がり落ちて床
    (高さ 0)に散る。上から落とすと跳ねて椀の中身まで飛び出した(500 個中 172 個しか残らず山ができない、実測)ので、
    すくい上げた直後の静かな状態を模す。摩擦の作法は granular の
    ``heap_scene_mjcf`` と同じ(転がり摩擦は無次元 μ_r × 半径)。
    返り: ``xml``, ``positions``(初期中心)、``info``(n, radius, a, h, R, rim_height, bottom_height, mass_each, timestep,
    n_tiles, V_struck)。**Raises** ``ValueError``: ``contact_tc < 2 timestep`` / ``h > a`` / 綴り違い / 球が入らない。"""
    if float(contact_tc) < 2.0 * float(timestep):
        raise ValueError("contact_tc (%g) must be >= 2 * timestep (%g)" % (contact_tc, timestep))
    _choice(cone, "cone", ("elliptic", "pyramidal"))
    _choice(solver, "solver", ("CG", "Newton", "PGS"))
    r = _pos(radius, "radius")
    n = int(n_spheres)
    if n < 1:
        raise ValueError("n_spheres must be >= 1")
    geo = spoon_bowl_volume(a, h)
    a, h, R = geo["a"], geo["h"], geo["R"]
    zr = _pos(rim_height, "rim_height")
    zb = zr - h
    if zb <= 4.0 * r:
        raise ValueError("rim_height too low for the bowl depth")
    zc = zb + R                                              # 球の中心
    th = 0.002
    t_ = _pos(tile, "tile")
    alpha_rim = math.atan2(a, R - h)
    n_ring = max(2, int(math.ceil(R * alpha_rim / t_)))
    geoms = []
    fric = 'friction="%.3f 0.005 %.6f" condim="%d"' % (_pos(bowl_mu, "bowl_mu"), mu_roll * r, int(condim))
    # 底の 1 枚
    geoms.append('<geom type="box" size="%.5f %.5f %.5f" pos="0 0 %.5f" rgba="0.75 0.75 0.8 0.35" %s/>'
                 % (0.75 * t_, 0.75 * t_, th / 2, zb - th / 2, fric))
    for i in range(1, n_ring + 1):
        al = alpha_rim * i / n_ring
        ring_r = R * math.sin(al)
        n_az = max(6, int(math.ceil(2.0 * math.pi * ring_r / t_)))
        seg_az = 2.0 * math.pi * ring_r / n_az
        seg_al = R * alpha_rim / n_ring
        for j in range(n_az):
            ps = 2.0 * math.pi * (j + 0.5 * (i % 2)) / n_az
            nx, ny, nz = math.sin(al) * math.cos(ps), math.sin(al) * math.sin(ps), -math.cos(al)
            cx, cy, cz = (R + th / 2) * nx, (R + th / 2) * ny, zc + (R + th / 2) * nz
            # 板の局所 x = 方位の接線、局所 y = 緯度の接線、局所 z = 外向きの法線
            tx, ty, tz = -math.sin(ps), math.cos(ps), 0.0
            geoms.append('<geom type="box" size="%.5f %.5f %.5f" pos="%.5f %.5f %.5f" xyaxes="%.5f %.5f %.5f %.5f %.5f %.5f" '
                         'rgba="0.75 0.75 0.8 0.35" %s/>'
                         % (0.675 * seg_az, 0.675 * seg_al, th / 2, cx, cy, cz, tx, ty, tz,
                            ny * tz - nz * ty, nz * tx - nx * tz, nx * ty - ny * tx, fric))
    rng = np.random.default_rng(seed)
    pts = []
    layer = 0
    gap = _nonneg(drop_gap, "drop_gap")
    step = 2.0 * r * 1.02
    while len(pts) < n:
        z = zb + r + gap + layer * step * 0.87                     # 千鳥(層間隔 √3/2·2r)
        if z <= zr:
            dz = zc - z
            lim = math.sqrt(max((R - r - gap) ** 2 - dz * dz, 0.0))   # 椀の内面から r + gap 離す
        else:
            lim = a - r                                          # 縁より上は縁の円柱の中(崩れて山になる)
        off = (layer % 2) * r
        cand = [(gx, gy) for gy in np.arange(-lim, lim + 1e-12, step) for gx in np.arange(-lim + off, lim + 1e-12, step)
                if math.hypot(gx, gy) <= lim]
        rng.shuffle(cand)
        for gx, gy in cand:
            if len(pts) < n:
                pts.append((gx + rng.uniform(-0.05, 0.05) * r, gy + rng.uniform(-0.05, 0.05) * r, z))
        layer += 1
        if layer > 400:
            raise ValueError("cannot stack %d spheres in the bowl" % n)
    pts = np.asarray(pts)
    xml = (_header(timestep, cone, solver, solver_iterations, _pos(contact_tc, "contact_tc"))
           + '<worldbody>\n<geom type="plane" size="1 1 0.1" friction="1.0 0.005 0.01" condim="%d"/>\n' % int(condim)
           + "\n".join(geoms) + "\n" + _sphere_lines(pts, r, _pos(density, "density"), mu_slide, mu_roll, condim)
           + "\n</worldbody></mujoco>")
    m_each = density * 4.0 / 3.0 * math.pi * r ** 3
    info = {"n": n, "radius": r, "a": a, "h": h, "R": R, "rim_height": zr, "bottom_height": zb, "mass_each": m_each,
            "timestep": float(timestep), "n_tiles": len(geoms), "V_struck": geo["V_struck"], "mu_slide": float(mu_slide),
            "mu_roll": float(mu_roll), "density": float(density)}
    return {"xml": xml, "positions": pts, "info": info}


def pour_scene_mjcf(L: float = 0.06, B: float = 0.04, h0: float = 0.016, radius: float = 0.002, *, wall: float = 0.04,
                    lip_height: float = 0.15, mu_slide: float = 0.16, mu_roll: float = 0.09, density: float = 2500.0,
                    floor_mu: float = 1.0, wall_mu: float = 0.3, timestep: float = 1.5e-3, contact_tc: float = 0.006,
                    solver_iterations: int = 50, solver: str = "CG", cone: str = "elliptic", condim: int = 6, seed: int = 0) -> dict:
    """口の開いた樋(床の長さ ``L``、幅 ``B``、奥壁と側壁の高さ ``wall``)に深さ ``h0`` まで剛体球を格子で詰めた場面の MJCF
    (**mujoco 不要**)。樋は mocap の body(``name="trough"``、原点 = 口の床の縁、高さ ``lip_height``)で、口を下げる向き
    (y 軸まわりに −θ)に回すのは :func:`scoop_mujoco_pour` が毎歩 ``mocap_quat`` を書いて行う。床は粗く(滑り摩擦
    ``floor_mu``、底の層が床ごと滑り出さない —— granular の粗い台と同じ役)、側壁は ``wall_mu``。床の口の側(x < 0)が
    開いていて、こぼれた球は落ちて地面(高さ 0)に届く。
    返り: ``xml``, ``positions``, ``info``(L, B, h0, wall, radius, lip_height, mass_each, n, timestep, A_fill = L·h0)。
    **Raises** ``ValueError``: ``h0 ≥ wall`` / ``contact_tc < 2 timestep`` / 球が 1 層も入らない / 綴り違い。"""
    L, B, h0, r, W = _pos(L, "L"), _pos(B, "B"), _pos(h0, "h0"), _pos(radius, "radius"), _pos(wall, "wall")
    if h0 >= W:
        raise ValueError("h0 (%g) must be below the wall height (%g)" % (h0, W))
    if float(contact_tc) < 2.0 * float(timestep):
        raise ValueError("contact_tc (%g) must be >= 2 * timestep (%g)" % (contact_tc, timestep))
    _choice(cone, "cone", ("elliptic", "pyramidal"))
    _choice(solver, "solver", ("CG", "Newton", "PGS"))
    if L < 4 * r or B < 4 * r or h0 < 2 * r:
        raise ValueError("trough too small for spheres of radius %g" % r)
    zl = _pos(lip_height, "lip_height")
    th = 0.002
    ff = 'friction="%.3f 0.005 %.6f" condim="%d"' % (_pos(floor_mu, "floor_mu"), mu_roll * r, int(condim))
    fw = 'friction="%.3f 0.005 %.6f" condim="%d"' % (_pos(wall_mu, "wall_mu"), mu_roll * r, int(condim))
    g = ['<geom type="box" size="%.5f %.5f %.5f" pos="%.5f 0 %.5f" rgba="0.6 0.6 0.65 0.5" %s/>' % (L / 2, B / 2 + th, th / 2, L / 2, -th / 2, ff),
         '<geom type="box" size="%.5f %.5f %.5f" pos="%.5f 0 %.5f" rgba="0.6 0.6 0.65 0.3" %s/>' % (th / 2, B / 2 + th, W / 2, L + th / 2, W / 2, fw),
         '<geom type="box" size="%.5f %.5f %.5f" pos="%.5f %.5f %.5f" rgba="0.6 0.6 0.65 0.15" %s/>' % (L / 2, th / 2, W / 2, L / 2, B / 2 + th / 2, W / 2, fw),
         '<geom type="box" size="%.5f %.5f %.5f" pos="%.5f %.5f %.5f" rgba="0.6 0.6 0.65 0.15" %s/>' % (L / 2, th / 2, W / 2, L / 2, -B / 2 - th / 2, W / 2, fw)]
    rng = np.random.default_rng(seed)
    pts = []
    step = 2.0 * r * 1.01
    nz = int(math.floor((h0 - 2 * r) / (step * 0.87))) + 1
    for k in range(nz):
        z = zl + r + 0.0002 + k * step * 0.87                     # 千鳥で詰める(層間隔 √3/2·2r)
        off = (k % 2) * r
        for gy in np.arange(-B / 2 + r + 0.0002 + off * 0.5, B / 2 - r, step):
            for gx in np.arange(r + 0.0002 + off, L - r, step):
                pts.append((gx + rng.uniform(-0.05, 0.05) * r, gy, z))
    if not pts:
        raise ValueError("no sphere fits in the trough")
    pts = np.asarray(pts)
    xml = (_header(timestep, cone, solver, solver_iterations, _pos(contact_tc, "contact_tc"))
           + '<worldbody>\n<geom type="plane" size="1 1 0.1" friction="1.0 0.005 0.01" condim="%d"/>\n' % int(condim)
           + '<body name="trough" mocap="true" pos="0 0 %.5f">\n%s\n</body>\n' % (zl, "\n".join(g))
           + _sphere_lines(pts, r, _pos(density, "density"), mu_slide, mu_roll, condim) + "\n</worldbody></mujoco>")
    m_each = density * 4.0 / 3.0 * math.pi * r ** 3
    info = {"L": L, "B": B, "h0": h0, "wall": W, "radius": r, "lip_height": zl, "mass_each": m_each, "n": int(len(pts)),
            "timestep": float(timestep), "A_fill": L * h0, "mu_slide": float(mu_slide), "mu_roll": float(mu_roll), "density": float(density)}
    return {"xml": xml, "positions": pts, "info": info}


# ----------------------------------------------------------------------------------------------
# facade(mujoco が要る、台帳の外)
# ----------------------------------------------------------------------------------------------
def _mujoco():
    try:
        import mujoco
    except ImportError as exc:
        raise ValueError("needs mujoco: %s" % exc)
    return mujoco


def scoop_mujoco_fill(n_spheres: int = 500, radius: float = 0.002, *, duration: float = 1.2, **scene) -> dict:
    """:func:`scoop_scene_mjcf` を MuJoCo で ``duration`` [s] 走らせ、椀に残った球を数える(**facade、mujoco が要る**)。

    残った球 = 軸からの距離が ``a + r`` 以内で、底より ``2r`` 下より上(床に落ちた球と、縁の外を落ちている途中の球は
    数えない)。返り: ``pos``(全球の最終中心)、``retained``(残った球の bool)、``n_retained``(**真値**)、``max_speed_end``、
    ``elapsed_s``、``info``(場面の info + steps)。**Raises** ``ValueError``: mujoco が無い / 場面の引数。"""
    mujoco = _mujoco()
    import time as _time
    sc = scoop_scene_mjcf(n_spheres, radius, **scene)
    info = dict(sc["info"])
    t0 = _time.perf_counter()
    model = mujoco.MjModel.from_xml_string(sc["xml"])
    data = mujoco.MjData(model)
    steps = int(round(_pos(duration, "duration") / info["timestep"]))
    for _ in range(steps):
        mujoco.mj_step(model, data)
    n = info["n"]
    pos = data.qpos.reshape(n, 7)[:, :3].copy()
    vel = data.qvel.reshape(n, 6)[:, :3]
    rad = np.hypot(pos[:, 0], pos[:, 1])
    ret = (rad <= info["a"] + info["radius"]) & (pos[:, 2] > info["bottom_height"] - 2.0 * info["radius"])
    info["steps"] = steps
    return {"pos": pos, "retained": ret, "n_retained": int(ret.sum()), "max_speed_end": float(np.linalg.norm(vel[ret], axis=1).max()) if ret.any() else 0.0,
            "elapsed_s": _time.perf_counter() - t0, "info": info}


def scoop_mujoco_pour(L: float = 0.06, B: float = 0.04, h0: float = 0.016, radius: float = 0.002, *, omega_deg_s: float = 15.0,
                      theta_end_deg: float = 40.0, settle: float = 0.4, record_every: int = 2, **scene) -> dict:
    """:func:`pour_scene_mjcf` の樋を ``settle`` [s] 置いてから(口の前面が崩れて安息角の斜面になる)、口の床の縁を軸に
    ω [度/s] で ``theta_end_deg`` まで傾け、最後に 0.3 s 止める(**facade、mujoco が要る**)。

    ``record_every`` 歩ごとに全球の中心(``frames``)、時刻、傾き θ、器の外に出た球の数(器の座標で口より前 ``x < −r``、
    **真値**)を記録する。数えるのは傾け始めの時点で器の中にあった球だけ(置く間にこぼれた球は初めの量に入れない)。
    返り: ``frames``, ``times``, ``theta_deg``, ``n_out``(各コマで外に出た数)、``n_start``(傾け始めに器にあった数)、
    ``start_index``(傾け始めのコマ)、``in_start``(その球の bool)、``elapsed_s``、``info``。
    **Raises** ``ValueError``: mujoco が無い / 引数の範囲。"""
    mujoco = _mujoco()
    import time as _time
    sc = pour_scene_mjcf(L, B, h0, radius, **scene)
    info = dict(sc["info"])
    n, r, ts, zl = info["n"], info["radius"], info["timestep"], info["lip_height"]
    w = math.radians(_pos(omega_deg_s, "omega_deg_s"))
    th_end = math.radians(_angle(theta_end_deg, "theta_end_deg"))
    t_set = _nonneg(settle, "settle")
    T = t_set + th_end / w + 0.3
    every = int(record_every)
    if every < 1:
        raise ValueError("record_every must be >= 1")
    t0 = _time.perf_counter()
    model = mujoco.MjModel.from_xml_string(sc["xml"])
    data = mujoco.MjData(model)
    steps = int(round(T / ts))
    frames, times, thetas, nout = [], [], [], []
    in_start = None
    start_index = None
    for st in range(steps + 1):
        t = st * ts
        th = min(max(t - t_set, 0.0) * w, th_end)
        data.mocap_quat[0] = (math.cos(-th / 2), 0.0, math.sin(-th / 2), 0.0)
        if st % every == 0:
            q = data.qpos.reshape(n, 7)[:, :3].copy()
            xr = q[:, 0] * math.cos(th) + (q[:, 2] - zl) * math.sin(th)       # 器の座標の床に沿った x
            yr = -q[:, 0] * math.sin(th) + (q[:, 2] - zl) * math.cos(th)
            inside = (xr > -r) & (yr > -2.0 * r)
            if in_start is None and t >= t_set:
                in_start = inside.copy()
                start_index = len(frames)
            frames.append(q)
            times.append(t)
            thetas.append(math.degrees(th))
            nout.append(int(np.sum(in_start & ~inside)) if in_start is not None else 0)
        if st < steps:
            mujoco.mj_step(model, data)
    info["steps"] = steps
    return {"frames": frames, "times": np.asarray(times), "theta_deg": np.asarray(thetas), "n_out": np.asarray(nout),
            "n_start": int(in_start.sum()) if in_start is not None else 0, "start_index": start_index, "in_start": in_start,
            "elapsed_s": _time.perf_counter() - t0, "info": info}
