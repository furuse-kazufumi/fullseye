# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 映像の物理整合性検査 —— 壁を上って跳ぶ車の映像は弾道か推力か、時間は引き延ばされていないか

壁を駆け上がって宙を飛ぶ車の映像が話題になった(ほぼロケットに見えた)。映像だけから言えることは何か。
この PoC は **学習なし・単位つき** で 2 つの問いに答える:

1. **弾道か推力か**: 単眼の映像から車の箱(bbox)を追い、既知の車長で尺度を入れて平面 (x, z) の軌跡にし、
   「重力 + 抗力」と「重力 + 抗力 + 一定の比推力」の 2 つの運動方程式を当てて **AIC の差**で選ぶ
   (:func:`ballistics.ballistic_vs_thrust`。op は判定を返さず ΔAIC を返し、「決定的」の慣用 10 はこの PoC が決める)。返るのは ΔAIC と **推力の大きさ [m/s²]** と抗力係数。
2. **時間は改変されていないか**: 時刻を k 倍に引き延ばした映像では重力加速度が g/k² に見えるので、当てはめた g から
   k を閉形式で逆算する(:func:`ballistics.time_stretch_from_gravity`)。白黒の判定はせず、清浄な映像の帰無分布の
   **どのあたりに座るか**で返す(:func:`imgforensics.null_distribution` / :func:`imgforensics.evidence_quantile`)。

門(真値の出どころ: 世界は合成で、軌跡の式・推力・倍率は生成時に決めた値):
  1. **恒等式**: 推力つきの RK4 は真空で閉形式 p₀ + v₀ t + ½ (a_T − g ẑ) t² と 1e-9、推力 0 なら既存の飛翔と 1e-12 で一致。
  2. **同定は真値に戻る**: 真値の軌跡(雑音なし)から推力は 1e-4 m/s²、C_d は 1e-3 で戻る。推力 0 の軌跡では推力は 1e-4 以下。
  3. **映像から軌跡**: 960 × 540・30 fps の単眼カメラで車の箱を写し、bbox(:func:`drivettc.label_extent`)と既知の車長から
     起こした位置は真値と中央値 10 cm 以内(誤差の正体は画素の量子化 —— 45 m 先で 1 画素 ≈ 7.5 cm)。
  4. **弾道 vs 推力**: 弾道 40 本・推力 40 本(1〜6 m/s²、発射条件は乱数)を映像から判定して正答率 ≥ 95 %、
     弾道で「推力あり」と誤る本数は 2 本以下(雑音だけの ΔAIC は −2Δk = −4 を中心に χ²(2) の幅で散り、画素の量子化は
     時間的に相関する鋸歯なので裾が少し重い —— 床 10 を超える偽陽性は 1 % 前後)、推力の ΔAIC は全部 10 以上。
     推力の大きさは中央値で 15 % 以内(C_d は推力と分け合うので決まりにくく、``cond`` に出る)。
  5. **どれだけ弱い推力まで見えるか**: 0.25〜4 m/s² を 10 本ずつ。g の 5 %(0.5 m/s²)でも 60 コマで決定的に見える。
  6. **時間の引き延ばし**: k ∈ {0.5, 0.8, 1.25, 2, 4} を 10 本ずつ。k̂ は 5 % 以内、清浄 200 本の帰無分布に対する位置は 0.99 以上。
     清浄な別の 100 本では 0.99 を超えるものが 5 % 以下(偽陽性の床)。
  7. **絵だけでは区別できないこと**(正直に): 時間を 1.5 倍に引き延ばした弾道の映像は、推力の検査には
     「上向きに g(1 − 1/k²) = 5.45 m/s² の推力」として映る —— 鉛直の一定推力と時間の引き延ばしは単眼の軌跡では縮退する。
     測った鉛直推力がその閉形式と 5 % 以内で一致することを門にし、順番(先に k、次に推力)と限界を文書にする。

正直に書くこと: 世界は合成(車は水平姿勢の箱、カメラは側面・既知の距離の平面運動、検出器は完全で誤差は画素の量子化と
0.3 画素の揺れだけ)。実写の映像は同梱しない。推力は世界座標で一定(機体固定で向きを変える推力は近似)。
抗力の前面積・質量・C_d は乗用車の代表値で、真値も同じ式で作っている。

Run: py -3.11 examples/poc_video_physics_consistency.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import ballistics as B  # noqa: E402
import drivettc as TTC  # noqa: E402
import imgforensics as IF  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
FPS = 30
T_END = 2.0
DT_FIT = 1.0 / 120.0
# 乗用車の代表値: 長さ・幅・高さ [m]、質量 [kg]、前面積 [m²]、抗力係数(真値)。
L_CAR, W_CAR, H_CAR = 4.7, 1.9, 1.4
MASS, AREA, CD_TRUE = 1900.0, 2.2, 0.30
# 単眼カメラ: 960 × 540、焦点距離 600 px(35 mm 判換算の標準レンズ相当)、側面 45 m、高さ 6 m、x = 18 m を向く。
IMG_W, IMG_H, F_PX = 960, 540, 600.0
CAM = np.array([18.0, -45.0, 6.0])
JITTER_PX = 0.3
MIN_DELTA = 10.0                     # ΔAIC の「決定的」の慣用(op は閾値を同梱しない。呼び手 = この PoC が決める)
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def car_params():
    return B.ball_params(radius=math.sqrt(AREA / math.pi), mass=MASS, cd=CD_TRUE, cl=0.0, rho=1.2)


# ───────────────────────── 世界: 発射 → 飛翔(推力あり/なし)→ カメラ ─────────────────────────
def launch(rng):
    """壁(傾斜路)の先端から飛び出す条件: 速さ 18〜24 m/s、仰角 28〜42°。"""
    sp = rng.uniform(18.0, 24.0)
    ang = math.radians(rng.uniform(28.0, 42.0))
    return np.array([0.0, 0.0, 0.8]), np.array([sp * math.cos(ang), 0.0, sp * math.sin(ang)])


def truth_track(p0, v0, thrust, bp, t):
    f = B.thrust_ode(p0, v0, thrust, bp, float(t[-1]) + 1e-3, 1e-3)
    return np.column_stack([np.interp(t, f["t"], f["p"][:, k]) for k in range(3)])


def project(points_xyz):
    """ピンホール: 画像 u = cx + f X/Y、v = cy − f Z/Y(Y はカメラからの奥行き)。"""
    d = np.asarray(points_xyz, float) - CAM
    u = IMG_W / 2.0 + F_PX * d[..., 0] / d[..., 1]
    v = IMG_H / 2.0 - F_PX * d[..., 2] / d[..., 1]
    return np.stack([u, v], axis=-1)


def box_corners(centre):
    off = np.array([[sx * L_CAR / 2, sy * W_CAR / 2, sz * H_CAR / 2] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    return np.asarray(centre) + off


def convex_hull(pts):
    pts = sorted(map(tuple, pts))
    def half(seq):
        h = []
        for q in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (q[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (q[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(q)
        return h
    lo, hi = half(pts), half(pts[::-1])
    return np.asarray(lo[:-1] + hi[:-1])


def render_label(centre, scale=1):
    """車の箱の影絵をラベル像(0/1)に描く。``scale`` < 1 で小さい絵(GIF 用)。"""
    uv = project(box_corners(centre)) * scale
    hull = convex_hull(uv)
    W, H = int(IMG_W * scale), int(IMG_H * scale)
    lab = np.zeros((H, W), np.uint8)
    c0, c1 = max(int(np.floor(uv[:, 0].min())), 0), min(int(np.ceil(uv[:, 0].max())) + 1, W)
    r0, r1 = max(int(np.floor(uv[:, 1].min())), 0), min(int(np.ceil(uv[:, 1].max())) + 1, H)
    if c1 <= c0 or r1 <= r0:
        return lab
    cc, rr = np.meshgrid(np.arange(c0, c1) + 0.5, np.arange(r0, r1) + 0.5)
    inside = np.ones(cc.shape, bool)
    n = len(hull)
    for i in range(n):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % n]
        inside &= (bx - ax) * (rr - ay) - (by - ay) * (cc - ax) >= 0
    lab[r0:r1, c0:c1] = inside
    return lab


def bbox_predicted(centre):
    """箱の中心 → 画像での bbox の 4 辺 [u_min, u_max, v_min, v_max](連続値)。"""
    uv = project(box_corners(centre))
    return np.array([uv[:, 0].min(), uv[:, 0].max(), uv[:, 1].min(), uv[:, 1].max()])


def solve_box_centre(obs, x0, free):
    """観測した bbox の 4 辺に、既知の寸法の箱の射影を Gauss–Newton で合わせる(未知数は ``free`` の座標だけ)。
    辺は角の max/min なので区分的にアフィン —— 数値ヤコビアンで 6 回も回せば十分。"""
    x = np.asarray(x0, float).copy()
    for _ in range(6):
        r = bbox_predicted(x) - obs
        J = np.empty((4, len(free)))
        for j, k in enumerate(free):
            xp = x.copy()
            xp[k] += 1e-3
            J[:, j] = (bbox_predicted(xp) - obs - r) / 1e-3
        dx = np.linalg.lstsq(J, -r, rcond=None)[0]
        x[free] += dx
        if np.abs(dx).max() < 1e-7:
            break
    return x


def track_from_video(frames_labels, rng):
    """各コマの bbox → 既知の車の寸法で奥行き → 平面 (x, z)。2 段: (1) 各コマで (x, y, z) を解いて奥行き y の**中央値**を
    その映像の奥行きにする(平面運動 = 奥行き一定の仮定。1 コマの奥行きは 1 % 揺れるが 60 コマの中央値は 0.2 %)、
    (2) 奥行きを固定して各コマの (x, z) を解く。検出器は完全(影絵そのもの)で、誤差は画素の量子化 + 0.3 px の揺れ。
    bbox の辺は画素の境界(col0 と col1 + 1)に読む —— 影絵は画素中心で塗っているので、真の辺はその ±0.5 画素の中にある。"""
    obs_list = []
    for lab in frames_labels:
        e = TTC.label_extent(lab, 1)
        if e["n"] == 0:
            obs_list.append(None)
            continue
        j = rng.normal(0.0, JITTER_PX, 4)
        obs_list.append(np.array([e["col0"], e["col1"] + 1.0, e["row0"], e["row1"] + 1.0]) + j)
    depths, guesses = [], []
    for obs in obs_list:
        if obs is None:
            guesses.append(None)
            continue
        w_px = obs[1] - obs[0]
        d0 = F_PX * L_CAR / w_px + W_CAR / 2.0
        uc, vc = 0.5 * (obs[0] + obs[1]), 0.5 * (obs[2] + obs[3])
        g = np.array([CAM[0] + (uc - IMG_W / 2.0) * d0 / F_PX, CAM[1] + d0, CAM[2] - (vc - IMG_H / 2.0) * d0 / F_PX])
        sol = solve_box_centre(obs, g, [0, 1, 2])
        depths.append(sol[1])
        guesses.append(sol)
    depth0 = float(np.median(depths))

    def solve_all(depth):
        """奥行きを固定して各コマの (x, z) を解き、bbox の残差の総和と位置を返す。"""
        xz, total = [], 0.0
        for obs, g in zip(obs_list, guesses):
            if obs is None:
                xz.append([np.nan, np.nan])
                continue
            g = g.copy()
            g[1] = depth
            sol = solve_box_centre(obs, g, [0, 2])
            total += float(np.sum((bbox_predicted(sol) - obs) ** 2))
            xz.append([sol[0], sol[2]])
        return np.asarray(xz), total

    # 奥行きは「コマごとの中央値」では 0.2 m ずれることがあり、一様な尺度誤差は両端で 10 cm の U 字誤差になって
    # 「小さな推力」に化ける(尺度 0.5 % ≈ 0.05 m/s²)。全コマの辺 4N 本の残差を 1 つの奥行きで最小にする(黄金分割)。
    lo, hi = depth0 * 0.97, depth0 * 1.03
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
    fa, fb = solve_all(a)[1], solve_all(b)[1]
    for _ in range(18):
        if fa < fb:
            hi, b, fb = b, a, fa
            a = hi - phi * (hi - lo)
            fa = solve_all(a)[1]
        else:
            lo, a, fa = a, b, fb
            b = lo + phi * (hi - lo)
            fb = solve_all(b)[1]
    depth = 0.5 * (lo + hi)
    xz, _ = solve_all(depth)
    return xz


def make_clip(rng, thrust_mag, bp, t, keep_labels=False, launch_at=None):
    p0, v0 = launch(rng) if launch_at is None else launch_at
    direction = v0 / np.linalg.norm(v0)
    thrust = thrust_mag * direction
    P = truth_track(p0, v0, thrust, bp, t)
    labels = [render_label(c) for c in P]
    xz = track_from_video(labels, rng)
    return {"p0": p0, "v0": v0, "thrust": thrust, "truth": P, "xz": xz, "labels": labels if keep_labels else None}


def draw_frame(lab, bbox, text, trail_uv=None, depth=None):
    """影絵 + bbox + 起こした位置の軌跡(点)+ 地面の線。"""
    H, W = lab.shape
    img = np.ones((H, W, 3), np.float64) * np.array([0.93, 0.95, 0.98])
    if depth is not None:                              # 地面 z = 0 を奥行き depth で写した線
        v = int(round(IMG_H / 2.0 - F_PX * (0.0 - CAM[2]) / depth))
        if 0 <= v < H:
            img[v, :, :] = (0.75, 0.78, 0.82)
    img[lab > 0] = (0.15, 0.15, 0.18)
    c0, c1, r0, r1 = bbox
    img[r0:r1 + 1, [c0, c1], :] = (0.85, 0.2, 0.1)
    img[[r0, r1], c0:c1 + 1, :] = (0.85, 0.2, 0.1)
    if trail_uv is not None:
        for u, v in trail_uv:
            ui, vi = int(round(u)), int(round(v))
            if 1 <= ui < W - 1 and 1 <= vi < H - 1:
                img[vi - 1:vi + 2, ui - 1:ui + 2, :] = (0.0, 0.45, 0.7)
    try:
        img = AN.text_box(img, text, (8, 8), color="neutral")
    except Exception:
        pass
    return img


def main() -> int:
    rng = np.random.default_rng(20261023)
    bp = car_params()
    t = np.arange(0, T_END, 1.0 / FPS)
    print("映像の物理整合性検査: %d fps × %.1f s = %d コマ、カメラ 45 m・焦点距離 %.0f px(1 画素 ≈ %.1f cm)" % (
        FPS, T_END, len(t), F_PX, 100 * 45.0 / F_PX))

    # 1. 恒等式
    print("1. 恒等式(閉形式との一致)")
    p0, v0 = launch(rng)
    vac = dict(bp, rho=0.0)
    a_T = np.array([3.0, 0.0, 2.0])
    f = B.thrust_ode(p0, v0, a_T, vac, T_END, 1e-3)
    closed = p0 + f["t"][:, None] * v0 + 0.5 * f["t"][:, None] ** 2 * (a_T - np.array([0, 0, bp["g"]]))
    e1 = float(np.abs(f["p"] - closed).max())
    e2 = float(np.abs(B.thrust_ode(p0, v0, (0, 0, 0), bp, T_END, 1e-3)["p"] - B.flight_ode(p0, v0, (0, 0, 0), bp, T_END, 1e-3)["p"]).max())
    gate("真空の推力つき RK4 = 閉形式", e1 < 1e-9, "最大差 %.1e m" % e1)
    gate("推力 0 の RK4 = 既存の飛翔(抗力つき)", e2 < 1e-12, "最大差 %.1e m" % e2)

    # 2. 同定は真値に戻る(雑音なし、平面入力)
    print("2. 同定(雑音なしの真値)")
    PT = truth_track(p0, v0, a_T, bp, t)[:, [0, 2]]
    PB = truth_track(p0, v0, (0, 0, 0), bp, t)[:, [0, 2]]
    ft = B.thrust_fit(t, PT, bp, dt=DT_FIT)
    fb = B.thrust_fit(t, PB, bp, dt=DT_FIT)
    db = B.drag_fit(t, PB, bp, dt=DT_FIT)
    et = float(np.linalg.norm(ft["thrust"] - a_T))
    gate("推力つき軌跡から推力が戻る", et < 1e-4, "|Δa_T| = %.1e m/s², C_d %.4f(真値 %.2f)" % (et, ft["cd"], CD_TRUE))
    gate("推力 0 の軌跡では推力 ≈ 0", fb["thrust_norm"] < 1e-4, "|a_T| = %.1e m/s²" % fb["thrust_norm"])
    gate("C_d は 1e-3 で戻る", abs(db["cd"] - CD_TRUE) < 1e-3, "C_d %.5f" % db["cd"])

    # 3. 映像から軌跡
    print("3. 単眼映像 → 尺度つきの平面軌跡")
    clipB = make_clip(rng, 0.0, bp, t, keep_labels=True)
    clipT = make_clip(rng, 4.0, bp, t, keep_labels=True, launch_at=(clipB["p0"], clipB["v0"]))   # 同じ発射で推力だけ足す
    errs = np.concatenate([np.linalg.norm(c["xz"] - c["truth"][:, [0, 2]], axis=1) for c in (clipB, clipT)])
    med_err = float(np.median(errs))
    gate("bbox + 車長から起こした位置は真値と中央値 10 cm 以内", med_err < 0.10, "中央値 %.1f cm、最大 %.1f cm" % (100 * med_err, 100 * errs.max()))

    # 4. 弾道 vs 推力(映像から)
    print("4. 弾道 40 本 vs 推力 40 本(映像から判定)")
    rows = []
    dA_b, dA_t, ratio = [], [], []
    for i in range(40):
        c = make_clip(rng, 0.0, bp, t)
        r = B.ballistic_vs_thrust(t, c["xz"], bp, dt=DT_FIT)
        dA_b.append(r["delta_aic"])
        rows.append(("弾道", 0.0, r["delta_aic"], r["thrust_norm"], r["delta_aic"] >= MIN_DELTA))
    for i in range(40):
        a = rng.uniform(1.0, 6.0)
        c = make_clip(rng, a, bp, t)
        r = B.ballistic_vs_thrust(t, c["xz"], bp, dt=DT_FIT)
        dA_t.append(r["delta_aic"])
        ratio.append(r["thrust_norm"] / a)
        rows.append(("推力", a, r["delta_aic"], r["thrust_norm"], r["delta_aic"] >= MIN_DELTA))
    correct = sum(1 for r in rows if r[4] == (r[1] > 0))
    n_false = sum(d >= 10 for d in dA_b)
    gate("正答率 ≥ 95 %", correct >= 76, "%d / 80" % correct)
    gate("弾道 40 本のうち『推力あり』の誤判定は 2 本以下", n_false <= 2,
         "%d 本(ΔAIC 中央値 %.1f、90 %% 点 %.1f、最大 %.1f —— 雑音だけなら −2Δk = −4 を中心に χ²(2) の幅、量子化の鋸歯で裾が少し重い)" % (
             n_false, np.median(dA_b), np.quantile(dA_b, 0.9), max(dA_b)))
    gate("推力の ΔAIC は全部 10 以上", min(dA_t) >= 10, "最小 %.0f、中央値 %.0f" % (min(dA_t), np.median(dA_t)))
    med_ratio = float(np.median(ratio))
    gate("推力の大きさは中央値で 15 % 以内", abs(med_ratio - 1) < 0.15, "推定/真値 中央値 %.3f(範囲 %.2f〜%.2f)" % (med_ratio, min(ratio), max(ratio)))

    # 5. 検出の床
    print("5. どれだけ弱い推力まで見えるか(10 本ずつ)")
    floor_rows = []
    for a in (0.25, 0.5, 1.0, 2.0, 4.0):
        ds = [B.ballistic_vs_thrust(t, make_clip(rng, a, bp, t)["xz"], bp, dt=DT_FIT)["delta_aic"] for _ in range(10)]
        floor_rows.append((a, float(np.median(ds)), float(np.min(ds)), sum(d >= 10 for d in ds)))
        print("   a_T = %.2f m/s² (g の %4.1f %%): ΔAIC 中央値 %6.1f、最小 %6.1f、10 以上 %2d / 10" % (a, 100 * a / bp["g"], np.median(ds), min(ds), floor_rows[-1][3]))
    gate("g の 5 %(0.5 m/s²)の推力が 10 / 10 で決定的", floor_rows[1][3] == 10, "ΔAIC 最小 %.1f" % floor_rows[1][2])

    # 6. 時間の引き延ばし
    print("6. 時間の引き延ばし k の逆算と帰無分布")
    def khat_of(xz, k):
        P3 = np.column_stack([xz[:, 0], np.zeros(len(xz)), xz[:, 1]])
        par = B.fit_parabola(t * k, P3)           # 映像は「30 fps」と名乗るが、中身は k 倍に引き延ばされている
        return B.time_stretch_from_gravity(par["g"])
    null_vals = [abs(khat_of(make_clip(rng, 0.0, bp, t)["xz"], 1.0)["log_k"]) for _ in range(200)]
    null = IF.null_distribution(null_vals)
    print("   清浄 200 本の |ln k̂|: 中央値 %.4f、95 %% 点 %.4f、99 %% 点 %.4f(抗力を放物線が g に吸う分の偏りを含む)" % (
        null["quantiles"][50], null["quantiles"][95], null["quantiles"][99]))
    k_rows = []
    worst_rel, worst_q = 0.0, 1.0
    for k in (0.5, 0.8, 1.25, 2.0, 4.0):
        ks, qs = [], []
        for _ in range(10):
            r = khat_of(make_clip(rng, 0.0, bp, t)["xz"], k)
            ks.append(r["k"])
            qs.append(IF.evidence_quantile(abs(r["log_k"]), null)["beyond_fraction"])
        rel = float(np.max(np.abs(np.asarray(ks) / k - 1)))
        worst_rel, worst_q = max(worst_rel, rel), min(worst_q, float(np.min(qs)))
        k_rows.append((k, float(np.median(ks)), rel, float(np.min(qs))))
        print("   k = %.2f: k̂ 中央値 %.4f、最大相対誤差 %.2f %%、帰無分布での位置(最小)%.3f" % (k, np.median(ks), 100 * rel, min(qs)))
    gate("k̂ は 5 % 以内(k ∈ [0.5, 4])", worst_rel < 0.05, "最大 %.2f %%" % (100 * worst_rel))
    gate("改変した映像の位置は 0.99 以上", worst_q >= 0.99, "最小 %.3f" % worst_q)
    fp = [IF.evidence_quantile(abs(khat_of(make_clip(rng, 0.0, bp, t)["xz"], 1.0)["log_k"]), null)["beyond_fraction"] for _ in range(100)]
    n_fp = sum(q > 0.99 for q in fp)
    gate("清浄な別の 100 本で 0.99 超は 5 % 以下", n_fp <= 5, "%d / 100" % n_fp)

    # 7. 縮退(正直に)
    print("7. 絵だけでは区別できないこと: 引き延ばした弾道は上向きの推力に見える")
    k = 1.5
    c = make_clip(rng, 0.0, bp, t)
    r = B.ballistic_vs_thrust(t * k, c["xz"], bp, dt=DT_FIT)
    pred = bp["g"] * (1 - 1 / k ** 2)
    az = float(r["thrust"]["thrust"][2])
    gate("k = 1.5 の弾道映像を推力検査にかけると『推力あり』", r["delta_aic"] >= MIN_DELTA, "ΔAIC %.0f" % r["delta_aic"])
    gate("その鉛直推力は g(1 − 1/k²) = %.2f m/s² と 5 %% 以内" % pred, abs(az / pred - 1) < 0.05, "測定 %.2f m/s²" % az)
    print("   → 単眼の軌跡では『鉛直の一定推力』と『時間の引き延ばし』は同じ絵になる。順番は 先に k(重力の見え方)、次に推力。")

    # 図
    if figs.enabled():
        frames = []
        for i, (lab, xz) in enumerate(zip(clipT["labels"], clipT["xz"])):
            e = TTC.label_extent(lab, 1)
            trail = project(np.column_stack([clipT["xz"][:i + 1, 0], np.zeros(i + 1), clipT["xz"][:i + 1, 1]]))
            frames.append(draw_frame(lab, (e["col0"], e["col1"], e["row0"], e["row1"]),
                                     "t = %.2f s  x = %.1f m  z = %.1f m" % (t[i], xz[0], xz[1]), trail_uv=trail, depth=-CAM[1]))
        figs.save_gif("monocular_clip", frames, "推力 4 m/s² の車を 45 m 先の単眼カメラで写した合成映像(960 × 540、30 fps)。箱の影絵と bbox、bbox と車の寸法から起こした位置の軌跡(点)、地面の線。", fps=15)
        figs.save_plot("trajectories",
                       [("弾道(映像から)", clipB["xz"][:, 0], clipB["xz"][:, 1]), ("弾道(真値)", clipB["truth"][:, 0], clipB["truth"][:, 2]),
                        ("同じ発射 + 推力 4 m/s²(映像から)", clipT["xz"][:, 0], clipT["xz"][:, 1]), ("推力(真値)", clipT["truth"][:, 0], clipT["truth"][:, 2])],
                       xlabel="x [m]", ylabel="z [m]", title="単眼映像から起こした平面軌跡(同じ発射、推力の有無)",
                       caption="点は bbox から、破線は世界の真値。同じ発射でも推力があると放物線から外れて伸びる。",
                       kinds=["scatter", "line", "scatter", "line"], styles=[None, "dashed", None, "dashed"],
                       colors=["reference", "reference", "emphasis", "emphasis"], aspect="equal")
        idx_b = np.arange(1, 41)
        figs.save_plot("delta_aic_ballistic",
                       [("弾道 40 本の ΔAIC", idx_b, np.asarray(dA_b)), ("−2Δk(雑音だけの中心)", np.array([1, 40]), np.array([-4.0, -4.0])),
                        ("ΔAIC = 10(門)", np.array([1, 40]), np.array([10.0, 10.0]))],
                       xlabel="clip", ylabel="ΔAIC = AIC_弾道 − AIC_推力", title="弾道のクリップ: 推力の模型は罰則を超えて勝てない",
                       caption="雑音だけなら ΔAIC は −2Δk = −4 を中心に χ²(2) の幅で散る。10 を超えたら『推力あり』。",
                       kinds=["scatter", "line", "line"], styles=[None, "dashed", "dashed"], colors=["reference", "neutral", "wrong"], ylim=(-8, 14))
        a_true = np.asarray([r[1] for r in rows if r[1] > 0])
        figs.save_plot("delta_aic_thrusted",
                       [("推力 40 本の ΔAIC", a_true, np.asarray(dA_t)), ("ΔAIC = 10(門)", np.array([1.0, 6.0]), np.array([10.0, 10.0]))],
                       xlabel="真の比推力 a_T [m/s²]", ylabel="ΔAIC", title="推力のクリップ: ΔAIC は桁で超える",
                       caption="1 m/s²(g の 10 %)でも 60 コマで決定的。", kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "wrong"])
        figs.save_plot("detection_floor", [("ΔAIC 中央値", np.array([r[0] for r in floor_rows]), np.array([r[1] for r in floor_rows])),
                                           ("ΔAIC 最小", np.array([r[0] for r in floor_rows]), np.array([r[2] for r in floor_rows])),
                                           ("10(門)", np.array([0.25, 4.0]), np.array([10.0, 10.0]))],
                       xlabel="比推力 a_T [m/s²]", ylabel="ΔAIC", title="どれだけ弱い推力まで見えるか(60 コマ、1 画素 7.5 cm)",
                       caption="g の 2.5 % の推力でも床の 10 を超える。床は雑音(画素)とコマ数で決まる。", kinds=["line", "line", "line"],
                       styles=[None, None, "dashed"], colors=["reference", "emphasis", "neutral"])
        kk = np.array([r[0] for r in k_rows])
        q99 = 100.0 * (math.exp(null["quantiles"][99]) - 1.0)
        figs.save_plot("time_stretch", [("k̂ の相対誤差(中央値)", kk, 100 * (np.array([r[1] for r in k_rows]) / kk - 1)),
                                        ("最大相対誤差", kk, 100 * np.array([r[2] for r in k_rows])),
                                        ("清浄 200 本の 99 %% 点(±%.2f %%)" % q99, np.array([0.5, 4.0]), np.array([q99, q99])),
                                        ("", np.array([0.5, 4.0]), np.array([-q99, -q99]))],
                       xlabel="真の引き延ばし倍率 k", ylabel="k̂ / k − 1 [%]", title="時間の引き延ばしは g/k² から戻る(門は ±5 %、図は ±1 %)",
                       caption="k = √(g_ref / g_fit)。偏りは抗力を放物線が g に吸う分で、帰無分布(破線)に含めて読む。",
                       kinds=["line", "line", "line", "line"], styles=[None, None, "dashed", "dashed"], colors=["emphasis", "reference", "neutral", "neutral"], ylim=(-1, 1))
        figs.save_table("summary", ["検査", "値", "門"],
                        [["位置の誤差(中央値)", "%.1f cm" % (100 * med_err), "< 10 cm"],
                         ["正答率(80 本)", "%d / 80" % correct, "≥ 76"],
                         ["弾道 40 本の誤判定(ΔAIC ≥ 10)", "%d 本(最大 %.1f)" % (n_false, max(dA_b)), "≤ 2"],
                         ["推力の ΔAIC 最小", "%.0f" % min(dA_t), "≥ 10"],
                         ["推力の大きさ(推定/真値 中央値)", "%.3f" % med_ratio, "±15 %"],
                         ["k̂ の最大相対誤差", "%.2f %%" % (100 * worst_rel), "< 5 %"],
                         ["改変映像の帰無分布での位置(最小)", "%.3f" % worst_q, "≥ 0.99"],
                         ["清浄 100 本の偽陽性", "%d" % n_fp, "≤ 5"],
                         ["k = 1.5 の見かけの鉛直推力", "%.2f m/s²" % az, "g(1−1/k²) = %.2f" % pred]],
                        title="映像の物理整合性検査 —— 門の数字", caption="全部、合成の世界の真値に対する実測。")

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        OK.append(False)
    print("所要 %.1f 秒" % (time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    raise SystemExit(main())
