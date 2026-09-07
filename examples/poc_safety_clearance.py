# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""人と機械の安全距離 —— 「近い」を測る点をどこに置くかで危険が消える。

協働ロボット・搬送機・プレスの安全は「人と機械がどれだけ離れているか」で決まり
ます(ISO/TS 15066 の速度分離監視 SSM は**分離距離そのもの**が指標)。ところが
現場の実装は人を 1 点(重心や足元)で代表しがちで、**手を伸ばした指先**が入った
危険を見落とします。ここでは人を多関節の骨格 + 太さを持つカプセルで作り、機械も
カプセルと直方体で作って、**真の最小分離距離(表面どうし)を時刻ごとに閉形式で**
持ったうえで、距離センサの自己遮蔽・点密度・更新間隔を掃引します。

EXTEND: 実測に差し替えるなら :func:`observe` の戻り値(センサ座標系ではなく
world の点群 (N,3) と、その点がどのセンサから見えたか)を実機の 1 フレームに
置き換えます。実データでは (a) 真の分離距離が無いので「見落とし」を数えられず、
基準は**別のもっと密なセンサ**にしかならない、(b) 人の部位ラベルが無いので
「いちばん近いのは手か胴か」を切り分けられない、(c) 機械側の姿勢はエンコーダで
分かるが、その**据付け誤差**が Z_r に乗る —— の 3 点が変わります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(人を重心 1 点 + 半径 0.30 m の円柱で代表)を先に測る**。★予想は
   「真の距離は『腕の長さ + 体の厚み』ぶん過大評価される」= 0.42 m。**実測の
   平均は +0.410 m、最大 +0.646 m** —— 予想どおり。この過大評価が
   そのまま見落としになり、**危険な 66 フレームのうち 46 を見落とす
   (69.7 %)**。誤検知は 0 件で、**片側にしか壊れない**。
2. ★**足元 1 点(2-D 安全レーザスキャナ)はもっと悪い**。同じ場面で
   過大評価の平均 +0.575 m、見落とし **60/66 (90.9 %)**。高さを捨てると
   「伸ばした手」だけでなく「上体の前傾」も消える。
3. ★★**見えている部位だけで測ると危険が消える**。全表面が見えれば推定は
   真値に張り付く(平均 +0.007 m、見落とし 0 件)。ところが頭上センサ 1 台では
   **危険フレームの 33.3 % で「いちばん近い部位が 1 点も見えていない」**。
   そのとき推定は次に近い部位(胴)に飛ぶので、過大評価は平均 +0.062 m /
   最大 **+0.334 m**、見落とし **9/66 (13.6 %)**。**遮蔽は雑音と違って
   片側にしか出ない** —— 見えない点は必ず「もっと遠い」と報告される。
4. ★**崖は点密度でも更新間隔でもなく遮蔽**。点密度を 1600 → 100 点と
   16 倍疎にしても見落としは 13.6 → 16.7 % しか動かない(予想 = 標本間隔
   s の 2 乗 / 曲率半径で、最疎でも 0.019 m の過大評価。実測 0.020 m)。
   更新間隔 0.15 → 0.60 s は 13.6 → 21.2 %(予想 = v_h·Δt = 0.15 m ぶん
   遅れる)。**同じ土俵で遮蔽は 0 → 13.6 %** で、1 台か 2 台かが効く。
5. ★★**Z_d を測定から見積もると足りない**。同じ姿勢を 24 回測り直した
   ばらつきから Z_d を出すと **0.006 m**(3σ)。ところが遮蔽による過大評価の
   95 % 点は **0.181 m** —— **29 倍**。繰り返し性で不確かさを名乗ると、
   見落とし 13.6 % がそのまま残る。見落としを 0 にする Z_d は 0.334 m で、
   そのとき機械が止まっている時間は 34.8 → 61.0 % に増える。**安全の代金は
   稼働率で払う**。
6. ★**よく報告される指標(Chamfer)はこの危険に盲目**。真の表面点群と測定点群の
   Chamfer 距離は 0.0289 m で「よく合っている」ように見えるが、Hausdorff は
   0.5417 m。**危険を決めるのは最悪値のほう**で、平均は隠れた手を薄める。
7. ★**格子で測ると距離が刻まれる**。機械を占有格子にして ESDF を引く
   (`esdf` + `query_distance`)と、厳密な CSG 距離に対して 40 mm 格子で
   +0.0209 m / 20 mm で +0.0104 m / 10 mm で +0.0055 m の偏りが出る ——
   **ほぼ半ボクセル**(予想 0.0200 / 0.0100 / 0.0050 m)。これは Z_d に
   足すべき既知の系統誤差であって、雑音ではない。

【グラウンドトゥルース】人は 9 本のカプセル(胴・頭・両腕 3 節・両脚)、機械は
2 本のカプセル(リンク)+ 直方体(基台)。関節角は既知の時間関数。真の最小分離
距離は**線分どうしの最短距離 - 半径の和**(閉形式)と、**線分-直方体の凸 1 次元
最小化**(黄金分割 48 回、残差 < 1e-9 m)で求める。表面点は解析サンプル、
遮蔽は場面全体の SDF を視線上で評価して判定するので、遮蔽の真値も既知。

来歴(公開文献のみ): ISO/TS 15066:2016 *Robots and robotic devices — Collaborative
robots*(速度分離監視 SSM と分離距離の式)/ ISO 13855:2010(最小距離の算出)/
IEC 61496-3(能動的光電式防護装置)/ Ericson, *Real-Time Collision Detection*
(Morgan Kaufmann, 2005) 5.1.9 —— 線分どうしの最短距離。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_L = fs.ledger

# --- 場面の諸元(単位はメートル・秒。x = 機械へ向かう軸、z = 上) ------------- #
SEED = 20260907

# 機械(危険源): 基台の直方体 + 2 本のリンク。リンクは水平面を掃く。
BASE_C, BASE_H = (0.0, 0.0, 0.55), (0.32, 0.32, 0.55)
J0 = (0.0, 0.0, 1.40)          # 肩(第 1 関節)
L1, R1 = 0.55, 0.085           # 第 1 リンクの長さと半径
L2, R2 = 0.45, 0.070           # 第 2 リンク
THETA_A, T_SWEEP, PHI2 = 0.85, 3.7, 0.55

# 環境(危険源ではないが視線を遮る): 治具台
TABLE_C, TABLE_H = (0.70, 0.0, 0.38), (0.38, 0.50, 0.38)

# 人(多関節)。長さは日本人成人男性の中央値に近い値を使う。
# ★胴は**カプセル 2 本を並べて**作る。1 本の円柱にすると断面が円になり、
#   肩(体幹中心から ±0.19 m)が胴の影から外れてしまう —— 実際の胴は幅 0.50 m /
#   奥行き 0.30 m の扁平な断面で、伸ばした腕は背後から見ると胴に隠れる。
R_TORSO, R_HEAD, R_UARM, R_FARM, R_HAND, R_LEG = 0.150, 0.105, 0.055, 0.048, 0.042, 0.085
TORSO_HALF_W = 0.10           # 胴カプセル 2 本の中心間の半分 [m]
TORSO_H, HEAD_H = 0.50, 0.12
UARM_L, FARM_L, HAND_L = 0.30, 0.27, 0.11
PELVIS_Z = 0.95
A1_MAX, A2_ADD = np.radians(50.0), np.radians(10.0)   # 肩・肘の伸展角

# 歩行と手伸ばし
X0, V_WALK = 2.85, 0.25        # 初期位置 [m] と接近速度 [m/s]
T_END, DT = 6.0, 0.15
REACH_T0, REACH_T1 = 1.8, 4.6  # 手を伸ばす区間 [s]

# センサ(既知の位置。1 台目 = 頭上、2 台目 = 隅)
SENSOR_TOP = (0.55, 0.10, 2.90)
SENSOR_COR = (2.30, 1.75, 2.20)
N_SURF = 1600                  # 表面点の総数(最密。掃引ではここから間引く)
N_RAY = 6                      # 視線を刻む数(遮蔽判定)
SIG0, SIG_K = 0.004, 0.0012    # 距離雑音 σ = SIG0 + SIG_K·z² [m]
DROPOUT = 0.08                 # 欠測率

# 速度分離監視(SSM)。S = v_h(T_r+T_s) + v_r·T_r + B + C + Z_d + Z_r
V_H, T_R, T_S, V_R = 1.6, 0.10, 0.15, 0.50
B_STOP, C_INTRUSION, Z_R = 0.04, 0.15, 0.02
ZD_BASE = 0.03                 # まず「繰り返し性から」名乗る Z_d

BODY_RADIUS = 0.30             # ゼロ点が人に被せる円柱の半径 [m]

_S_BASE = (V_H * (T_R + T_S) + V_R * T_R + B_STOP + C_INTRUSION + Z_R)


def required_separation(z_d: float = ZD_BASE) -> float:
    """ISO/TS 15066 の必要分離距離 S。``z_d`` はセンサの不確かさ [m]。"""
    return _S_BASE + float(z_d)


# --------------------------------------------------------------------------- #
# 幾何 —— 真値はここで閉形式に決まる                                            #
# --------------------------------------------------------------------------- #
def _unit(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.array([0.0, 0.0, 1.0])


def seg_seg_distance(p1, q1, p2, q2):
    """線分 p1-q1 と p2-q2 の最短距離(Ericson 5.1.9 の clamp 法)。

    先頭次元でブロードキャストする。``distance_line_line`` は**無限直線**の
    距離なので、腕や リンクのような**有限の線分**には使えない(必ず過小評価に
    なる)—— 公開経路に線分どうしの口が無いのでここで書く。
    """
    p1 = np.asarray(p1, np.float64); q1 = np.asarray(q1, np.float64)
    p2 = np.asarray(p2, np.float64); q2 = np.asarray(q2, np.float64)
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a = (d1 * d1).sum(-1); e = (d2 * d2).sum(-1)
    b = (d1 * d2).sum(-1); c = (d1 * r).sum(-1); f = (d2 * r).sum(-1)
    eps = 1e-14
    a_s = np.where(a > eps, a, 1.0)
    e_s = np.where(e > eps, e, 1.0)
    denom = a * e - b * b
    s = np.where(denom > eps, (b * f - c * e) / np.where(denom > eps, denom, 1.0), 0.0)
    s = np.clip(s, 0.0, 1.0)
    t = (b * s + f) / e_s
    s = np.where(t < 0.0, np.clip(-c / a_s, 0.0, 1.0),
                 np.where(t > 1.0, np.clip((b - c) / a_s, 0.0, 1.0), s))
    t = np.clip(t, 0.0, 1.0)
    # 退化(点に潰れた線分)を上書き
    deg_a = a <= eps
    s = np.where(deg_a, 0.0, s)
    t = np.where(deg_a, np.clip(f / e_s, 0.0, 1.0), t)
    deg_e = e <= eps
    t = np.where(deg_e, 0.0, t)
    s = np.where(deg_e, np.clip(-c / a_s, 0.0, 1.0), s)
    c1 = p1 + s[..., None] * d1
    c2 = p2 + t[..., None] * d2
    return np.linalg.norm(c1 - c2, axis=-1), c1, c2


def seg_box_distance(p0, p1, center, half, iters=48):
    """線分と軸平行直方体の符号付き距離(凸 1 次元最小化)。

    ``box_sdf`` は凸集合の符号付き距離なので線分上で凸 —— 黄金分割ならぬ
    三分探索を ``iters`` 回まわせば区間が (2/3)^iters に縮む(48 回で 1e-9 未満)。
    先頭次元でブロードキャストする(全ペアを一度に潰す)。
    """
    p0 = np.atleast_2d(np.asarray(p0, np.float64))
    p1 = np.atleast_2d(np.asarray(p1, np.float64))
    d = p1 - p0
    lo = np.zeros(len(p0)); hi = np.ones(len(p0))
    for _ in range(iters):
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        v1 = np.asarray(_L.box_sdf(p0 + m1[:, None] * d, center, half))
        v2 = np.asarray(_L.box_sdf(p0 + m2[:, None] * d, center, half))
        take = v1 < v2
        hi = np.where(take, m2, hi)
        lo = np.where(take, lo, m1)
    t = 0.5 * (lo + hi)
    pt = p0 + t[:, None] * d
    return np.asarray(_L.box_sdf(pt, center, half)), pt


def machine_pose(t: float) -> dict:
    """時刻 ``t`` の機械。``links`` = カプセル、``box`` = 基台(危険源)。"""
    th = THETA_A * np.sin(2.0 * np.pi * t / T_SWEEP)
    j0 = np.asarray(J0, np.float64)
    j1 = j0 + np.array([L1 * np.cos(th), L1 * np.sin(th), -0.08])
    j2 = j1 + np.array([0.6 * L2 * np.cos(th + PHI2),
                        0.6 * L2 * np.sin(th + PHI2), -0.34])
    return {"links": [(j0, j1, R1), (j1, j2, R2)],
            "box": (np.asarray(BASE_C), np.asarray(BASE_H)),
            "theta": float(th), "tool": j2}


def reach_alpha(t: float, t0: float = REACH_T0, t1: float = REACH_T1) -> float:
    """手を伸ばす度合い α ∈ [0,1](smoothstep。既知の関数 = 真値)。"""
    u = float(np.clip((t - t0) / (t1 - t0), 0.0, 1.0))
    return u * u * (3.0 - 2.0 * u)


def human_pose(t: float, y_h: float = 0.22, t0: float = REACH_T0,
               v: float = V_WALK) -> list:
    """時刻 ``t`` の人。``[(部位名, a, b, r), ...]`` の 9 カプセル。"""
    px = X0 - v * t
    p = np.array([px, y_h, PELVIS_Z])
    n = p + np.array([0.0, 0.0, TORSO_H])                # 首
    al = reach_alpha(t, t0, t0 + (REACH_T1 - REACH_T0))
    a1 = al * A1_MAX
    a2 = a1 + al * A2_ADD
    u1 = np.array([-np.sin(a1), 0.0, -np.cos(a1)])
    u2 = np.array([-np.sin(a2), 0.0, -np.cos(a2)])
    s_r = n + np.array([0.0, -0.19, -0.03])              # 右肩(伸ばす側)
    e_r = s_r + UARM_L * u1
    w_r = e_r + FARM_L * u2
    f_r = w_r + HAND_L * u2
    s_l = n + np.array([0.0, 0.19, -0.03])               # 左腕は下げたまま
    return [
        ("胴", p, n, R_TORSO),
        ("頭", n + np.array([0.0, 0.0, 0.06]), n + np.array([0.0, 0.0, 0.06 + HEAD_H]), R_HEAD),
        ("右上腕", s_r, e_r, R_UARM),
        ("右前腕", e_r, w_r, R_FARM),
        ("右手", w_r, f_r, R_HAND),
        ("左腕", s_l, s_l + np.array([0.02, 0.02, -0.58]), R_UARM),
        ("右脚", p + np.array([0.0, -0.10, 0.0]), p + np.array([0.02, -0.11, -0.90]), R_LEG),
        ("左脚", p + np.array([0.0, 0.10, 0.0]), p + np.array([0.02, 0.11, -0.90]), R_LEG),
        ("肩帯", s_r, s_l, R_UARM),
    ]


def true_clearance(human: list, mach: dict) -> tuple:
    """真の最小分離距離(表面どうし)と、いちばん近い部位の名前・端点。

    人のカプセル × (機械のリンク 2 本 + 基台) を全部当たる。線分どうしは
    閉形式、線分-直方体は凸 1 次元最小化。
    """
    names = [h[0] for h in human]
    A = np.array([h[1] for h in human]); B = np.array([h[2] for h in human])
    R = np.array([h[3] for h in human])
    best = np.full(len(human), np.inf)
    pa = np.zeros((len(human), 3)); pb = np.zeros((len(human), 3))
    for (la, lb, lr) in mach["links"]:
        d, c1, c2 = seg_seg_distance(A, B, np.asarray(la)[None], np.asarray(lb)[None])
        d = d - R - lr
        upd = d < best
        best = np.where(upd, d, best)
        pa[upd] = c1[upd]; pb[upd] = c2[upd]
    bc, bh = mach["box"]
    d, pt = seg_box_distance(A, B, bc, bh)
    d = d - R
    upd = d < best
    best = np.where(upd, d, best)
    pa[upd] = pt[upd]
    pb[upd] = np.clip(pt[upd], bc - bh, bc + bh)
    k = int(np.argmin(best))
    return float(best[k]), names[k], pa[k], pb[k], best


def hazard_sdf(pts, mach: dict):
    """危険源(リンク + 基台)の SDF を任意点 (...,3) で厳密に評価する。"""
    d = None
    for (la, lb, lr) in mach["links"]:
        v = _L.capsule_sdf(pts, la, lb, lr)
        d = v if d is None else _L.sdf_union(d, v)
    bc, bh = mach["box"]
    return np.asarray(_L.sdf_union(d, _L.box_sdf(pts, bc, bh)))


def scene_sdf(pts, human: list, mach: dict, with_table=True):
    """視線を遮るもの全部(人 + 機械 + 治具台)の SDF。"""
    d = hazard_sdf(pts, mach)
    for (_n, a, b, r) in human:
        d = np.asarray(_L.sdf_union(d, _L.capsule_sdf(pts, a, b, r)))
    if with_table:
        d = np.asarray(_L.sdf_union(d, _L.box_sdf(pts, TABLE_C, TABLE_H)))
    return d


# --------------------------------------------------------------------------- #
# 測定 —— 表面をサンプルし、遮蔽・雑音・欠測を既知の量で入れる                   #
# --------------------------------------------------------------------------- #
_GA = np.pi * (3.0 - np.sqrt(5.0))          # 黄金角


def capsule_surface(a, b, r, n: int):
    """カプセル表面の準一様サンプル(点と外向き法線)。面積比で側面と端に配る。"""
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    ax = b - a
    ln = float(np.linalg.norm(ax))
    u = ax / ln if ln > 1e-12 else np.array([0.0, 0.0, 1.0])
    e1 = _unit(np.cross(u, [0.0, 0.0, 1.0] if abs(u[2]) < 0.9 else [1.0, 0.0, 0.0]))
    e2 = np.cross(u, e1)
    a_cyl, a_cap = 2 * np.pi * r * ln, 4 * np.pi * r * r
    n_cyl = int(round(n * a_cyl / (a_cyl + a_cap)))
    n_cap = max(4, n - n_cyl)
    pts, nrm = [], []
    if n_cyl > 0:
        k = np.arange(n_cyl)
        s = (k + 0.5) / n_cyl
        ph = k * _GA
        rad = np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2
        pts.append(a + s[:, None] * ax + r * rad)
        nrm.append(rad)
    k = np.arange(n_cap)
    zz = 1.0 - 2.0 * (k + 0.5) / n_cap
    rr = np.sqrt(np.maximum(0.0, 1.0 - zz * zz))
    ph = k * _GA
    d = (zz[:, None] * u + rr[:, None] * (np.cos(ph)[:, None] * e1
                                          + np.sin(ph)[:, None] * e2))
    ctr = np.where(zz[:, None] >= 0.0, b, a)
    pts.append(ctr + r * d)
    nrm.append(d)
    return np.concatenate(pts), np.concatenate(nrm)


def human_surface(human: list, n_total: int = N_SURF):
    """人の全身表面点(面積比で配分)。``part`` は部位の番号。"""
    areas = np.array([2 * np.pi * h[3] * float(np.linalg.norm(h[2] - h[1]))
                      + 4 * np.pi * h[3] ** 2 for h in human])
    share = np.maximum(8, np.round(n_total * areas / areas.sum()).astype(int))
    P, N, K = [], [], []
    for i, (_n, a, b, r) in enumerate(human):
        p, q = capsule_surface(a, b, r, int(share[i]))
        P.append(p); N.append(q); K.append(np.full(len(p), i))
    return np.concatenate(P), np.concatenate(N), np.concatenate(K), float(areas.sum())


def visible_from(pts, nrm, sensor, human, mach, k_ray: int = N_RAY):
    """センサから見えるか(裏面判定 + 視線上の SDF)。真値として使える。"""
    S = np.asarray(sensor, np.float64)
    ray = S - pts
    rng_ = np.linalg.norm(ray, axis=1)
    ok = (nrm * ray).sum(1) > 0.0                       # 裏面は見えない
    idx = np.nonzero(ok)[0]
    if idx.size == 0:
        return ok
    d0 = 0.05 / np.maximum(rng_[idx], 1e-6)             # 自分の表面から 5 cm 離す
    ss = d0[:, None] + (np.linspace(0.0, 1.0, k_ray)[None, :]
                        * (0.97 - d0)[:, None])
    q = pts[idx][:, None, :] + ss[..., None] * ray[idx][:, None, :]
    blocked = (scene_sdf(q, human, mach) < 0.0).any(axis=1)
    ok[idx[blocked]] = False
    return ok


def observe(pts, nrm, vis, rng, sensor_of, density=None, noise=True):
    """見えた点に距離雑音と欠測を入れて返す(``sensor_of`` は視線方向の基準)。"""
    idx = np.nonzero(vis)[0]
    if density is not None and idx.size > density:
        idx = rng.choice(idx, size=int(density), replace=False)
    if idx.size == 0:
        return np.zeros((0, 3)), idx
    q = pts[idx].copy()
    if noise:
        S = sensor_of[idx]
        ray = S - q
        rr = np.linalg.norm(ray, axis=1, keepdims=True)
        sig = SIG0 + SIG_K * rr ** 2
        q = q + (ray / np.maximum(rr, 1e-9)) * (sig * rng.standard_normal((len(q), 1)))
        keep = rng.random(len(q)) > DROPOUT
        q, idx = q[keep], idx[keep]
    return q, idx


# --------------------------------------------------------------------------- #
# 1 フレームぶんを組み立てる                                                    #
# --------------------------------------------------------------------------- #
def frame(t: float, y_h: float, t0: float, rng, n_surf: int = N_SURF) -> dict:
    human = human_pose(t, y_h, t0)
    mach = machine_pose(t)
    d_true, part, pa, pb, per_part = true_clearance(human, mach)
    P, N, K, area = human_surface(human, n_surf)
    v_top = visible_from(P, N, SENSOR_TOP, human, mach)
    v_cor = visible_from(P, N, SENSOR_COR, human, mach)
    return {"t": t, "human": human, "mach": mach, "d_true": d_true,
            "part": part, "pa": pa, "pb": pb, "per_part": per_part,
            "P": P, "N": N, "K": K, "area": area,
            "v_top": v_top, "v_cor": v_cor}


def _sensor_of(vis_top, vis_cor):
    """点ごとに「どちらのセンサから見た距離か」(頭上を優先)。"""
    S = np.repeat(np.asarray(SENSOR_COR)[None], len(vis_top), axis=0)
    S[vis_top] = np.asarray(SENSOR_TOP)
    return S


def estimate(fr: dict, vis, rng, density=None, noise=True) -> float:
    """測定点群から出す分離距離の推定 = 点ごとの危険源 SDF の最小。"""
    q, _idx = observe(fr["P"], fr["N"], vis, rng, _sensor_of(fr["v_top"], fr["v_cor"]),
                      density=density, noise=noise)
    if len(q) == 0:
        return np.inf
    return float(np.min(hazard_sdf(q, fr["mach"])))


def estimate_centroid(fr: dict, vis, rng, mode="centroid") -> float:
    """ゼロ点: 人を 1 点で代表し、半径 BODY_RADIUS の球で被せる。"""
    q, _ = observe(fr["P"], fr["N"], vis, rng, _sensor_of(fr["v_top"], fr["v_cor"]))
    if len(q) == 0:
        return np.inf
    if mode == "centroid":
        c = q.mean(axis=0)
    else:                                   # 足元(2-D 安全レーザ、高さ 0.20 m)
        low = q[q[:, 2] < 0.35]
        c = (low.mean(axis=0) if len(low) else q.mean(axis=0))
        c = np.array([c[0], c[1], PELVIS_Z])
    return float(hazard_sdf(c[None], fr["mach"])[0]) - BODY_RADIUS


# --------------------------------------------------------------------------- #
# 0. 自己検算 —— 真値の道具そのものを疑う                                        #
# --------------------------------------------------------------------------- #
def section_selfcheck() -> None:
    print("\n" + "=" * 78)
    print("0) 真値の自己検算 —— 閉形式 vs 総当たり")
    print("=" * 78)
    rng = np.random.default_rng(SEED)
    p1 = rng.uniform(-1, 1, (200, 3)); q1 = rng.uniform(-1, 1, (200, 3))
    p2 = rng.uniform(-1, 1, (200, 3)); q2 = rng.uniform(-1, 1, (200, 3))
    d, _, _ = seg_seg_distance(p1, q1, p2, q2)
    s = np.linspace(0, 1, 400)
    brute = np.array([np.min(np.linalg.norm(
        (p1[i] + s[:, None] * (q1[i] - p1[i]))[:, None, :]
        - (p2[i] + s[:, None] * (q2[i] - p2[i]))[None, :, :], axis=-1))
        for i in range(200)])
    err = float(np.max(np.abs(d - brute)))
    print("  線分どうし: 閉形式 vs 400x400 総当たり  最大差 %.2e m" % err)
    assert err < 2e-3, err

    # 線分-直方体: 三分探索 vs 密なサンプル
    a = rng.uniform(-1.5, 1.5, (60, 3)); b = rng.uniform(-1.5, 1.5, (60, 3))
    dv, _ = seg_box_distance(a, b, (0, 0, 0), (0.4, 0.3, 0.5))
    ss = np.linspace(0, 1, 4001)
    pts = a[:, None, :] + ss[None, :, None] * (b - a)[:, None, :]
    dense = np.asarray(_L.box_sdf(pts, (0, 0, 0), (0.4, 0.3, 0.5))).min(axis=1)
    err2 = float(np.max(np.abs(dv - dense)))
    print("  線分-直方体: 三分探索 48 回 vs 4001 点  最大差 %.2e m"
          "(粗いのは総当たり側 —— 三分探索は必ず等しいか小さい)" % err2)
    assert err2 < 2e-3, err2
    assert float(np.max(dv - dense)) < 1e-7, float(np.max(dv - dense))

    # 表面サンプルの面積 = 解析値(カプセルの表面積 2πrL + 4πr²)
    a0, b0, r0 = np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 0.6]), 0.12
    grid, _ext = _L.grid_coords.raw(((-0.3, 0.3), (-0.3, 0.3), (-0.3, 0.9)), (60, 60, 120))
    occ = np.asarray(_L.sdf_to_occupancy(_L.capsule_sdf(grid, a0, b0, r0)))
    vtx, fac, _nn = _L.voxel_to_mesh.raw(occ)
    vox = np.array([0.6 / 60, 0.6 / 60, 1.2 / 120])
    area_mesh = float(np.sum(_L.face_areas((vtx * vox, fac))))
    area_true = 2 * np.pi * r0 * 0.6 + 4 * np.pi * r0 ** 2
    print("  カプセル表面積: marching cubes %.4f m² / 解析 %.4f m²  (%+.1f %%)"
          % (area_mesh, area_true, 100 * (area_mesh - area_true) / area_true))
    assert abs(area_mesh - area_true) / area_true < 0.10


# --------------------------------------------------------------------------- #
# 1-3. ゼロ点と遮蔽 —— 時系列で数える                                            #
# --------------------------------------------------------------------------- #
def _reach_bias_prediction(y_h=0.22) -> float:
    """★予想: 重心 1 点は「腕の伸び + 体の厚み - 被せた半径」ぶん過大評価する。"""
    human = human_pose(REACH_T1, y_h)          # 伸ばしきった姿勢
    P, _N, _K, _a = human_surface(human, 2000)
    c = P.mean(axis=0)
    tip = human[4][2]                          # 右手の指先
    reach = float(np.linalg.norm(tip - c)) + R_HAND
    return reach - BODY_RADIUS


def section_timeseries() -> dict:
    print("\n" + "=" * 78)
    print("1-3) ゼロ点(1 点で代表)と、見えている部位だけで測ること")
    print("=" * 78)
    rng = np.random.default_rng(SEED)
    pred = _reach_bias_prediction()
    print("  ★予想: 重心 1 点の過大評価 = 腕の伸び + 体の厚み - 被せた半径"
          " = %+.3f m" % pred)

    ts = np.arange(0.0, T_END + 1e-9, DT)
    frames = [frame(t, 0.22, REACH_T0, rng) for t in ts]
    d_true = np.array([f["d_true"] for f in frames])
    S = required_separation()

    est = {"重心 1 点": [], "足元 1 点": [], "全表面(遮蔽なし)": [],
           "頭上 1 台": [], "頭上 + 隅 2 台": []}
    hidden_nearest = 0
    n_haz = 0
    for f in frames:
        allv = np.ones(len(f["P"]), bool)
        est["重心 1 点"].append(estimate_centroid(f, allv, rng, "centroid"))
        est["足元 1 点"].append(estimate_centroid(f, allv, rng, "feet"))
        est["全表面(遮蔽なし)"].append(estimate(f, allv, rng))
        est["頭上 1 台"].append(estimate(f, f["v_top"], rng))
        est["頭上 + 隅 2 台"].append(estimate(f, f["v_top"] | f["v_cor"], rng))
        if f["d_true"] < S:
            n_haz += 1
            k = int(np.argmin(f["per_part"]))          # いちばん近い部位
            if not np.any(f["v_top"][f["K"] == k]):
                hidden_nearest += 1
    for k in est:
        est[k] = np.array(est[k])

    haz = d_true < S
    rows = []
    print("\n  必要分離距離 S = %.3f m(Z_d = %.3f m)。危険フレーム %d / %d"
          % (S, ZD_BASE, int(haz.sum()), len(ts)))
    print("  推定器                過大評価 平均 / 最大 [m]   見落とし        誤検知")
    for name in ("重心 1 点", "足元 1 点", "全表面(遮蔽なし)", "頭上 1 台",
                 "頭上 + 隅 2 台"):
        e = est[name] - d_true
        miss = int(np.count_nonzero(haz & (est[name] >= S)))
        fa = int(np.count_nonzero(~haz & (est[name] < S)))
        rows.append([name, "%+.3f" % e.mean(), "%+.3f" % e.max(),
                     "%d/%d (%.1f %%)" % (miss, haz.sum(), 100 * miss / max(1, haz.sum())),
                     "%d/%d" % (fa, int((~haz).sum()))])
        print("   %-18s  %+7.3f / %+7.3f      %-16s %s"
              % (name, e.mean(), e.max(), rows[-1][3], rows[-1][4]))
    print("\n  ★危険フレームのうち **%d / %d (%.1f %%)** で、いちばん近い部位が"
          " 頭上センサから 1 点も見えていない。"
          % (hidden_nearest, n_haz, 100 * hidden_nearest / max(1, n_haz)))
    print("     遮蔽は雑音と違って**片側にしか出ない** —— 見えない点は必ず"
          "「もっと遠い」と報告される。")

    figs.save_table("conditions", ["推定器", "過大評価 平均 m", "最大 m",
                                   "見落とし", "誤検知"], rows,
                    title="人をどう代表するかで、危険の見え方が変わる",
                    caption="S = %.3f m。見落とし = 真の距離 < S なのに推定 >= S。" % S)
    figs.save_plot("frames_clearance",
                   [("真の最小分離距離", ts, d_true),
                    ("重心 1 点(ゼロ点)", ts, est["重心 1 点"]),
                    ("頭上 1 台(遮蔽あり)", ts, est["頭上 1 台"]),
                    ("必要分離距離 S", ts, np.full_like(ts, S))],
                   xlabel="時刻 [s]", ylabel="分離距離 [m]",
                   title="人が近づき手を伸ばす 6 秒間",
                   caption="重心 1 点は手の伸びをまるごと見落とす。"
                           "S を下回るのは真値だけ、という時間帯が見落とし。")
    return {"ts": ts, "frames": frames, "d_true": d_true, "est": est,
            "S": S, "haz": haz, "pred": pred,
            "hidden_nearest": (hidden_nearest, n_haz)}


# --------------------------------------------------------------------------- #
# 4. 崖 —— 点密度・遮蔽・更新間隔を掃引し、見落としと誤検知を分けて数える         #
# --------------------------------------------------------------------------- #
TRIALS = ((0.22, 1.8, 0.25), (0.00, 2.4, 0.22), (-0.18, 1.4, 0.28), (0.35, 3.0, 0.24))


def _rates(d_true, est, S):
    haz = d_true < S
    miss = np.count_nonzero(haz & (est >= S))
    fa = np.count_nonzero(~haz & (est < S))
    return (100.0 * miss / max(1, haz.sum()), 100.0 * fa / max(1, (~haz).sum()),
            int(haz.sum()), int((~haz).sum()))


def section_sweep() -> dict:
    print("\n" + "=" * 78)
    print("4) 崖 —— 点密度・遮蔽・更新間隔。見落としと誤検知は 1 つの数字に畳まない")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 1)
    ts = np.arange(0.0, T_END + 1e-9, DT)
    S = required_separation()

    frames, dt_list = [], []
    for (y_h, t0, v) in TRIALS:
        for t in ts:
            h = human_pose(t, y_h, t0, v)
            m = machine_pose(t)
            dtr, _p, _a, _b, per = true_clearance(h, m)
            P, N, K, _ar = human_surface(h, N_SURF)
            vt = visible_from(P, N, SENSOR_TOP, h, m)
            vc = visible_from(P, N, SENSOR_COR, h, m)
            frames.append({"t": t, "human": h, "mach": m, "d_true": dtr,
                           "per_part": per, "P": P, "N": N, "K": K,
                           "v_top": vt, "v_cor": vc})
            dt_list.append(dtr)
    d_true = np.array(dt_list)
    print("  試行 %d 本 x %d フレーム = %d フレーム(危険 %d)"
          % (len(TRIALS), len(ts), len(frames), int((d_true < S).sum())))

    # --- (i) 点密度 ------------------------------------------------------- #
    dens = (1600, 800, 400, 200, 100)
    print("\n  (i) 点密度(頭上 1 台)")
    print("      点数   標本間隔 [m]  予想の過大評価 [m]  実測 [m]  見落とし   誤検知")
    d_rows, d_miss, d_fa, d_bias = [], [], [], []
    for n in dens:
        e = np.array([estimate(f, f["v_top"], rng, density=n) for f in frames])
        e = np.where(np.isfinite(e), e, 10.0)
        m_, fa_, _nh, _nf = _rates(d_true, e, S)
        area = 1.75                                   # 全身の表面積 [m²](実測は下で印字)
        spacing = np.sqrt(area / n)
        predicted = (0.5 * spacing) ** 2 / (2 * R_HAND)
        bias = float(np.mean(e - d_true))
        d_rows.append([str(n), "%.3f" % spacing, "%.3f" % predicted, "%+.3f" % bias,
                       "%.1f %%" % m_, "%.1f %%" % fa_])
        d_miss.append(m_); d_fa.append(fa_); d_bias.append(bias)
        print("     %5d      %.3f         %.3f          %+.3f    %5.1f %%   %5.1f %%"
              % (n, spacing, predicted, bias, m_, fa_))

    # --- (ii) 遮蔽 --------------------------------------------------------- #
    print("\n  (ii) 遮蔽(点密度 800 で固定)")
    occ_rows, occ_miss, occ_fa = [], [], []
    conds = [("(a) 遮蔽なし", lambda f: np.ones(len(f["P"]), bool)),
             ("(b) 頭上 + 隅 2 台", lambda f: f["v_top"] | f["v_cor"]),
             ("(c) 頭上 1 台", lambda f: f["v_top"]),
             ("(c') 頭上 1 台 + 疎(100 点)", lambda f: f["v_top"])]
    for i, (name, sel) in enumerate(conds):
        dd = 100 if i == 3 else 800
        e = np.array([estimate(f, sel(f), rng, density=dd) for f in frames])
        e = np.where(np.isfinite(e), e, 10.0)
        m_, fa_, _a, _b = _rates(d_true, e, S)
        seen = float(np.mean([sel(f).mean() for f in frames]))
        bias = float(np.mean(e - d_true))
        occ_rows.append([name, "%.1f %%" % (100 * seen), "%+.3f" % bias,
                         "%+.3f" % float(np.max(e - d_true)),
                         "%.1f %%" % m_, "%.1f %%" % fa_])
        occ_miss.append(m_); occ_fa.append(fa_)
        print("     %-24s 見えた面 %5.1f %%  過大評価 平均 %+.3f / 最大 %+.3f m"
              "  見落とし %5.1f %%  誤検知 %4.1f %%"
              % (name, 100 * seen, bias, float(np.max(e - d_true)), m_, fa_))

    # 「いちばん近い部位が 1 点も見えない」割合(条件ごと)
    for name, sel in conds[:3]:
        hid = 0; nh = 0
        for f in frames:
            if f["d_true"] < S:
                nh += 1
                k = int(np.argmin(f["per_part"]))
                if not np.any(sel(f)[f["K"] == k]):
                    hid += 1
        print("     %-24s 危険時に最近傍部位が全く見えない: %d / %d (%.1f %%)"
              % (name, hid, nh, 100 * hid / max(1, nh)))

    # --- (iii) 更新間隔 ---------------------------------------------------- #
    print("\n  (iii) 更新間隔(頭上 1 台、点密度 800。古い推定を保持する)")
    e_full = np.array([estimate(f, f["v_top"], rng, density=800) for f in frames])
    e_full = np.where(np.isfinite(e_full), e_full, 10.0)
    nT = len(ts)
    lat_rows, lat_miss, lat_fa, lat_x = [], [], [], []
    for step in (1, 2, 4):
        held = e_full.copy()
        for tr in range(len(TRIALS)):
            seg = held[tr * nT:(tr + 1) * nT]
            for i in range(nT):
                seg[i] = seg[(i // step) * step]
        m_, fa_, _a, _b = _rates(d_true, held, S)
        pred = V_WALK * DT * step
        lat_rows.append(["%.2f" % (DT * step), "%.3f" % pred,
                         "%+.3f" % float(np.mean(held - d_true)),
                         "%.1f %%" % m_, "%.1f %%" % fa_])
        lat_miss.append(m_); lat_fa.append(fa_); lat_x.append(DT * step)
        print("     間隔 %.2f s  予想の遅れ %.3f m  実測の過大評価 %+.3f m"
              "  見落とし %5.1f %%  誤検知 %4.1f %%"
              % (DT * step, pred, float(np.mean(held - d_true)), m_, fa_))

    figs.save_plot("sweep_density",
                   [("見落とし率", list(dens), d_miss),
                    ("誤検知率", list(dens), d_fa)],
                   xlabel="測定点の数 [点/全身]", ylabel="率 [%]",
                   title="点密度を 16 倍疎にしても崖は来ない",
                   caption="見落としと誤検知を分けて数える。畳むと片側の壊れ方が消える。")
    figs.save_plot("sweep_latency",
                   [("見落とし率", lat_x, lat_miss), ("誤検知率", lat_x, lat_fa)],
                   xlabel="更新間隔 [s]", ylabel="率 [%]",
                   title="更新間隔は接近速度ぶんだけ効く(v_h·Δt)")
    figs.save_table("sweep_occlusion",
                    ["条件", "見えた面", "過大評価 平均 m", "最大 m",
                     "見落とし", "誤検知"], occ_rows,
                    title="崖は遮蔽にある(点密度でも更新間隔でもない)")
    return {"dens": dens, "d_miss": d_miss, "d_bias": d_bias,
            "occ_rows": occ_rows, "occ_miss": occ_miss, "lat_miss": lat_miss,
            "frames": frames, "d_true": d_true, "S": S, "e_full": e_full}


# --------------------------------------------------------------------------- #
# 5. 見落としの地図 —— 手先をどこに置くと危険が消えるか                          #
# --------------------------------------------------------------------------- #
def section_miss_map(t_ref: float = 4.6) -> dict:
    print("\n" + "=" * 78)
    print("5) 見落としの地図 —— 手先の位置ごとに「危険なのに安全と出る」領域")
    print("=" * 78)
    human = human_pose(t_ref, 0.22, REACH_T0)
    mach = machine_pose(t_ref)
    body = [h for h in human if h[0] not in ("右手", "右前腕")]
    S = required_separation()

    nx, ny = 68, 60
    xs = np.linspace(-0.20, 2.20, nx)
    ys = np.linspace(-1.10, 1.10, ny)
    z_h = float(human[4][2][2])                      # 指先の高さ
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    hand_c = np.stack([XX, YY, np.full_like(XX, z_h)], axis=-1).reshape(-1, 3)

    # 胴などの「本体」の推定(手の位置によらない)
    Pb, Nb, Kb, _ar = human_surface(body, 900)
    vb = visible_from(Pb, Nb, SENSOR_TOP, body, mach)
    d_body_est = float(np.min(hazard_sdf(Pb[vb], mach))) if vb.any() else np.inf
    d_body_true = float(np.min(hazard_sdf(Pb, mach)))

    # 手をそこへ置いたときの真値と、見える点だけの推定
    sph = capsule_surface([0, 0, 0], [0, 0, 0], R_HAND, 16)[0]      # 球のサンプル
    nsph = sph / R_HAND
    d_hand_true = np.empty(len(hand_c))
    d_hand_est = np.empty(len(hand_c))
    vis_frac = np.empty(len(hand_c))
    for i, c in enumerate(hand_c):
        pts = sph + c
        dt_ = float(np.min(hazard_sdf(pts, mach)))
        d_hand_true[i] = dt_
        v = visible_from(pts, nsph, SENSOR_TOP, body, mach, k_ray=5)
        vis_frac[i] = v.mean()
        d_hand_est[i] = float(np.min(hazard_sdf(pts[v], mach))) if v.any() else np.inf

    true_map = np.minimum(d_hand_true, d_body_true).reshape(nx, ny)
    est_map = np.minimum(np.where(np.isfinite(d_hand_est), d_hand_est, np.inf),
                         d_body_est).reshape(nx, ny)
    over = est_map - true_map
    miss = (true_map < S) & (est_map >= S)
    vis_map = vis_frac.reshape(nx, ny)

    cell = (xs[1] - xs[0]) * (ys[1] - ys[0])
    print("  基準時刻 %.2f s、指先の高さ %.2f m、格子 %d x %d(%.0f mm 刻み)"
          % (t_ref, z_h, nx, ny, 1000 * (xs[1] - xs[0])))
    print("  手が 1 点も見えない面積: %.3f m²(全体の %.1f %%)"
          % (cell * np.count_nonzero(vis_map == 0.0),
             100 * np.mean(vis_map == 0.0)))
    print("  危険(真値 < S)な面積 %.3f m² のうち、**安全と出る**面積 %.3f m²"
          " = %.1f %%"
          % (cell * np.count_nonzero(true_map < S), cell * np.count_nonzero(miss),
             100 * np.count_nonzero(miss) / max(1, np.count_nonzero(true_map < S))))
    print("  過大評価の最大 %.3f m(手が完全に隠れて、推定が胴へ飛んだところ)"
          % float(np.max(over[np.isfinite(over)])))

    figs.save_grid("map_miss",
                   [true_map.T, np.clip(over, 0.0, 0.6).T, miss.astype(float).T],
                   ["真の分離距離 [m](手先の位置ごと)",
                    "過大評価 [m](0〜0.6 で切った)",
                    "危険なのに安全と出る領域"],
                   ncols=3,
                   title="見落としの地図(頭上センサ 1 台、指先の高さ %.2f m の水平面)" % z_h,
                   caption="横 = x [%.1f, %.1f] m、縦 = y [%.1f, %.1f] m。"
                           "白い帯はロボットのリンクが落とす影。"
                           % (xs[0], xs[-1], ys[0], ys[-1]))
    figs.save("map_visibility", vis_map.T,
              "手の表面のうち頭上センサから見えた割合。0 の帯 = リンクと治具台の影。")
    return {"miss_area": float(cell * np.count_nonzero(miss)),
            "haz_area": float(cell * np.count_nonzero(true_map < S)),
            "over_max": float(np.max(over[np.isfinite(over)])),
            "blind": float(np.mean(vis_map == 0.0))}


# --------------------------------------------------------------------------- #
# 6. 指標の選び方 —— Chamfer は危険に盲目                                        #
# --------------------------------------------------------------------------- #
def section_metrics(sw: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) 点群の一致指標 —— Chamfer は隠れた手を薄める、Hausdorff は残す")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 2)
    ch, hd, err = [], [], []
    for f in sw["frames"][::7]:
        q, _ = observe(f["P"], f["N"], f["v_top"], rng,
                       _sensor_of(f["v_top"], f["v_cor"]), density=800)
        if len(q) < 10:
            continue
        ch.append(float(_L.chamfer_distance(np.ascontiguousarray(f["P"]), q)))
        hd.append(float(_L.hausdorff_distance(np.ascontiguousarray(f["P"]), q)))
        err.append(float(np.min(hazard_sdf(q, f["mach"]))) - f["d_true"])
    ch, hd, err = np.array(ch), np.array(hd), np.array(err)
    print("  %d フレーム: Chamfer 平均 %.4f m / Hausdorff 平均 %.4f m"
          % (len(ch), ch.mean(), hd.mean()))
    print("  分離距離の過大評価との相関: Chamfer r = %.3f / Hausdorff r = %.3f"
          % (float(np.corrcoef(ch, err)[0, 1]), float(np.corrcoef(hd, err)[0, 1])))
    print("  ★平均で丸める指標は「見えている大半が合っている」を報告してしまう。")
    figs.save_plot("metric_blindness",
                   [("Chamfer(平均)", np.arange(len(ch)) * 7 * DT, ch),
                    ("Hausdorff(最悪)", np.arange(len(hd)) * 7 * DT, hd),
                    ("分離距離の過大評価", np.arange(len(err)) * 7 * DT, err)],
                   xlabel="通し時刻 [s](4 試行を連結)", ylabel="距離 [m]",
                   title="平均の指標は安全の最悪値を隠す")
    return {"ch": float(ch.mean()), "hd": float(hd.mean()),
            "r_ch": float(np.corrcoef(ch, err)[0, 1]),
            "r_hd": float(np.corrcoef(hd, err)[0, 1])}


# --------------------------------------------------------------------------- #
# 7. 格子で測ると距離が刻まれる(esdf + query_distance)                          #
# --------------------------------------------------------------------------- #
def section_grid_bias(sw: dict) -> dict:
    print("\n" + "=" * 78)
    print("7) 機械を占有格子にして距離を引くと、半ボクセルの偏りが乗る")
    print("=" * 78)
    bounds = ((-0.9, 1.9), (-1.0, 1.0), (0.0, 2.0))
    span = np.array([2.8, 2.0, 2.0])
    mach = machine_pose(2.0)
    rng = np.random.default_rng(SEED + 3)
    Q = rng.uniform([0.4, -0.6, 0.6], [1.6, 0.6, 1.6], (4000, 3))
    exact = hazard_sdf(Q, mach)
    keep = exact > 0.02
    Q, exact = Q[keep], exact[keep]

    rows, xs, bias = [], [], []
    for vox in (0.04, 0.02, 0.01):
        res = np.round(span / vox).astype(int)
        grid, _e = _L.grid_coords.raw(bounds, res)
        occ = np.asarray(_L.sdf_to_occupancy(hazard_sdf(grid, mach)))
        E = np.asarray(_L.esdf(occ, [vox, vox, vox]))
        d = np.asarray(_L.query_distance(E, bounds, res, Q))
        b = float(np.mean(d - exact))
        rows.append(["%.0f" % (1000 * vox), "x".join(map(str, res)),
                     "%.4f" % (vox / 2), "%+.4f" % b,
                     "%.4f" % float(np.std(d - exact))])
        xs.append(1000 * vox); bias.append(b)
        print("  ボクセル %2.0f mm  格子 %-14s  予想 +%.4f m  実測 %+.4f m"
              "  (ばらつき %.4f m)"
              % (1000 * vox, "x".join(map(str, res)), vox / 2, b,
                 float(np.std(d - exact))))
    print("  ★これは雑音ではなく**既知の系統誤差**なので、Z_d に足すのではなく"
          "\n     格子から引いた距離そのものを補正すべき量。")
    figs.save_table("grid_bias", ["ボクセル mm", "格子", "予想 m", "実測 m", "ばらつき m"],
                    rows, title="占有格子 + ESDF は距離を半ボクセルだけ遠く言う")
    return {"xs": xs, "bias": bias}


# --------------------------------------------------------------------------- #
# 8. Z_d を測定から見積もる —— 繰り返し性では足りない                            #
# --------------------------------------------------------------------------- #
def section_zd(sw: dict) -> dict:
    print("\n" + "=" * 78)
    print("8) 不確かさ Z_d を測定から見積もると何が起きるか")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 4)
    f0 = sw["frames"][len(sw["frames"]) // 2]
    reps = np.array([estimate(f0, f0["v_top"], rng, density=800) for _ in range(24)])
    zd_rep = 3.0 * float(np.std(reps))
    print("  同じ姿勢を 24 回測り直したばらつき: σ = %.4f m -> Z_d(3σ) = %.4f m"
          % (float(np.std(reps)), zd_rep))

    over = sw["e_full"] - sw["d_true"]
    zd_occ = float(np.percentile(over, 95))
    zd_max = float(np.max(over))
    print("  ところが遮蔽による過大評価: 95 %% 点 %.4f m / 最大 %.4f m"
          "  —— 繰り返し性の **%.0f 倍**" % (zd_occ, zd_max, zd_occ / max(zd_rep, 1e-9)))

    rows, zs, miss_r, stop_r = [], [], [], []
    for name, zd in (("繰り返し性 3σ", zd_rep), ("既定値 0.030", ZD_BASE),
                     ("遮蔽の 95 % 点", zd_occ), ("遮蔽の最大", zd_max)):
        S = required_separation(zd)
        m_, fa_, nh, nf = _rates(sw["d_true"], sw["e_full"], S)
        stop = 100.0 * np.count_nonzero(sw["e_full"] < S) / len(sw["e_full"])
        rows.append([name, "%.3f" % zd, "%.3f" % S, "%.1f %%" % m_,
                     "%.1f %%" % fa_, "%.1f %%" % stop])
        zs.append(zd); miss_r.append(m_); stop_r.append(stop)
        print("   Z_d = %.3f (%-14s) -> S = %.3f m  見落とし %5.1f %%"
              "  誤検知 %5.1f %%  停止時間 %5.1f %%"
              % (zd, name, S, m_, fa_, stop))
    print("\n  ★安全の代金は稼働率で払う: 見落としを 0 にする Z_d = %.3f m で、"
          "\n     機械が止まっている時間は %.1f %% -> %.1f %% に増える。"
          % (zd_max, stop_r[1], stop_r[-1]))
    figs.save_table("zd_budget", ["Z_d の出どころ", "Z_d m", "S m", "見落とし",
                                  "誤検知", "停止時間"], rows,
                    title="不確かさをどこから取るかで、安全と稼働率の配分が決まる")
    figs.save_plot("zd_tradeoff",
                   [("見落とし率", zs, miss_r), ("停止時間の割合", zs, stop_r)],
                   xlabel="Z_d [m]", ylabel="率 [%]",
                   title="Z_d を上げれば危険は消えるが、機械も止まる")
    return {"zd_rep": zd_rep, "zd_occ": zd_occ, "zd_max": zd_max,
            "stop": stop_r, "miss": miss_r}


# --------------------------------------------------------------------------- #
# 9. 場面の図(3-D らしく: 投影・断面・注記)                                     #
# --------------------------------------------------------------------------- #
def section_scene_figures() -> None:
    if not figs.enabled():
        return
    print("\n" + "=" * 78)
    print("9) 場面の図(投影・断面・注記)")
    print("=" * 78)
    bounds = ((-0.9, 3.1), (-1.2, 1.2), (0.0, 2.2))
    res = (140, 84, 77)
    grid, _e = _L.grid_coords.raw(bounds, res)

    panels, caps = [], []
    for t in (1.5, 4.6):
        human = human_pose(t, 0.22, REACH_T0)
        mach = machine_pose(t)
        d_h = None
        for (_n, a, b, r) in human:
            v = _L.capsule_sdf(grid, a, b, r)
            d_h = v if d_h is None else _L.sdf_union(d_h, v)
        d_m = hazard_sdf(grid, mach)
        d_m = np.asarray(_L.sdf_union(d_m, _L.box_sdf(grid, TABLE_C, TABLE_H)))
        occ = (np.asarray(_L.sdf_to_occupancy(d_h)) * 1.0
               + np.asarray(_L.sdf_to_occupancy(d_m)) * 0.45)
        # ★ボリューム op は (depth,row,col)。grid_coords は (nx,ny,nz) なので転置する。
        vol = occ.transpose(2, 1, 0)[::-1]
        panels.append(np.asarray(_L.render_volume_projection(vol, 0.0, 0.0, "mip")))
        caps.append("側面図 t=%.1f s(真の分離 %.3f m)"
                    % (t, true_clearance(human, mach)[0]))
        panels.append(np.asarray(_L.render_volume_projection(vol, 0.0, 90.0, "mip")))
        caps.append("上から見た図 t=%.1f s" % t)
    figs.save_grid("scene", panels, caps, ncols=2,
                   title="協働ロボットのセル(人 = 明、機械と治具台 = 暗)",
                   caption="人は 9 本のカプセル、機械は 2 本のリンク + 基台。"
                           "占有格子の最大値投影。")

    # 距離場の断面(指先の高さの水平面)
    t = 4.6
    human = human_pose(t, 0.22, REACH_T0)
    mach = machine_pose(t)
    z_h = float(human[4][2][2])
    xs = np.linspace(-0.9, 2.6, 220)
    ys = np.linspace(-1.1, 1.1, 140)
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    P = np.stack([XX, YY, np.full_like(XX, z_h)], axis=-1)
    dm = hazard_sdf(P, mach)
    S = required_separation()
    band = np.clip(dm, 0.0, 1.6)
    band[np.abs(dm - S) < 0.02] = 0.0          # S の等高線を黒く抜く
    figs.save("map_distance_slice", band.T,
              "危険源までの距離場を指先の高さ %.2f m で切った断面 [m]。"
              "黒い輪 = 必要分離距離 S = %.3f m の等高線。" % (z_h, S))

    # 3-D 描画 + 最短距離の注記
    try:
        b2 = ((-0.9, 3.1), (-1.2, 1.2), (0.0, 2.2))
        r2 = (168, 100, 92)
        g2, _e2 = _L.grid_coords.raw(b2, r2)
        lo = np.array([b2[0][0], b2[1][0], b2[2][0]])
        span = np.array([b2[0][1] - b2[0][0], b2[1][1] - b2[1][0], b2[2][1] - b2[2][0]])
        d_h = None
        for (_n, a, b, r) in human:
            v = _L.capsule_sdf(g2, a, b, r)
            d_h = v if d_h is None else _L.sdf_union(d_h, v)
        d_m = hazard_sdf(g2, mach)
        d_m = np.asarray(_L.sdf_union(d_m, _L.box_sdf(g2, TABLE_C, TABLE_H)))
        pose = fs.look_at((4.2, -3.4, 2.5), (1.0, 0.0, 1.1))
        K = fs.intrinsics_from_fov(42.0, 560, 400)
        imgs, depths = [], []
        for fld in (d_h, d_m):
            occ = np.asarray(_L.sdf_to_occupancy(fld))
            V, F, _n = _L.voxel_to_mesh.raw(occ)
            V = lo + (V + 0.5) / np.asarray(r2) * span
            out = fs.render_mesh(V, F, pose=pose, intrinsics=K, width=560, height=400)
            imgs.append(np.asarray(out["normals"]))
            depths.append(np.asarray(out["depth"]))
        near = depths[0] <= depths[1]
        shade = np.where(near[..., None], imgs[0], imgs[1])
        shade = np.abs(shade[..., 2])
        tint = np.zeros(shade.shape + (3,))
        tint[near] = np.stack([shade, shade * 0.75, shade * 0.55], -1)[near]
        tint[~near] = np.stack([shade * 0.45, shade * 0.62, shade * 0.85], -1)[~near]
        depth = np.minimum(depths[0], depths[1])
        d0, part, pa, pb, _pp = true_clearance(human, mach)
        img = np.asarray(fs.annotate3d_measure(np.clip(tint, 0, 1), pa, pb, pose, K,
                                               unit=" m", depth=depth,
                                               label_fmt="{:.3f}"))
        img = np.asarray(fs.annotate3d_label(img, "最も近い部位: " + part,
                                             pa, pose, K, depth=depth))
        figs.save("scene_closest", img,
                  "最短分離 %.3f m を結ぶ線(最も近い部位 = %s)。"
                  "人 = 暖色、機械と治具台 = 寒色。" % (d0, part))
    except Exception as exc:                    # noqa: BLE001
        print("  3-D 描画は諦めた: %s: %s" % (type(exc).__name__, exc))


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)
    # (a) 線分どうしの最短距離が無い。distance_line_line は**無限直線**。
    p1 = np.array([0.0, 0.0, 0.0]); q1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([5.0, 0.5, 0.0]); q2 = np.array([6.0, 0.5, 0.0])
    inf_line = float(_L.distance_line_line(p1, q1 - p1, p2, q2 - p2))
    seg, _c1, _c2 = seg_seg_distance(p1, q1, p2, q2)
    print("  (a) 線分どうしの最短距離が公開経路に無い。`distance_line_line` は"
          "**無限直線**なので\n      同じ 2 本で %.3f m と答える(線分の真値は %.3f m)。"
          "腕やリンクは有限なので\n      そのまま使うと分離距離を %.1f %% 過小評価する。"
          % (inf_line, float(seg), 100 * (1 - inf_line / float(seg))))
    assert inf_line < float(seg)

    # (b) 線分/カプセルと直方体の距離も無い(凸 1 次元最小化を自前で書いた)
    assert not hasattr(fs.ledger, "segment_box_distance")
    print("  (b) 線分-直方体(掃引体積 vs AABB)の距離も無い。`box_sdf` は点でしか"
          "\n      引けないので、線分上の凸 1 次元最小化を呼び手が書く。")

    # (c) SDF から「最近点」が返らない
    assert not hasattr(fs.ledger, "sdf_closest_point")
    print("  (c) SDF は値しか返さない。**最近点**(どこが近いか)が無いので、"
          "\n      `annotate3d_measure` に渡す 2 端点は呼び手が別途持つ必要がある。")

    # (d) 視線の遮蔽判定(ray marching)が無い
    assert not hasattr(fs.ledger, "sdf_raymarch") and not hasattr(fs, "sdf_raymarch")
    print("  (d) SDF の ray marching / 可視判定が無い。`annotate3d_project` は"
          "\n      深度画像があれば遮蔽を判定するが、**点群を作る前**の"
          "「その表面点は\n      センサから見えるか」は自前(この PoC は視線を刻んで"
          "SDF を評価した)。")

    # (e) render_volume_projection は正射影、annotate3d_* は透視投影
    print("  (e) `render_volume_projection` は軸投影(正射影)で pose/K を取らない。"
          "\n      `annotate3d_*` は (pose, K) の透視投影なので、**同じ図に重ねられない**。"
          "\n      重ねるには mesh 化して `render_mesh` を通す必要がある。")

    # (f) ゼロ点になる「1 点代表」も、SSM の式も公開経路に無い
    assert not hasattr(fs.ledger, "speed_and_separation")
    print("  (f) ISO/TS 15066 の必要分離距離 S の式が無い。安全の文脈で距離 op を"
          "\n      使うなら、判定の式まで含めて族にする価値はある。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("人と機械の安全距離 —— 「近い」を測る点をどこに置くかで危険が消える")
    print("人 = 9 カプセルの多関節 / 機械 = 2 リンク + 基台 / センサ 2 台")
    print("=" * 78)

    section_selfcheck()
    ts = section_timeseries()
    sw = section_sweep()
    mm = section_miss_map()
    me = section_metrics(sw)
    gb = section_grid_bias(sw)
    zd = section_zd(sw)
    section_scene_figures()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    e0 = ts["est"]["重心 1 点"] - ts["d_true"]
    print("  * 重心 1 点は %+.3f m 過大評価する(予想 %+.3f m)。危険の %.1f %% を"
          "見落とし、誤検知は 0。"
          % (e0.mean(), ts["pred"],
             100 * np.count_nonzero(ts["haz"] & (ts["est"]["重心 1 点"] >= ts["S"]))
             / max(1, int(ts["haz"].sum()))))
    print("  * 崖は遮蔽にある: 見えている部位だけで測ると、危険時の %.1f %% で"
          "最近傍部位が 1 点も見えない。"
          % (100 * ts["hidden_nearest"][0] / max(1, ts["hidden_nearest"][1])))
    print("  * Z_d を繰り返し性から出すと %.4f m。遮蔽の 95 %% 点は %.4f m で"
          "**%.0f 倍**足りない。" % (zd["zd_rep"], zd["zd_occ"],
                                     zd["zd_occ"] / max(zd["zd_rep"], 1e-9)))
    print("  * 見落としを 0 にすると停止時間は %.1f %% -> %.1f %%。"
          % (zd["stop"][1], zd["stop"][-1]))

    # 所見を固定する assert(壊れたら鳴る)
    assert e0.mean() > 0.25, e0.mean()
    assert np.count_nonzero(ts["haz"] & (ts["est"]["重心 1 点"] >= ts["S"])) > 0
    assert np.count_nonzero(ts["haz"] & (ts["est"]["全表面(遮蔽なし)"] >= ts["S"])) == 0
    assert zd["zd_occ"] > 8.0 * zd["zd_rep"], (zd["zd_occ"], zd["zd_rep"])
    assert me["hd"] > 5.0 * me["ch"], (me["hd"], me["ch"])
    for b, v in zip(gb["bias"], (0.020, 0.010, 0.005)):
        assert 0.3 * v < b < 2.2 * v, (b, v)
    assert mm["over_max"] > 0.15, mm["over_max"]

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
