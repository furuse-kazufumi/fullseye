# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""電池セルの劣化を CT で測る —— 膨れは外から見えるが、その何割かは中に隠れる。

角形リチウムイオンセルの劣化診断です。現場でいちばん手軽な指標は**外形**
(厚みをノギスで測る、治具に入るか見る)ですが、劣化の実体は缶の中の積層電極
—— 電極の膨れ、層間に溜まったガス、電極のずれ —— にあります。この PoC は
積層電極とアルミ缶を真値つきで作り、**実際に順投影 → ビームハードニング →
FBP 再構成**した CT ボリュームから、外形指標と内部指標を並べて測ります。

EXTEND: 実機 CT に差し替えるなら :func:`build_cell` が返す ``mu``(線減弱係数の
ボリューム)を実測の再構成ボリュームに置き換えます。``truth`` 辞書(層厚・層中心・
空隙体積・ずれ量)は**実データでは手に入りません** —— そこが差し替えの限界で、
実機では破壊検査(断面研磨)か、既知の膨れを与えた較正セルが要ります。缶の外形は
非破壊で測れるので、**外形だけは実測と突き合わせられます**。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. 数字は実行時に印字されます。

【グラウンドトゥルース】積層電極(17 層・ピッチ 0.320 mm・電極厚 0.200 mm)と
アルミ缶(肉厚 0.200 mm)を解析的な場と ``box_sdf`` / ``plane_sdf`` の CSG で構成。
劣化は既知の場として与える —— 一様膨れ(全層が一定率で厚くなる)/ 局所膨れ
(ガウス分布)/ 層間ガス空隙(レンズ形)/ 電極ずれ(層ごとに一定量の面内シフト)。
缶の端板は「はみ出した体積を平板のたわみ形状 cos^2 で受ける」保存則で膨らませる。

来歴(公開文献のみ): Kok et al., *J. Phys. Energy* 1 (2019) 032003 —— X 線 CT による
電池内部の非破壊観察 / Bond et al., *J. Electrochem. Soc.* 169 (2022) 080531 ——
セル膨れと内部劣化の対応 / Barrett & Keat, *Radiographics* 24 (2004) 1679 ——
CT のアーティファクト(ビームハードニング・金属)/ Kak & Slaney,
*Principles of Computerized Tomographic Imaging* (IEEE, 1988) —— FBP と標本化。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger

# --- 格子の諸元(ボリュームは (深さ z, 行 y, 列 x) = (D, H, W)) ---------------- #
SZ, SY, SX = 0.12, 0.04, 0.04     # voxel [mm]。スライス間隔は面内より粗い(実機どおり)
ND, NH, NW = 16, 176, 96          # 格子の大きさ [voxel] -> 1.92 x 7.04 x 3.84 mm
SPACING = (SZ, SY, SX)

# --- セルの諸元 [mm] --------------------------------------------------------- #
CAN_X = (0.30, 3.54)              # 缶の外形(x)
CAN_Y = (0.40, 6.48)              # 缶の外形(y = 積層方向)
CAN_Z = (0.12, 1.80)              # 缶の外形(z)
WALL = 0.20                       # 缶の肉厚
CAV_X = (CAN_X[0] + WALL, CAN_X[1] - WALL)
CAV_Y = (CAN_Y[0] + WALL, CAN_Y[1] - WALL)
CAV_Z = (CAN_Z[0] + WALL, CAN_Z[1] - WALL)
CAV_LEN = CAV_Y[1] - CAV_Y[0]     # 空洞の積層方向の長さ = 5.68 mm

N_LAYER = 17                      # 電極層の数
T_ELEC = 0.20                     # 電極の厚み
GAP = 0.12                        # 層間(セパレータ + 電解液)
PITCH = T_ELEC + GAP              # 層のピッチ = 0.32 mm
H_BASE = N_LAYER * PITCH          # 健全時の積層高さ = 5.44 mm(クリアランス 0.24 mm)

ELEC_X = (0.80, 3.04)             # 電極の面内の広がり(x)
ELEC_Z = (0.52, 1.40)             # 電極の面内の広がり(z)

MU_CAN, MU_ELEC, MU_LIQ, MU_GAS = 2.2, 1.0, 0.35, 0.02   # 線減弱(コントラスト単位)

# --- 撮像の諸元 -------------------------------------------------------------- #
N_ANGLE = 120                     # 投影数
# サイノグラムは **voxel 添字** 単位の線積分なので、光子統計とビームハードニングに
# 渡す前に物理的な光学的厚み [-] へ直す: 1 コントラスト単位 = 0.35 /mm、1 step = SY mm。
ATT = 0.35 * SY                   # コントラスト単位・voxel -> 光学的厚み
N0_NOMINAL = 1.0e5                # 公称のフォトン数
BH_NOMINAL = 0.70                 # ビームハードニングの硬さ比(1.0 = 単色)
RING_NOMINAL = 0.006              # 検出器ゲイン誤差(リング/ストリークの元)
SEED = 20260907

# --- 劣化の量 ---------------------------------------------------------------- #
ALPHA_UNIFORM = 0.10              # 一様膨れ: 全層が 10 % 厚くなる
MISALIGN = 0.020                  # 電極ずれ: 1 層あたり x に 0.020 mm

_GRID = None


# --------------------------------------------------------------------------- #
# 格子 —— grid_coords は (nx, ny, nz, 3) を (x, y, z) 順で返す。ボリューム op は
# (D, H, W) = (z, y, x) なので、**組み立ては格子順・最後に一度だけ転置**する。
# 途中で混ぜると静かに間違う(3-D でいちばん多い事故)。
# --------------------------------------------------------------------------- #
def grid():
    """CSG 用の座標格子(``(nx, ny, nz, 3)``、成分は ``(x, y, z)``)。"""
    global _GRID
    if _GRID is None:
        _GRID = np.asarray(L.grid_coords(
            ((0.0, NW * SX), (0.0, NH * SY), (0.0, ND * SZ)), (NW, NH, ND)))
    return _GRID


def to_volume(a):
    """格子順 ``(nx, ny, nz)`` -> ボリューム順 ``(D, H, W) = (z, y, x)``。"""
    return np.ascontiguousarray(np.asarray(a).transpose(2, 1, 0))


def _xz_field(f):
    """``(nx, nz)`` の面内の場を格子順に放送できる ``(nx, 1, nz)`` にする。"""
    return np.asarray(f)[:, None, :]


# --------------------------------------------------------------------------- #
# 1. 劣化の場 —— 積層高さ h(x, z) を先に決め、そこから缶のふくらみを保存則で出す
# --------------------------------------------------------------------------- #
def _panel_grids():
    """端板の面内座標 ``(x, z)`` と、板の内側かどうか。"""
    x = (np.arange(NW) + 0.5) * SX
    z = (np.arange(ND) + 0.5) * SZ
    xx, zz = np.meshgrid(x, z, indexing="ij")
    inside = ((xx >= CAV_X[0]) & (xx <= CAV_X[1])
              & (zz >= CAV_Z[0]) & (zz <= CAV_Z[1]))
    return xx, zz, inside


def _elec_footprint(xx, zz):
    return ((xx >= ELEC_X[0]) & (xx <= ELEC_X[1])
            & (zz >= ELEC_Z[0]) & (zz <= ELEC_Z[1]))


def _plate_shape(xx, zz):
    """周辺固定の平板のたわみ形状 ``cos^2 * cos^2``(中央 1、縁 0、面平均 1/4)。"""
    u = (xx - 0.5 * (CAV_X[0] + CAV_X[1])) / (CAV_X[1] - CAV_X[0])
    v = (zz - 0.5 * (CAV_Z[0] + CAV_Z[1])) / (CAV_Z[1] - CAV_Z[0])
    phi = np.cos(np.pi * np.clip(u, -0.5, 0.5)) ** 2 * np.cos(np.pi * np.clip(v, -0.5, 0.5)) ** 2
    _, _, inside = _panel_grids()
    return np.where(inside, phi, 0.0)


def degradation_fields(kind: str, scale: float = 1.0):
    """劣化の場を返す。

    戻り値は ``alpha``(層の増厚率の場、``(nx, nz)``)と ``voids``(層間ガス空隙の
    リスト ``[(gap_index, height_field), ...]``)と ``shift``(層あたりの x シフト)。
    """
    xx, zz, _ = _panel_grids()
    foot = _elec_footprint(xx, zz)
    alpha = np.zeros((NW, ND))
    voids: list[tuple[int, np.ndarray]] = []
    shift = 0.0

    if kind == "healthy":
        pass
    elif kind == "uniform":
        alpha = np.where(foot, ALPHA_UNIFORM, 0.0)
    elif kind == "local":
        # 局所膨れ: 面内のガウス分布で全層が厚くなる(電極の一部だけが劣化する)
        g = np.exp(-(((xx - 2.30) / 0.55) ** 2 + ((zz - 0.96) / 0.34) ** 2))
        alpha = np.where(foot, scale * g, 0.0)
    elif kind == "gas":
        # 層間ガス空隙: レンズ形(扁平楕円体)を 3 つの層間に置く
        for k, (xc, zc, ax, az) in enumerate(((1.35, 0.85, 0.34, 0.30),
                                              (2.05, 1.05, 0.30, 0.28),
                                              (2.65, 0.86, 0.32, 0.30))):
            gap_index = 4 + 4 * k
            r2 = ((xx - xc) / ax) ** 2 + ((zz - zc) / az) ** 2
            hv = 2.0 * scale * np.sqrt(np.clip(1.0 - r2, 0.0, None))
            voids.append((gap_index, np.where(foot, hv, 0.0)))
    elif kind == "misalign":
        shift = MISALIGN
    else:
        raise ValueError("未知の劣化: %r" % (kind,))
    return {"alpha": alpha, "voids": voids, "shift": shift}


def stack_height(fields) -> np.ndarray:
    """積層高さの場 ``h(x, z)`` [mm]。電極が無いところは 0。"""
    xx, zz, _ = _panel_grids()
    foot = _elec_footprint(xx, zz)
    h = np.where(foot, H_BASE, 0.0)
    h = h + N_LAYER * T_ELEC * fields["alpha"]
    for _, hv in fields["voids"]:
        h = h + hv
    return h


def bulge(fields) -> dict:
    """積層のはみ出しを缶の端板のたわみに変換する(体積保存)。

    はみ出し ``excess(x, z) = max(0, h - CAV_LEN)`` を、端板 2 枚が
    ``w(x, z) = w_max * phi(x, z)`` の形で受ける。``phi`` の面平均は 1/4 なので
    ``2 * w_max * (1/4) = <excess>`` -> ``w_max = 2 <excess>``。
    **中央のノギスは ``2 w_max`` を読む = 体積等価な平均の 4 倍**になる。
    """
    xx, zz, inside = _panel_grids()
    h = stack_height(fields)
    excess = np.maximum(0.0, h - CAV_LEN)
    area_cell = SX * SZ
    mean_excess = float(excess[inside].sum() / max(1, int(inside.sum())))
    w_max = 2.0 * mean_excess
    w = w_max * _plate_shape(xx, zz)
    return {"h": h, "excess": excess, "w": w, "w_max": w_max,
            "mean_excess": mean_excess,
            "dv_ext": float(excess[inside].sum() * area_cell),
            "dv_int": float((h - np.where(_elec_footprint(xx, zz), H_BASE, 0.0)).sum()
                            * area_cell),
            "panel_area": float(inside.sum() * area_cell)}


def match_to_bulge(kind: str, target_mean_excess: float) -> float:
    """外形のふくらみが ``target_mean_excess`` に一致する劣化の大きさを二分法で探す。

    **対照群の作り方そのもの** —— 外側から見て同じセルを、中身の違う 2 通りで作る。
    """
    lo, hi = 0.0, 4.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        me = bulge(degradation_fields(kind, mid))["mean_excess"]
        if me < target_mean_excess:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------- #
# 2. セルを組む —— 缶は SDF の CSG、積層は解析的な場
# --------------------------------------------------------------------------- #
def _box(g, xr, yr, zr):
    c = (0.5 * (xr[0] + xr[1]), 0.5 * (yr[0] + yr[1]), 0.5 * (zr[0] + zr[1]))
    hx = (0.5 * (xr[1] - xr[0]), 0.5 * (yr[1] - yr[0]), 0.5 * (zr[1] - zr[0]))
    return np.asarray(L.box_sdf(g, c, hx))


def build_cell(kind: str, scale: float = 1.0) -> dict:
    """線減弱ボリューム ``mu`` (D, H, W) と真値の辞書を作る。"""
    g = grid()
    fields = degradation_fields(kind, scale)
    bl = bulge(fields)
    w = _xz_field(bl["w"])                      # 端板のたわみ (nx, 1, nz)

    # --- 缶: 側壁(SDF の差集合)+ たわんだ端板 2 枚(場でずらした格子で評価)---
    # ★``sdf_offset`` は**スカラのみ**なので、場でずらすには格子を歪めて評価する。
    g_lo = g.copy(); g_lo[..., 1] += w          # 下の端板を -y へ w だけ動かす
    g_hi = g.copy(); g_hi[..., 1] -= w          # 上の端板を +y へ
    side = L.sdf_subtract(_box(g, CAN_X, CAN_Y, CAN_Z),
                          _box(g, CAV_X, (-50.0, 50.0), CAV_Z))
    plate_lo = _box(g_lo, CAN_X, (CAN_Y[0], CAV_Y[0]), CAN_Z)
    plate_hi = _box(g_hi, CAN_X, (CAV_Y[1], CAN_Y[1]), CAN_Z)
    can_sdf = L.sdf_union(L.sdf_union(side, plate_lo), plate_hi)
    can = np.asarray(L.sdf_to_occupancy(can_sdf)) > 0.5

    # --- 空洞(電解液で満たされる): 側壁の内側 x たわんだ端板のあいだ ---
    inner_xz = _box(g, CAV_X, (-50.0, 50.0), CAV_Z)
    lo_face = np.asarray(L.plane_sdf(g_lo, (0.0, CAV_Y[0], 0.0), (0.0, -1.0, 0.0)))
    hi_face = np.asarray(L.plane_sdf(g_hi, (0.0, CAV_Y[1], 0.0), (0.0, 1.0, 0.0)))
    cav = np.asarray(L.sdf_to_occupancy(
        L.sdf_intersect(L.sdf_intersect(inner_xz, lo_face), hi_face))) > 0.5

    # --- 積層電極: 面内の場から層ごとの y 区間を積み上げる ---
    X, Y, Z = g[..., 0], g[..., 1], g[..., 2]
    xx, zz, _ = _panel_grids()
    foot_base = _elec_footprint(xx, zz)
    h = _xz_field(bl["h"])
    y_bot = 0.5 * (CAV_Y[0] + CAV_Y[1]) - 0.5 * h        # 積層は空洞の中央に座る
    t_i = _xz_field(T_ELEC * (1.0 + fields["alpha"]))
    void_by_gap = {k: _xz_field(hv) for k, hv in fields["voids"]}

    elec = np.zeros(X.shape, bool)
    voids = np.zeros(X.shape, bool)
    cursor = y_bot + 0.5 * GAP
    layer_lo, layer_hi, layer_dx = [], [], []
    for i in range(N_LAYER):
        dx = fields["shift"] * (i - 0.5 * (N_LAYER - 1))
        foot = _xz_field(((xx - dx >= ELEC_X[0]) & (xx - dx <= ELEC_X[1])
                          & (zz >= ELEC_Z[0]) & (zz <= ELEC_Z[1])))
        elec |= (Y >= cursor) & (Y < cursor + t_i) & foot
        layer_lo.append(cursor.copy())
        layer_hi.append((cursor + t_i).copy())
        layer_dx.append(dx)
        cursor = cursor + t_i
        hv = void_by_gap.get(i)
        gap_h = GAP + (hv if hv is not None else 0.0)
        if hv is not None:
            mid = cursor + 0.5 * gap_h
            voids |= (Y >= mid - 0.5 * hv) & (Y < mid + 0.5 * hv) & (hv > 1e-9) \
                & _xz_field(foot_base)
        cursor = cursor + gap_h

    mu = np.zeros(X.shape)
    mu[cav] = MU_LIQ
    mu[elec] = MU_ELEC
    mu[voids] = MU_GAS
    mu[can] = MU_CAN                     # 缶が最後(食い込みは缶を優先)

    area_cell = SX * SZ
    truth = {
        "kind": kind, "scale": scale,
        "n_layer": N_LAYER, "t_elec": T_ELEC, "pitch": PITCH,
        "t_mean": float(np.mean([T_ELEC * (1.0 + a) for a in
                                 fields["alpha"][foot_base].ravel()])) if foot_base.any() else T_ELEC,
        "h_mean": float(bl["h"][foot_base].mean()),
        "dh_mean": float(bl["h"][foot_base].mean() - H_BASE),
        "dv_int": bl["dv_int"], "dv_ext": bl["dv_ext"],
        "mean_excess": bl["mean_excess"], "w_max": bl["w_max"],
        "caliper_gain": 2.0 * bl["w_max"],
        "void_volume": float(sum(np.sum(hv) for _, hv in fields["voids"]) * area_cell),
        "void_voxels": int(voids.sum()),
        "shift": fields["shift"],
        "layer_center_mm": [float(np.mean(0.5 * (lo + hi))) for lo, hi in
                            zip(layer_lo, layer_hi)],
    }
    return {"mu": to_volume(mu), "can": to_volume(can), "elec": to_volume(elec),
            "void": to_volume(voids), "cav": to_volume(cav),
            "truth": truth, "bulge": bl}


# --------------------------------------------------------------------------- #
# 3. 撮像 —— 順投影 -> ビームハードニング -> リング -> フォトン雑音 -> FBP
# --------------------------------------------------------------------------- #
ANGLES = None


def angles():
    global ANGLES
    if ANGLES is None:
        ANGLES = np.asarray(fs.projection_angles(N_ANGLE, 180.0))
    return ANGLES


def forward(mu: np.ndarray) -> np.ndarray:
    """順投影(平行ビーム、回転軸 = z)。**これが実行時間の大半**。"""
    return np.asarray(fs.radon_volume(mu, angles()))


def acquire(sino: np.ndarray, n0=N0_NOMINAL, bh=BH_NOMINAL, ring=RING_NOMINAL,
            seed=SEED) -> np.ndarray:
    """サイノグラムに撮像の劣化を入れて再構成する。

    順序は物理どおり: 光学的厚みへ換算 -> 多色化(ビームハードニング)->
    検出器ゲイン誤差(リング/ストリーク)-> 光子計数 -> 対数 -> FBP。
    """
    p = np.asarray(sino, float) * ATT
    if bh < 1.0:
        p = np.stack([np.asarray(fs.beam_hardening_apply(p[k], 0.5, bh))
                      for k in range(p.shape[0])])
    if ring > 0.0:
        p = np.stack([np.asarray(fs.ring_artifact_apply(p[k], ring, seed))
                      for k in range(p.shape[0])])
    if n0 is not None and np.isfinite(n0):
        rng = np.random.default_rng(seed)
        inten = np.exp(-np.clip(p, 0.0, 30.0))
        counts = rng.poisson(np.clip(n0 * inten, 1e-9, None)).astype(float)
        p = -np.log(np.maximum(counts, 0.5) / n0)
    rec = np.asarray(fs.fbp_volume(p / ATT, angles(), size=NH))
    c0 = (rec.shape[2] - NW) // 2
    return np.ascontiguousarray(rec[:, :, c0:c0 + NW])


# --------------------------------------------------------------------------- #
# 4. 測る —— 外形(ゼロ点)と内部指標
# --------------------------------------------------------------------------- #
def _vidx(z_mm, y_mm, x_mm):
    """物理座標 [mm] -> ボリュームの (z, y, x) 添字(中心アライン)。"""
    return (z_mm / SZ - 0.5, y_mm / SY - 0.5, x_mm / SX - 0.5)


def outer_metrics(vol: np.ndarray) -> dict:
    """**ゼロ点** —— 缶の外形だけから劣化を測る(非破壊で誰でもできる方法)。

    外(空気)から内へ向かって最初に缶を横切る位置を、列ごとに**サブボクセルで**
    出す。しきい値は缶の水準の半分(空気 0 と缶の中間 = 縁の半値)にとる ——
    絶対値にするとビームハードニングで缶の水準が下がったときに破綻する。
    電極が誤って明るく出ても、それは 2 つの交差の**あいだ**なので影響しない。

    ``caliper`` は中央 3x3 の平均(ノギスで真ん中を挟む)、``mean`` は端板の面平均
    (体積等価)。**「外形が囲む高さ」を出す op は公開経路に無いので自前**。
    """
    v = np.asarray(vol, float)
    v_can = float(np.median(v[v > np.percentile(v, 98.0)]))
    thr = 0.5 * v_can
    above = v > thr
    ok = above.any(axis=1)
    first = np.argmax(above, axis=1)
    last = NH - 1 - np.argmax(above[:, ::-1, :], axis=1)

    def _sub(idx, back):
        """しきい値交差のサブボクセル位置 [voxel]。``back`` なら 1 つ後ろ側と補間。"""
        j = np.clip(idx + (1 if back else -1), 0, NH - 1)
        a = np.take_along_axis(v, j[:, None, :], axis=1)[:, 0, :]
        b = np.take_along_axis(v, idx[:, None, :], axis=1)[:, 0, :]
        d = np.where(np.abs(b - a) < 1e-9, np.nan, b - a)
        f = np.clip((thr - a) / d, 0.0, 1.0)
        return j + f * (idx - j)

    y_lo, y_hi = _sub(first, False), _sub(last, True)
    heights = np.where(ok, (y_hi - y_lo) * SY, np.nan)
    _, _, inside = _panel_grids()
    panel = inside.T & np.isfinite(heights)
    cz, cx = ND // 2, NW // 2
    core = heights[cz - 1:cz + 2, cx - 1:cx + 2]
    return {"height": heights, "panel": panel, "thr": thr,
            "caliper": float(np.nanmean(core)),
            "mean": float(heights[panel].mean()),
            "bbox": tuple(int(b) for b in np.asarray(L.vol_bounding_box(above)))}


def _probe_points():
    """内部を突くプローブの ``(z, x)`` [mm]。電極の内側だけを使う。"""
    zs = np.linspace(ELEC_Z[0] + 0.10, ELEC_Z[1] - 0.10, 5)
    xs = np.linspace(ELEC_X[0] + 0.25, ELEC_X[1] - 0.25, 7)
    return [(float(z), float(x)) for z in zs for x in xs]


def _edge_threshold(vol, spacing, zc, xc):
    """観測されたコントラストから微分しきい値を決める(voxel に依らない規約)。

    「2 voxel のあいだにコントラストの 30 % を振る縁だけを縁と認める」。
    固定値にすると崖の位置がしきい値の選び方で動いてしまう。
    """
    p0 = _vidx(zc, CAV_Y[0] + 0.02, xc)
    p1 = _vidx(zc, CAV_Y[1] - 0.02, xc)
    pr = np.asarray(L.vol_profile_line(vol, p0, p1, spacing=spacing))
    v = pr[:, 1]
    c = float(np.percentile(v, 95) - np.percentile(v, 5))
    return max(1e-6, 0.30 * c / (2.0 * spacing[1])), c, pr


def internal_metrics(vol: np.ndarray, spacing=SPACING) -> dict:
    """内部指標 —— 層数・層厚・層間隔の散らばり・空隙率・層の平面度。"""
    counts, thicks, pitches, contrasts = [], [], [], []
    fft_pitch = []
    for zc, xc in _probe_points():
        thr, contrast, pr = _edge_threshold(vol, spacing, zc, xc)
        contrasts.append(contrast)
        p0 = _vidx(zc, CAV_Y[0] + 0.02, xc)
        p1 = _vidx(zc, CAV_Y[1] - 0.02, xc)
        th = list(L.vol_wall_thickness(vol, p0, p1, sigma=1.2, threshold=thr,
                                       spacing=spacing))
        counts.append(len(th))
        thicks.extend(th)
        ed = L.vol_edge_probe(vol, p0, p1, sigma=1.2, threshold=thr,
                              spacing=spacing, polarity="positive")
        t = np.asarray([e["t_mm"] for e in ed])
        if t.size >= 2:
            pitches.extend(np.diff(t).tolist())
        fft_pitch.append(_fft_pitch(pr[:, 0], pr[:, 1]))

    # 空隙率: 電解液より暗い連結成分を数える(気体 0.02 < 電解液 0.35)
    roi = np.zeros(vol.shape, bool)
    z0, z1 = int(ELEC_Z[0] / SZ) + 1, int(ELEC_Z[1] / SZ)
    y0, y1 = int((CAV_Y[0] + 0.10) / SY), int((CAV_Y[1] - 0.10) / SY)
    x0, x1 = int(ELEC_X[0] / SX) + 2, int(ELEC_X[1] / SX) - 2
    roi[z0:z1, y0:y1, x0:x1] = True
    dark = (np.asarray(vol) < 0.5 * (MU_GAS + MU_LIQ)) & roi
    lab = np.asarray(L.vol_label(dark, connectivity=26))
    props = L.vol_region_props(lab, spacing=spacing)
    cell_vol = SZ * SY * SX
    big = [p for p in props if p["volume"] > 20 * cell_vol]
    void_vol = float(sum(p["volume"] for p in big))
    roi_vol = float(roi.sum() * cell_vol)

    return {"n_layer": int(np.median(counts)) if counts else 0,
            "n_layer_min": int(np.min(counts)) if counts else 0,
            "n_layer_max": int(np.max(counts)) if counts else 0,
            "t_mean": float(np.mean(thicks)) if thicks else float("nan"),
            "t_sd": float(np.std(thicks)) if thicks else float("nan"),
            "pitch_mean": float(np.mean(pitches)) if pitches else float("nan"),
            "pitch_sd": float(np.std(pitches)) if pitches else float("nan"),
            "fft_pitch": float(np.median(fft_pitch)),
            "contrast": float(np.mean(contrasts)),
            "void_volume": void_vol, "n_void": len(big),
            "void_fraction": 100.0 * void_vol / roi_vol,
            "roi_volume": roi_vol}


def _fft_pitch(t_mm, values) -> float:
    """プロファイルの卓越周期 [mm]。**数えるのではなく周期を測る**別経路。

    ★1-D の周期性(自己相関・卓越周期)を出す op が公開経路に無いので自前。
    """
    v = np.asarray(values, float)
    v = v - v.mean()
    if v.size < 8:
        return float("nan")
    dt = float(t_mm[1] - t_mm[0])
    sp = np.abs(np.fft.rfft(v * np.hanning(v.size)))
    freq = np.fft.rfftfreq(v.size, d=dt)
    lo = (freq > 1.0 / 1.2) & (freq < 1.0 / 0.12)      # 0.12 .. 1.2 mm の周期だけ
    if not lo.any():
        return float("nan")
    k = np.nonzero(lo)[0][np.argmax(sp[lo])]
    return float(1.0 / freq[k])


def flatness(vol: np.ndarray, y_target: float, spacing=SPACING) -> dict:
    """層の平面度 —— 1 枚の界面を面で測り、``fit_plane_3d`` の残差 RMS を返す。"""
    pts = []
    for zc, xc in _probe_points():
        thr, _, _ = _edge_threshold(vol, spacing, zc, xc)
        p0 = _vidx(zc, CAV_Y[0] + 0.02, xc)
        p1 = _vidx(zc, CAV_Y[1] - 0.02, xc)
        ed = L.vol_edge_probe(vol, p0, p1, sigma=1.2, threshold=thr,
                              spacing=spacing, polarity="positive")
        if not ed:
            continue
        y = np.asarray([CAV_Y[0] + 0.02 + e["t_mm"] for e in ed])
        j = int(np.argmin(np.abs(y - y_target)))
        if abs(y[j] - y_target) < 0.5 * PITCH:
            pts.append((xc, float(y[j]), zc))          # 点の op は (x, y, z)
    if len(pts) < 6:
        return {"resid": float("nan"), "n": len(pts), "points": np.zeros((0, 3))}
    p = np.asarray(pts)
    point, normal, resid = L.fit_plane_3d.raw(p)
    return {"resid": float(resid), "n": len(pts), "points": p,
            "normal": np.asarray(normal)}


def misalign_slope(vol: np.ndarray, truth, spacing=SPACING) -> dict:
    """電極端のずれ —— 層ごとに x 方向の縁を測り、層番号に対する傾きを出す。"""
    zc = 0.5 * (ELEC_Z[0] + ELEC_Z[1])
    xs, idx = [], []
    for i, yc in enumerate(truth["layer_center_mm"]):
        p0 = _vidx(zc, yc, CAV_X[0] + 0.02)
        p1 = _vidx(zc, yc, CAV_X[1] - 0.02)
        thr = 0.30 * (MU_ELEC - MU_LIQ) / (2.0 * spacing[2])
        ed = L.vol_edge_probe(vol, p0, p1, sigma=1.2, threshold=thr,
                              spacing=spacing, polarity="positive")
        if ed:
            xs.append(CAV_X[0] + 0.02 + ed[0]["t_mm"])
            idx.append(i)
    if len(xs) < 5:
        return {"slope": float("nan"), "n": len(xs), "idx": idx, "x": xs}
    a, b = np.polyfit(np.asarray(idx, float), np.asarray(xs), 1)
    return {"slope": float(a), "intercept": float(b), "n": len(xs),
            "idx": idx, "x": xs}


# --------------------------------------------------------------------------- #
# 節 1 —— 場面と、外形指標がどれだけ見落とすか
# --------------------------------------------------------------------------- #
def section_scene(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("1) 場面 —— 積層 %d 層 / ピッチ %.3f mm / 缶の肉厚 %.2f mm" % (
        N_LAYER, PITCH, WALL))
    print("=" * 78)
    hz = cells["healthy"]
    print("  格子 %s voxel、voxel %.2f x %.2f x %.2f mm、投影 %d 本" % (
        (ND, NH, NW), SZ, SY, SX, N_ANGLE))
    print("  空洞の長さ %.3f mm / 健全な積層高さ %.3f mm -> クリアランス %.3f mm"
          % (CAV_LEN, H_BASE, CAV_LEN - H_BASE))
    o = outer_metrics(recs["healthy"])
    print("  健全セルの外形高さ: 中央 %.3f mm / 平均 %.3f mm(真値 %.3f mm)"
          % (o["caliper"], o["mean"], CAN_Y[1] - CAN_Y[0]))

    mid = ND // 2
    figs.save_grid("scene", [cells["healthy"]["mu"][mid], recs["healthy"][mid],
                             recs["uniform"][mid], recs["gas"][mid]],
                   ["真値 μ(健全)", "CT 再構成(健全)",
                    "CT 再構成(一様膨れ)", "CT 再構成(ガス空隙)"],
                   title="角形セルの断面(z 中央、縦 = 積層方向 y、1 目盛 %.2f mm)" % SY,
                   ncols=2,
                   caption="缶(明)・電極(中)・電解液(暗)・ガス(最暗)。"
                           "順投影 → ビームハードニング → リング → フォトン雑音 → FBP。")
    return {"outer_healthy": o}


def section_outer_blindness(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 外形だけで測ると、膨れの何割が見えるか")
    print("=" * 78)

    t = cells["uniform"]["truth"]
    frac = 100.0 * t["dv_ext"] / t["dv_int"]
    pred = 100.0 * (t["dh_mean"] - (CAV_LEN - H_BASE)) / t["dh_mean"]
    print("  一様膨れ %.0f %%: 積層は %.3f mm 伸びる(体積 %.4f mm3)。" % (
        100 * ALPHA_UNIFORM, t["dh_mean"], t["dv_int"]))
    print("    クリアランス %.3f mm を食い潰した残りだけが缶を押す"
          " -> 外形の体積増 %.4f mm3" % (CAV_LEN - H_BASE, t["dv_ext"]))
    print("    ★外から見える割合 = %.1f %%(幾何からの予測 %.1f %%)" % (frac, pred))

    o0 = outer_metrics(recs["healthy"])
    o1 = outer_metrics(recs["uniform"])
    d_cal = o1["caliper"] - o0["caliper"]
    d_mean = o1["mean"] - o0["mean"]
    print("\n  CT から測った外形の増分: 中央のノギス %+.3f mm / 面平均 %+.3f mm"
          % (d_cal, d_mean))
    print("    真値: 中央 %+.3f mm / 面平均 %+.3f mm" % (
        t["caliper_gain"], t["mean_excess"]))
    print("    ★中央のノギスは平均の %.1f 倍を読む(平板のたわみ形状 cos^2 の"
          "面平均が 1/4 なので、幾何からの予測は 4.0 倍)。" % (d_cal / max(1e-9, d_mean)))
    print("    「厚みが %.2f mm 増えた」と書くと、体積では %.2f mm しか"
          "増えていない。" % (d_cal, d_mean))

    # クリアランスを振ると「見える割合」は設計値で決まる
    clr, seen = [], []
    for c in np.linspace(0.0, 0.50, 11):
        dh = t["dh_mean"]
        clr.append(c)
        seen.append(100.0 * max(0.0, dh - c) / dh)
    print("\n  ★「見える割合」は劣化の大きさではなく**セルの初期クリアランス**で"
          "決まる設計量:")
    for c, s in zip(clr[::2], seen[::2]):
        print("     クリアランス %.2f mm -> 外から見えるのは %5.1f %%" % (c, s))

    xx, _, _ = _panel_grids()
    x_mm = (np.arange(NW) + 0.5) * SX
    figs.save_plot("outer_profile",
                   [("健全", x_mm, o0["height"][ND // 2]),
                    ("一様膨れ", x_mm, o1["height"][ND // 2]),
                    ("ガス空隙(外形は同じ)", x_mm,
                     outer_metrics(recs["gas"])["height"][ND // 2])],
                   xlabel="x [mm]", ylabel="缶の外形高さ [mm]",
                   title="外形はふくらむが、真ん中しかふくらまない",
                   caption="端板は周辺で固定なので中央だけが出る。ノギスは中央を"
                           "読むので体積等価な平均の 4 倍を報告する。")
    figs.save_plot("visible_fraction",
                   [("外から見える割合", clr, seen)],
                   xlabel="初期クリアランス [mm]", ylabel="外形に出る割合 [%]",
                   title="外形指標が拾う割合はセルの設計で決まる",
                   caption="同じ劣化でもクリアランスが厚いセルでは外形に何も出ない。")
    return {"frac": frac, "pred": pred, "d_cal": d_cal, "d_mean": d_mean,
            "ratio": d_cal / max(1e-9, d_mean), "clearance": clr, "seen": seen}


# --------------------------------------------------------------------------- #
# 節 3 —— 対照群: 外形が同じで中身が違う 3 つ
# --------------------------------------------------------------------------- #
def section_control(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("3) 対照群 —— 外形のふくらみを揃えた 3 つのセル")
    print("=" * 78)

    rows, res = [], {}
    for key, name in (("healthy", "健全"), ("uniform", "一様膨れ"),
                      ("local", "局所膨れ"), ("gas", "層間ガス空隙")):
        o = outer_metrics(recs[key])
        m = internal_metrics(recs[key])
        t = cells[key]["truth"]
        res[key] = {"outer": o, "inner": m, "truth": t}
        rows.append([name,
                     "%.3f" % o["caliper"], "%.3f" % o["mean"],
                     "%d" % m["n_layer"], "%.3f" % m["t_mean"],
                     "%.3f" % m["pitch_sd"], "%.2f" % m["void_fraction"],
                     "%.4f" % t["dv_int"]])
        print("  %-10s 外形: 中央 %.3f mm 平均 %.3f mm | 内部: 層 %2d 枚 "
              "層厚 %.3f mm 層間隔σ %.3f mm 空隙率 %.2f %% | 真の膨張体積 %.4f mm3"
              % (name, o["caliper"], o["mean"], m["n_layer"], m["t_mean"],
                 m["pitch_sd"], m["void_fraction"], t["dv_int"]))

    base = res["healthy"]
    print("\n  ★外形は 3 つとも同じ(中央 %.3f / %.3f / %.3f mm、ばらつき %.3f mm)。"
          % (res["uniform"]["outer"]["caliper"], res["local"]["outer"]["caliper"],
             res["gas"]["outer"]["caliper"],
             float(np.std([res[k]["outer"]["caliper"]
                           for k in ("uniform", "local", "gas")]))))
    print("     内部は違う: 層厚 %.3f / %.3f / %.3f mm、空隙率 %.2f / %.2f / %.2f %%"
          % (res["uniform"]["inner"]["t_mean"], res["local"]["inner"]["t_mean"],
             res["gas"]["inner"]["t_mean"],
             res["uniform"]["inner"]["void_fraction"],
             res["local"]["inner"]["void_fraction"],
             res["gas"]["inner"]["void_fraction"]))
    print("     ★同じ外形を作るのに必要な**内部の膨張体積**は "
          "一様 %.4f / 局所 %.4f / ガス %.4f mm3 —— 集中した膨れは"
          "少ない体積で同じ外形変化を作る。"
          % (res["uniform"]["truth"]["dv_int"], res["local"]["truth"]["dv_int"],
             res["gas"]["truth"]["dv_int"]))

    # 層の平面度
    y_mid = float(cells["healthy"]["truth"]["layer_center_mm"][N_LAYER // 2])
    flat = {}
    for key in ("healthy", "uniform", "local", "gas"):
        flat[key] = flatness(recs[key], y_mid)
        print("     平面度(中央の層の界面、%s): 残差 RMS %.4f mm(%d 点)"
              % (key, flat[key]["resid"], flat[key]["n"]))

    figs.save_table("control_group",
                    ["セル", "外形 中央 mm", "外形 平均 mm", "層数", "層厚 mm",
                     "層間隔σ mm", "空隙率 %", "真の膨張体積 mm3"], rows,
                    title="外形が同じ 3 つのセル ―― 内部指標だけが分ける",
                    caption="外形の 2 列はほぼ同じ。層厚・空隙率・膨張体積は違う。")

    mid = ND // 2
    figs.save_grid("map_control",
                   [recs["healthy"][mid], recs["uniform"][mid],
                    recs["local"][mid], recs["gas"][mid]],
                   ["健全", "一様膨れ", "局所膨れ", "層間ガス空隙"],
                   title="外形のふくらみを揃えた 4 つの断面(同じ窓)", ncols=4,
                   caption="缶の外形はほぼ同じ。違いは中の層にしか出ない。")
    return {"res": res, "flat": flat, "base": base}


# --------------------------------------------------------------------------- #
# 節 4 —— 空隙の 3-D 地図
# --------------------------------------------------------------------------- #
def section_voidmap(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("4) 空隙を 3-D で拾う —— 位置と体積を真値と突き合わせる")
    print("=" * 78)

    vol = recs["gas"]
    t = cells["gas"]["truth"]
    roi = np.zeros(vol.shape, bool)
    z0, z1 = int(ELEC_Z[0] / SZ) + 1, int(ELEC_Z[1] / SZ)
    y0, y1 = int((CAV_Y[0] + 0.10) / SY), int((CAV_Y[1] - 0.10) / SY)
    x0, x1 = int(ELEC_X[0] / SX) + 2, int(ELEC_X[1] / SX) - 2
    roi[z0:z1, y0:y1, x0:x1] = True
    dark = (vol < 0.5 * (MU_GAS + MU_LIQ)) & roi
    lab = np.asarray(L.vol_label(dark, connectivity=26))
    props = L.vol_region_props(lab, spacing=SPACING)
    cell_vol = SZ * SY * SX
    big = sorted([p for p in props if p["volume"] > 20 * cell_vol],
                 key=lambda p: -p["volume"])
    est = float(sum(p["volume"] for p in big))
    print("  真値: 空隙 3 個 / 合計体積 %.4f mm3" % t["void_volume"])
    print("  推定: %d 個 / 合計体積 %.4f mm3 (%+.1f %%)"
          % (len(big), est, 100.0 * (est - t["void_volume"]) / t["void_volume"]))
    for p in big[:4]:
        cz, cy, cx = p["centroid"]
        print("     重心 (z %.2f, y %.2f, x %.2f) mm  体積 %.4f mm3"
              % (cz * SZ, cy * SY, cx * SX, p["volume"]))
    print("  ★体積が過小に出るのは、レンズ形の空隙の**縁が薄い**から ——"
          " しきい値は厚い中央しか拾えない(部分体積効果)。")

    # 疑似カラーの空隙地図: ラベルを y 方向へ最大値投影(z-x 平面の地図)
    lab_map = lab.max(axis=1).astype(float)
    truth_map = cells["gas"]["void"].max(axis=1).astype(float)
    figs.save_grid("void_map",
                   [np.repeat(truth_map, 3, axis=0), np.repeat(lab_map, 3, axis=0)],
                   ["真値の空隙(y 方向の投影)", "CT から拾ったラベル"],
                   title="空隙の 3-D 地図(縦 z を 3 倍に伸ばして表示)", ncols=2,
                   caption="位置は当たる。縁が薄いところは落ちるので体積は過小。")
    figs.save_grid("void_slices",
                   [recs["gas"][ND // 2], (dark.astype(float))[ND // 2]],
                   ["CT 断面(ガス空隙)", "しきい値で拾った空隙"],
                   title="空隙のしきい値検出(z 中央の断面)", ncols=2)
    return {"est": est, "true": t["void_volume"], "n": len(big)}


# --------------------------------------------------------------------------- #
# 節 5 —— 電極ずれ
# --------------------------------------------------------------------------- #
def section_misalign(cells, recs) -> dict:
    print("\n" + "=" * 78)
    print("5) 電極ずれ —— 層ごとの端の位置から 1 層あたりのずれを出す")
    print("=" * 78)
    t = cells["misalign"]["truth"]
    m = misalign_slope(recs["misalign"], t)
    m0 = misalign_slope(recs["healthy"], cells["healthy"]["truth"])
    print("  真値 %.4f mm/層 -> 推定 %.4f mm/層 (%+.1f %%、%d 層で回帰)"
          % (t["shift"], m["slope"], 100.0 * (m["slope"] - t["shift"]) / t["shift"],
             m["n"]))
    print("  対照(健全、ずれ 0): 推定 %.4f mm/層 —— これが測定系の零点"
          % m0["slope"])
    o = outer_metrics(recs["misalign"])
    o0 = outer_metrics(recs["healthy"])
    print("  ★外形はまったく動かない(中央 %.3f -> %.3f mm、差 %+.4f mm)。"
          " ずれは体積を変えないので、外形指標には**原理的に**出ない。"
          % (o0["caliper"], o["caliper"], o["caliper"] - o0["caliper"]))

    idx = np.asarray(m["idx"], float)
    figs.save_plot("misalign",
                   [("測定した電極端 x", idx, np.asarray(m["x"])),
                    ("真値の直線", idx,
                     m["intercept"] + t["shift"] * idx),
                    ("健全セル", np.asarray(m0["idx"], float), np.asarray(m0["x"]))],
                   xlabel="層番号", ylabel="電極端の x 位置 [mm]",
                   title="電極ずれは層番号に対する直線として出る",
                   caption="外形指標はこの劣化に完全に盲目(体積が変わらない)。")
    return {"slope": m["slope"], "true": t["shift"], "zero": m0["slope"],
            "d_outer": o["caliper"] - o0["caliper"]}


# --------------------------------------------------------------------------- #
# 節 6 —— 崖(1): 分解能。標本化定理の側から先に予測して突き合わせる
# --------------------------------------------------------------------------- #
def section_resolution(cells, sinos) -> dict:
    print("\n" + "=" * 78)
    print("6) 崖(1) 分解能 —— ボクセルが層厚の何倍で層は融合するか")
    print("=" * 78)
    v_nyq = 0.5 * PITCH
    print("  ★先に予測する: 層は周期 %.3f mm の縞なので、標本化定理は"
          " voxel < %.3f mm を要求する。" % (PITCH, v_nyq))
    print("     電極厚 %.3f mm に対する比では **voxel/層厚 = %.2f が崖**のはず。"
          % (T_ELEC, v_nyq / T_ELEC))
    print("     もう 1 つの限界: 再構成のぼけ σ ≈ 0.6 voxel は縞の振幅を"
          " exp(-2π²σ²/p²) に落とす。")

    rec = acquire(sinos["gas"])
    truth = cells["gas"]["truth"]
    rows, ratios, n_err, t_err, v_err, mod, fftp = [], [], [], [], [], [], []
    for v in (0.04, 0.06, 0.08, 0.10, 0.12, 0.16, 0.20, 0.24):
        if v > SY + 1e-9:
            sigma = 0.6 * v
            cutoff = 1.0 / (2.0 * np.pi * sigma)          # cycles/mm
            blur = np.asarray(L.vol_fft_lowpass(rec, cutoff, SPACING))
            shape = (ND, max(8, int(round(NH * SY / v))), max(8, int(round(NW * SX / v))))
            small = np.asarray(L.vol_resize(blur, shape=shape, order=1))
            sp = (SZ, NH * SY / shape[1], NW * SX / shape[2])
        else:
            small, sp, sigma = rec, SPACING, 0.6 * SY
        m = internal_metrics(small, sp)
        ratio = sp[1] / T_ELEC
        theo = float(np.exp(-2.0 * np.pi ** 2 * sigma ** 2 / PITCH ** 2))
        ratios.append(ratio)
        n_err.append(m["n_layer"] - truth["n_layer"])
        t_err.append(100.0 * (m["t_mean"] - T_ELEC) / T_ELEC
                     if np.isfinite(m["t_mean"]) else np.nan)
        v_err.append(100.0 * (m["void_volume"] - truth["void_volume"])
                     / truth["void_volume"])
        mod.append(100.0 * theo)
        fftp.append(m["fft_pitch"])
        rows.append(["%.3f" % sp[1], "%.2f" % ratio, "%d" % m["n_layer"],
                     "%d..%d" % (m["n_layer_min"], m["n_layer_max"]),
                     "%.3f" % m["t_mean"], "%.3f" % m["fft_pitch"],
                     "%.2f" % m["void_fraction"], "%.0f" % (100 * theo)])
        print("   voxel %.3f mm (層厚比 %.2f)  層数 %2d (%2d..%2d)  層厚 %.3f mm  "
              "周期 %.3f mm  空隙率 %.2f %%  予測コントラスト %3.0f %%"
              % (sp[1], ratio, m["n_layer"], m["n_layer_min"], m["n_layer_max"],
                 m["t_mean"], m["fft_pitch"], m["void_fraction"], 100 * theo))

    bad = [r for r, e in zip(ratios, n_err) if e != 0]
    cliff = min(bad) if bad else float("nan")
    print("\n  ★実測の崖: 層数が狂い始めるのは voxel/層厚 = %.2f。予測は %.2f。"
          % (cliff, v_nyq / T_ELEC))
    ok_fft = [r for r, p in zip(ratios, fftp) if abs(p - PITCH) < 0.02 * PITCH]
    print("     **数えるのと周期を測るのは別の崖**: 周期(FFT)は"
          " voxel/層厚 %.2f まで %.3f mm を保つ。" % (max(ok_fft), PITCH))

    figs.save_plot("sweep_resolution",
                   [("層数の誤差 [枚]", ratios, n_err),
                    ("層厚の誤差 [%]", ratios, t_err),
                    ("空隙体積の誤差 [%]", ratios, v_err),
                    ("縞の予測コントラスト [%]", ratios, mod)],
                   xlabel="voxel / 電極厚", ylabel="誤差 [枚 or %]",
                   title="分解能の崖(予測 %.2f)" % (v_nyq / T_ELEC),
                   caption="層厚の誤差は崖の手前でも大きい。空隙は層より早く痩せる。")
    figs.save_table("sweep_resolution_table",
                    ["voxel mm", "voxel/層厚", "層数", "層数の幅", "層厚 mm",
                     "FFT 周期 mm", "空隙率 %", "予測 コントラスト %"], rows,
                    title="分解能を振る(真値: 層 17 枚 / 層厚 0.200 mm / 周期 0.320 mm)")
    return {"ratios": ratios, "n_err": n_err, "cliff": cliff,
            "pred": v_nyq / T_ELEC, "fft_ok": max(ok_fft)}


# --------------------------------------------------------------------------- #
# 節 7 —— 崖(2): 雑音とビームハードニング
# --------------------------------------------------------------------------- #
def section_noise_streak(cells, sinos) -> dict:
    print("\n" + "=" * 78)
    print("7) 崖(2) 雑音とビームハードニング —— 壊れ方を種類ごとに数える")
    print("=" * 78)
    truth = cells["gas"]["truth"]

    print("  フォトン数を振る(ビームハードニングは公称のまま):")
    n0s, n_err, v_err, sd = [], [], [], []
    for n0 in (3.0e6, 3.0e5, 1.0e5, 3.0e4, 1.0e4, 3.0e3):
        rec = acquire(sinos["gas"], n0=n0)
        m = internal_metrics(rec)
        n0s.append(np.log10(n0))
        n_err.append(m["n_layer"] - truth["n_layer"])
        v_err.append(100.0 * (m["void_volume"] - truth["void_volume"])
                     / truth["void_volume"])
        sd.append(m["pitch_sd"])
        print("   N0 = %8.0f  層数 %2d (%2d..%2d)  層厚 %.3f mm  "
              "空隙率 %.2f %% (真 %.2f %%)  層間隔σ %.3f mm"
              % (n0, m["n_layer"], m["n_layer_min"], m["n_layer_max"],
                 m["t_mean"], m["void_fraction"],
                 100.0 * truth["void_volume"] / m["roi_volume"], m["pitch_sd"]))

    print("\n  ビームハードニングを振る(硬さ比 1.0 = 単色 = むら無し):")
    bhs, bh_terr, bh_verr, bh_cal = [], [], [], []
    for bh in (1.0, 0.85, 0.70, 0.55, 0.40):
        rec = acquire(sinos["gas"], bh=bh)
        m = internal_metrics(rec)
        o = outer_metrics(rec)
        bhs.append(bh)
        bh_terr.append(100.0 * (m["t_mean"] - T_ELEC) / T_ELEC)
        bh_verr.append(100.0 * (m["void_volume"] - truth["void_volume"])
                       / truth["void_volume"])
        bh_cal.append(o["caliper"])
        print("   硬さ比 %.2f  層厚 %.3f mm (%+.1f %%)  空隙率 %.2f %%  "
              "外形 中央 %.3f mm  コントラスト %.3f"
              % (bh, m["t_mean"], bh_terr[-1], m["void_fraction"],
                 o["caliper"], m["contrast"]))
    print("  ★ビームハードニングは**外形指標をほとんど動かさない**"
          "(中央 %.3f -> %.3f mm)。缶の縁は強い縁なので生き残る。"
          % (bh_cal[0], bh_cal[-1]))
    print("     壊れるのは中の指標のほう —— 缶に近い層のコントラストが"
          "落ちて空隙体積が %+.1f %% -> %+.1f %% と動く。" % (bh_verr[0], bh_verr[-1]))

    figs.save_plot("sweep_noise",
                   [("層数の誤差 [枚]", n0s, n_err),
                    ("空隙体積の誤差 [%]", n0s, v_err),
                    ("層間隔の散らばり x100 [mm]", n0s, [100 * s for s in sd])],
                   xlabel="log10(フォトン数 N0)", ylabel="誤差",
                   title="雑音の崖 —— 空隙が先に壊れ、層数は後から壊れる")
    figs.save_plot("sweep_beamhardening",
                   [("層厚の誤差 [%]", bhs, bh_terr),
                    ("空隙体積の誤差 [%]", bhs, bh_verr),
                    ("外形 中央 [mm] x10", bhs, [10 * c for c in bh_cal])],
                   xlabel="ビームハードニングの硬さ比(1.0 = 単色)",
                   ylabel="誤差 [%] / 外形 x10 [mm]",
                   title="低周波むらは外形を動かさず、内部指標だけを曲げる")
    return {"n0": n0s, "n_err": n_err, "v_err": v_err,
            "bh": bhs, "bh_terr": bh_terr, "bh_verr": bh_verr, "bh_cal": bh_cal}


# --------------------------------------------------------------------------- #
# 節 8 —— 測れないもの / 道具の穴
# --------------------------------------------------------------------------- #
def section_limits() -> None:
    print("\n" + "=" * 78)
    print("8) 測れないもの、と道具の穴")
    print("=" * 78)
    print("  * この PoC は **SoH(健全度)も寿命も測っていない**。測ったのは"
          "「外形指標が内部の違いに盲目であること」と「どの分解能・雑音まで"
          "内部指標が生き残るか」だけ。容量劣化との対応づけには"
          "**充放電の実測**が要る(画像だけでは原理的に出ない)。")
    print("  * 空隙率は「ガスの体積 / ROI の体積」であって、電気化学的な"
          "ガス発生量ではない(溶解した分は写らない)。")
    print("  * 3-D の落とし穴: 座標の順が 2 系統ある —— **点の op は (N,3)=(x,y,z)、"
          "ボリュームの op は (D,H,W)=(z,y,x)**。この PoC は組み立てを格子順で"
          "通し、最後に 1 回だけ転置している(`to_volume`)。")
    print("  * `fit_plane_3d` の法線は**符号が任意**。平面度(残差)は符号に"
          "依らないので使えるが、傾きの向きを言うときは基準が要る。")

    print("\n  公開経路に無かった処理(自前で書いた):")
    assert not hasattr(fs, "sdf_offset_field") and not hasattr(L, "sdf_offset_field")
    print("   (a) `sdf_offset` は**スカラのみ**。場でゼロ等値面を動かす口が無い"
          "(缶のたわみは格子を歪めて評価した)。")
    assert not hasattr(fs, "vol_convolve") and not hasattr(L, "vol_convolve")
    print("   (b) `vol_gaussian_psf` で PSF は作れるのに、それで**畳み込む** op が"
          "無い(`vol_richardson_lucy` は逆問題側だけ)。ぼけは"
          " `vol_fft_lowpass` の伝達関数 exp(-f²/2c²) を σ=1/(2πc) と読み替えて使った。")
    assert not any(hasattr(o, n) for o in (fs, L) for n in ("profile_period",
                                                            "autocorrelation_1d"))
    print("   (c) 1-D プロファイルの**卓越周期・自己相関**を出す op が無い"
          "(積層のような周期構造では層を数えるより頑健なのに)。")
    print("   (d) 二値ボリュームの**外形が囲む高さ/体積**(穴を埋めた包絡)を出す口が"
          "無い。缶の外形高さは列ごとに自前で数えた。")
    assert hasattr(L, "grid_coords") and not hasattr(fs, "grid_coords")
    print("   (e) `grid_coords` / `plane_sdf` / `box_sdf` / `sdf_*` / `esdf` /"
          " `render_volume_projection` / `fit_plane_3d` は `fullseye.ledger` 経由のみ"
          "(1 行ファサードには出ていない)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("電池セルの劣化を CT で測る —— 膨れは外から見え、原因は中にある")
    print("=" * 78)

    # --- 4 通りのセルを作る。局所膨れとガス空隙は**外形のふくらみを揃える** ---
    cells = {"healthy": build_cell("healthy"), "uniform": build_cell("uniform")}
    target = cells["uniform"]["truth"]["mean_excess"]
    s_local = match_to_bulge("local", target)
    s_gas = match_to_bulge("gas", target)
    cells["local"] = build_cell("local", s_local)
    cells["gas"] = build_cell("gas", s_gas)
    cells["misalign"] = build_cell("misalign")
    print("  外形のふくらみを揃える(面平均のはみ出し %.4f mm):"
          " 局所膨れの倍率 %.4f / ガス空隙の倍率 %.4f" % (target, s_local, s_gas))

    sinos = {k: forward(c["mu"]) for k, c in cells.items()}
    print("  順投影 %d 条件 x %d 角 (%.1f 秒経過)" % (
        len(sinos), N_ANGLE, time.perf_counter() - t0))
    recs = {k: acquire(s) for k, s in sinos.items()}

    scene = section_scene(cells, recs)
    outer = section_outer_blindness(cells, recs)
    ctrl = section_control(cells, recs)
    void = section_voidmap(cells, recs)
    mis = section_misalign(cells, recs)
    resn = section_resolution(cells, sinos)
    noise = section_noise_streak(cells, sinos)
    section_limits()

    # --- 所見を固定する(壊れたら鳴る)---
    assert 25.0 < outer["frac"] < 35.0, outer["frac"]
    assert abs(outer["frac"] - outer["pred"]) < 1e-6
    assert 3.0 < outer["ratio"] < 5.5, outer["ratio"]
    assert ctrl["res"]["uniform"]["inner"]["t_mean"] > \
        ctrl["res"]["gas"]["inner"]["t_mean"] + 0.005
    assert ctrl["res"]["gas"]["inner"]["void_fraction"] > \
        5.0 * ctrl["res"]["uniform"]["inner"]["void_fraction"] + 0.1
    assert abs(mis["slope"] - mis["true"]) < 0.25 * mis["true"]
    assert abs(mis["d_outer"]) < 0.02
    assert np.isfinite(resn["cliff"])

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 一様膨れ %.0f %% のうち外形に出るのは %.1f %%。残りは"
          "クリアランスが飲む。" % (100 * ALPHA_UNIFORM, outer["frac"]))
    print("  * 中央のノギスは体積等価な平均の %.1f 倍を読む。" % outer["ratio"])
    print("  * 外形を揃えた 3 つのセルは、層厚・空隙率・平面度で分かれる。")
    print("  * 分解能の崖は voxel/層厚 = %.2f(予測 %.2f)。周期の測定は"
          " %.2f まで持つ。" % (resn["cliff"], resn["pred"], resn["fft_ok"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
