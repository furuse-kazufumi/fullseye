# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cutting — 食材の切断を画像で測る: 刃の追跡・切り込み深さ・切片の厚み・切断面の粗さ・手首のたわみからの切断力(2026-10-05)。

物理シミュ × Fullseye 系列。題材はロボットの食材スライスの研究(arXiv:2404.02569、ICRA 2024)。規則だけで学習はしない。
画像の幾何と閉形式の切断力学をつなぎ、「画像 → 刃の高さ → 柔らかい手首のたわみ → 力 → 靱性 R」の鎖を閉じる。
外から来る真値は 3 つ:

  * **閉形式の切断力学**: Atkins, Interface Focus 6:20160019 (2016) の式 1.1〜1.4(摩擦なしの押し + 引き、ξ = slice/push 比):
    ``V/(Rw) = 1/(1+ξ²)``、``H/(Rw) = ξ/(1+ξ²)``、``F_res/(Rw) = 1/√(1+ξ²)``。本文の数(H/Rw は ξ = 1 で最大 0.5、傾けた刃を
    縦に動かすと ξ = tan i)を門にする。Williams & Patel, Interface Focus 6:20150108 (2016) の式 2.6(押すだけ、弾性の切りくず +
    Coulomb 摩擦 μ = tan β)と本文の例(μ = 0.2 で θo = 79°、最小 1.24)。式はどちらも PMC の無料公開版の本文と式の画像で照合した。
    ★ 摩擦と刃角を含む slice/push の式(Atkins 2003 / 2004 / 2006)は**未読**なので実装しない —— 組み合わせは ValueError。
  * **物理エンジン**: MuJoCo の正射影カメラで描いた刃を同じ追跡器で追い、手首の拘束力と比べる(facade
    :func:`cutting_mujoco_wrist`、mujoco が要るので台帳の外)。食材の抵抗は関節の摩擦損失として毎歩 ``R·w_eff·g(ξ)`` に置き換える。
  * **有限要素の力曲線(任意、非商用)**: 微分可能な切断シミュレーションの論文(Heiden ほか、arXiv:2105.12244、RSS 2021)が
    公開した FEM の刃の力の CSV(CC BY-NC 4.0)を :func:`cut_force_csv_load` で読む。データは repo に入れず、置き場所は
    環境変数 ``FULLSEYE_CUT_FORCE_DATA`` で渡す。商用の門には入れない。

台帳 ``cutting``(numpy + scipy、16 op):
  合成世界 :func:`cutting_scene` / :func:`cutting_face_render`(正面像)/ :func:`cutting_edge_render`(刃先方向の像)/
  :func:`cutting_episode_synth`(閉形式の切断 1 回分)/ :func:`cutting_wrist_mjcf`(MJCF 文字列、mujoco 不要);
  画像 :func:`knife_edge_track` / :func:`cut_depth_from_side` / :func:`slice_thickness_profile` / :func:`cut_surface_roughness`;
  力 :func:`force_from_wrist_displacement` / :func:`cut_force_atkins` / :func:`slice_push_ratio` / :func:`slice_push_from_track` /
  :func:`food_cut_width` / :func:`cut_force_fit` / :func:`cut_force_csv_load`。
mujoco 層(facade のみ): :func:`cutting_mujoco_wrist`。

正直に:
  * **力の真値は外から来ていない**。合成の力も当てはめも同じ Atkins の模型で作るので、画像 → R の鎖は配管の検査にしかならない
    (摩擦で力が 25 % 増えた世界でも R が 25 % 大きく出るだけで、模型の誤りは見つけられない。PoC の門で固定してある)。
  * 描画した食材は変形しない。刃先は直線を仮定し、食材の幅の中(隠れている所)は両側からの内挿。片刃(切片側が平ら)を仮定。
  * 靱性 R の実測値は引用しない(合成の R = 400 J/m² は材料値ではない)。画像つきの切断の公開データは見つからなかった。
  * MuJoCo の柔体(flexcomp)は破断しない(押し込むと頭打ちの後に要素へ潜り込む)ので、切断は摩擦損失で入れる。

規約: 長さ mm、力 N、靱性 J/m²、角は度(引数名 ``_deg``)。画像は (row, col)、画素中心が整数、z 上向き、z = 0 がまな板の上面。
刃の傾き θ は x 右・z 上で反時計回り。角度はすべて atan2 で出す(acos の床を踏まない)。
"""
from __future__ import annotations

import math
import os

import numpy as np

__all__ = [
    "cutting_scene", "cutting_face_render", "cutting_edge_render", "cutting_episode_synth", "cutting_wrist_mjcf",
    "knife_edge_track", "cut_depth_from_side", "slice_thickness_profile", "cut_surface_roughness",
    "force_from_wrist_displacement", "cut_force_atkins", "slice_push_ratio", "slice_push_from_track", "food_cut_width",
    "cut_force_fit", "cut_force_csv_load",
    # mujoco が要る(facade のみ、台帳の外)
    "cutting_mujoco_wrist",
]

_METHODS_EDGE = ("coverage", "gradient")
_FORCE_MODELS = ("slice_push", "wedge_friction")
_KINDS = ("face", "edge")

#: 既定の場面(mm)。``H`` / ``W`` / ``board_row`` は ``px_per_mm`` に比例して縮む(既定の解像度での値)。
_FACE = {"kind": "face", "px_per_mm": 8.0, "H": 480, "W": 800, "board_row": 440.0, "food_xc": 50.0, "food_w": 34.0,
         "food_h": 24.0, "blade_len": 70.0, "blade_h": 20.0, "tip_slant": 18.0}
_EDGE = {"kind": "edge", "px_per_mm": 20.0, "H": 560, "W": 520, "board_row": 520.0, "food_top": 24.0, "blade_tb": 1.6,
         "blade_hb": 4.0, "blade_h": 30.0}
_PIX_KEYS = ("H", "W", "board_row")

# 色(RGB、0..1)
_C_WALL = np.array([0.84, 0.85, 0.86])
_C_BOARD = np.array([0.42, 0.28, 0.16])
_C_BLADE = np.array([0.50, 0.53, 0.57])
_C_FOOD = np.array([0.95, 0.83, 0.42])
_C_DARK = np.array([0.10, 0.10, 0.12])


# ----------------------------------------------------------------------------------------------------------------------
# 入力の検査
def _req_finite(x, op, name, lo=None, hi=None, lo_open=False):
    if isinstance(x, bool):
        raise ValueError(f"{op}: {name} must be a number, got {x!r}")
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError(f"{op}: {name} must be a number, got {x!r}") from None
    if not math.isfinite(v):
        raise ValueError(f"{op}: {name} must be finite, got {v!r}")
    if lo is not None and (v < lo or (lo_open and v <= lo)):
        raise ValueError(f"{op}: {name} must be {'>' if lo_open else '>='} {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValueError(f"{op}: {name} must be <= {hi}, got {v}")
    return v


def _req_image(img, op, rgb_only=False):
    try:
        a = np.asarray(img, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError(f"{op}: image must be a numeric array") from None
    if a.ndim == 3 and a.shape[2] == 3:
        pass
    elif a.ndim == 2 and not rgb_only:
        pass
    else:
        raise ValueError(f"{op}: image must be {'(H, W, 3) RGB' if rgb_only else '2-D gray or (H, W, 3) RGB'}, "
                         f"got shape {a.shape}")
    if a.shape[0] < 16 or a.shape[1] < 16:
        raise ValueError(f"{op}: image too small {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: image contains non-finite values")
    return a


def _req_scene(scene, kind, op):
    if scene is None:
        return cutting_scene(kind)
    if not isinstance(scene, dict) or scene.get("kind") != kind:
        raise ValueError(f"{op}: scene must be the dict from cutting_scene({kind!r})")
    return scene


def _med(x):
    """短い列の中央値(np.median より 1 桁速い。窓は数 px なので並べ替えで十分)。"""
    x = np.sort(np.asarray(x, float).ravel())
    n = x.size
    if n == 0:
        return math.nan
    return 0.5 * float(x[(n - 1) // 2] + x[n // 2])


def _gray(a):
    return a.mean(axis=2) if a.ndim == 3 else a


# ----------------------------------------------------------------------------------------------------------------------
# 合成世界
def cutting_scene(kind: str = "face", px_per_mm: float | None = None, **overrides) -> dict:
    """合成の場面の諸元(dict)。``kind="face"`` = 正面像(カメラは刃の面の法線方向)、``"edge"`` = 刃先方向の像。

    正面像: 刃は食材より長く、食材の左右で刃先の直線が見える。食材の幅の中は食材に隠れる。キーは ``food_xc`` / ``food_w`` /
    ``food_h``(食材の中心・幅・高さ)、``blade_len`` / ``blade_h`` / ``tip_slant``(刃先の長さ・刃の高さ・先端の斜め部)。
    刃先方向の像: 刃は細い帯に見え、片刃の平らな面と食材の端面の距離が切片の厚み。キーは ``food_top``、``blade_tb``(峰の厚み)、
    ``blade_hb``(片刃の切刃の高さ)、``blade_h``。

    ``px_per_mm`` を変えると画素の寸法 ``H`` / ``W`` / ``board_row``(z = 0 の行)が比例して変わる(mm の寸法は同じ)。
    既定は正面像 8 px/mm(800×480)、刃先方向 20 px/mm(520×560)。知らないキーは ValueError(綴り壊しを黙って通さない)。"""
    op = "cutting_scene"
    if kind not in _KINDS:
        raise ValueError(f"{op}: kind must be one of {_KINDS}, got {kind!r}")
    base = dict(_FACE if kind == "face" else _EDGE)
    if px_per_mm is not None:
        s = _req_finite(px_per_mm, op, "px_per_mm", 1.0, 100.0)
        f = s / base["px_per_mm"]
        base["px_per_mm"] = s
        base["H"] = int(round(base["H"] * f))
        base["W"] = int(round(base["W"] * f))
        base["board_row"] = float(round(base["board_row"] * f))
    for k, v in overrides.items():
        if k not in base or k in ("kind", "px_per_mm"):
            raise ValueError(f"{op}: unknown key {k!r} for kind {kind!r} (known: {sorted(set(base) - {'kind'})})")
        base[k] = int(_req_finite(v, op, k, 16)) if k in ("H", "W") else _req_finite(v, op, k, 0.0, lo_open=k != "board_row")
    if not (1.0 <= base["board_row"] <= base["H"] - 1):
        raise ValueError(f"{op}: board_row must lie inside the image rows")
    return base


_SUB = (np.arange(8) + 0.5) / 8.0 - 0.5


def _cov_halfplane(H, W, ny, nx, c):
    """画素 (r, q) の被覆率: 半平面 ny·r + nx·q <= c((ny, nx) は単位法線)。境界から 1 px 以内だけ副列 8 本で縦を厳密に積分。"""
    r = np.arange(H, dtype=np.float64)[:, None]
    q = np.arange(W, dtype=np.float64)[None, :]
    d = ny * r + nx * q - c
    cov = (d <= 0).astype(np.float64)
    ri, qi = np.nonzero(np.abs(d) < 1.0)
    if ri.size == 0:
        return cov
    rr = ri.astype(np.float64)
    acc = np.zeros(ri.size)
    for ox in _SUB:
        x = qi + ox
        if abs(ny) < 1e-12:
            acc += (nx * x <= c)
            continue
        lim = (c - nx * x) / ny
        if ny > 0:
            acc += np.clip(lim - (rr - 0.5), 0.0, 1.0)
        else:
            acc += np.clip((rr + 0.5) - lim, 0.0, 1.0)
    cov[ri, qi] = acc / len(_SUB)
    return cov


def _cov_polygon(H, W, verts_rc):
    """凸多角形 (row, col) の被覆率 = 半平面の積(角の近くだけ近似)。"""
    v = np.asarray(verts_rc, float)
    n = len(v)
    assert n >= 3
    ctr = v.mean(axis=0)
    cov = np.zeros((H, W))
    r0, r1 = max(0, int(math.floor(v[:, 0].min())) - 2), min(H, int(math.ceil(v[:, 0].max())) + 3)
    c0, c1 = max(0, int(math.floor(v[:, 1].min())) - 2), min(W, int(math.ceil(v[:, 1].max())) + 3)
    if r0 >= r1 or c0 >= c1:
        return cov
    sub = np.ones((r1 - r0, c1 - c0))
    for i in range(n):
        p, q = v[i], v[(i + 1) % n]
        d = q - p
        ny, nx = d[1], -d[0]
        nrm = math.hypot(ny, nx)
        ny, nx = ny / nrm, nx / nrm
        c = ny * p[0] + nx * p[1]
        if ny * ctr[0] + nx * ctr[1] > c:          # 中心が内側になる向きへ
            ny, nx, c = -ny, -nx, -c
        sub *= _cov_halfplane(r1 - r0, c1 - c0, ny, nx, c - ny * r0 - nx * c0)   # 外接箱の中だけ(原点を (r0, c0) へ)
    cov[r0:r1, c0:c1] = sub
    return cov


_TEX_CACHE: dict = {}


def _smooth_texture(H, W, seed, scale, amp):
    key = (H, W, seed, round(scale, 6), amp)
    if key not in _TEX_CACHE:
        from scipy.ndimage import gaussian_filter
        rng = np.random.default_rng(seed)
        f = gaussian_filter(rng.standard_normal((H, W)), max(scale, 0.5))
        f /= (f.std() + 1e-12)
        if len(_TEX_CACHE) > 16:
            _TEX_CACHE.clear()
        _TEX_CACHE[key] = amp * f
    return _TEX_CACHE[key]


def _camera(img, gain, gradient, blur_px, noise, seed, op):
    gain = _req_finite(gain, op, "gain", 0.0, lo_open=True)
    gradient = _req_finite(gradient, op, "gradient", 0.0, 1.9)
    blur_px = _req_finite(blur_px, op, "blur_px", 0.0, 50.0)
    noise = _req_finite(noise, op, "noise", 0.0, 1.0)
    H, W = img.shape[:2]
    if gradient:
        img = img * (1.0 + gradient * (np.arange(W) / (W - 1) - 0.5))[None, :, None]
    img = img * gain
    if blur_px > 0:
        from scipy.ndimage import gaussian_filter
        img = np.stack([gaussian_filter(img[..., k], blur_px) for k in range(3)], -1)
    if noise > 0:
        img = img + np.random.default_rng(int(seed)).normal(0, noise, img.shape)
    return img


def _face_xz_to_rc(sc, x, z):
    return sc["board_row"] - np.asarray(z, float) * sc["px_per_mm"], np.asarray(x, float) * sc["px_per_mm"]


def _blade_polygon_xz(sc, heel_x, heel_z, theta_deg):
    """刃の 4 頂点 (x, z): heel 刃先・tip 刃先・tip 峰側・heel 峰。"""
    th = math.radians(theta_deg)
    u = np.array([math.cos(th), math.sin(th)])
    v = np.array([-math.sin(th), math.cos(th)])
    h = np.array([heel_x, heel_z])
    L, Hb, ts = sc["blade_len"], sc["blade_h"], sc["tip_slant"]
    return np.array([h, h + L * u, h + (L - ts) * u + Hb * v, h + Hb * v])


_LAYER_CACHE: dict = {}


def _face_layers(sc, food_visible):
    """動かない層(壁 + まな板、食材の被覆率と色、刃の光沢の列)を場面ごとに 1 回だけ作る。"""
    key = tuple(sorted((k, v) for k, v in sc.items())) + (bool(food_visible),)
    if key in _LAYER_CACHE:
        return _LAYER_CACHE[key]
    H, W, s = sc["H"], sc["W"], sc["px_per_mm"]
    k = s / 8.0
    base = np.ones((H, W, 3)) * _C_WALL
    base = base * (1.0 + _smooth_texture(H, W, 101, 20 * k, 0.01)[..., None])
    cb = np.clip((np.arange(H)[:, None] + 0.5) - sc["board_row"], 0, 1) * np.ones((1, W))
    base = base * (1 - cb[..., None]) + cb[..., None] * _C_BOARD
    sheen = 1.0 + 0.10 * np.sin(np.arange(W) / (90.0 * k))
    x0, x1 = sc["food_xc"] - sc["food_w"] / 2, sc["food_xc"] + sc["food_w"] / 2
    r_top = sc["board_row"] - sc["food_h"] * s
    c0, c1 = x0 * s, x1 * s
    fr0, fr1 = max(0, int(math.floor(r_top - 0.5))), min(H, int(math.ceil(sc["board_row"] + 0.5)) + 1)
    fc0, fc1 = max(0, int(math.floor(c0 - 0.5))), min(W, int(math.ceil(c1 + 0.5)) + 1)
    col = np.arange(fc0, fc1) + 0.0
    row = np.arange(fr0, fr1) + 0.0
    cx = np.clip(np.minimum(col + 0.5, c1) - np.maximum(col - 0.5, c0), 0, 1)
    cy = np.clip(np.minimum(row + 0.5, sc["board_row"]) - np.maximum(row - 0.5, r_top), 0, 1)
    cf = cy[:, None] * cx[None, :]
    tex = 1.0 + _smooth_texture(H, W, 7, 2.5 * k, 0.06)[fr0:fr1, fc0:fc1]
    food_rgb = _C_FOOD[None, None, :] * tex[..., None]
    if len(_LAYER_CACHE) > 8:
        _LAYER_CACHE.clear()
    _LAYER_CACHE[key] = (base, cf, food_rgb, (fr0, fr1, fc0, fc1), sheen)
    return _LAYER_CACHE[key]


def cutting_face_render(scene, heel_x: float, heel_z: float, theta_deg: float, gain: float = 1.0, gradient: float = 0.0,
                        blur_px: float = 0.0, noise: float = 0.0, seed: int = 0, food_visible: bool = True):
    """正面像(RGB、(H, W, 3) float)。壁 → まな板 → 刃 → 食材(手前)の順に、被覆率の解析描画で重ねる。

    ``heel_x`` / ``heel_z`` は刃の根元の刃先(mm)、``theta_deg`` は刃先の傾き。カメラは ``gain``(明るさの倍率)、``gradient``
    (左右の照明勾配、全幅で ±gradient/2)、``blur_px``(ガウスぼけの σ)、``noise``(加法の正規雑音の σ)。
    刃の面積は副列 8 本で縦方向を厳密に積分する(多角形の面積と 2e-4 以内、PoC の門)。"""
    op = "cutting_face_render"
    sc = _req_scene(scene, "face", op)
    heel_x = _req_finite(heel_x, op, "heel_x")
    heel_z = _req_finite(heel_z, op, "heel_z")
    theta_deg = _req_finite(theta_deg, op, "theta_deg", -60.0, 60.0)
    H, W, s = sc["H"], sc["W"], sc["px_per_mm"]
    base, cf, food_rgb, (fr0, fr1, fc0, fc1), sheen = _face_layers(sc, food_visible)
    img = base.copy()
    vx = _blade_polygon_xz(sc, heel_x, heel_z, theta_deg)
    rr, cc = _face_xz_to_rc(sc, vx[:, 0], vx[:, 1])
    cov = _cov_polygon(H, W, np.stack([rr, cc], 1))
    nz = np.flatnonzero(cov.any(axis=1))
    if nz.size:                                         # 刃の外接箱の行だけ混ぜる
        r0, r1 = int(nz[0]), int(nz[-1]) + 1
        cv = cov[r0:r1, :, None]
        img[r0:r1] = img[r0:r1] * (1 - cv) + cv * (_C_BLADE[None, None, :] * sheen[None, :, None])
    if food_visible and fr1 > fr0 and fc1 > fc0:        # 食材は手前(刃の上に重ねる)
        c = cf[..., None]
        img[fr0:fr1, fc0:fc1] = img[fr0:fr1, fc0:fc1] * (1 - c) + c * food_rgb
    return _camera(img, gain, gradient, blur_px, noise, seed, op)


def _end_face_fn(end_face, op):
    """端面 y(z) の指定 → z の配列を受けて y の配列を返す関数。スカラー(平らな面)か (z, y) の 2 列か dict。"""
    if isinstance(end_face, dict):
        if "z_mm" not in end_face or "y_mm" not in end_face:
            raise ValueError(f"{op}: end_face dict needs 'z_mm' and 'y_mm'")
        z, y = np.asarray(end_face["z_mm"], float), np.asarray(end_face["y_mm"], float)
    elif np.ndim(end_face) == 0:
        y0 = _req_finite(end_face, op, "end_face")
        return lambda zz: np.full(np.shape(zz), y0)
    else:
        a = np.asarray(end_face, float)
        if a.ndim != 2 or a.shape[1] != 2:
            raise ValueError(f"{op}: end_face must be a number, a dict(z_mm, y_mm) or an (N, 2) array of (z, y)")
        z, y = a[:, 0], a[:, 1]
    if z.ndim != 1 or z.shape != y.shape or z.size < 2 or not (np.all(np.isfinite(z)) and np.all(np.isfinite(y))):
        raise ValueError(f"{op}: end_face samples must be two equal finite 1-D arrays with >= 2 points")
    if np.any(np.diff(z) <= 0):
        raise ValueError(f"{op}: end_face z_mm must be strictly increasing")
    return lambda zz: np.interp(zz, z, y)


def cutting_edge_render(scene, end_face, cut_y_top: float, lean_deg: float, edge_z: float, blade: bool = True,
                        gain: float = 1.0, gradient: float = 0.0, blur_px: float = 0.0, noise: float = 0.0, seed: int = 0):
    """刃先方向の像(RGB)。暗い背景・食材(右側が本体)・刃(片刃、平らな面が切片側)。

    ``end_face`` は食材の端面 y(z)(mm): 数なら平らな面、``{"z_mm", "y_mm"}`` か (N, 2) の配列なら標本を線形補間(前の切断面の
    粗さを持たせる)。``cut_y_top`` は切断面(= 刃の平らな面)が食材の上面と交わる y、``lean_deg`` は刃の傾き(鉛直から、+ で下ほど
    本体側 = 下ほど切片が厚い)、``edge_z`` は刃先の高さ。端面は行ごとに縦 8 副行で被覆率を積分する。"""
    op = "cutting_edge_render"
    sc = _req_scene(scene, "edge", op)
    fn = _end_face_fn(end_face, op)
    cut_y_top = _req_finite(cut_y_top, op, "cut_y_top")
    lean_deg = _req_finite(lean_deg, op, "lean_deg", -30.0, 30.0)
    edge_z = _req_finite(edge_z, op, "edge_z")
    H, W, s = sc["H"], sc["W"], sc["px_per_mm"]
    img = np.ones((H, W, 3)) * _C_DARK
    rows = np.arange(H) + 0.0
    col = np.arange(W) + 0.0
    cov = np.zeros((H, W))
    zz = [(sc["board_row"] - (rows + oy)) / s for oy in _SUB]
    yy = [fn(z) * s for z in zz]
    ins = [(z >= 0) & (z <= sc["food_top"]) for z in zz]
    yv = np.concatenate([y[m] for y, m in zip(yy, ins)]) if any(m.any() for m in ins) else np.zeros(0)
    if yv.size:
        if not np.all(np.isfinite(yv)):
            raise ValueError(f"{op}: end_face gives non-finite y")
        b0 = int(min(max(math.floor(yv.min()) - 1, 0), W))     # この列より左は食材なし、b1 から右は全部食材
        b1 = int(min(max(math.ceil(yv.max()) + 2, 0), W))
        for z, yf, inside in zip(zz, yy, ins):
            cov[:, b0:b1] += np.clip((col[None, b0:b1] + 0.5) - yf[:, None], 0, 1) * inside[:, None]
        cov[:, b1:] = np.sum(ins, axis=0)[:, None]
        cov /= len(_SUB)
    tex = 1.0 + _smooth_texture(H, W, 11, 3.0 * s / 20.0, 0.05)
    img = img * (1 - cov[..., None]) + cov[..., None] * (_C_FOOD * tex[..., None])
    if blade:
        lam = math.radians(lean_deg)
        b_dir = np.array([-math.sin(lam), math.cos(lam)])      # 面に沿って上向き (y, z)
        a_dir = np.array([math.cos(lam), math.sin(lam)])       # 面の法線(本体側 +)
        y_edge = cut_y_top + (sc["food_top"] - edge_z) * math.tan(lam)
        e = np.array([y_edge, edge_z])
        pts = np.array([e, e + sc["blade_h"] * b_dir, e + sc["blade_h"] * b_dir + sc["blade_tb"] * a_dir,
                        e + sc["blade_hb"] * b_dir + sc["blade_tb"] * a_dir])
        rr, cc = sc["board_row"] - pts[:, 1] * s, pts[:, 0] * s
        cb = _cov_polygon(H, W, np.stack([rr, cc], 1))
        img = img * (1 - cb[..., None]) + cb[..., None] * _C_BLADE
    return _camera(img, gain, gradient, blur_px, noise, seed, op)


# ----------------------------------------------------------------------------------------------------------------------
# 1 次元の副画素の縁
def _edge_coverage(prof, i0, i1, a, b):
    """prof[i0:i1] が A(前)→ B(後)へ移る縁の位置(副画素、画素中心 = 整数)= 窓の中の A 側の長さ。"""
    seg = np.asarray(prof[i0:i1], float)
    if abs(b - a) < 1e-6 or seg.size == 0:
        return np.nan
    f = np.clip((seg - a) / (b - a), 0.0, 1.0)
    return i0 - 0.5 + (len(seg) - f.sum())


def _edge_at(prof, d1, i, sign, win, limit, method):
    """列 prof の段(行 i 付近、sign = +1 で暗 → 明)を副画素に。窓の幅はぼけの推定(微分の 2 次モーメント)で広げる。"""
    lo, hi = max(0, i - 15), min(limit, i + 16)
    w = sign * d1[lo:hi]
    if w.size == 0:
        return np.nan
    w = np.clip(w - 0.25 * w.max(), 0, None)          # 段の裾の模様(食材の肌理)を重みから外す
    if w.sum() <= 0:
        return np.nan
    rr = np.arange(lo, hi)
    c = float((w * rr).sum() / w.sum())
    sig = math.sqrt(float((w * (rr - c) ** 2).sum() / w.sum()))
    half = int(min(14, math.ceil(3.0 * sig) + 2))
    ic = int(round(c))
    a0, a1 = ic - half, ic + half + 1
    if a0 - win < 0 or a1 + win > limit:
        return np.nan
    if method == "gradient":
        return c
    A = _med(prof[a0 - win:a0])
    B = _med(prof[a1:a1 + win])
    return _edge_coverage(prof, a0, a1, A, B)


def _tls(P):
    """全最小二乗の直線(``measure.fit_line`` と同じ定式。向きは dx >= 0 にそろえる)。P は (row, col)。"""
    assert len(P) >= 2
    y, x = P[:, 0], P[:, 1]
    mx, my = x.mean(), y.mean()
    _, s, vt = np.linalg.svd(np.column_stack([x - mx, y - my]), full_matrices=False)
    dx, dy = vt[0, 0], vt[0, 1]
    if dx < 0:
        dx, dy = -dx, -dy
    resid = (x - mx) * (-dy) + (y - my) * dx
    return {"cy": float(my), "cx": float(mx), "dy": float(dy), "dx": float(dx), "rms": float(np.sqrt(np.mean(resid ** 2)))}


def _signed_dist(P, f):
    return (P[:, 1] - f["cx"]) * (-f["dy"]) + (P[:, 0] - f["cy"]) * f["dx"]


def _robust_line(P, reject_px, min_n):
    """外れ点を 10 % ずつ削る全最小二乗(最大残差 <= reject_px まで)。返り値 (fit or None, keep)。"""
    keep = np.ones(len(P), bool)
    for _ in range(60):
        if keep.sum() < max(min_n, 2):
            return None, keep
        fit = _tls(P[keep])
        res = np.abs(_signed_dist(P, fit))
        if res[keep].max() <= reject_px:
            keep = res <= reject_px
            return _tls(P[keep]), keep
        keep = keep & (res <= max(reject_px, float(np.percentile(res[keep], 90))))
    return None, keep


def _intersect(f1, f2):
    A = np.array([[f1["dy"], -f2["dy"]], [f1["dx"], -f2["dx"]]])
    b = np.array([f2["cy"] - f1["cy"], f2["cx"] - f1["cx"]])
    if abs(np.linalg.det(A)) < 1e-9:
        return None
    t, _ = np.linalg.solve(A, b)
    return np.array([f1["cy"] + t * f1["dy"], f1["cx"] + t * f1["dx"]])


def _food_mask(a):
    """食材 = 彩度(R − B)が壁・刃・まな板より高い画素。閾値は画像の R の中央値に比例(明るさの倍率に追従)。"""
    if a.ndim != 3:
        return np.zeros(a.shape, bool)
    mr = max(float(np.median(a[..., 0])), 1e-6)
    return (a[..., 0] - a[..., 2]) > mr * (0.25 + 0.05 / 0.84)


# ----------------------------------------------------------------------------------------------------------------------
# 刃の追跡(正面像)
def knife_edge_track(image, board_row: float | None = None, win: int = 6, reject_px: float = 1.0, method: str = "coverage") -> dict:
    """正面像から刃先の直線・峰・先端を出す(規則のみ)。

    手順: 輝度の縦の段が「暗 → 明」(刃 → 壁)になる行を列ごとに拾う → 食材の列(彩度の規則)と周辺 3 px を除く → 被覆率法で
    副画素に(窓はぼけの推定に合わせて広げる)→ 全最小二乗の直線(``measure.fit_line`` と同じ定式)→ 残差 > ``reject_px`` を外して
    当て直す。上側の境界(峰と先端の斜め線)も同じく拾い、峰の直線から外れた右側の連続部分 = 斜め線、刃先線との交点 = 先端。
    食材に隠れた列(``occluded_cols``)の刃先は、両側から当てた 1 本の直線の内挿になる。

    ``method``: ``"coverage"``(既定)か ``"gradient"``(微分の重心、比較用)。返り値: ``angle_deg``(x 右・z 上の反時計回り、
    atan2)、``line``(row = cy + (col − cx)·dy/dx の全最小二乗)、``slope``、``offset``、``tip_rc``(先端、見つからなければ None)、
    ``n_points``、``rms_px``、``cols_used``、``occluded_cols``。刃が写っていなければ ValueError。"""
    op = "knife_edge_track"
    if method not in _METHODS_EDGE:
        raise ValueError(f"{op}: method must be one of {_METHODS_EDGE}, got {method!r}")
    a = _req_image(image, op)
    win = int(_req_finite(win, op, "win", 2, 40))
    reject_px = _req_finite(reject_px, op, "reject_px", 0.05, lo_open=True)
    L = _gray(a)
    H, W = L.shape
    br = H - 1 if board_row is None else int(_req_finite(board_row, op, "board_row", 9, H))
    from scipy.ndimage import binary_dilation, uniform_filter1d
    food_cols = _food_mask(a)[:br].any(axis=0)
    excl = binary_dilation(food_cols, iterations=3)
    occl = np.flatnonzero(food_cols)
    Ls = uniform_filter1d(L, 3, axis=1)
    g = np.zeros_like(L)
    g[4:-4] = (Ls[8:] - Ls[:-8]) / 2.0                 # 段の強さ = 8 行離れた差(ぼけ σ ≲ 3 px まで段の高さが残る)
    g[max(br - 5, 0):] = 0
    g1 = np.zeros_like(L)
    g1[1:-1] = (Ls[2:] - Ls[:-2]) / 2.0
    gthr = 0.08 * float(np.percentile(L, 95))
    cols = np.flatnonzero(~excl)
    pts, Q = [], []
    if cols.size:
        imax = np.argmax(g[:, cols], axis=0)
        imin = np.argmin(g[:, cols], axis=0)
        for j, i_dn, i_up in zip(cols, imax, imin):
            if g[i_dn, j] >= gthr:
                r = _edge_at(L[:, j], g1[:, j], int(i_dn), +1, win, br, method)
                if np.isfinite(r):
                    pts.append((r, float(j)))
            if -g[i_up, j] >= gthr:
                r = _edge_at(L[:, j], g1[:, j], int(i_up), -1, win, br, method)
                if np.isfinite(r):
                    Q.append((r, float(j)))
    if len(pts) < 20:
        raise ValueError(f"{op}: only {len(pts)} blade-edge columns found; blade not visible")
    P = np.array(pts)
    fit, keep = _robust_line(P, reject_px, 20)
    if fit is None:
        raise ValueError(f"{op}: edge line not stable ({int(keep.sum())} inliers)")
    tip_rc, tip_fit, spine_fit = None, None, None
    if len(Q) >= 30:
        Q = np.array(Q)
        spine_fit, kq = _robust_line(Q, reject_px, 10)
        if spine_fit is not None:
            sl = Q[(~kq) & (Q[:, 1] > Q[kq, 1].max() + 2)]
            if len(sl) >= 6:
                tip_fit, _ = _robust_line(sl, reject_px, 6)
                if tip_fit is not None:
                    tip_rc = _intersect(fit, tip_fit)
    slope = fit["dy"] / fit["dx"] if abs(fit["dx"]) > 1e-12 else math.inf
    ang = -math.degrees(math.atan2(fit["dy"], fit["dx"]))     # 画像の行は下向き → x-z(上向き)では符号が反転
    ang = ((ang + 90.0) % 180.0) - 90.0
    return {"angle_deg": float(ang), "slope": float(slope), "offset": float(fit["cy"] - slope * fit["cx"]),
            "line": fit, "tip_rc": None if tip_rc is None else (float(tip_rc[0]), float(tip_rc[1])),
            "tip_fit": tip_fit, "spine_fit": spine_fit, "n_points": int(keep.sum()), "rms_px": float(fit["rms"]),
            "cols_used": (float(P[keep, 1].min()), float(P[keep, 1].max())),
            "occluded_cols": (int(occl.min()), int(occl.max())) if occl.size else None}


def _line_row_at(f, col):
    return f["cy"] + (col - f["cx"]) * f["dy"] / f["dx"]


def cut_depth_from_side(image, track, px_per_mm: float, board_row: float, win: int = 5) -> dict:
    """正面像の食材の上面(彩度の縁、列ごと副画素 → 中央値)と刃先の直線から切り込み深さ(mm)。

    深さ = 上面の z − 食材の幅の中央での刃先の z(:func:`knife_edge_track` の直線の内挿)。刃が曲がっていればそのまま誤差になる。
    返り値: ``depth_mm``、``top_z_mm``、``edge_z_mm``、``food_cols``(左右)、``n_cols``、``centre_col``。"""
    op = "cut_depth_from_side"
    a = _req_image(image, op, rgb_only=True)
    s = _req_finite(px_per_mm, op, "px_per_mm", 0.0, lo_open=True)
    br = _req_finite(board_row, op, "board_row", 9.0, a.shape[0] - 1)
    win = int(_req_finite(win, op, "win", 2, 30))
    if not isinstance(track, dict) or not isinstance(track.get("line"), dict):
        raise ValueError(f"{op}: track must be the dict returned by knife_edge_track")
    f = track["line"]
    if abs(f.get("dx", 0.0)) < 1e-9:
        raise ValueError(f"{op}: blade edge is vertical in the image; no depth")
    S = a[..., 0] - a[..., 2]
    food = _food_mask(a)
    cols = np.flatnonzero(food[: int(br)].sum(axis=0) > 5)
    if cols.size < 10:
        raise ValueError(f"{op}: food not found ({cols.size} columns)")
    c0, c1 = int(cols.min()) + 3, int(cols.max()) - 3
    d1 = np.zeros_like(S)
    d1[1:-1] = (S[2:] - S[:-2]) / 2.0
    tops = []
    for j in range(c0, c1 + 1):
        i = int(np.argmax(food[: int(br), j]))
        r = _edge_at(S[:, j], d1[:, j], i, +1, win, int(br) - 2, "coverage")
        if np.isfinite(r):
            tops.append(r)
    if len(tops) < 5:
        raise ValueError(f"{op}: food top edge not measurable ({len(tops)} columns)")
    r_top = float(np.median(tops))
    xc = 0.5 * (c0 + c1)
    z_top = (br - r_top) / s
    z_edge = (br - _line_row_at(f, xc)) / s
    return {"depth_mm": float(z_top - z_edge), "top_z_mm": float(z_top), "edge_z_mm": float(z_edge),
            "food_cols": (c0 - 3, c1 + 3), "n_cols": len(tops), "centre_col": float(xc)}


# ----------------------------------------------------------------------------------------------------------------------
# 切片の厚み(刃先方向の像)
def _blur_sigma_rows(S, cand):
    """端面(背景 → 食材)の段の微分の 2 次モーメントから、画像のぼけ σ(px)を行の中央値で出す。"""
    sig = []
    for i, j0 in cand:
        lo, hi = max(1, j0 - 14), min(S.shape[1] - 1, j0 + 15)
        if hi - lo < 8:
            continue
        d = (S[i, lo + 1:hi + 1] - S[i, lo - 1:hi - 1]) / 2.0
        d = np.clip(d - 0.25 * d.max(), 0, None)
        if d.sum() <= 0:
            continue
        x = np.arange(lo, hi)
        c = (d * x).sum() / d.sum()
        sig.append(math.sqrt(float((d * (x - c) ** 2).sum() / d.sum())))
    return float(np.median(sig)) if sig else 0.5


def slice_thickness_profile(image, px_per_mm: float, board_row: float, z_band=None, win: int = 4) -> dict:
    """刃先方向の像で、行ごとに「食材の端面」と「刃の平らな面」の副画素位置を出し、差 = 切片の厚み(mm)。

    各画素を 3 色(背景・食材・刃)の割合に**線形分解**する(彩度 R − B と輝度の 2 チャンネル + 和 = 1)。背景の割合は端面で
    1 → 0 に落ちる純粋な段、刃の割合は刃の面で 0 → 1 に上がる純粋な段なので、それぞれの窓の中の和が縁の位置になる(被覆率法)。
    ぼけは割合の和を変えないので、窓をぼけの推定(端面の段の 2 次モーメント σ)に合わせて ±(3σ + 1) px に広げれば偏らない。
    切片が窓より薄くても、2 つの段は別々の割合なので干渉しない。参照の色は行ごとに局所で取る(照明の左右勾配に追従)。
    刃の判定は「刃の輝度が背景と食材の間のどこにあるか」の比で行い、明るさの倍率(gain)に依らない。

    端面と刃の面はそれぞれ直線に乗るはず: 1.5 px より外れた行を外し、外れが 3 割を超えたら ValueError(黙って間違えない)。
    ``z_band``: (z_lo, z_hi) mm で使う行を絞る(片刃の切刃部を外すのに使う)。返り値: ``z_mm``、``thickness_mm``(行ごと)、
    ``mean_mm``、``lean_deg``(刃の面の鉛直からの傾き、atan2)、``face_line``、``end_line``、``n_rows``、``n_rejected``、``blur_px``。"""
    op = "slice_thickness_profile"
    a = _req_image(image, op, rgb_only=True)
    s = _req_finite(px_per_mm, op, "px_per_mm", 0.0, lo_open=True)
    br = _req_finite(board_row, op, "board_row", 1.0, a.shape[0] - 1)
    win = int(_req_finite(win, op, "win", 2, 30))
    if z_band is not None:
        if np.ndim(z_band) != 1 or len(z_band) != 2 or not (float(z_band[1]) > float(z_band[0])):
            raise ValueError(f"{op}: z_band must be (z_lo, z_hi) with z_hi > z_lo, got {z_band!r}")
    L = _gray(a)
    S = a[..., 0] - a[..., 2]
    H, W = L.shape
    s99 = float(np.percentile(S, 99))
    if s99 <= 0:
        raise ValueError(f"{op}: no food colour in the image")
    s_thr = 0.3 * s99                                   # 低めの閾値: 1 px の薄い切片(被覆率 0.5 前後)も拾う
    cand = []
    for i in range(H):
        z = (br - i) / s
        if z <= 0 or (z_band is not None and not (z_band[0] <= z <= z_band[1])):
            continue
        food = S[i] > s_thr
        if food.sum() < 4:
            continue
        j0 = int(np.argmax(food))
        rest = ~food[j0:]
        if not rest.any():
            continue
        k = j0 + int(np.argmax(rest))
        cand.append((i, j0, k))
    if len(cand) < 8:
        raise ValueError(f"{op}: blade face found on only {len(cand)} rows")
    sig = _blur_sigma_rows(S, [(i, j0) for i, j0, _ in cand])
    h = int(max(3, math.ceil(3.0 * sig) + 1))
    m = int(math.ceil(3.0 * sig)) + 1                   # 縁から m px 離れれば純粋な色
    rows = []
    for i, j0, k in cand:
        if j0 - h - 1 - win - 2 < 0 or k + h + 2 + win > W:
            continue
        after = S[i, k:] > s_thr                        # 刃の帯の向こう(本体)の始まり
        if not after.any():
            continue
        k2 = k + int(np.argmax(after))
        if k2 - k < 2 * h + win + 3:                    # 刃の帯がぼけに比べて細すぎ = 刃の色を測れない(偏るので拒否)
            continue
        rows.append((i, j0, k, k2))
    if len(rows) < 8:
        raise ValueError(f"{op}: blade face found on only {len(rows)} rows (blur {sig:.1f} px vs the blade band)")
    # 照明の左右勾配は列だけの関数: 刃の帯(一様な灰)の輝度を全行で列に直線当てはめ → 薄い切片の食材の参照色を補正する
    bc, bv = [], []
    for i, j0, k, k2 in rows:
        cc = np.arange(k + m, k2 - m)
        bc.append(cc)
        bv.append(L[i, k + m:k2 - m])
    bc, bv = np.concatenate(bc), np.concatenate(bv)
    if bc.size >= 8 and np.ptp(bc) >= 4:
        slope, icpt = np.polyfit(bc, bv, 1)
    else:
        slope, icpt = 0.0, float(np.median(bv)) if bv.size else 1.0

    def illum(x):
        return icpt + slope * x
    zs, ends, faces = [], [], []
    for i, j0, k, k2 in rows:
        rS, rL = S[i], L[i]
        bgs = slice(j0 - h - 1 - win - 2, j0 - h - 1)
        bg = (_med(rS[bgs]), _med(rL[bgs]))
        bls = slice(k + h + 2, k + h + 2 + win)
        bl = (_med(rS[bls]), _med(rL[bls]))
        if k - j0 >= 2 * m + 3:                         # 厚い: 切片の中の純粋な画素
            seg = slice(j0 + m + 1, k - m)
            fd = (_med(rS[seg]), _med(rL[seg]))
        else:                                           # 薄い: 刃の向こうの本体の頭を、照明の勾配で切片の位置へ戻す
            seg = slice(k2 + m + 1, k2 + m + 1 + win + 4)
            if seg.stop > W:
                continue
            ratio = illum(0.5 * (j0 + k)) / max(illum(0.5 * (seg.start + seg.stop - 1)), 1e-9)
            fd = (_med(rS[seg]) * ratio, _med(rL[seg]) * ratio)
        if fd[1] - bg[1] <= 1e-6 or (bl[1] - bg[1]) / (fd[1] - bg[1]) < 0.35:
            continue                                    # 刃の灰でない(背景の暗色が続いている)
        Mx = np.array([[bg[0], fd[0], bl[0]], [bg[1], fd[1], bl[1]], [1.0, 1.0, 1.0]])
        if np.linalg.cond(Mx) > 1e4:
            continue
        lo, hi = j0 - h - 1, k + h + 2
        X = np.linalg.inv(Mx) @ np.vstack([rS[lo:hi], rL[lo:hi], np.ones(hi - lo)])
        Bb, Bk = X[0], X[2]
        nb = (j0 + h + 2) - lo                          # 端面の窓 [lo, j0 + h + 2): 背景の割合は 1 → 0 の段
        e = lo - 0.5 + float(np.clip(Bb[:nb], 0, 1).sum())
        ks = (k - h - 1) - lo                           # 刃の面の窓 [k − h − 1, hi): 刃の割合は 0 → 1 の段
        f = (hi - 0.5) - float(np.clip(Bk[ks:], 0, 1).sum())
        if np.isfinite(e) and np.isfinite(f) and f > e:
            zs.append((br - i) / s)
            ends.append(e)
            faces.append(f)
    if len(zs) < 8:
        raise ValueError(f"{op}: blade face found on only {len(zs)} rows")
    zs, ends, faces = map(np.asarray, (zs, ends, faces))
    rowsz = br - zs * s
    ff, kf = _robust_line(np.column_stack([rowsz, faces]), 1.5, 8)
    fe, ke = _robust_line(np.column_stack([rowsz, ends]), 1.5, 8)
    n_all = len(zs)
    keep = kf & ke if (ff is not None and fe is not None) else np.zeros(n_all, bool)
    if keep.sum() < max(8, 0.7 * n_all):
        raise ValueError(f"{op}: only {int(keep.sum())}/{n_all} rows lie on straight blade-face / end-face lines "
                         "(noise or blur too strong to separate slice from blade)")
    zs, ends, faces, rowsz = zs[keep], ends[keep], faces[keep], rowsz[keep]
    th = (faces - ends) / s
    ff = _tls(np.column_stack([rowsz, faces]))
    fe = _tls(np.column_stack([rowsz, ends]))
    # 鉛直からの傾き: 行が下る(z が減る)ほど col が増える向きを +
    lean = math.degrees(math.atan2(ff["dx"] * (1.0 if ff["dy"] >= 0 else -1.0), abs(ff["dy"])))
    return {"z_mm": zs, "thickness_mm": th, "mean_mm": float(th.mean()), "lean_deg": float(lean), "face_line": ff,
            "end_line": fe, "n_rows": int(len(zs)), "n_rejected": int(n_all - len(zs)), "blur_px": sig}


def cut_surface_roughness(image, px_per_mm: float, board_row: float, z_band, n_sampling: int = 5) -> dict:
    """切った後の端面のシルエット(行ごと副画素)を断面とみなし、最小二乗の直線を引いて ISO 4287 のパラメータ(µm)を出す。

    パラメータは ``roughness.profile_params``(Ra / Rq / Rz / Rt …)をそのまま呼ぶ。断面は行の高さ 1 px で平均されるので、
    正弦の凹凸は箱型の閉形式 ``sinc(πΔ/λ)``(Δ = 1 px)倍に弱まる。平らな面でも測りの床(雑音と肌理による Rq)が残るので、
    比べるときは床を二乗で引く。Rz は雑音の山に引っ張られる(床の扱いは Rq でだけ意味がある)。
    返り値: ``profile_um``(行ごとの偏差)、``z_mm``、``params``、``dz_um``(標本間隔)、``n_rows``。"""
    op = "cut_surface_roughness"
    a = _req_image(image, op)
    s = _req_finite(px_per_mm, op, "px_per_mm", 0.0, lo_open=True)
    br = _req_finite(board_row, op, "board_row", 1.0, a.shape[0] - 1)
    if z_band is None or np.ndim(z_band) != 1 or len(z_band) != 2 or not (float(z_band[1]) > float(z_band[0])):
        raise ValueError(f"{op}: z_band must be (z_lo, z_hi) with z_hi > z_lo, got {z_band!r}")
    S = a[..., 0] - a[..., 2] if a.ndim == 3 else _gray(a)
    H, W = S.shape
    lo, hi = float(np.percentile(S, 2)), float(np.percentile(S, 98))
    if hi - lo < 1e-3:
        raise ValueError(f"{op}: no contrast between food and background")
    zs, ys = [], []
    for i in range(H):
        z = (br - i) / s
        if not (z_band[0] <= z <= z_band[1]):
            continue
        row = S[i]
        food = row > 0.5 * (lo + hi)
        if not food.any():
            continue
        j0 = int(np.argmax(food))
        if j0 < 8 or j0 > W - 10:
            continue
        e = _edge_coverage(row, j0 - 3, j0 + 4, lo, _med(row[j0 + 3:j0 + 9]))
        if np.isfinite(e):
            zs.append(z)
            ys.append(e / s)
    if len(zs) < 40:
        raise ValueError(f"{op}: only {len(zs)} silhouette rows in z_band")
    zs, ys = np.asarray(zs), np.asarray(ys)
    order = np.argsort(zs)
    zs, ys = zs[order], ys[order]
    A = np.column_stack([zs, np.ones_like(zs)])
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    dev_um = (ys - A @ coef) * 1000.0
    import roughness
    prm = roughness.profile_params(dev_um, dx=1000.0 / s, n_sampling=int(n_sampling))
    return {"profile_um": dev_um, "z_mm": zs, "params": prm, "dz_um": 1000.0 / s, "n_rows": int(len(zs))}


# ----------------------------------------------------------------------------------------------------------------------
# 力
def force_from_wrist_displacement(z_meas_mm, z_cmd_mm, k_n_per_mm: float):
    """柔らかい手首(縦のばね k、N/mm)なら押し力 F = k (z_meas − z_cmd): 刃が指令より上に残った分が力(N の配列)。

    準静的の近似: 手首の慣性と減衰は入らない。減衰 c の手首を速さ v で下げると、空中での風袋引きに c·v が入り、刃が食材に
    止められている間だけそれが抜ける —— 誤差の上限は c·v(PoC の --full で MuJoCo の拘束力と比べる)。"""
    op = "force_from_wrist_displacement"
    k = _req_finite(k_n_per_mm, op, "k_n_per_mm", 0.0, lo_open=True)
    try:
        zm = np.asarray(z_meas_mm, float)
        zc = np.asarray(z_cmd_mm, float)
    except (TypeError, ValueError):
        raise ValueError(f"{op}: positions must be numeric arrays") from None
    if zm.shape != zc.shape:
        raise ValueError(f"{op}: shapes differ {zm.shape} vs {zc.shape}")
    if not (np.all(np.isfinite(zm)) and np.all(np.isfinite(zc))):
        raise ValueError(f"{op}: non-finite positions")
    return k * (zm - zc)


def cut_force_atkins(R_j_per_m2: float, width_mm: float, xi: float = 0.0, wedge_deg: float | None = None, mu: float = 0.0,
                     model: str | None = None) -> dict:
    """柔らかい固体の切断力の閉形式(尺度 = 靱性 R × 切っている幅 w、R と w の 1 次)。返り値 dict(N)。

    ``model="slice_push"``(既定、``wedge_deg`` なし): 摩擦なしの押し + 引き(Atkins 2016、Interface Focus 6:20160019 の
    式 1.2〜1.4): ``V/(Rw) = 1/(1+ξ²)``、``H/(Rw) = ξ/(1+ξ²)``、``F_res/(Rw) = 1/√(1+ξ²)``。ξ = 刃に沿う速度 / 刃を横切る速度。
    ``model="wedge_friction"``(``wedge_deg`` を渡す、押しだけ ξ = 0): 弾性の切りくず + Coulomb 摩擦(Williams & Patel 2016、
    Interface Focus 6:20150108 の式 2.6、μ = tan β): ``Fc/(b Gc) = 1 / ((1 − cos θ) + sin θ / tan(β + θ))``。θ は原文の工具角。
    最小は θ + β = 90° で ``1/(1 − sin β)``。
    ★ 摩擦と刃角が入った slice/push の式は未読なので実装しない: ξ > 0 と ``wedge_deg`` / ``mu`` の同時指定は ValueError。

    返り値: ``V``(押し)、``H``(引き、wedge_friction では nan)、``F_res``、``scale`` = R·w、wedge_friction では ``Fc_over_bGc``。"""
    op = "cut_force_atkins"
    R = _req_finite(R_j_per_m2, op, "R_j_per_m2", 0.0, lo_open=True)
    w = _req_finite(width_mm, op, "width_mm", 0.0)
    xi = _req_finite(xi, op, "xi", 0.0)
    mu = _req_finite(mu, op, "mu", 0.0, 10.0)
    if model is None:
        model = "wedge_friction" if wedge_deg is not None else "slice_push"
    if model not in _FORCE_MODELS:
        raise ValueError(f"{op}: model must be one of {_FORCE_MODELS}, got {model!r}")
    scale = R * w * 1e-3                                  # J/m² × m = N
    if model == "slice_push":
        if wedge_deg is not None or mu != 0.0:
            raise ValueError(f"{op}: slice_push is the frictionless form; the friction/wedge form with xi > 0 "
                             "has not been read and is not implemented")
        d = 1.0 + xi * xi
        return {"V": scale / d, "H": scale * xi / d, "F_res": scale / math.sqrt(d), "scale": scale}
    if xi != 0.0:
        raise ValueError(f"{op}: wedge_friction is push-only (xi = 0); the combined form has not been read")
    if wedge_deg is None:
        raise ValueError(f"{op}: wedge_friction needs wedge_deg")
    th = math.radians(_req_finite(wedge_deg, op, "wedge_deg", 0.0, 90.0, lo_open=True))
    beta = math.atan(mu)
    # sin θ / tan(β + θ) = sin θ · cos(β + θ) / sin(β + θ)(β + θ ≥ 90° でも連続)
    den = (1.0 - math.cos(th)) + math.sin(th) * math.cos(beta + th) / math.sin(beta + th)
    if den <= 0:
        raise ValueError(f"{op}: no positive cutting force for wedge {wedge_deg} deg, mu {mu}")
    fc = scale / den
    return {"V": fc, "H": float("nan"), "F_res": fc, "scale": scale, "Fc_over_bGc": 1.0 / den}


def slice_push_ratio(theta_deg: float, vx: float, vz: float) -> float:
    """刃先の傾き θ(x-z、反時計回り)と刃の速度 (vx, −vz)(vz > 0 で下へ)から slice/push 比 ξ。

    刃先方向 u = (cos θ, sin θ)、法線 n = (−sin θ, cos θ) として ξ = |v·u| / |v·n|。vx = 0 なら ξ = tan|θ|(Atkins 2016 の本文
    「傾けた刃を縦に動かすと ξ = tan i」)に戻る。刃が自分の刃先に沿って動く(押しが無い)と ValueError。"""
    op = "slice_push_ratio"
    th = math.radians(_req_finite(theta_deg, op, "theta_deg", -89.0, 89.0))
    vx = _req_finite(vx, op, "vx")
    vz = _req_finite(vz, op, "vz")
    along = vx * math.cos(th) - vz * math.sin(th)
    across = -vx * math.sin(th) - vz * math.cos(th)
    if abs(across) < 1e-12 * max(1.0, abs(vx), abs(vz)):
        raise ValueError(f"{op}: blade moves along its own edge (no push); xi is infinite")
    return abs(along) / abs(across)


def food_cut_width(theta_deg: float, edge_z_at_xc: float, food_w: float, food_top: float) -> float:
    """刃先の直線(食材の中央で高さ ``edge_z_at_xc``、傾き θ)が食材の上面より下にある x の長さ = 切っている幅(mm、閉形式)。"""
    op = "food_cut_width"
    t = math.tan(math.radians(_req_finite(theta_deg, op, "theta_deg", -89.0, 89.0)))
    ez = _req_finite(edge_z_at_xc, op, "edge_z_at_xc")
    w = _req_finite(food_w, op, "food_w", 0.0)
    top = _req_finite(food_top, op, "food_top")
    if abs(t) < 1e-15:
        return float(w) if ez < top else 0.0
    xs = (top - ez) / t                                  # 刃先が上面と交わる x(食材の中央が 0)
    length = xs + w / 2 if t > 0 else w / 2 - xs
    return float(min(max(length, 0.0), w))


def slice_push_from_track(theta_deg: float, x_mm, z_mm) -> float:
    """刃の 1 点の軌跡 (x, z)(画像から)と刃先の傾き θ(画像から)で ξ を出す。速度は軌跡の直線当てはめの向き(ξ は比)。

    押している区間だけを渡すこと。入り始め(手首が縮む途中)を混ぜると刃が指令より遅れて ξ が偏る —— 刃が食材の全幅を
    切っている定常区間を使う(PoC で 0.63 → 0.57 = 真値に戻ることを確かめた)。"""
    op = "slice_push_from_track"
    try:
        x = np.asarray(x_mm, float)
        z = np.asarray(z_mm, float)
    except (TypeError, ValueError):
        raise ValueError(f"{op}: track must be numeric arrays") from None
    if x.shape != z.shape or x.ndim != 1 or x.size < 3:
        raise ValueError(f"{op}: need two equal 1-D arrays with >= 3 samples")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(z))):
        raise ValueError(f"{op}: non-finite track")
    if abs(z[-1] - z[0]) < 1e-9:
        raise ValueError(f"{op}: no push motion (dz = 0); xi undefined")
    t = np.arange(x.size, dtype=float)
    vx = float(np.polyfit(t, x, 1)[0])
    vz = -float(np.polyfit(t, z, 1)[0])
    return slice_push_ratio(theta_deg, vx, vz)


def cut_force_fit(F_n, w_eff_mm, xi: float, min_w_mm: float = 2.0) -> dict:
    """切断中の力の列 F(N)と切っている幅 w_eff(mm)から靱性 R(J/m²)を原点を通る最小二乗で出す。

    模型: ``F = R · w_eff · g(ξ)``、g = 1/(1+ξ²)(:func:`cut_force_atkins` の slice_push、摩擦なし)。w_eff < ``min_w_mm`` の点
    (入り始め)は使わない。★ 合成の真値を同じ模型で作るとこの当てはめは配管の検査にしかならず、摩擦の分は R に吸い込まれる
    (返り値の ``model`` に書く)。返り値: ``R``、``rms_n``、``n``、``g``、``model``。"""
    op = "cut_force_fit"
    try:
        F = np.asarray(F_n, float)
        w = np.asarray(w_eff_mm, float)
    except (TypeError, ValueError):
        raise ValueError(f"{op}: F_n and w_eff_mm must be numeric arrays") from None
    xi = _req_finite(xi, op, "xi", 0.0)
    min_w = _req_finite(min_w_mm, op, "min_w_mm", 0.0)
    if F.shape != w.shape or F.ndim != 1:
        raise ValueError(f"{op}: F_n and w_eff_mm must be equal 1-D arrays")
    if not (np.all(np.isfinite(F)) and np.all(np.isfinite(w))):
        raise ValueError(f"{op}: non-finite input")
    m = w >= max(min_w, 1e-9)
    if m.sum() < 3:
        raise ValueError(f"{op}: only {int(m.sum())} samples with w_eff >= {min_w} mm")
    g = 1.0 / (1.0 + xi * xi)
    a = w[m] * 1e-3 * g
    R = float(np.dot(a, F[m]) / np.dot(a, a))
    if R <= 0:
        raise ValueError(f"{op}: non-positive toughness fit ({R:.3g}); forces have the wrong sign")
    res = F[m] - R * a
    return {"R": R, "rms_n": float(np.sqrt(np.mean(res ** 2))), "n": int(m.sum()), "g": g,
            "model": "frictionless slice/push (friction is absorbed into R)"}


def cutting_episode_synth(R: float = 400.0, theta_deg: float = 4.0, vx: float = 6.0, vz: float = 4.0, k_wrist: float = 4.0,
                          dt: float = 0.1, n_frames: int = 40, heel_x0: float = 12.0, edge_start: float = 27.0,
                          scene=None) -> dict:
    """閉形式の運動で切断の 1 回分を作る(準静的、剛塑性の食材 + 縦だけ柔らかい手首)。返り値 dict(列は numpy 配列)。

    指令: 刃の根元を (vx, −vz) mm/s で動かす(``k_wrist`` N/mm)。食材は切れ始めるまで動かず、切れている間の押し力は
    ``R · w_eff · 1/(1+ξ²)``(:func:`cut_force_atkins` の slice_push)。刃は「指令 + F/k」の高さに止まり、切った所は戻らない。
    刃先の最下点(食材の幅の中)がまな板の 0.3 mm 上に来たら止める。
    返り値: ``t``、``heel_x``、``heel_z_cmd``、``heel_z``、``edge_z_c``(食材中央での刃先の高さの真値)、``F``(押し力の真値)、
    ``w_eff``、``xi``、``params``。"""
    op = "cutting_episode_synth"
    sc = _req_scene(scene, "face", op)
    R = _req_finite(R, op, "R", 0.0, lo_open=True)
    theta_deg = _req_finite(theta_deg, op, "theta_deg", -45.0, 45.0)
    vx = _req_finite(vx, op, "vx")
    vz = _req_finite(vz, op, "vz", 0.0, lo_open=True)
    k = _req_finite(k_wrist, op, "k_wrist", 0.0, lo_open=True)
    dt = _req_finite(dt, op, "dt", 0.0, lo_open=True)
    n = int(_req_finite(n_frames, op, "n_frames", 3, 5000))
    heel_x0 = _req_finite(heel_x0, op, "heel_x0")
    edge_start = _req_finite(edge_start, op, "edge_start")
    xi = slice_push_ratio(theta_deg, vx, vz)
    g = 1.0 / (1.0 + xi * xi)
    tt = math.tan(math.radians(theta_deg))
    fw, fh, fxc = sc["food_w"], sc["food_h"], sc["food_xc"]
    hz0 = edge_start - (fxc - heel_x0) * tt
    cols = {c: [] for c in ("t", "heel_x", "heel_z_cmd", "heel_z", "edge_z_c", "F", "w_eff")}
    hz_prev = math.inf
    for i in range(n):
        t = i * dt
        hx = heel_x0 + vx * t
        hzc = hz0 - vz * t

        def resid(hz):  # (hz − hzc)·k − F_cap(hz): 増加関数
            return (hz - hzc) * k - R * food_cut_width(theta_deg, hz + (fxc - hx) * tt, fw, fh) * 1e-3 * g
        lo, hi = hzc, hzc + R * fw * 1e-3 * g / k + 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if resid(mid) > 0:
                hi = mid
            else:
                lo = mid
        hz = max(min(0.5 * (lo + hi), hz_prev), hzc)
        hz_prev = hz
        ez = hz + (fxc - hx) * tt
        if ez - abs(tt) * fw / 2 < 0.3:
            break
        for c, v in zip(cols, (t, hx, hzc, hz, ez, k * (hz - hzc), food_cut_width(theta_deg, ez, fw, fh))):
            cols[c].append(v)
    if len(cols["t"]) < 3:
        raise ValueError(f"{op}: episode too short ({len(cols['t'])} frames); start higher or move slower")
    out = {c: np.asarray(v, float) for c, v in cols.items()}
    out.update(xi=xi, params={"R": R, "theta_deg": theta_deg, "vx": vx, "vz": vz, "k_wrist": k, "g": g, "dt": dt})
    return out


def cut_force_csv_load(path, license: str) -> dict:
    """有限要素の切断シミュレーションが書いた刃の力の CSV を読む(1 行目に ``Rcforc``、2 行目が列名、列 = 時刻と力の 3 成分が交互)。

    想定しているのは arXiv:2105.12244 が公開したデータセット(CC BY-NC 4.0 = 非商用)。``license`` は呼び手が**必ず**書く
    (データの使い道を返り値に残すため、空なら ValueError)。データは repo に入れず、置き場所は環境変数で渡す。
    返り値: ``t_s``、``F_xyz``(N、(N, 3))、``license``、``path`` は返さない(ローカルパスを記録に残さない)。"""
    op = "cut_force_csv_load"
    if not isinstance(license, str) or not license.strip():
        raise ValueError(f"{op}: license must be a non-empty string stating the data licence")
    if not isinstance(path, (str, os.PathLike)):
        raise ValueError(f"{op}: path must be a string or path-like, got {type(path).__name__}")
    p = os.fspath(path)
    if not os.path.isfile(p):
        raise ValueError(f"{op}: file not found")
    with open(p, encoding="utf-8", errors="replace") as fh:
        head = fh.readline()
        cols = fh.readline()
    if "Rcforc" not in head or "force" not in cols.lower():
        raise ValueError(f"{op}: not a contact-force CSV (header {head[:40]!r})")
    arr = np.genfromtxt(p, delimiter=",", skip_header=2)
    if arr.ndim != 2 or arr.shape[1] < 6:
        raise ValueError(f"{op}: unexpected shape {arr.shape}")
    arr = arr[:, :6]
    if arr.shape[0] < 3 or not np.all(np.isfinite(arr)):
        raise ValueError(f"{op}: too few rows or non-finite values")
    return {"t_s": arr[:, 0], "F_xyz": arr[:, [1, 3, 5]], "license": license.strip()}


# ----------------------------------------------------------------------------------------------------------------------
# MuJoCo(MJCF は文字列で mujoco 不要、走行は facade)
def cutting_wrist_mjcf(scene=None, theta_deg: float = 4.0, k_n_per_mm: float = 4.0, damping: float = 25.0,
                       mass: float = 0.15) -> str:
    """柔らかい手首の刃の場面(MJCF 文字列、mujoco 不要)。刃は縦のスライド関節(ばね ``k``・減衰)1 本、食材と板は見た目だけ。

    カメラ ``face`` は正射影で、画素の寸法と ``board_row`` が :func:`cutting_face_render` と同じになるよう置く。画像の中心は
    画素中心で数えて ((H−1)/2, (W−1)/2)(H/2 と書くと 0.5 px ずれる)。関節の摩擦損失は硬くしてある(既定の柔らかい摩擦損失は
    速度に比例する粘性のように振る舞い、切断力が 1 桁小さく出る)。食材の抵抗は走行中に関節の摩擦損失として毎歩書き換える
    (:func:`cutting_mujoco_wrist`)。"""
    op = "cutting_wrist_mjcf"
    sc = _req_scene(scene, "face", op)
    th = math.radians(_req_finite(theta_deg, op, "theta_deg", -45.0, 45.0))
    k = _req_finite(k_n_per_mm, op, "k_n_per_mm", 0.0, lo_open=True) * 1000.0
    c = _req_finite(damping, op, "damping", 0.0)
    m = _req_finite(mass, op, "mass", 0.0, lo_open=True)
    L, Hb = sc["blade_len"] / 1000, sc["blade_h"] / 1000
    cx = (L / 2) * math.cos(th) - (Hb / 2) * math.sin(th)
    cz = (L / 2) * math.sin(th) + (Hb / 2) * math.cos(th)
    q = (math.cos(-th / 2), 0.0, math.sin(-th / 2), 0.0)       # y 軸まわり(x → z が正になる向き)
    s = sc["px_per_mm"]
    zc = (sc["board_row"] - (sc["H"] - 1) / 2) / s / 1000
    xc = ((sc["W"] - 1) / 2) / s / 1000
    ext = sc["H"] / s / 1000
    return f"""<mujoco model="cutting_wrist">
 <option timestep="0.0005" gravity="0 0 -9.81"/>
 <visual>
  <headlight ambient="0.75 0.75 0.75" diffuse="0.25 0.25 0.25" specular="0 0 0"/>
  <global offwidth="{sc['W']}" offheight="{sc['H']}"/>
  <quality shadowsize="0"/>
 </visual>
 <default><geom contype="0" conaffinity="0"/></default>
 <worldbody>
  <geom name="wall" type="box" pos="0.05 0.10 0.03" size="0.2 0.001 0.2" rgba="0.84 0.85 0.86 1"/>
  <geom name="board" type="box" pos="0.05 0 -0.01" size="0.2 0.2 0.01" rgba="0.42 0.28 0.16 1"/>
  <geom name="food" type="box" pos="{sc['food_xc'] / 1000} -0.02 {sc['food_h'] / 2000}" size="{sc['food_w'] / 2000} 0.0195 {sc['food_h'] / 2000}" rgba="0.95 0.83 0.42 1"/>
  <body name="knife" pos="0 0 0">
   <joint name="kz" type="slide" axis="0 0 1" stiffness="{k}" damping="{c}" springref="0" solreffriction="0.001 1" solimpfriction="0.999 0.9999 0.001"/>
   <geom name="blade" type="box" pos="{cx} 0.0015 {cz}" quat="{q[0]} {q[1]} {q[2]} {q[3]}" size="{L / 2} 0.0005 {Hb / 2}" mass="{m}" rgba="0.50 0.53 0.57 1"/>
  </body>
  <camera name="face" pos="{xc} -0.5 {zc}" xyaxes="1 0 0 0 0 1" projection="orthographic" fovy="{ext}"/>
 </worldbody>
</mujoco>"""


def cutting_mujoco_wrist(scene=None, theta_deg: float = 4.0, R: float = 400.0, k_n_per_mm: float = 4.0, damping: float = 25.0,
                         mass: float = 0.15, vz: float = 6.0, heel_x: float = 18.0, edge_start: float = 28.5,
                         dt_frame: float = 0.15, n_frames: int = 30, render: bool = True) -> dict:
    """MuJoCo の柔らかい手首で刃を押し下げ、切断の 1 回分を描く(mujoco が要る facade、台帳の外)。

    ばねの基準点(qpos_spring)を指令の高さとして ``vz`` mm/s で下げ、食材の抵抗 = 関節の摩擦損失を毎歩
    ``R·w_eff·g(ξ)``(ξ = tan θ、縦に押すだけ)に置き換える。MuJoCo の拘束が付着と滑りを解くので剛塑性の食材と同じ振る舞いになる。
    ``render=True`` なら各コマを正射影カメラで描く(RGB float)。刃先の最下点がまな板の 1 mm 上に来たら止める。
    返り値: ``t``、``z_cmd_c``(食材中央での指令の刃先高さ)、``edge_z_true``、``F_constraint``(摩擦損失の拘束力 = 食材の抵抗、
    上向き +)、``frames``(``render`` のとき)、``params``。"""
    op = "cutting_mujoco_wrist"
    try:
        import mujoco
    except ImportError as exc:                                  # pragma: no cover - 環境依存
        raise ImportError(f"{op}: needs the optional dependency mujoco") from exc
    sc = _req_scene(scene, "face", op)
    R = _req_finite(R, op, "R", 0.0, lo_open=True)
    vz = _req_finite(vz, op, "vz", 0.0, lo_open=True)
    n_frames = int(_req_finite(n_frames, op, "n_frames", 1, 1000))
    dt_frame = _req_finite(dt_frame, op, "dt_frame", 0.0, lo_open=True)
    k = _req_finite(k_n_per_mm, op, "k_n_per_mm", 0.0, lo_open=True)
    xi = slice_push_ratio(theta_deg, 0.0, vz)
    g = 1.0 / (1.0 + xi * xi)
    m = mujoco.MjModel.from_xml_string(cutting_wrist_mjcf(sc, theta_deg, k, damping, mass))
    d = mujoco.MjData(m)
    jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "kz")
    dof, jq = m.jnt_dofadr[jid], m.jnt_qposadr[jid]
    tt = math.tan(math.radians(theta_deg))
    hz0 = edge_start - (sc["food_xc"] - heel_x) * tt
    m.body_pos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "knife")] = [heel_x / 1000, 0, 0]
    renderer = mujoco.Renderer(m, sc["H"], sc["W"]) if render else None
    steps = int(round(dt_frame / m.opt.timestep))
    out = {"t": [], "z_cmd_c": [], "edge_z_true": [], "F_constraint": [], "frames": []}
    try:
        for _ in range(n_frames):
            for _ in range(steps):
                m.qpos_spring[jq] = (hz0 - vz * d.time) / 1000
                ez = d.qpos[jq] * 1000 + (sc["food_xc"] - heel_x) * tt
                m.dof_frictionloss[dof] = R * food_cut_width(theta_deg, ez, sc["food_w"], sc["food_h"]) * 1e-3 * g
                mujoco.mj_step(m, d)
            if not np.all(np.isfinite(d.qacc)):
                raise ValueError(f"{op}: simulation became unstable")
            mujoco.mj_forward(m, d)
            ez_true = d.qpos[jq] * 1000 + (sc["food_xc"] - heel_x) * tt
            out["t"].append(float(d.time))
            out["z_cmd_c"].append((hz0 - vz * d.time) + (sc["food_xc"] - heel_x) * tt)
            out["edge_z_true"].append(float(ez_true))
            out["F_constraint"].append(float(d.qfrc_constraint[dof]))
            if renderer is not None:
                renderer.update_scene(d, camera="face")
                out["frames"].append(renderer.render().astype(np.float64) / 255.0)
            if ez_true - abs(tt) * sc["food_w"] / 2 < 1.0:
                break
    finally:
        if renderer is not None:
            renderer.close()
    res = {c: np.asarray(v, float) for c, v in out.items() if c != "frames"}
    res["frames"] = out["frames"]
    res["params"] = {"theta_deg": theta_deg, "R": R, "k_n_per_mm": k, "damping": damping, "mass": mass, "vz": vz,
                     "heel_x": heel_x, "xi": xi, "g": g, "plateau_N": R * sc["food_w"] * 1e-3 * g}
    return res
