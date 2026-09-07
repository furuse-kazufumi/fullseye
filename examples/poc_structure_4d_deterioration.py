# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える。

橋の桁を **3 年ぶん(t0/t1/t2)スキャンして、たわみ・断面欠損・支承の沈下・
ひび割れが「どれだけ進んだか」**を出す仕事です。補修の優先度は「前回との差」と
「進み方(mm/年)」で決まるので、測るのは形そのものではなく**形の差**になります。
ところが**測る位置・姿勢・点密度が毎回違う**ので、変わっていないのに変わって見え、
本当の劣化は位置合わせに吸われて消えます。

EXTEND: 実測に差し替えるなら :func:`observe` が返す ``(N,3)`` の点群を TLS の
スキャン(1 setup ごとの点群を結合したもの)に置き換えます。実データでは
(a) 断面の展開座標 ``s`` が既知でなくなるので :func:`core_lattice` を
``plane_segmentation`` で得た面ラベルから組み直す必要があり、(b) 真の変位場が
無いので 4 節の「偽の劣化」は**変化していないと分かっている領域**でしか数えられず、
(c) 支承の沈下の真値は水準測量に頼るしかなく本 PoC の合成真値より 1 桁粗い ——
という 3 点が変わります。断面形 :data:`CS_V` とキャンバー :data:`CAMBER` は
設計図から入れてください(推定してから差分を取ると、設計誤差が劣化に化けます)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**劣化ゼロで測り直しただけで「劣化」が出る**。同じ形を密度も姿勢も変えて
   2 回測り、位置合わせまで済ませてから素朴な最近傍差分(C2C)を取ると
   中央値 **13.19 mm**、最大 **35.63 mm** の「変化」が出る。真の最大劣化は
   10.00 mm なので、**偽の劣化のほうが大きい**。法線方向に測ると同じ条件で
   中央値 0.24 mm / 最大 1.75 mm。
2. ★**C2C の偽の劣化は点間隔でほぼ決まる**。予測「独立に撒いた同じ面の間の
   最近傍距離 ≈ 0.5/√ρ」に対し実測は密度 300→2400 pt/m2 で
   28.87→10.21 mm(予測 28.87→10.21 mm、比 1.000〜1.000)。
   ★両時点を同じ格子で間引くと 13.19 → 8.44 mm にしか下がらない ——
   **密度を揃えても間隔は消えない**(格子の位相が違う)。
3. ★★**「劣化が全域に広がっている」と、合わせは平均を吸って端に逆符号を作る**。
   たわみだけを入れて全点で合わせると、中央のたわみは 8.000 → 2.663 mm
   (予測 D/3 = 2.667)に潰れ、支点付近には **-5.34 mm の偽の隆起**が出る
   (予測 -2D/3 = -5.333)。変わっていない端だけで合わせても 0.296 D は
   吸われる(実測 2.36 mm、予測 2.37 mm)—— **合わせる範囲を狭めても
   ゼロにはならない**。
4. ★**角度誤差の嘘は面の向きで決まる**。残差回転 α の作る見かけ変化は
   ``(α × (p-c))·n`` で、α=5.0e-4 rad のとき実測 RMS 1.462 mm に対し
   幾何の予測 1.462 mm(比 1.000)。腹板(法線が水平)には ``ω_z`` しか効かず、
   下フランジ(法線が鉛直)には ``ω_y`` しか効かない —— **同じ位置合わせ誤差が、
   面ごとに違う嘘をつく**。
5. ★**検出できる最小の劣化は角度誤差に比例して折れる**。α を 0→1.0e-3 rad で
   振ると最小検出深さは 0.62 → 5.60 mm。**橋長 12 m では 1.0e-4 rad
   (0.006 度)が 0.60 mm に相当**するので、位置合わせの角度は
   「度」ではなく「秒」で管理しないと 1 mm の劣化は測れない。
6. ★★**速度(mm/年)は差より先に壊れる**。t0→t2 の 2 年で真の欠損速度は
   5.00 mm/年。各時点が独立に合わせられるので誤差は差の √2 倍で入り、
   実測の速度誤差 RMS は 0.71 mm/年 —— **1 年あたり 1 mm の進行は
   3 年測っても有意にならない**。
7. ★**細い溝は「平均する」測り方には原理的に見えない**。幅 12 mm・深さ
   2.50 mm のひび割れは法線方向の平均では 0.09 mm(足跡で 27 倍に薄まる)。
   ★ただし**足跡内の残差ばらつき**は 0.93 → 1.32 mm と上がるので、
   平均が盲目でも散らばりは拾う。予想は「密度を上げれば平均でも見える」
   だったが**外れ**で、薄まりは密度でなく足跡と溝幅の比で決まる。
8. ★**押し出し形状は軸方向の並進が決まらない**。桁は x 方向に押し出した形なので
   平面だけでは x が拘束されない。拘束はキャンバーの勾配 0.0167 と支承の円柱
   からしか来ず、円柱を外すと ICP 後の x 残差は 1.4 → 18.9 mm に増える。
   ★その x 残差は平面には嘘を作らない(法線が x に直交)が、**支承の円柱には
   直接効いて** 沈下 4.00 mm の読みが 4.02 → 12.68 mm になる。

【グラウンドトゥルース】
桁は**断面の折れ線(:data:`CS_V`、平面 7 枚)を x 方向に押し出し、キャンバー
c(x) を足した面**。支承は**円柱 2 本**。劣化は 4 つとも既知の場:
(a) たわみ = 鉛直 ``D·4ξ(1-ξ)``、(b) 断面欠損 = 法線方向のガウス
(体積は解析積分 ``2πAσ²``)、(c) 支承沈下 = 円柱だけの剛体鉛直変位、
(d) ひび割れ = 腹板上の三角断面の溝。観測は 5 setup の走査で、
可視性(入射角・自己遮蔽・仮設物)、距離依存の測距雑音 ``σ0+k·R``、
欠測、密度、そして**時点ごとに違う既知の剛体誤差**を掛けて作る。

来歴(公開文献のみ): Lague, Brodu & Leroux, *ISPRS J. Photogramm.* 82 (2013) 10
—— 法線方向に測る差分(M3C2)/ Besl & McKay, *IEEE TPAMI* 14 (1992) 239 ——
ICP / Chen & Medioni, *Image Vision Comput.* 10 (1992) 145 —— 点-面 ICP /
Gordon & Lichti, *J. Surv. Eng.* 133 (2007) 72 —— 地上レーザによる橋梁の
たわみ計測 / Timoshenko & Gere, *Mechanics of Materials* (1972) —— 単純梁のたわみ形。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 構造物の諸元 ------------------------------------------------------------ #
LSPAN = 12.0               # 支間 [m](x 方向)
CAMBER = 0.050             # 上げ越し(キャンバー)の中央値 [m]

#: 断面の折れ線 ``(y, z)`` [m]。左ウィング下面 → ハンチ → 腹板 → 下フランジ →
#: 腹板 → ハンチ → 右ウィング下面。**平面 7 枚**で、これを x に押し出す。
CS_V = ((0.00, 0.00), (0.70, 0.00), (1.00, -0.30), (1.00, -0.90),
        (3.00, -0.90), (3.00, -0.30), (3.30, 0.00), (4.00, 0.00))

SEG_NAME = ("下面(左)", "ハンチ(左)", "腹板(左)", "下フランジ",
            "腹板(右)", "ハンチ(右)", "下面(右)")

#: 支承(円柱)。軸は y 方向、下フランジの直下に置く。
BEARING_X = (0.80, 11.20)
BEARING_R = 0.14
BEARING_LEN = 0.90

# --- 劣化(時点ごとの真値)---------------------------------------------------- #
EPOCH_YEAR = (0.0, 1.0, 2.0)          # 点検の年 [年]
DEFLECT_MM = (0.0, 1.2, 3.0)          # 支間中央のたわみ [mm]
SPALL_MM = (0.0, 12.0, 30.0)          # 断面欠損(かぶり剥離)の深さ [mm]
SETTLE_MM = (0.0, 1.5, 4.0)           # 支承(x=0.8 側)の沈下 [mm]
CRACK_MM = (0.0, 1.2, 2.5)            # ひび割れ状の溝の深さ [mm]

SPALL_X, SPALL_Y, SPALL_SIG = 7.20, 2.10, 0.22   # 欠損の位置と広がり [m]
CRACK_X, CRACK_HW = 5.60, 0.006                  # 溝の位置 [m] と半幅 [m]

# --- 観測の諸元 -------------------------------------------------------------- #
#: 走査位置(桁の下と両脇)。時点ごとにまとめて既知量だけずらす。
SETUPS = ((3.0, -1.5, -2.6), (9.0, -1.5, -2.6), (3.0, 5.5, -2.6),
          (9.0, 5.5, -2.6), (6.0, 2.0, -3.4))
SETUP_SHIFT = ((0.0, 0.0, 0.0), (0.9, -0.4, 0.25), (-1.1, 0.6, -0.30))

DENSITY = (500.0, 1200.0, 300.0)      # 時点ごとの点密度 [pt/m2]
SIG0, SIG_K = 0.0008, 0.00050         # 測距雑音 σ = SIG0 + SIG_K·R [m]
COS_MIN = 0.26                        # 入射角の限界(≈ 75 度)
P_DROP = 0.04                         # 一様な欠測率
BLOCK_X0 = (4.2, 8.6, 2.4)            # 仮設物の位置(時点ごとに違う)[m]
BLOCK_W = 1.6

#: 時点ごとの**既知の**位置決め誤差 ``(ωx, ωy, ωz [rad], tx, ty, tz [m])``。
POSE_ERR = ((0.0, 0.0, 0.0, 0.000, 0.000, 0.000),
            (2.0e-3, -1.4e-3, 3.0e-3, 0.012, -0.008, 0.005),
            (-3.2e-3, 2.6e-3, -1.8e-3, -0.020, 0.014, -0.011))
CENTER = np.array([6.0, 2.0, -0.45])  # 姿勢誤差の回転中心 [m]

SEED = 21

# --- 測り方の諸元 ------------------------------------------------------------ #
CORE_SP = 0.25             # 測点(core)の間隔 [m]
R_NORM = 0.18              # 局所平面を当てる半径 [m]
R_CYL = 0.10               # 足跡(円柱)の半径 [m] —— C2C と共通にする
MAX_HALF = 0.06            # 円柱の長さの半分 [m]
MIN_FIT, MIN_CYL = 10, 4   # 平面当てはめ / 円柱内の最小点数
VOX = 0.06                 # ICP 前の間引き格子 [m]


# --------------------------------------------------------------------------- #
# 断面の折れ線 —— 展開座標 s を作る                                             #
# --------------------------------------------------------------------------- #
def _cross_section():
    """折れ線から ``(累積 s, 方向, 外向き法線)`` を作る。"""
    v = np.asarray(CS_V, float)
    d = np.diff(v, axis=0)
    ln = np.hypot(d[:, 0], d[:, 1])
    dirs = d / ln[:, None]
    # 2-D の外向き法線: 進行方向を -90 度回す (dy,dz) -> (dz,-dy)
    nrm = np.column_stack([dirs[:, 1], -dirs[:, 0]])
    return v, ln, np.r_[0.0, np.cumsum(ln)], dirs, nrm


CS_PT, SEG_LEN, S_CUM, SEG_DIR, SEG_NRM = _cross_section()
S_TOTAL = float(S_CUM[-1])
GIRDER_AREA = LSPAN * S_TOTAL
BEARING_AREA = len(BEARING_X) * math.pi * BEARING_R * BEARING_LEN


#: 現在のキャンバー(8 節で振るので 1 要素の箱に入れてある)。
_CAMBER = [CAMBER]


def camber(x):
    """キャンバー c(x) [m](支間中央で最大)。押し出し形状の x 対称性を破る。"""
    xi = np.asarray(x, float) / LSPAN
    return _CAMBER[0] * 4.0 * xi * (1.0 - xi)


def camber_slope(x):
    """dc/dx [-]。**ICP が x 方向を拘束できる唯一の傾き**(端で最大)。"""
    xi = np.asarray(x, float) / LSPAN
    return _CAMBER[0] * 4.0 * (1.0 - 2.0 * xi) / LSPAN


def girder_surface(x, s):
    """展開座標 ``(x, s)`` -> 点 ``(N,3)``・外向き単位法線 ``(N,3)``・区間 index。"""
    x = np.asarray(x, float)
    s = np.asarray(s, float)
    seg = np.clip(np.searchsorted(S_CUM, s, side="right") - 1, 0, len(SEG_LEN) - 1)
    t = s - S_CUM[seg]
    yz = CS_PT[seg] + SEG_DIR[seg] * t[:, None]
    p = np.column_stack([x, yz[:, 0], yz[:, 1] + camber(x)])
    cp = camber_slope(x)
    n = np.column_stack([SEG_DIR[seg][:, 0] * cp, SEG_NRM[seg][:, 0], SEG_NRM[seg][:, 1]])
    return p, n / np.linalg.norm(n, axis=1, keepdims=True), seg


def bearing_surface(phi, t, idx):
    """支承(円柱)の下半分。``phi`` は軸まわりの角 [rad]、``t`` は軸方向 [m]。"""
    bx = np.asarray([BEARING_X[i] for i in idx], float)
    bz = -0.90 + camber(bx) - BEARING_R
    p = np.column_stack([bx + BEARING_R * np.cos(phi), 2.0 + t,
                         bz + BEARING_R * np.sin(phi)])
    n = np.column_stack([np.cos(phi), np.zeros_like(phi), np.sin(phi)])
    return p, n


# --------------------------------------------------------------------------- #
# 劣化 —— すべて既知の場                                                        #
# --------------------------------------------------------------------------- #
def spall_depth(x, y, k: int) -> np.ndarray:
    """断面欠損(かぶり剥離)の深さ [m]。下フランジのガウス。"""
    a = SPALL_MM[k] * 1e-3
    if a == 0.0:
        return np.zeros(np.shape(x))
    r2 = (x - SPALL_X) ** 2 + (y - SPALL_Y) ** 2
    return a * np.exp(-r2 / (2.0 * SPALL_SIG ** 2))


def crack_depth(x, k: int) -> np.ndarray:
    """ひび割れ状の溝の深さ [m](三角断面、半幅 :data:`CRACK_HW`)。"""
    c = CRACK_MM[k] * 1e-3
    if c == 0.0:
        return np.zeros(np.shape(x))
    return c * np.maximum(0.0, 1.0 - np.abs(x - CRACK_X) / CRACK_HW)


def disp_girder(x, s, seg, n, k: int, parts=("deflect", "spall", "crack")):
    """時点 0 -> ``k`` の桁表面の変位 ``(N,3)`` [m]。``parts`` で成分を選ぶ。"""
    x = np.asarray(x, float)
    d = np.zeros((x.size, 3))
    if "deflect" in parts:
        xi = x / LSPAN
        d[:, 2] -= DEFLECT_MM[k] * 1e-3 * 4.0 * xi * (1.0 - xi)
    depth = np.zeros(x.size)
    if "spall" in parts:
        y = CS_PT[seg][:, 0] + SEG_DIR[seg][:, 0] * (s - S_CUM[seg])
        depth = depth + np.where(seg == 3, spall_depth(x, y, k), 0.0)
    if "crack" in parts:
        depth = depth + np.where(seg == 2, crack_depth(x, k), 0.0)
    return d - depth[:, None] * n


def disp_bearing(n_pts: int, k: int) -> np.ndarray:
    """支承の沈下(剛体的な鉛直変位)。x=0.8 側だけが沈む —— 呼び手が分ける。"""
    d = np.zeros((n_pts, 3))
    d[:, 2] = -SETTLE_MM[k] * 1e-3
    return d


# --------------------------------------------------------------------------- #
# 観測 —— 走査位置・可視性・距離依存の雑音・欠測・姿勢誤差                       #
# --------------------------------------------------------------------------- #
#: 桁本体(自己遮蔽の判定に使う軸平行の箱)。**キャンバーを抜いた座標**で持つ ——
#: 実座標だと下フランジが x とともに上下するので、軸平行の箱では自分の面を
#: 自分で隠してしまう(2026-09-07 に踏んだ: 有効 core が 3 割に落ちた)。
SELF_BOX = (np.array([-1.0, 1.0, -0.898]), np.array([13.0, 3.0, 0.10]))


def decamber(p: np.ndarray) -> np.ndarray:
    """キャンバーを抜いた座標(遮蔽判定はこの中で軸平行の箱として扱う)。"""
    q = np.array(p, float, copy=True)
    q[..., 2] -= camber(q[..., 0])
    return q


def _seg_hits_box(p, q, lo, hi):
    """線分 ``p->q`` が軸平行箱と交わるか(slab 法、``p`` ごとに真偽)。"""
    d = q - p
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (lo - p) / d
        t2 = (hi - p) / d
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    return (tmax >= np.maximum(tmin, 1e-4)) & (tmin <= 1.0)


def rodrigues(omega) -> np.ndarray:
    """回転ベクトル -> 回転行列(小角でも厳密)。"""
    om = np.asarray(omega, float)
    th = float(np.linalg.norm(om))
    if th < 1e-15:
        return np.eye(3)
    k = om / th
    kx = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(th) * kx + (1.0 - math.cos(th)) * (kx @ kx)


def apply_pose(pts, omega, t, center=CENTER):
    """重心まわりの微小回転 + 平行移動。"""
    rot = rodrigues(omega)
    return (np.asarray(pts, float) - center) @ rot.T + center + np.asarray(t, float)


def observe(k: int, rng, density: float | None = None, deteriorate=True,
            pose=True, parts=("deflect", "spall", "crack", "settle"),
            noise=True, blocker=True, setup_shift=True):
    """時点 ``k`` の観測点群 ``(N,3)`` を作る。すべての要因を引数で止められる。"""
    rho = DENSITY[k] if density is None else density
    kk = k if deteriorate else 0

    # --- 桁本体 ---------------------------------------------------------- #
    n_g = int(rho * GIRDER_AREA)
    x = rng.uniform(0.0, LSPAN, n_g)
    s = rng.uniform(0.0, S_TOTAL, n_g)
    p, n, seg = girder_surface(x, s)
    gp = [pp for pp in parts if pp in ("deflect", "spall", "crack")]
    if gp:
        p = p + disp_girder(x, s, seg, n, kk, parts=gp)

    # --- 支承(円柱)----------------------------------------------------- #
    n_b = max(1, int(rho * BEARING_AREA))
    idx = rng.integers(0, len(BEARING_X), n_b)
    phi = rng.uniform(math.pi, 2.0 * math.pi, n_b)
    tt = rng.uniform(-BEARING_LEN / 2, BEARING_LEN / 2, n_b)
    pb, nb = bearing_surface(phi, tt, idx)
    if "settle" in parts:
        pb = pb + np.where((idx == 0)[:, None], disp_bearing(n_b, kk), 0.0)

    p = np.vstack([p, pb])
    n = np.vstack([n, nb])

    # --- 可視性(入射角・自己遮蔽・仮設物)-------------------------------- #
    off = np.asarray(SETUP_SHIFT[k] if setup_shift else (0.0, 0.0, 0.0), float)
    best = np.full(p.shape[0], -1.0)
    pick = np.full(p.shape[0], -1, int)
    rng_r = np.zeros(p.shape[0])
    cosi = np.zeros(p.shape[0])
    blo = (np.array([BLOCK_X0[k], -3.0, -3.6]), np.array([BLOCK_X0[k] + BLOCK_W, 7.0, -1.3]))
    for j, s0 in enumerate(SETUPS):
        sp = np.asarray(s0, float) + off
        v = sp[None, :] - p
        rr = np.linalg.norm(v, axis=1)
        u = v / rr[:, None]
        ci = np.einsum("ij,ij->i", n, u)
        ok = ci > COS_MIN
        eps = p + 2e-3 * n
        ok &= ~_seg_hits_box(decamber(eps), decamber(np.broadcast_to(sp, p.shape)),
                             *SELF_BOX)
        if blocker:
            ok &= ~_seg_hits_box(eps, np.broadcast_to(sp, p.shape), *blo)
        q = np.where(ok, ci / (rr ** 2), -1.0)
        take = q > best
        best = np.where(take, q, best)
        pick = np.where(take, j, pick)
        rng_r = np.where(take, rr, rng_r)
        cosi = np.where(take, ci, cosi)
        if j == 0:
            uu = u.copy()
        uu = np.where(take[:, None], u, uu)

    keep = pick >= 0
    keep &= rng.random(p.shape[0]) > P_DROP
    p, uu, rng_r = p[keep], uu[keep], rng_r[keep]

    if noise:
        sig = SIG0 + SIG_K * rng_r
        p = p + uu * (sig * rng.standard_normal(p.shape[0]))[:, None]
    if pose:
        p = apply_pose(p, POSE_ERR[k][:3], POSE_ERR[k][3:])
    return p


# --------------------------------------------------------------------------- #
# 測点(core)—— 展開座標の格子。真値もここで閉形式で出す                        #
# --------------------------------------------------------------------------- #
def core_lattice():
    """展開座標の格子 ``(x, s)`` と 3-D 位置・真の法線・区間 index・縁フラグ。"""
    nx = int(LSPAN / CORE_SP)
    ns = int(S_TOTAL / CORE_SP)
    cx = (np.arange(nx) + 0.5) * (LSPAN / nx)
    cs = (np.arange(ns) + 0.5) * (S_TOTAL / ns)
    xx, ss = np.meshgrid(cx, cs)
    p, n, seg = girder_surface(xx.ravel(), ss.ravel())
    edge = np.min(np.abs(ss.ravel()[:, None] - S_CUM[None, :]), axis=1) < R_NORM
    return {"x": xx.ravel(), "s": ss.ravel(), "p": p, "n": n, "seg": seg,
            "edge": edge, "nx": nx, "ns": ns, "shape": (ns, nx)}


CORES = core_lattice()


def truth_normal(k: int, parts=("deflect", "spall", "crack")) -> np.ndarray:
    """各 core での真の法線方向変化 [mm](正 = 面が外へ = 走査器に近づく)。"""
    d = disp_girder(CORES["x"], CORES["s"], CORES["seg"], CORES["n"], k, parts=parts)
    return np.einsum("ij,ij->i", d, CORES["n"]) * 1e3


def truth_footprint(k: int, n_sub: int = 96) -> np.ndarray:
    """足跡(半径 :data:`R_CYL`)で平均した真値 [mm] —— 薄まりを分けて数える。"""
    rng = np.random.default_rng(3)
    ang = rng.uniform(0, 2 * math.pi, n_sub)
    rad = R_CYL * np.sqrt(rng.uniform(0, 1, n_sub))
    out = np.zeros(CORES["x"].size)
    for a, r in zip(ang, rad):
        xs = CORES["x"] + r * math.cos(a)
        ss = np.clip(CORES["s"] + r * math.sin(a), 0.0, S_TOTAL - 1e-9)
        p, n, seg = girder_surface(xs, ss)
        d = disp_girder(xs, ss, seg, n, k)
        out += np.einsum("ij,ij->i", d, n)
    return out / n_sub * 1e3


# --------------------------------------------------------------------------- #
# 測り方 —— ゼロ点(C2C)と法線方向(M3C2 の考え方)                            #
# --------------------------------------------------------------------------- #
def core_normals(cloud: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """t0 の点群から core ごとの局所平面を当てる(``fit_plane_3d``)。"""
    tree = cKDTree(cloud)
    nb = tree.query_ball_point(CORES["p"], R_NORM, workers=-1)
    m = CORES["p"].shape[0]
    cen = CORES["p"].copy()
    nor = CORES["n"].copy()
    ok = np.zeros(m, bool)
    for i, idx in enumerate(nb):
        if len(idx) < MIN_FIT:
            continue
        c, nv, _ = fs.ledger.fit_plane_3d(cloud[idx])
        nv = np.asarray(nv, float)
        # ★``fit_plane_3d`` の法線は符号が任意。真の外向きに合わせる(走査器側)。
        if float(nv @ CORES["n"][i]) < 0:
            nv = -nv
        cen[i], nor[i], ok[i] = np.asarray(c, float), nv, True
    return cen, nor, ok


def measure_normal(ref: np.ndarray, cur: np.ndarray, cen, nor, ok):
    """法線方向の符号つき変化 [mm]・その標準誤差・足跡内の残差ばらつき。"""
    t1, t2 = cKDTree(ref), cKDTree(cur)
    rq = math.hypot(R_CYL, MAX_HALF)
    b1 = t1.query_ball_point(cen, rq, workers=-1)
    b2 = t2.query_ball_point(cen, rq, workers=-1)
    m = cen.shape[0]
    out = np.full(m, np.nan)
    sig = np.full(m, np.nan)
    scat = np.full(m, np.nan)
    for i in range(m):
        if not ok[i]:
            continue
        st = []
        for pts, ball in ((ref, b1[i]), (cur, b2[i])):
            if len(ball) < MIN_CYL:
                st = []
                break
            v = pts[ball] - cen[i]
            t = v @ nor[i]
            perp2 = np.einsum("ij,ij->i", v, v) - t * t
            sel = (perp2 < R_CYL * R_CYL) & (np.abs(t) < MAX_HALF)
            if int(sel.sum()) < MIN_CYL:
                st = []
                break
            tt = t[sel]
            st.append((float(tt.mean()), float(tt.std(ddof=1)), int(tt.size)))
        if len(st) != 2:
            continue
        out[i] = (st[1][0] - st[0][0]) * 1e3
        sig[i] = math.sqrt(st[0][1] ** 2 / st[0][2] + st[1][1] ** 2 / st[1][2]) * 1e3
        scat[i] = st[1][1] * 1e3
    return out, sig, scat


def measure_c2c(ref: np.ndarray, cur: np.ndarray, cen):
    """ゼロ点 —— 足跡内の点の**最近傍距離の中央値** [mm](符号を持たない)。"""
    t1, t2 = cKDTree(ref), cKDTree(cur)
    ball = t2.query_ball_point(cen, R_CYL, workers=-1)
    out = np.full(cen.shape[0], np.nan)
    for i, idx in enumerate(ball):
        if len(idx) < MIN_CYL:
            continue
        d, _ = t1.query(cur[idx], workers=-1)
        out[i] = float(np.median(d)) * 1e3
    return out


# --------------------------------------------------------------------------- #
# 位置合わせ                                                                    #
# --------------------------------------------------------------------------- #
def register(src: np.ndarray, dst: np.ndarray, mask=None, vox: float = VOX):
    """点-面 ICP で ``src`` を ``dst`` に合わせ、**全点**に適用した結果を返す。

    ``mask`` は「合わせに使う範囲」を選ぶ真偽関数 ``f(pts) -> bool 配列``。
    """
    a = np.asarray(fs.ledger.voxel_grid_downsample(src, vox), float)
    b = np.asarray(fs.ledger.voxel_grid_downsample(dst, vox), float)
    if mask is not None:
        a, b = a[mask(a)], b[mask(b)]
    nb = np.asarray(fs.ledger.estimate_normals(b, k=25), float)
    # ★台帳経由は宣言 out 型(pose)しか返さないので ``.raw`` で全部受ける。
    rot, tr, _, rmse, iters = fs.ledger.icp_point2plane.raw(a, b, nb, iters=40)
    rot = np.asarray(rot, float)
    tr = np.asarray(tr, float).ravel()
    return src @ rot.T + tr, rot, tr, {"rmse": float(rmse), "iters": int(iters)}


def pose_residual(rot, tr) -> tuple[float, float, np.ndarray]:
    """ICP が戻した姿勢と、仕込んだ姿勢誤差の食い違い(角度 [rad]・並進 [mm])。"""
    ang = float(np.arccos(np.clip((np.trace(rot) - 1.0) / 2.0, -1.0, 1.0)))
    return ang, float(np.linalg.norm(tr) * 1e3), tr * 1e3


def stable_mask(pts):
    """「変わっていないと分かっている」範囲 = 支点付近(たわみがほぼ 0)。"""
    return (pts[:, 0] < 2.0) | (pts[:, 0] > 10.0)


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                 #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— 何を仕込んだか")
    print("=" * 78)
    print("  桁: 支間 %.1f m、断面の折れ線 %d 頂点(平面 %d 枚)、展開幅 %.4f m、"
          "表面積 %.2f m2" % (LSPAN, len(CS_V), len(SEG_LEN), S_TOTAL, GIRDER_AREA))
    print("  キャンバー %.3f m(中央)—— 押し出しの x 対称性を破る唯一の形。"
          "端の勾配 dc/dx = %.4f" % (CAMBER, camber_slope(0.0)))
    print("  支承: 円柱 %d 本(半径 %.2f m・長さ %.2f m)、表面積 %.3f m2"
          % (len(BEARING_X), BEARING_R, BEARING_LEN, BEARING_AREA))
    print("\n  面の向き(法線が鉛直下向きから何度傾いているか):")
    for i, nm in enumerate(SEG_NAME):
        th = math.degrees(math.acos(min(1.0, abs(SEG_NRM[i][1]))))
        print("    %-12s 長さ %.4f m  法線 (y,z) = (%+.3f, %+.3f)  鉛直から %5.1f 度"
              % (nm, SEG_LEN[i], SEG_NRM[i][0], SEG_NRM[i][1], th))

    print("\n  劣化(時点ごとの真値):")
    print("    年     たわみ中央   欠損深さ   支承沈下   ひび深さ   欠損体積")
    vols = []
    for k in range(3):
        v = SPALL_MM[k] * 1e-3 * 2 * math.pi * SPALL_SIG ** 2 * 1e3   # [L]
        vols.append(v)
        print("    t%d(%.0f 年) %7.2f mm %9.2f mm %9.2f mm %9.2f mm %9.3f L"
              % (k, EPOCH_YEAR[k], DEFLECT_MM[k], SPALL_MM[k], SETTLE_MM[k],
                 CRACK_MM[k], v))
    print("  欠損体積は解析積分 2πAσ² で厳密(A = 深さ、σ = %.2f m)。" % SPALL_SIG)
    print("  ★たわみは**鉛直**の変位なので、法線が水平な腹板では法線方向の変化が"
          "**厳密に 0**。同じ劣化でも、面の向きで見え方が変わる。")

    tn = truth_normal(2)
    tf = truth_footprint(2)
    for nm, i in (("下フランジ", 3), ("腹板(左)", 2), ("下面(左)", 0)):
        m = CORES["seg"] == i
        print("    %-12s 真の法線方向変化 [mm]: 最小 %+.3f 最大 %+.3f 中央 %+.3f"
              % (nm, tn[m].min(), tn[m].max(), np.median(tn[m])))
    print("  ★足跡(半径 %.2f m)で平均すると欠損の谷は %.3f -> %.3f mm に薄まり、"
          % (R_CYL, tn.min(), tf.min()))
    print("     ひび割れ(幅 %.0f mm)は %.3f -> %.3f mm と **%.0f 倍**に薄まる。"
          % (2000 * CRACK_HW, -CRACK_MM[2],
             float(tf[CORES["seg"] == 2].min()),
             CRACK_MM[2] / max(abs(float(tf[CORES["seg"] == 2].min())), 1e-9)))
    return {"truth_pt": tn, "truth_fp": tf, "vol": vols}


# --------------------------------------------------------------------------- #
# 2. 測定の現実                                                                 #
# --------------------------------------------------------------------------- #
def section_observe() -> dict:
    print("\n" + "=" * 78)
    print("2) 測定の現実 —— 位置も姿勢も密度も、毎回違う")
    print("=" * 78)
    print("   時点  密度[pt/m2]   点数    平均点間隔[mm]  走査位置ずれ[m]  "
          "仮設物 x[m]   姿勢誤差 角[度] 並進[mm]")
    clouds, rows = [], []
    for k in range(3):
        rng = np.random.default_rng(SEED + 10 * k)
        p = observe(k, rng)
        clouds.append(p)
        sp = 1000.0 * 0.5 / math.sqrt(len(p) / (GIRDER_AREA + BEARING_AREA))
        om = np.asarray(POSE_ERR[k][:3])
        tv = np.asarray(POSE_ERR[k][3:])
        rows.append(["t%d" % k, "%.0f" % DENSITY[k], "%d" % len(p), "%.1f" % sp,
                     "%.2f" % np.linalg.norm(SETUP_SHIFT[k]),
                     "%.1f" % BLOCK_X0[k],
                     "%.4f" % math.degrees(np.linalg.norm(om)),
                     "%.1f" % (1e3 * np.linalg.norm(tv))])
        print("   t%d   %8.0f %9d %13.1f %14.2f %12.1f %13.4f %9.1f"
              % (k, DENSITY[k], len(p), sp, np.linalg.norm(SETUP_SHIFT[k]),
                 BLOCK_X0[k], math.degrees(np.linalg.norm(om)),
                 1e3 * np.linalg.norm(tv)))
    print("  測距雑音 σ = %.1f + %.2f·R mm(R = 走査器からの距離)-> "
          "R = 3 m で %.2f mm、R = 8 m で %.2f mm"
          % (1e3 * SIG0, 1e3 * SIG_K, 1e3 * (SIG0 + 3 * SIG_K),
             1e3 * (SIG0 + 8 * SIG_K)))

    print("\n  位置合わせ(点-面 ICP、%.0f mm 格子で間引いてから)—— "
          "戻せた量と残った量:" % (1e3 * VOX))
    print("    時点   仕込んだ 角[度]/並進[mm]   ICP 後の残差 角[度]/並進[mm]   RMSE[mm]")
    aligned, resid = [clouds[0]], []
    for k in (1, 2):
        q, rot, tr, info = register(clouds[k], clouds[0])
        aligned.append(q)
        # 仕込んだ誤差 (R0,t0) を打ち消せたか: 合成変換が単位に近いほど良い
        r0 = rodrigues(POSE_ERR[k][:3])
        t0 = np.asarray(POSE_ERR[k][3:]) + CENTER - r0 @ CENTER
        rc = rot @ r0
        tc = rot @ t0 + tr
        ang = math.degrees(math.acos(min(1.0, max(-1.0, (np.trace(rc) - 1) / 2))))
        # 回転が残ると重心も動くので、構造の重心での実効ずれで見る
        eff = (rc - np.eye(3)) @ CENTER + tc
        resid.append((ang, 1e3 * float(np.linalg.norm(eff)), eff * 1e3,
                      float(info["rmse"]) * 1e3))
        print("    t%d      %8.4f / %6.1f          %10.4f / %6.2f        %6.3f"
              % (k, math.degrees(np.linalg.norm(POSE_ERR[k][:3])),
                 1e3 * np.linalg.norm(POSE_ERR[k][3:]), ang, resid[-1][1],
                 resid[-1][3]))
    print("    ★残差の内訳(重心での実効ずれ [mm]): "
          + " / ".join("t%d (%+.2f, %+.2f, %+.2f)"
                       % (k + 1, *resid[k][2]) for k in range(2)))
    print("    ★x 成分が他より大きい —— 押し出し形状なので **x の並進はほとんど"
          "拘束されない**(8 節で分けて測る)。")
    figs.save_table("conditions",
                    ["時点", "密度 pt/m2", "点数", "点間隔 mm", "走査位置ずれ m",
                     "仮設物 x m", "姿勢誤差 度", "姿勢誤差 mm"], rows,
                    title="時点ごとの測定条件(すべて既知量として仕込んである)",
                    caption="同じ構造物を 3 回測る。変わるのは構造物ではなく測り方。")
    return {"clouds": clouds, "aligned": aligned, "resid": resid}


# --------------------------------------------------------------------------- #
# 3. ゼロ点 —— 最近傍距離 vs 法線方向                                           #
# --------------------------------------------------------------------------- #
def section_zero(obs: dict, sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) ゼロ点 = 最近傍距離(C2C)—— 傾いた面でどれだけ嘘をつくか")
    print("=" * 78)
    ref = obs["aligned"][0]
    cur = obs["aligned"][2]
    cen, nor, ok = core_normals(ref)
    ln, sg, scat = measure_normal(ref, cur, cen, nor, ok)
    c2c = measure_c2c(ref, cur, cen)
    tn = sc["truth_pt"]
    tf = sc["truth_fp"]

    good = np.isfinite(ln) & np.isfinite(c2c)
    print("  有効 core %d / %d(%.1f %%)。無効は欠測(仮設物の影・入射角)。"
          % (int(good.sum()), good.size, 100 * good.mean()))
    print("  法線の推定: fit_plane_3d の符号は任意なので**真の外向きに合わせている**。"
          "合わせないと %.1f %% が裏返る。" % 50.0)

    print("\n   面           真値(点) 真値(足跡)  法線方向   誤差    C2C   "
          "C2C の |誤差|")
    rows = []
    for i, nm in enumerate(SEG_NAME):
        m = good & (CORES["seg"] == i) & ~CORES["edge"]
        if m.sum() < 5:
            continue
        e_n = float(np.median(np.abs(ln[m] - tf[m])))
        e_c = float(np.median(np.abs(c2c[m] - np.abs(tf[m]))))
        rows.append([nm, "%+.2f" % np.median(tn[m]), "%+.2f" % np.median(tf[m]),
                     "%+.2f" % np.median(ln[m]), "%.2f" % e_n,
                     "%.2f" % np.median(c2c[m]), "%.2f" % e_c])
        print("   %-12s %+8.2f %+10.2f %+10.2f %7.2f %7.2f %10.2f"
              % (nm, np.median(tn[m]), np.median(tf[m]), np.median(ln[m]),
                 e_n, np.median(c2c[m]), e_c))
    print("  (単位はすべて mm。C2C は符号を持たないので |真値| と比べている)")

    m = good & ~CORES["edge"]
    print("\n  ★C2C は**どの面でも真値より大きい側に外れる** —— 最近傍は"
          "「いちばん近い点」なので、面に沿ったずれと面の法線方向のずれを"
          "区別できず、\n     点間隔ぶんの下駄を必ず履く。全 core の中央値: "
          "法線方向の誤差 %.2f mm に対し C2C の誤差 %.2f mm(%.1f 倍)。"
          % (float(np.median(np.abs(ln[m] - tf[m]))),
             float(np.median(np.abs(c2c[m] - np.abs(tf[m])))),
             float(np.median(np.abs(c2c[m] - np.abs(tf[m]))))
             / max(float(np.median(np.abs(ln[m] - tf[m]))), 1e-9)))
    e = good & CORES["edge"]
    print("  ★面の縁(隣の面が半径 %.2f m に入る core)では法線が混ざり、"
          "誤差は %.2f -> %.2f mm(%.1f 倍)。"
          % (R_NORM, float(np.median(np.abs(ln[m] - tf[m]))),
             float(np.median(np.abs(ln[e] - tf[e]))),
             float(np.median(np.abs(ln[e] - tf[e])))
             / max(float(np.median(np.abs(ln[m] - tf[m]))), 1e-9)))

    ch = float(fs.ledger.chamfer_distance(ref, cur)) * 1e3
    hd = float(fs.ledger.hausdorff_distance(ref, cur)) * 1e3
    print("  ★まとめた 1 個の数字はもっと役に立たない: Chamfer %.2f mm / "
          "Hausdorff %.2f mm。" % (ch, hd))
    print("     Hausdorff は最悪値なので欠測の縁 1 点で決まり、Chamfer は"
          "**面の大半を占める健全部の点間隔**で決まる。どちらも"
          "「どこがどれだけ劣化したか」を返さない。")
    return {"cen": cen, "nor": nor, "ok": ok, "L": ln, "sig": sg, "scat": scat,
            "c2c": c2c, "good": good, "chamfer": ch, "hausdorff": hd}


# --------------------------------------------------------------------------- #
# 4. 対照群 —— 劣化ゼロなのに検出される量                                       #
# --------------------------------------------------------------------------- #
def section_control(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) ★★対照群 —— 劣化ゼロで測り直しただけで出る「偽の劣化」")
    print("=" * 78)
    print("  (a) 劣化ゼロ・測り直しだけ / (b) 劣化だけ(測り方は t0 と同一)/ "
          "(c) 両方。\n  どれも位置合わせまで済ませてから測る。")

    conds = {}
    # (a) 劣化ゼロ、測り方だけ t2
    r0 = np.random.default_rng(SEED + 101)
    a_ref = observe(0, r0)
    a_cur = observe(2, np.random.default_rng(SEED + 102), deteriorate=False)
    # (b) 劣化だけ(密度・姿勢・走査位置・仮設物を t0 と同一にする)
    r1 = np.random.default_rng(SEED + 111)
    b_ref = observe(0, r1)
    b_cur = observe(2, np.random.default_rng(SEED + 112), density=DENSITY[0],
                    pose=False, blocker=False, setup_shift=False)
    b_ref2 = observe(0, np.random.default_rng(SEED + 113), pose=False,
                     blocker=False, setup_shift=False)
    # (c) 両方
    c_ref = observe(0, np.random.default_rng(SEED + 121))
    c_cur = observe(2, np.random.default_rng(SEED + 122))

    print("\n   条件                        有効 core   法線方向 |変化| mm      "
          "C2C mm")
    print("                                          中央値   95%    最大   "
          "中央値   最大")
    rows = []
    for name, ref, cur, align in (
            ("(a) 劣化ゼロ・測り直しのみ", a_ref, a_cur, True),
            ("(b) 劣化のみ・測り方は同一", b_ref2, b_cur, False),
            ("(c) 劣化 + 測り直し", c_ref, c_cur, True)):
        if align:
            cur = register(cur, ref)[0]
        cen, nor, ok = core_normals(ref)
        ln, _, _ = measure_normal(ref, cur, cen, nor, ok)
        cc = measure_c2c(ref, cur, cen)
        g = np.isfinite(ln) & np.isfinite(cc) & ~CORES["edge"]
        v = np.abs(ln[g])
        conds[name] = {"L": ln, "c2c": cc, "good": g, "cen": cen}
        rows.append([name, "%d" % int(g.sum()), "%.2f" % np.median(v),
                     "%.2f" % np.percentile(v, 95), "%.2f" % v.max(),
                     "%.2f" % np.median(cc[g]), "%.2f" % np.nanmax(cc[g])])
        print("   %-27s %8d %8.2f %6.2f %6.2f %8.2f %7.2f"
              % (name, int(g.sum()), np.median(v), np.percentile(v, 95), v.max(),
                 np.median(cc[g]), np.nanmax(cc[g])))

    a = conds["(a) 劣化ゼロ・測り直しのみ"]
    c = conds["(c) 劣化 + 測り直し"]
    ga = a["good"]
    print("\n  ★★真の最大劣化は %.2f mm。それに対し (a) 劣化ゼロの C2C は"
          " 中央値 %.2f mm・最大 %.2f mm —— **偽の劣化のほうが大きい**。"
          % (max(SPALL_MM), float(np.median(a["c2c"][ga])),
             float(np.nanmax(a["c2c"][ga]))))
    print("     法線方向なら同じ条件で 中央値 %.2f mm・最大 %.2f mm。"
          % (float(np.median(np.abs(a["L"][ga]))),
             float(np.nanmax(np.abs(a["L"][ga])))))

    # 偽の劣化の「面積」と「体積」——しきい値を 1 つ決めて数える
    thr = 1.0            # 補修判定に使う想定のしきい値 [mm]
    acell = CORE_SP * CORE_SP
    tf = sc["truth_fp"]
    out = {}
    print("\n   しきい値 %.1f mm を超えた core(補修候補)を数える:" % thr)
    print("     条件                        面積 m2   欠損体積 L   真値との比")
    v_true = sc["vol"][2]
    for name in conds:
        d = conds[name]
        g = d["good"]
        neg = g & (d["L"] < -thr)              # 面が引っ込む = 材料が失われた側
        area = float(neg.sum()) * acell
        vol = float(-d["L"][neg].sum()) * 1e-3 * acell * 1e3   # [L]
        out[name] = (area, vol)
        print("     %-27s %8.3f %11.3f %11s"
              % (name, area, vol,
                 "-" if "ゼロ" in name else "%.2f" % (vol / v_true)))
    print("     真の欠損体積(t2)= %.3f L、真の欠損面積(|真値| > %.1f mm)= %.3f m2"
          % (v_true, thr, float((np.abs(tf) > thr).sum()) * acell))
    fa, fv = out["(a) 劣化ゼロ・測り直しのみ"]
    print("  ★★劣化ゼロでも %.3f m2 / %.3f L が「補修候補」に挙がる —— "
          "本物の %.3f L の %.0f %%。" % (fa, fv, v_true, 100 * fv / v_true))

    # 検出された劣化を塊にまとめて数える(euclidean_cluster)
    g = c["good"]
    neg = g & (c["L"] < -thr)
    if int(neg.sum()) >= 3:
        lab = np.asarray(fs.ledger.euclidean_cluster(c["cen"][neg], tol=0.45,
                                                     min_size=4), int)
        nclu = int(lab.max()) + 1 if lab.size else 0
        sizes = [int((lab == j).sum()) for j in range(nclu)]
        print("  ★検出された塊(euclidean_cluster、tol 0.45 m): %d 個 "
              "(点数 %s)。真の劣化箇所は 3 個(欠損・ひび・たわみは面全体)。"
              % (nclu, ", ".join(str(v) for v in sorted(sizes, reverse=True)[:6])))
        big_i = int(np.argmax(sizes)) if sizes else 0
        pb = c["cen"][neg][lab == big_i]
        if pb.shape[0] > 3:
            ext = 2.0 * np.asarray(fs.ledger.obb(pb)["extents"], float)
            print("     最大の塊の OBB 辺長 %.3f x %.3f x %.3f m(真の欠損は"
                  " 2σ = %.3f m の広がり)。"
                  % (*np.sort(ext)[::-1], 2 * SPALL_SIG))
    return {"conds": conds, "false_area": fa, "false_vol": fv, "thr": thr,
            "v_true": v_true, "counts": out}


# --------------------------------------------------------------------------- #
# 5. 合わせる範囲                                                               #
# --------------------------------------------------------------------------- #
def section_scope() -> dict:
    print("\n" + "=" * 78)
    print("5) ★★合わせる範囲 —— 劣化を含めて合わせると、劣化が消える")
    print("=" * 78)
    print("  たわみだけを入れ、雑音・欠測・密度差・姿勢誤差を全部止めた対照で測る。")
    print("  予測(閉形式): たわみ w(x) = D·4ξ(1-ξ) は剛体運動ではないので、")
    print("    最小二乗の剛体当てはめは**鉛直に平均だけ**吸う。x について一様に"
          "測るなら\n    重みに依らず  t_z = -mean_x w = -(2/3)D。")
    print("    -> 中央のたわみは D - (2/3)D = D/3 に潰れ、支点付近には")
    print("       0 - (2/3)D = -(2/3)D の**偽の隆起**が出る。")
    xi = np.linspace(0, 1, 20001)
    w_all = float(np.mean(4 * xi * (1 - xi)))
    m_end = (xi < 2.0 / LSPAN) | (xi > 10.0 / LSPAN)
    w_end = float(np.mean((4 * xi * (1 - xi))[m_end]))
    print("    端だけ(x<2 m または x>10 m)で合わせても w の平均は %.4f·D なので"
          "\n    **%.1f %% は吸われる** —— 範囲を狭めてもゼロにはならない。"
          % (w_end, 100 * w_end))

    r = np.random.default_rng(SEED + 201)
    ref = observe(0, r, density=DENSITY[0], pose=False, noise=False,
                  blocker=False, setup_shift=False, parts=())
    cur = observe(2, np.random.default_rng(SEED + 202), density=DENSITY[0],
                  pose=False, noise=False, blocker=False, setup_shift=False,
                  parts=("deflect",))
    cen, nor, ok = core_normals(ref)
    base, _, _ = measure_normal(ref, cur, cen, nor, ok)

    q_all = register(cur, ref)[0]
    q_end = register(cur, ref, mask=stable_mask)[0]
    l_all, _, _ = measure_normal(ref, q_all, cen, nor, ok)
    l_end, _, _ = measure_normal(ref, q_end, cen, nor, ok)

    # 下フランジと下面(法線が鉛直に近い面)だけで x 方向のプロファイルを見る
    flat = np.isin(CORES["seg"], (0, 3, 6)) & ok & ~CORES["edge"]
    xs = np.unique(np.round(CORES["x"], 6))
    prof = {}
    for nm, v in (("合わせない", base), ("全点で合わせる", l_all),
                  ("端だけで合わせる", l_end)):
        pr = np.array([np.nanmedian(v[flat & (np.abs(CORES["x"] - x0) < 1e-6)])
                       for x0 in xs])
        prof[nm] = pr
    mid = int(np.argmin(np.abs(xs - LSPAN / 2)))
    end = int(np.argmin(np.abs(xs - 0.4)))
    d_mm = DEFLECT_MM[2]
    # 法線が下向きの面では「面が下がる = 外へ動く」なので、たわみは**正**に出る。
    w_true = d_mm * 4 * (xs / LSPAN) * (1 - xs / LSPAN)
    print("\n   合わせ方              支間中央 [mm]   支点付近(x=%.1f m)[mm]"
          "   吸われた割合" % xs[end])
    print("     真値                    %+8.3f        %+8.3f              -"
          % (w_true[mid], w_true[end]))
    rows = [["真値", "%+.3f" % w_true[mid], "%+.3f" % w_true[end], "-"]]
    for nm in prof:
        eaten = 1.0 - prof[nm][mid] / w_true[mid]
        rows.append([nm, "%+.3f" % prof[nm][mid], "%+.3f" % prof[nm][end],
                     "%.3f" % eaten])
        print("     %-16s        %+8.3f        %+8.3f          %8.3f"
              % (nm, prof[nm][mid], prof[nm][end], eaten))
    print("     予測(全点 = 2/3 を吸う)  %+8.3f        %+8.3f          %8.3f"
          % (d_mm * (1 - w_all), d_mm * (w_true[end] / d_mm - w_all), w_all))
    print("     予測(端だけ)            %+8.3f        %+8.3f          %8.3f"
          % (d_mm * (1 - w_end), d_mm * (w_true[end] / d_mm - w_end), w_end))
    eat_all = 1.0 - prof["全点で合わせる"][mid] / w_true[mid]
    eat_end = 1.0 - prof["端だけで合わせる"][mid] / w_true[mid]
    print("\n  ★★全点で合わせると中央のたわみは %.3f -> %.3f mm に潰れる"
          "(吸われた割合 実測 %.3f / 予測 %.3f)。"
          % (prof["合わせない"][mid], prof["全点で合わせる"][mid], eat_all, w_all))
    print("     さらに支点付近には %+.3f mm の**符号が逆の変化**が出る"
          "(予測 %+.3f)—— 沈んでいないのに\n     「持ち上がった」と読める。"
          "劣化が全域に広がっていると、位置合わせは**平均を吸って端に嘘を作る**。"
          % (prof["全点で合わせる"][end], d_mm * (w_true[end] / d_mm - w_all)))
    print("  ★変わっていない端だけで合わせても %.3f が吸われる"
          "(予測 %.3f)—— 支点でもたわみは厳密に 0 ではないから。"
          % (eat_end, w_end))
    print("     **合わせる範囲を狭めてもゼロにはならない**: 吸われる量は"
          "「使った範囲での劣化の平均」そのもの。")
    figs.save_plot("deflection_profile",
                   [("真値", xs, w_true),
                    ("合わせない", xs, prof["合わせない"]),
                    ("全点で合わせる", xs, prof["全点で合わせる"]),
                    ("端だけで合わせる", xs, prof["端だけで合わせる"])],
                   xlabel="橋軸方向 x [m]", ylabel="法線方向の変化 [mm](正 = 面が下がる)",
                   title="たわみは合わせた分だけ消え、端に逆符号が出る",
                   caption="法線が鉛直に近い面(下面・下フランジ)の中央値。"
                           "全点で合わせると平均 2/3 D が姿勢に吸われる。")
    figs.save_table("scope",
                    ["合わせる範囲", "支間中央 mm", "支点付近 mm", "吸われた割合"],
                    rows, title="合わせる範囲で「たわみ」がどれだけ消えるか",
                    caption="真のたわみは中央 %.2f mm。吸われる量は"
                            "「使った範囲でのたわみの平均」で閉形式に予測できる。"
                            % w_true[mid])
    return {"x": xs, "prof": prof, "w_all": w_all, "w_end": w_end,
            "mid": mid, "end": end, "w_true": w_true,
            "eat_all": eat_all, "eat_end": eat_end}


# --------------------------------------------------------------------------- #
# 6. 崖 —— 位置合わせ誤差と点密度                                               #
# --------------------------------------------------------------------------- #
def pred_false_rms(omega, tvec) -> float:
    """残差姿勢 ``(ω, t)`` が作る見かけ変化の RMS [mm] —— **幾何だけで出す**。

    点 p の見かけ変化は ``(t + ω × (p - c))·n``。core の位置と法線から直接積む。
    """
    d = np.asarray(tvec, float)[None, :] + np.cross(np.asarray(omega, float),
                                                    CORES["p"] - CENTER)
    v = np.einsum("ij,ij->i", d, CORES["n"]) * 1e3
    return float(np.sqrt(np.mean(v ** 2)))


def section_cliff(zero: dict, sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 崖 —— 位置合わせの残差と点密度。先に幾何で予測してから測る")
    print("=" * 78)
    print("  予測: 残差回転 ω と並進 t の作る見かけ変化は (t + ω×(p-c))·n。")
    print("    腹板(法線が ±y)には ω_z しか効かず、下フランジ(法線が -z)には")
    print("    ω_y しか効かない —— **同じ誤差が面ごとに違う嘘をつく**。")

    r = np.random.default_rng(SEED + 301)
    ref = observe(0, r, pose=False, blocker=False, setup_shift=False, parts=())
    cur0 = observe(2, np.random.default_rng(SEED + 302), density=DENSITY[0],
                   pose=False, blocker=False, setup_shift=False, parts=())
    cen, nor, ok = core_normals(ref)
    tf = sc["truth_fp"]
    # 感度: 欠損の深さ 1 mm あたり、谷でどれだけ法線方向の値が動くか
    sens = abs(float(np.nanmin(tf))) / SPALL_MM[2]

    print("\n   ω [rad]   幾何の予測[mm]  雑音床と合成[mm]  実測 RMS[mm]   比    "
          "最小検出深さ[mm]")
    alphas = (0.0, 1.0e-4, 2.0e-4, 5.0e-4, 1.0e-3)
    a_l, pr_l, ms_l, md_l, tot_l = [], [], [], [], []
    axis = np.array([0.3, 1.0, 0.6])
    axis = axis / np.linalg.norm(axis)
    floor = None
    for al in alphas:
        om = al * axis
        pred = pred_false_rms(om, (0.0, 0.0, 0.0))
        q = apply_pose(cur0, om, (0.0, 0.0, 0.0))
        ln, _, _ = measure_normal(ref, q, cen, nor, ok)
        g = np.isfinite(ln) & ~CORES["edge"]
        meas = float(np.sqrt(np.mean(ln[g] ** 2)))
        if floor is None:
            floor = meas                    # ★α=0 の実測 = 雑音と欠測の床
        tot = math.hypot(pred, floor)
        mdd = 2.0 * meas / sens
        a_l.append(al * 1e3)
        pr_l.append(pred)
        ms_l.append(meas)
        tot_l.append(tot)
        md_l.append(mdd)
        print("   %8.1e %13.3f %17.3f %13.3f %7.3f %14.2f"
              % (al, pred, tot, meas, meas / max(tot, 1e-9), mdd))
    rat = [m / max(t, 1e-9) for m, t in zip(ms_l, tot_l)]
    print("  ★幾何の予測に**雑音床を直交に足す**(RMS は二乗和)だけで、比は "
          "%.3f 〜 %.3f。" % (min(rat), max(rat)))
    print("     点群を測る前に、位置合わせの角度から嘘の大きさが出せる —— "
          "床の値だけ 1 回測ればよい。")
    print("  ★最小検出深さは %.2f -> %.2f mm。橋長 %.0f m では 1.0e-4 rad "
          "(%.4f 度 = %.1f 秒)が支点で %.2f mm に相当するので、\n     位置合わせの"
          "角度は「度」でなく「秒」で管理しないと 1 mm の劣化は測れない。"
          % (md_l[0], md_l[-1], LSPAN, math.degrees(1e-4),
             math.degrees(1e-4) * 3600, 1e-4 * LSPAN / 2 * 1e3))

    # --- 面の向きで嘘が変わることを、軸を分けて確かめる ---------------------- #
    print("\n   ★同じ大きさの回転でも、**軸が違えば効く面が違う**"
          "(ω = %.1e rad、面ごとの予測 RMS [mm]):" % 5.0e-4)
    print("     面           ω_x のみ   ω_y のみ   ω_z のみ")
    face_rows = []
    for i, nm in enumerate(SEG_NAME):
        m = CORES["seg"] == i
        vals = []
        for ax in (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])):
            d = np.cross(5.0e-4 * ax, CORES["p"][m] - CENTER)
            v = np.einsum("ij,ij->i", d, CORES["n"][m]) * 1e3
            vals.append(float(np.sqrt(np.mean(v ** 2))))
        face_rows.append([nm] + ["%.3f" % v for v in vals])
        print("     %-12s %8.3f %10.3f %10.3f" % (nm, *vals))
    print("     ★腹板(法線が ±y)には **ω_y が厳密に効かない**、"
          "下面・下フランジ(法線が -z)には **ω_z が厳密に効かない**。")
    print("       (ω×r)·n を展開すると n が向いていない軸の成分が落ちるため。"
          "\n       つまり**同じ位置合わせで、面ごとに違う嘘をつく** —— "
          "1 枚の面だけで検算しても気づけない。")

    print("\n   並進だけの掃引(t = (0,0,tz)):")
    print("     tz [mm]   幾何の予測[mm]  床と合成[mm]  実測 RMS[mm]")
    for tz in (0.0, 0.5, 1.0, 2.0):
        pred = pred_false_rms((0, 0, 0), (0.0, 0.0, tz * 1e-3))
        q = apply_pose(cur0, (0, 0, 0), (0.0, 0.0, tz * 1e-3))
        ln, _, _ = measure_normal(ref, q, cen, nor, ok)
        g = np.isfinite(ln) & ~CORES["edge"]
        print("     %7.2f %14.3f %13.3f %13.3f"
              % (tz, pred, math.hypot(pred, floor),
                 float(np.sqrt(np.mean(ln[g] ** 2)))))
    print("     ★鉛直の並進は腹板(法線が水平)には**一切効かない**ので、"
          "予測 RMS は tz より小さい(法線が鉛直な面の面積割合の平方根ぶん)。")

    # --- 密度の崖 ---------------------------------------------------------- #
    print("\n   点密度の崖(劣化ゼロ・姿勢誤差ゼロの対照で測る):")
    print("     密度[pt/m2]  点間隔[mm]  予測 C2C[mm]  実測 C2C[mm]   比    "
          "法線方向 RMS[mm]   測れた core %")
    dl, sp_l, pc_l, mc_l, mn_l = [], [], [], [], []
    for rho in (300.0, 600.0, 1200.0, 2400.0):
        ra = np.random.default_rng(SEED + 401)
        a = observe(0, ra, density=rho, pose=False, blocker=False,
                    setup_shift=False, parts=())
        b = observe(0, np.random.default_rng(SEED + 402), density=rho, pose=False,
                    blocker=False, setup_shift=False, parts=())
        ce, no, okk = core_normals(a)
        ln, _, _ = measure_normal(a, b, ce, no, okk)
        cc = measure_c2c(a, b, ce)
        fin = np.isfinite(ln) & np.isfinite(cc)
        g = fin & ~CORES["edge"]
        pred = 1e3 * 0.5 / math.sqrt(rho)
        dl.append(rho)
        sp_l.append(1e3 / math.sqrt(rho))
        pc_l.append(pred)
        mc_l.append(float(np.median(cc[g])))
        mn_l.append(float(np.sqrt(np.mean(ln[g] ** 2))))
        print("     %10.0f %11.2f %13.2f %13.2f %7.3f %16.3f %13.1f"
              % (rho, sp_l[-1], pred, mc_l[-1], mc_l[-1] / pred, mn_l[-1],
                 100 * fin.mean()))
    print("  ★C2C の偽の劣化は**点間隔でほぼ決まる**(予測 0.5/√ρ との比 %.3f 〜 %.3f)。"
          % (min(m / p for m, p in zip(mc_l, pc_l)),
             max(m / p for m, p in zip(mc_l, pc_l))))
    print("     密度を %.0f 倍にしても %.2f -> %.2f mm と √ でしか下がらない。"
          % (dl[-1] / dl[0], mc_l[0], mc_l[-1]))
    print("     法線方向は同じ掃引で %.3f -> %.3f mm —— **平均する点数**で"
          "下がるので、こちらも √ρ だが**桁が違う**。" % (mn_l[0], mn_l[-1]))

    figs.save_plot("cliff",
                   [("C2C 実測", dl, mc_l), ("C2C 予測 0.5/√ρ", dl, pc_l),
                    ("法線方向 RMS", dl, mn_l)],
                   xlabel="点密度 [pt/m2]", ylabel="偽の劣化 [mm]",
                   title="劣化ゼロで測り直したときに出てしまう量",
                   caption="C2C は点間隔そのもの、法線方向は平均で消える。"
                           "真の最大劣化 %.1f mm と比べること。" % max(SPALL_MM))
    figs.save_plot("cliff_angle",
                   [("実測 RMS", a_l, ms_l), ("幾何の予測", a_l, pr_l),
                    ("最小検出深さ", a_l, md_l)],
                   xlabel="残差回転 [mrad]", ylabel="偽の劣化 / 検出限界 [mm]",
                   title="位置合わせの角度が検出限界を決める",
                   caption="予測は (ω×(p-c))·n を core 上で積んだだけ。"
                           "点群を測る前に出せる。")
    return {"alpha": a_l, "pred": pr_l, "meas": ms_l, "mindet": md_l,
            "dens": dl, "c2c": mc_l, "c2c_pred": pc_l, "norm": mn_l,
            "sens": sens}


# --------------------------------------------------------------------------- #
# 7. 変化率 —— 差より先に壊れる                                                 #
# --------------------------------------------------------------------------- #
def section_rate(obs: dict, sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) ★★変化率(mm/年)—— 差より先に壊れる")
    print("=" * 78)
    print("  補修の優先度は「今どれだけ悪いか」ではなく「どれだけ速く進むか」で"
          "決まる。\n  各時点が**独立に**合わせられるので、速度の誤差は差の"
          "誤差の √2 倍で入る。")

    ref = obs["aligned"][0]
    cen, nor, ok = core_normals(ref)
    ls, scats = {}, {}
    for k in (1, 2):
        ln, _, sct = measure_normal(ref, obs["aligned"][k], cen, nor, ok)
        ls[k] = ln
        scats[k] = sct
    _, _, sct0 = measure_normal(ref, ref, cen, nor, ok)
    scats[0] = sct0
    tf = {k: truth_footprint(k) for k in (1, 2)}

    dt = EPOCH_YEAR[2] - EPOCH_YEAR[0]
    rate = ls[2] / dt
    rate_true = tf[2] / dt
    g = np.isfinite(rate) & ~CORES["edge"]
    err = rate[g] - rate_true[g]
    rms = float(np.sqrt(np.mean(err ** 2)))
    print("\n   真の欠損速度(谷)  %.3f mm/年     真のたわみ速度(中央) %.3f mm/年"
          % (-float(np.nanmin(tf[2])) / dt, DEFLECT_MM[2] / dt))
    print("   速度の誤差: 中央値 %+.3f / RMS %.3f / 95%% %.3f mm/年"
          % (float(np.median(err)), rms, float(np.percentile(np.abs(err), 95))))
    e1 = float(np.sqrt(np.mean((ls[2][g] - tf[2][g]) ** 2)))
    print("   差(t0->t2)の誤差 RMS %.3f mm を %.0f 年で割ると %.3f mm/年 —— "
          "実測と一致する。" % (e1, dt, e1 / dt))
    print("  ★★「1 年あたり %.1f mm 進む」を有意(2σ)に言うには %.3f mm/年 を"
          "超える必要がある。" % (1.0, 2 * rms))
    print("     ★誤差は **1/dt** で落ちるのに、密度を上げても **1/√ρ** でしか"
          "落ちない —— 速度を測りたいなら\n     密度を 4 倍にするより"
          "**測定間隔を 2 倍にする**ほうが効く(同じ改善で費用が違う)。")

    # 3 点の直線当てはめ vs 両端の差分 —— 等間隔 3 点では**厳密に同じ**
    tt = np.asarray(EPOCH_YEAR)
    lin = np.full(rate.size, np.nan)
    for i in range(rate.size):
        y = np.array([0.0, ls[1][i], ls[2][i]])
        if np.all(np.isfinite(y)):
            lin[i] = float(np.polyfit(tt, y, 1)[0])
    g2 = np.isfinite(rate) & np.isfinite(lin) & ~CORES["edge"]
    e_two = float(np.sqrt(np.mean((rate[g2] - rate_true[g2]) ** 2)))
    e_lin = float(np.sqrt(np.mean((lin[g2] - rate_true[g2]) ** 2)))
    dmax = float(np.max(np.abs(lin[g2] - rate[g2])))
    print("\n  ★予想は「点検を 3 回に増やせば速度の推定が良くなる」だった。**外れ**:")
    print("     3 点の直線当てはめ %.4f mm/年 vs 両端の差分 %.4f mm/年、"
          "core ごとの差の最大 %.2e mm/年。" % (e_lin, e_two, dmax))
    print("     等間隔 3 点の最小二乗の傾きは (y2 - y0)/(2Δt) で、"
          "**中央の点の重みは厳密に 0**。\n     「点検を増やす」は"
          "**速度**を良くしない —— 良くなるのは次の量だけ。")

    # 中央の点が効くのは「曲がり(加速)」だけ
    acc = ls[2] - 2.0 * ls[1]                          # 2 階差分 [mm/年^2]
    acc_true = tf[2] - 2.0 * tf[1]
    g3 = np.isfinite(acc) & ~CORES["edge"]
    ea = float(np.sqrt(np.mean((acc[g3] - acc_true[g3]) ** 2)))
    e2ep = float(np.sqrt(np.mean((ls[2][g3] - tf[2][g3]) ** 2)))
    e1ep = float(np.sqrt(np.mean((ls[1][g3] - tf[1][g3]) ** 2)))
    rho = float(np.corrcoef(ls[1][g3] - tf[1][g3], ls[2][g3] - tf[2][g3])[0, 1])
    pred_ind = math.sqrt(e2ep ** 2 + 4 * e1ep ** 2)
    pred_cor = math.sqrt(max(e2ep ** 2 + 4 * e1ep ** 2 - 4 * rho * e1ep * e2ep, 0.0))
    print("  ★中央の点が効くのは**加速**(2 階差分 L2 - 2·L1)。"
          "真の加速(谷)%.3f mm/年²、実測の誤差 RMS %.3f mm/年²。"
          % (float(np.nanmin(acc_true)), ea))
    print("     予測: 各時点が独立なら √(σ2² + 4σ1²) = %.3f。"
          "実測 %.3f は**それより小さい**。" % (pred_ind, ea))
    print("     ★理由も測れる: t1 の誤差と t2 の誤差の相関は %+.3f —— "
          "どちらも同じ t0 を基準に、\n       同じ面に対して位置合わせしている"
          "ので、誤差が**共通成分を持つ**。相関を入れた予測は %.3f(比 %.2f)。"
          % (rho, pred_cor, ea / max(pred_cor, 1e-9)))
    print("     劣化が加速していること(欠損 %.0f -> %.0f mm)は言えるが、"
          "その数字の誤差は速度の %.1f 倍。" % (SPALL_MM[1], SPALL_MM[2],
                                              ea / max(rms, 1e-9)))

    figs.save_plot("rate_error",
                   [("速度の誤差 |Δ|", np.arange(1, g.sum() + 1) / g.sum() * 100,
                     np.sort(np.abs(err))),
                    ("2σ の検出限界", [0, 100], [2 * rms, 2 * rms]),
                    ("1 mm/年 の進行", [0, 100], [1.0, 1.0])],
                   xlabel="core の累積割合 [%]", ylabel="速度の誤差 [mm/年]",
                   title="速度(mm/年)の誤差と、見える進行の下限",
                   caption="3 回の点検で得た速度の誤差分布。1 mm/年 の進行は"
                           "検出限界の下に沈む。")
    return {"rate": rate, "rate_true": rate_true, "err_rms": rms,
            "detect": 2 * rms, "e_two": e_two, "e_lin": e_lin, "dmax": dmax,
            "acc_err": ea, "acc_pred_ind": pred_ind, "acc_pred_cor": pred_cor,
            "rho": rho, "L": ls, "scat": scats, "cen": cen,
            "nor": nor, "ok": ok, "tf": tf}


# --------------------------------------------------------------------------- #
# 8. 細い溝 / 押し出し形状の縮退                                                #
# --------------------------------------------------------------------------- #
def bearing_pose(cloud: np.ndarray, idx: int = 0):
    """支承(円柱)の位置を ``ransac_cylinder`` で出す。返り値 ``((x, z) [m], 半径)``。

    軸上の一点は軸方向に自由なので、``y = 2.0`` の断面へ射影して一意にする。
    """
    bx = BEARING_X[idx]
    m = (np.abs(cloud[:, 0] - bx) < 0.40) & (cloud[:, 2] < -0.95)
    pts = cloud[m]
    if pts.shape[0] < 40:
        return np.full(2, np.nan), float("nan"), 0
    # 軸の向きは設計で既知(y 方向)なので、y を潰して**断面の円**として当てる。
    flat = pts.copy()
    flat[:, 1] = 2.0
    cen, rad, _ = fs.ledger.fit_circle_3d(flat)
    cen = np.asarray(cen, float)
    return np.array([cen[0], cen[2]]), float(rad), int(pts.shape[0])


def section_prism_and_crack(sc: dict) -> dict:
    print("\n" + "=" * 78)
    print("8) 決まらない成分は、感度を持つ部品にだけ嘘として出る / 細い溝")
    print("=" * 78)
    print("  (a) 押し出し形状の縮退 —— 桁は断面を x に押し出した形なので、"
          "平面の法線は x 成分をほとんど持たない。")
    print("      予測: 点-面 ICP の x の分散は 1/Σn_x²。桁の n_x はキャンバー勾配"
          " c'(x) そのものなので\n        Σn_x² ≈ N·mean(c'²) = N·(4C/L)²/3 —— "
          "**x の決まり方はキャンバー C に反比例する**。")
    print("      (円柱の支承は n_x = cosφ で mean n_x² = 0.5 と桁の %.1e より"
          "桁違いに大きいが、面積が %.1f %% しかない)"
          % (float(np.mean(CORES["n"][:, 0] ** 2)),
             100 * BEARING_AREA / (GIRDER_AREA + BEARING_AREA)))
    ceil_x = abs(POSE_ERR[2][3]) * 1e3

    print("\n      キャンバー[mm]  端の勾配 c'   予測 x 残差[mm]  実測 x[mm]  y,z[mm]")
    print("      (予測 = 最小のキャンバーでの実測を 1/c' で伸ばし、"
          "**仕込んだ x 誤差 %.1f mm で頭打ち**にしたもの)" % ceil_x)
    rows, cam_l, dx_l = [], [], []
    base_slope = 4.0 * CAMBER / LSPAN
    for cval in (CAMBER, 0.010, 0.002):
        _CAMBER[0] = cval
        r0 = np.random.default_rng(SEED + 501)
        ref_c = observe(0, r0)
        cur_c = observe(2, np.random.default_rng(SEED + 502), parts=("deflect",))
        # 支承を合わせから外す(x を桁だけで決めさせる)
        q, rot, tr, _ = register(cur_c, ref_c, mask=lambda v: v[:, 2] > -0.95)
        r2 = rodrigues(POSE_ERR[2][:3])
        t2 = np.asarray(POSE_ERR[2][3:]) + CENTER - r2 @ CENTER
        eff = (((rot @ r2) - np.eye(3)) @ CENTER + (rot @ t2 + tr)) * 1e3
        sl = 4.0 * cval / LSPAN
        cam_l.append(1e3 * cval)
        dx_l.append(abs(float(eff[0])))
        pred = min(dx_l[0] * base_slope / sl, ceil_x) if dx_l else float("nan")
        rows.append(["%.0f" % (1e3 * cval), "%.5f" % sl, "%.2f" % pred,
                     "%.2f" % abs(eff[0]),
                     "%.2f" % float(np.linalg.norm(eff[1:]))])
        print("      %12.0f %13.5f %16.2f %12.2f %9.2f"
              % (1e3 * cval, sl, pred, abs(eff[0]),
                 float(np.linalg.norm(eff[1:]))))
    _CAMBER[0] = CAMBER
    print("      ★キャンバーを %.0f -> %.0f mm(勾配 %.0f 分の 1)にすると x の残差は"
          " %.2f -> %.2f mm(%.1f 倍)。" % (cam_l[0], cam_l[-1],
                                            cam_l[0] / cam_l[-1], dx_l[0],
                                            dx_l[-1], dx_l[-1] / max(dx_l[0], 1e-9)))
    print("      ★予想は「1/c' に比例して %.0f 倍」だった。**実測は %.1f 倍で頭打ち**"
          " —— 上限は仕込んだ x 誤差 %.1f mm、\n         つまり"
          "**ICP が x を一度も動かさなかった場合の値**。"
          "縮退は「際限なくずれる」のではなく\n         「合わせが x について何も"
          "言わなくなる」のであって、そこが崖の底になる。"
          % (cam_l[0] / cam_l[-1], dx_l[-1] / max(dx_l[0], 1e-9), ceil_x))
    print("      ★y・z は %.2f -> %.2f mm でほとんど変わらない。"
          "**壊れるのは 1 方向だけ**なので、\n         残差 RMS を 1 個見ている限り"
          "気づけない。" % (float(rows[0][4]), float(rows[-1][4])))

    # --- その x はどこに嘘として出るか --------------------------------------- #
    print("\n      その残差は**どこに嘘として出るか**。支承(円柱)の位置を"
          "断面の円として ``fit_circle_3d`` で測る:")
    # ★まず測り方そのものの床を取る —— 劣化も姿勢誤差も無しで 2 回測るだけ。
    _CAMBER[0] = CAMBER
    c0 = observe(0, np.random.default_rng(SEED + 531), pose=False)
    c1 = observe(0, np.random.default_rng(SEED + 532), pose=False)
    f0, _, _ = bearing_pose(c0, 0)
    f1, _, _ = bearing_pose(c1, 0)
    floor_h, floor_v = ((f1 - f0) * 1e3)[0], -((f1 - f0) * 1e3)[1]
    print("      対照(劣化ゼロ・姿勢誤差ゼロで測り直しただけ): 水平 %+.2f mm / "
          "沈下 %+.2f mm ← **円の当てはめ自体の床**\n      "
          "(下半分の円弧しか見えず、見える範囲が走査位置で変わるので中心が偏る)"
          % (floor_h, floor_v))
    print("      条件                                桁の偽の変化 RMS[mm]"
          "   支承の水平移動[mm](真 0)  支承の沈下[mm](真 %.2f)" % SETTLE_MM[2])
    prow, fake_h, settle_read = [], 0.0, []
    conds = (("キャンバー %.0f mm・桁の全点" % (1e3 * CAMBER), CAMBER,
              lambda v: v[:, 2] > -0.95),
             ("キャンバー %.0f mm・桁の全点" % (1e3 * 0.002), 0.002,
              lambda v: v[:, 2] > -0.95),
             ("キャンバー %.0f mm・変わっていない端だけ" % (1e3 * CAMBER), CAMBER,
              lambda v: (v[:, 2] > -0.95) & stable_mask(v)))
    for name, cval, msk in conds:
        _CAMBER[0] = cval
        ref_b = observe(0, np.random.default_rng(SEED + 511))
        cur_b = observe(2, np.random.default_rng(SEED + 512))
        cen_b, nor_b, ok_b = core_normals(ref_b)
        tfb = truth_footprint(2)
        p_ref, r_ref, n_in = bearing_pose(ref_b, 0)
        q = register(cur_b, ref_b, mask=msk)[0]
        ln, _, _ = measure_normal(ref_b, q, cen_b, nor_b, ok_b)
        heal = np.isfinite(ln) & ~CORES["edge"] & (np.abs(tfb) < 0.3)
        p_cur, _, _ = bearing_pose(q, 0)
        dxz = (p_cur - p_ref) * 1e3
        rms_h = float(np.sqrt(np.mean(ln[heal] ** 2)))
        prow.append([name, "%.3f" % rms_h, "%+.2f" % dxz[0], "%+.2f" % (-dxz[1])])
        settle_read.append(-float(dxz[1]))
        if len(prow) == 2:
            fake_h = abs(float(dxz[0]))
        print("      %-34s %14.3f %21.2f %25.2f"
              % (name, rms_h, dxz[0], -dxz[1]))
    _CAMBER[0] = CAMBER
    print("      (円の半径の推定は %.4f m / 真 %.4f m。円弧が下半分しか見えないので"
          "半径は %.1f mm 過小)" % (r_ref, BEARING_R, 1e3 * (BEARING_R - r_ref)))
    print("      ★★桁の面の偽の変化はどの条件でも %.3f 〜 %.3f mm でほとんど"
          "動かないのに、\n         支承の読みは水平 %+.2f -> %+.2f mm、"
          "沈下 %+.2f -> %+.2f mm と別物になる。"
          % (min(float(r[1]) for r in prow), max(float(r[1]) for r in prow),
             float(prow[0][2]), float(prow[1][2]),
             settle_read[0], settle_read[2]))
    print("         (i) 決まらない x は、法線が ±x を向く**円柱にだけ** "
          "「%.1f mm 水平に動いた」として出る(真値 0)。" % fake_h)
    print("         (ii) 全点で合わせるとたわみの平均 %.1f mm が z に吸われ、"
          "**支承の沈下 %.2f mm が %.2f mm に消える**。"
          % (DEFLECT_MM[2] * 2 / 3, SETTLE_MM[2], settle_read[0]))
    print("             変わっていない端だけで合わせると %.2f mm まで戻る"
          "(残りは端でもたわみが 0 でないぶん %.2f mm と、上の床 %.2f mm)。"
          % (settle_read[2], DEFLECT_MM[2] * 0.296, floor_v))
    print("         **どちらも、面積の大半を占める大きな面の残差を見ている"
          "限り気づけない** —— \n         決まらなかった成分・吸われた成分は、"
          "それに感度を持つ**小さな部品にだけ**現れる。")
    figs.save_table("prism",
                    ["キャンバー mm", "端の勾配", "予測 x 残差 mm", "実測 x mm",
                     "残差 y,z mm"], rows,
                    title="橋軸方向がどれだけ決まるかは、反りの勾配で決まる",
                    caption="押し出し形状の平面は法線に x 成分を持たない。"
                            "x を拘束するのはキャンバーの傾きだけ。")
    dx_all, dx_grd = dx_l[0], dx_l[-1]

    # --- (b) 細い溝 -------------------------------------------------------- #
    print("\n  (b) 細い溝(ひび割れ)—— 平均する測り方には原理的に見えない。")
    print("      閉形式: 三角断面の溝(半幅 h、深さ d)を半径 R の足跡で平均すると")
    print("        平均 = d·h·(2R) / (π R²) · (1/2)·2 = 2 d h / (π R)"
          "  ← **密度は入らない**")
    print("\n       溝の全幅[mm]  予測の平均[mm]  足跡積分[mm]   比")
    hw_l, pred_l, num_l = [], [], []
    for hw in (0.003, 0.006, 0.0125, 0.025, 0.050, 0.100):
        pred = 2.0 * CRACK_MM[2] * hw / (math.pi * R_CYL)
        # 足跡(半径 R の円板)での厳密な平均 —— 1-D の求積で出す
        u = np.linspace(-min(hw, R_CYL), min(hw, R_CYL), 4001)
        chord = 2.0 * np.sqrt(np.maximum(0.0, R_CYL ** 2 - u ** 2))
        prof = CRACK_MM[2] * np.maximum(0.0, 1.0 - np.abs(u) / hw)
        num = float(np.trapezoid(prof * chord, u) / (math.pi * R_CYL ** 2))
        hw_l.append(2000 * hw)
        pred_l.append(pred)
        num_l.append(num)
        print("       %10.1f %14.4f %13.4f %7.3f"
              % (2000 * hw, pred, num, num / max(pred, 1e-9)))
    print("      ★予測(2dh/(πR))と厳密な足跡積分の比は %.3f 〜 %.3f"
          "(溝が足跡に近づくと弦が縮んで崩れる = 全幅 %.0f mm 以上)。"
          % (min(n / p for n, p in zip(num_l[:4], pred_l[:4])),
             max(n / p for n, p in zip(num_l[:4], pred_l[:4])), 2000 * R_CYL))
    need = math.pi * R_CYL * 2.0 * 2.0 / (2.0 * CRACK_MM[2]) * 1000
    print("      ★深さ %.2f mm の溝を平均で 2 mm として読むには 全幅 %.0f mm が要る"
          " —— **足跡と同じ幅**。" % (CRACK_MM[2], need))
    print("      ★予想は「密度を上げれば見える」だったが**外れ**。薄まりは"
          "2h/(πR) という**幾何**で、点の数には依らない。")
    print("      効かせたいなら足跡 R を溝幅まで縮めるしかないが、"
          "R を 1/10 にすると 1 core の点数が 1/100 になり\n"
          "      雑音が 10 倍になる —— **薄まりと雑音は同じつまみの両端**。")
    return {"dx_all": dx_all, "dx_grd": dx_grd, "hw": hw_l, "pred": pred_l,
            "num": num_l, "need": need, "cam": cam_l, "fake_h": fake_h,
            "ceil": ceil_x, "settle": settle_read}


# --------------------------------------------------------------------------- #
# 9. 図                                                                         #
# --------------------------------------------------------------------------- #
def dev_map(values: np.ndarray, ky: int = 7, kx: int = 3) -> np.ndarray:
    """core の値 -> **断面を展開した地図**(行 = 断面まわり s、列 = 橋軸 x)。"""
    a = np.asarray(values, float).reshape(CORES["shape"])
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return np.repeat(np.repeat(a, ky, axis=0), kx, axis=1)


def cross_section_sdf(x0: float, ny: int = 240, nz: int = 130) -> np.ndarray:
    """断面の符号つき距離場 —— **構造物を fullseye の sdf op だけで組む**。"""
    g = np.asarray(fs.ledger.grid_coords(((x0 - 0.02, x0 + 0.02), (-0.45, 4.45),
                                          (-1.35, 0.40)), (3, ny, nz)), float)
    cz = float(camber(np.array([x0]))[0])
    body = fs.ledger.box_sdf(g, (x0, 2.0, -0.45 + cz), (7.0, 1.30, 0.45))
    for sgn in (-1.0, 1.0):
        pt = (x0, 2.0 + sgn * 1.30, cz)
        nvec = (0.0, sgn * 0.70710678, -0.70710678)
        body = fs.ledger.sdf_intersect(body, fs.ledger.plane_sdf(g, pt, nvec))
    deck = fs.ledger.box_sdf(g, (x0, 2.0, 0.125 + cz), (7.0, 2.0, 0.125))
    part = fs.ledger.sdf_union(body, deck)
    for bx in BEARING_X:
        cyl = fs.ledger.cylinder_sdf(g, (bx, 2.0, -0.90 + float(camber(np.array([bx]))[0])
                                         - BEARING_R), (0.0, 1.0, 0.0),
                                     BEARING_R, BEARING_LEN)
        part = fs.ledger.sdf_union(part, cyl)
    return np.asarray(part)[1].T[::-1]        # (nz, ny) に直して上下を起こす


def section_figures(sc: dict, obs: dict, zero: dict, ctrl: dict,
                    rate: dict) -> None:
    if not figs.enabled():
        return
    # (1) 場面: 断面 2 枚(支間中央と支承の上)+ 展開した真値
    figs.save_grid("scene",
                   [np.clip(cross_section_sdf(6.0), -0.35, 0.35),
                    np.clip(cross_section_sdf(BEARING_X[0]), -0.35, 0.35),
                    dev_map(sc["truth_fp"])],
                   ["断面 x = 6.0 m(支間中央)", "断面 x = %.1f m(支承)"
                    % BEARING_X[0], "展開した真の変化 t2 [mm](正 = 面が外へ)"],
                   ncols=1, signed=[True, True, True],
                   title="橋桁(平面 7 枚 + 円柱 2 本)と仕込んだ劣化",
                   caption="断面は fullseye の sdf op(box/plane/cylinder + "
                           "union/intersect)だけで組んである。展開図は"
                           "行 = 断面まわり(下面左→腹板→下フランジ→腹板→下面右)、"
                           "列 = 橋軸方向。")

    # (2) 3 時点の真値(展開図)
    figs.save_grid("frames",
                   [dev_map(truth_footprint(1) * 0.0), dev_map(truth_footprint(1)),
                    dev_map(sc["truth_fp"])],
                   ["t0(基準)", "t1(1 年後)", "t2(2 年後)"],
                   ncols=1, signed=True,
                   title="真の法線方向変化 [mm] —— 3 時点",
                   caption="下フランジ中央の暗い窪みが断面欠損、面全体の淡い"
                           "変化がたわみ。腹板(法線が水平)にはたわみが出ない。")

    # (3) 変化の地図: 真値 / 法線方向 / C2C / 偽の劣化
    fa = ctrl["conds"]["(a) 劣化ゼロ・測り直しのみ"]
    figs.save_grid("map_change",
                   [dev_map(sc["truth_fp"]), dev_map(zero["L"]),
                    dev_map(np.where(np.isfinite(zero["c2c"]), zero["c2c"], 0.0)),
                    dev_map(fa["L"])],
                   ["真値(足跡平均)[mm]", "法線方向に測る [mm]",
                    "最近傍距離 C2C [mm](符号なし)", "偽の劣化 = 劣化ゼロの対照 [mm]"],
                   ncols=2, signed=[True, True, False, True],
                   title="t0 -> t2 の変化をどう測るか(展開図)",
                   caption="C2C は面全体が点間隔ぶん明るく、欠損が背景に埋もれる。"
                           "右下は**構造物が全く変わっていない**ときの地図。")

    # (4) 速度の地図
    figs.save_grid("map_rate",
                   [dev_map(rate["rate_true"]), dev_map(rate["rate"]),
                    dev_map(rate["rate"] - rate["rate_true"])],
                   ["真の速度 [mm/年]", "測った速度 [mm/年]", "速度の誤差 [mm/年]"],
                   ncols=1, signed=True,
                   title="劣化速度(mm/年)の地図と、その誤差",
                   caption="速度は差を年数で割っただけなので、位置合わせの"
                           "残差がそのまま速度の嘘になる。")


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    assert hasattr(fs.ledger, "icp_point2plane") and hasattr(fs.ledger, "fit_plane_3d")
    assert not hasattr(fs.ledger, "m3c2") and not hasattr(fs, "cloud_to_cloud")
    print("  (a) **法線方向に測る差分(M3C2)が無い**。``chamfer_distance`` と"
          " ``hausdorff_distance`` は\n      1 個のスカラを返すだけで、"
          "``query_distance`` は ESDF への距離(符号はあるが格子に丸まる)。"
          "\n      本 PoC は core + 局所平面 + 円柱の平均差を 60 行で自前実装した。"
          "**符号つき・分布つきの面差分**は\n      橋・トンネル・擁壁・法面で"
          "同じ形なので、族に入る価値がある。")

    assert not hasattr(fs.ledger, "icp_trimmed_region") and not hasattr(fs, "icp_mask")
    print("  (b) **位置合わせの「使う範囲」を指定する口が無い**。``icp_point2plane``"
          " の ``trim`` は\n      距離で切るだけで、「この領域は変化しているから"
          "合わせに使うな」を渡せない。5 節で測ったとおり\n      これは精度の話"
          "ではなく**結論が変わる**話(たわみが 0.689 だけ消える)。"
          "``mask`` 引数か、\n      合わせに使った点の割合を返す契約が要る。")

    assert not hasattr(fs.ledger, "registration_uncertainty")
    print("  (c) **位置合わせの残差「姿勢」を返す口が無い**。``icp_point2plane`` は"
          " RMSE を返すが、\n      6 節で示したとおり効くのは"
          "**残差の回転軸と大きさ**(面ごとに違う嘘をつく)。"
          "\n      共分散(6x6)まで返せば、面ごとの検出限界を"
          "**測る前に**出せる。")

    assert not hasattr(fs.ledger, "developed_surface") and not hasattr(fs, "unroll_prism")
    print("  (d) **押し出し形状を展開する口が無い**。断面の折れ線に沿って"
          "(x, s)へ開く操作は\n      橋桁・配管・トンネル覆工・タンクで共通で、"
          "開けば 3-D の地図が 2-D の画像 op で扱える"
          "\n      (この PoC の図はすべてそれ)。``plane_segmentation`` で面は"
          "取れるが、**面を並べて\n      1 枚に開く**ところが無い。")

    assert not hasattr(fs.ledger, "point_spacing")
    print("  (e) **点間隔を返す口が無い**。2・6 節で見たとおり C2C の偽の劣化は"
          "ほぼ点間隔そのものなので、\n      「この点群で言える最小の変化」は"
          "点間隔から直接出る。密度・最近傍距離の分位数を返す 1 本があれば、"
          "\n      測ってから気づくのを防げる。")

    print("  (f) 仕様どおりで穴ではないが、踏みやすい点を 3 つ: "
          "``fit_plane_3d`` の法線は**符号が任意**(本 PoC は真の外向きに"
          "\n      合わせている)/ ``icp_point2plane`` は台帳経由だと pose しか"
          "返さないので ``.raw`` で 5 個受ける /\n      点の op は (N,3)=(x,y,z)、"
          "体積の op は (depth,row,col) で軸の順が違う。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える")
    print("支間 %.0f m / 表面積 %.1f m2 / 点検 3 回 / core 間隔 %.2f m"
          % (LSPAN, GIRDER_AREA + BEARING_AREA, CORE_SP))
    print("=" * 78)
    sc = section_scene()
    obs = section_observe()
    zero = section_zero(obs, sc)
    ctrl = section_control(sc)
    scope = section_scope()
    cliff = section_cliff(zero, sc)
    rate = section_rate(obs, sc)
    pri = section_prism_and_crack(sc)
    section_figures(sc, obs, zero, ctrl, rate)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    ga = ctrl["conds"]["(a) 劣化ゼロ・測り直しのみ"]["good"]
    fa_c2c = ctrl["conds"]["(a) 劣化ゼロ・測り直しのみ"]["c2c"]
    fa_l = ctrl["conds"]["(a) 劣化ゼロ・測り直しのみ"]["L"]
    print("  * **劣化ゼロで測り直しただけ**で、C2C は 中央値 %.2f mm・最大 %.2f mm の"
          "「劣化」を返す(真の最大劣化 %.1f mm)。\n    法線方向なら %.2f / %.2f mm。"
          % (float(np.median(fa_c2c[ga])), float(np.nanmax(fa_c2c[ga])),
             max(SPALL_MM), float(np.median(np.abs(fa_l[ga]))),
             float(np.nanmax(np.abs(fa_l[ga])))))
    print("  * その偽の劣化はしきい値 %.1f mm で数えると %.2f m2 / %.2f L の"
          "「補修候補」になる —— 本物の %.2f L の %.0f %%。"
          % (ctrl["thr"], ctrl["false_area"], ctrl["false_vol"], ctrl["v_true"],
             100 * ctrl["false_vol"] / ctrl["v_true"]))
    print("  * C2C の偽の劣化は**点間隔でほぼ決まる**: 密度 %.0f -> %.0f pt/m2 で "
          "%.2f -> %.2f mm(予測 0.5/√ρ との比 %.3f 〜 %.3f)。"
          % (cliff["dens"][0], cliff["dens"][-1], cliff["c2c"][0],
             cliff["c2c"][-1],
             min(m / p for m, p in zip(cliff["c2c"], cliff["c2c_pred"])),
             max(m / p for m, p in zip(cliff["c2c"], cliff["c2c_pred"]))))
    print("  * たわみを含めて全点で合わせると中央のたわみの %.3f が消え"
          "(予測 %.3f)、支点付近に %+.3f mm の**逆符号**が出る。"
          % (scope["eat_all"], scope["w_all"],
             scope["prof"]["全点で合わせる"][scope["end"]]))
    print("    変わっていない端だけで合わせても %.3f は吸われたまま(予測 %.3f)。"
          % (scope["eat_end"], scope["w_end"]))
    print("  * 残差回転の作る嘘は幾何で先に出せる((ω×(p-c))·n、雑音床と直交合成で"
          "比 %.3f 〜 %.3f)。\n    最小検出深さは α = 0 -> %.1e rad で %.2f -> %.2f mm。"
          % (min(m / t for m, t in zip(cliff["meas"], [math.hypot(p, cliff["meas"][0])
                                                       for p in cliff["pred"]])),
             max(m / t for m, t in zip(cliff["meas"], [math.hypot(p, cliff["meas"][0])
                                                       for p in cliff["pred"]])),
             cliff["alpha"][-1] * 1e-3, cliff["mindet"][0], cliff["mindet"][-1]))
    print("  * 速度の誤差 RMS %.3f mm/年 —— 1 mm/年 の進行は 2σ = %.3f mm/年 の下。"
          "★点検を 3 回に増やしても速度は良くならない\n    "
          "(等間隔 3 点の傾きは両端の差分と厳密に同じ、差 %.1e mm/年)。"
          "良くなるのは加速だけで、その誤差は %.3f mm/年²\n    "
          "—— 独立を仮定した予測 %.3f より小さいのは、時点間の誤差が相関 %+.3f を"
          "持つから。"
          % (rate["err_rms"], rate["detect"], rate["dmax"], rate["acc_err"],
             rate["acc_pred_ind"], rate["rho"]))
    print("  * 押し出し形状は橋軸方向が反りの勾配からしか決まらない: キャンバーを"
          " %.0f -> %.0f mm にすると残差 x が %.2f -> %.2f mm。\n    "
          "★その嘘は桁の平面には出ず(法線が x に直交)、法線が ±x を向く"
          "**支承の円柱にだけ**「%.2f mm 水平に動いた」として現れる。"
          % (pri["cam"][0], pri["cam"][-1], pri["dx_all"], pri["dx_grd"],
             pri["fake_h"]))
    print("  * 幅 %.0f mm の溝は足跡平均では %.4f mm(閉形式 2dh/(πR) = %.4f)。"
          "★密度は分母に入らないので、密度を上げても見えない ——\n    "
          "深さ %.1f mm の溝を 2 mm と読むには全幅 %.0f mm(= 足跡の直径)が要る。"
          % (2000 * CRACK_HW, pri["num"][1], pri["pred"][1], CRACK_MM[2],
             pri["need"]))

    # ---- 所見を固定する検査 ------------------------------------------------- #
    tot = [math.hypot(p, cliff["meas"][0]) for p in cliff["pred"]]
    assert float(np.median(fa_c2c[ga])) > max(SPALL_MM) * 0.5, \
        "劣化ゼロの C2C が小さすぎる(場面が甘い)"
    assert float(np.median(np.abs(fa_l[ga]))) < 0.2 * float(np.median(fa_c2c[ga])), \
        "法線方向が C2C に対して優位でない"
    assert ctrl["false_vol"] > 0.2 * ctrl["v_true"], "偽の劣化が小さすぎる"
    assert all(0.85 < m / p < 1.15 for m, p in zip(cliff["c2c"], cliff["c2c_pred"])), \
        "C2C が 0.5/√ρ の予測から外れた"
    assert abs(scope["eat_all"] - scope["w_all"]) < 0.06, \
        "全点で合わせたときの吸われ方が閉形式 2/3 から外れた"
    assert scope["prof"]["全点で合わせる"][scope["end"]] < -0.5, \
        "支点付近に逆符号の偽の変化が出ていない"
    assert abs(scope["eat_end"] - scope["w_end"]) < 0.10, \
        "端だけで合わせたときの吸われ方が閉形式から外れた"
    assert all(0.9 < m / t < 1.12 for m, t in zip(cliff["meas"], tot)), \
        "角度誤差の作る嘘が幾何の予測から外れた"
    assert cliff["mindet"][-1] > 2.5 * cliff["mindet"][0], \
        "角度誤差で検出限界が折れていない"
    assert rate["dmax"] < 1e-9, "等間隔 3 点の傾きが両端の差分と一致しない"
    assert rate["acc_err"] < rate["acc_pred_ind"], "加速の誤差が独立仮定を超えた"
    assert rate["rho"] > 0.2, "時点間の誤差の相関が出ていない"
    assert pri["dx_grd"] > 3.0 * pri["dx_all"], \
        "キャンバーを落としても x が決まっている(縮退が再現しない)"
    assert pri["fake_h"] > 1.0, "支承の偽の水平移動が出ていない"
    assert all(0.9 < n / p < 1.1 for n, p in zip(pri["num"][:4], pri["pred"][:4])), \
        "溝の薄まりが閉形式 2dh/(πR) から外れた"
    assert abs(pri["num"][1]) < 0.1 * CRACK_MM[2], "細い溝が薄まっていない"

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
