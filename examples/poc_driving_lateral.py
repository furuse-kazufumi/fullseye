# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉛(自動運転 第 10 回): 横の運動 —— カーブの手前で減速して車線の中を保って曲がる、左折で左に寄って内輪差の内側の
自転車を巻き込まない、右折で交差点の中心のすぐ内側を回る、を閉形式と独立な経路で採点する。

方針(ユーザーの決定): **部品はルールベースに限る**。学習・ニューラルネットは使わない。部品(:mod:`drivelateral`)は閉形式・幾何・
公表値・条文の判定・古典的な数値計算で、どれも独立な経路の検算(門)が立つ。手続きで作った世界は採点用の真値で、訓練には使わない。
AI は部品の組み合わせを考える側 —— ここでは「pure pursuit の定常の横ずれの閉形式で注視距離の上限を決める」「内輪差の閉形式と
追跡曲線で左折の円を選ぶ」が組み合わせの例。

門(真値の出どころ):
  0. **乱数の値の門**: 摩擦係数 μ・運転者の横加速度の上限・前方注視の時間(舵の癖)・自転車の速さは、参照分布(仮定)の両側 0.1 %
     分位点の外を 1 個ずつ落とし(理由を記録)、集団は切断正規分布との KS 検定で照合する。物理的にありえない値(μ 1.9 等)は落ち、
     単位の誤り(m/s をもう一度 3.6 で割った速さ)は 1 個ずつの門をほぼ通るが KS で落ちる(門が自明でない)。頻度が低いだけの
     出来事(近くから追いつく速い自転車)は落とさず、重要度サンプリングの重みで扱う。
  1. **カーブの速度計画**(S065): curvature_speed_plan(摩擦円つき)で計画した N 人は、2 輪等価モデル(RK4)で走っても摩擦円の
     使用率 ≤ 1、曲がり角の附近は 10 km/h 以下。計画なし(50 km/h のまま)は全員が摩擦円を出る。
  2. **車線の中**(S020, S021, S024, S033): 車体の 4 隅が中央線(黄の実線)をまたがず、外側線の外(路肩 0.5 m)に出ない。注視距離を
     pure_pursuit_circle_offset(2 自由度の定常)で「外への横ずれ ≤ 0.25 m」に抑える。抑えない運転者の癖のままだと予算を超えて外へ膨らむ人が
     出る、注視距離を 20 m に固定すると曲がり角で路肩へ内に切れ込む(門が自明でない)。
  3. **定常の横ずれ**: 半径 100 m の円弧の終わりの手前で測った後車軸の横ずれ = 2 自由度の半閉形式(後軸の横すべりを入れる)。
     運動学の閉形式 √(R² + K v² L_d²/L) − R は約半分に見積もる。
  4. **内輪差**: 前車軸の中心が半径 R_f の円に入ってから 90° の所の後車軸の半径 = offtracking_circle(閉形式)= rear_axle_path
     (折線の追跡曲線)。
  5. **左折**(S092, S091): あらかじめ左に寄り(車体の左側が外側線から 0.25 m)、内輪差の閉形式と追跡曲線で選んだ円で隅に沿って
     徐行 —— turn_maneuver_check で違反なし、隅で待つ自転車に触れない。前輪で隅に沿う(内輪差を無視)と後輪が隅に入り自転車に
     触れる。左に寄らない(車線の中央)と後ろから来た自転車が左に入り込み、曲がる車体に巻き込まれる(重要度サンプリングの推定 =
     素朴なモンテカルロ)。
  6. **右折**(S093): あらかじめ中央に寄り、交差点の中心のすぐ内側を徐行 —— 違反なし。中心を過ぎてから回る(大回り)・手前で
     小さく回る(早回り)は違反。

正直に書くこと:
* **仮定の値**: 車(質量 1500 kg・l_f 1.2 m・l_r 1.5 m・C_f 80 kN/rad・C_r 90 kN/rad・I_z 2500 kg m²、幅 1.8 m・輪距 1.55 m)、
  参照分布(μ ~ N(0.80, 0.07)、横加速度の上限 ~ N(2.5, 0.5) m/s²、注視時間 ~ N(1.0, 0.15) s、自転車 ~ N(14.5, 3.5) km/h(平均は国総研の車道の旅行速度 14.5 km/h、幅は仮定))、
  車線 3.0 m・路肩 0.5 m、徐行 = 10 km/h、曲がり角の「附近」= 30 m、隅切り半径 6 m、隅の人・自転車の場所 = 縁石から 1.2 m、
  自転車は縁石から 0.5 m の線を走り横に 0.2 m の隙が無いと追い越さず、追い越した後は止まらない(最悪の場合)。出典と状態は
  drivelateral.SOURCES と NOTES.md。
* 線形 2 輪等価モデルはタイヤの飽和を持たない。「計画なしは摩擦円を出る」は使用率 > 1 の判定で、滑った後の動きは描かない。
* 速さは計画どおりに出す(縦の運動は描かない)。車線の判定は車体の箱(4.5 × 1.8 m)の 4 隅。
* 左折の自転車は 2D の箱。人の判断(ミラーで見て待つ、第 9 回)はここでは入れず、**幾何だけで** 入り込む余地が残るかを比べる。

教則の場面: S020, S021, S024, S033, S065, S091, S092, S093(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_lateral.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
FULLSEYE_POC_BUDGET=reduced(CI の既定)で人数・試行数・動画の大きさを減らす)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivelateral as DL  # noqa: E402

#: 予算: reduced(CI の既定)は人数・試行数を減らす。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_DRIVERS = 40 if REDUCED else 120            # カーブを走る運転者
N_SUB = 20 if REDUCED else 40                 # 「上限なし」「20 m 固定」の版を走らせる人数
N_MC = 3000 if REDUCED else 24000             # 左折の素朴なモンテカルロ
N_IS = 600 if REDUCED else 3000               # 左折の重要度サンプリング
VID_WH = (320, 180) if REDUCED else (640, 360)
T0 = time.time()
OK = []

# ── 車(仮定) ──
CAR = {"mass": 1500.0, "l_f": 1.2, "l_r": 1.5, "c_f": 80000.0, "c_r": 90000.0, "inertia": 2500.0}
WB = CAR["l_f"] + CAR["l_r"]
WIDTH, TRACK, OVH = 1.8, 1.55, 0.9            # 車幅・輪距・前後のはみ出し(車軸から車体の端)→ 全長 4.5 m
K_US = DL.understeer_gradient(CAR)["K"]

# ── 道(座標: 中央線 n = 0、自車線 n ∈ [0, 3.0]、外側線 3.0、路肩 [3.0, 3.5]、縁石 3.5) ──
LANE, SHOULDER = 3.0, 0.5
CURB = LANE + SHOULDER
N_TARGET = 1.6                 # 車線の中央 1.5 m から 0.1 m 左(S021「左に寄って」、仮定)
V_ROAD = 50.0 / 3.6            # 速度の上限(仮定)
JOKOU = 10.0 / 3.6             # 徐行(仮定)
NEAR = 30.0                    # 曲がり角の「附近」(仮定)
R1, R2 = 100.0, 15.0           # なだらかなカーブ・曲がり角(中央線の半径)= 道路構造令 第15条の設計速度 50・20 km/h の最小値
L1, L2 = 40.0, 20.0            # 緩和区間(クロソイド)の長さ = 第18条の表の設計速度 50・20 km/h の値
V_DESIGN = (50.0, 20.0)        # それぞれの設計速度 [km/h]
OFFSET_BUDGET = 0.25           # 注視距離の上限を決める外への横ずれの予算 [m](仮定)
DT = 0.02

# ── 乱数の参照分布(すべて仮定。出典の候補は NOTES.md)と標本の門 ──
Z999 = 3.2905267314919255     # 標準正規の 99.95 % 点(両側 0.1 %)
REF = {
    "mu": {"mean": 0.80, "sd": 0.07, "unit": "", "what": "乾いた舗装の摩擦係数"},
    "a_lat": {"mean": 2.5, "sd": 0.5, "unit": "m/s²", "what": "運転者が選ぶ横加速度の上限"},
    "t_look": {"mean": 1.0, "sd": 0.15, "unit": "s", "what": "前方注視の時間(舵の癖)"},
    "v_bike": {"mean": 14.5 / 3.6, "sd": 3.5 / 3.6, "unit": "m/s", "what": "自転車の速さ"},   # 平均 = 山本・大脇・上坂 2011 表-6(車道)
}


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


# ───────────────────────────── 0. 標本の門 ─────────────────────────────
def _ncdf(x):
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(x, float) / math.sqrt(2.0)))


def screen(name, x):
    """1 個ずつの門: 参照分布の両側 0.1 % 分位点の外と非有限を落とす。返り値 (残した値, 落とした理由のリスト)。"""
    r = REF[name]
    lo, hi = r["mean"] - Z999 * r["sd"], r["mean"] + Z999 * r["sd"]
    x = np.asarray(x, float)
    keep = np.isfinite(x) & (x >= lo) & (x <= hi)
    why = ["%s = %.4g %s は参照 N(%.3g, %.3g) の両側 0.1 %% 点 [%.3g, %.3g] の外" % (name, v, r["unit"], r["mean"], r["sd"], lo, hi)
           for v in x[~keep]]
    return x[keep], why


def ks_truncnorm(name, x):
    """集団の門: 参照分布を 0.1 % 点で切った切断正規との 1 標本 KS。返り値 (D, p)(p は Kolmogorov の漸近級数)。"""
    r = REF[name]
    lo, hi = r["mean"] - Z999 * r["sd"], r["mean"] + Z999 * r["sd"]
    x = np.sort(np.asarray(x, float))
    n = len(x)
    F = lambda v: (_ncdf((v - r["mean"]) / r["sd"]) - _ncdf(-Z999)) / (_ncdf(Z999) - _ncdf(-Z999))  # noqa: E731
    Fx = np.clip(F(np.clip(x, lo, hi)), 0.0, 1.0)
    i = np.arange(1, n + 1)
    D = float(max(np.max(i / n - Fx), np.max(Fx - (i - 1) / n)))
    lam = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * D
    p = 2.0 * sum((-1) ** (k - 1) * math.exp(-2.0 * k * k * lam * lam) for k in range(1, 101))
    return D, float(min(max(p, 0.0), 1.0))


def draw(name, n, rng):
    """参照分布から n 個を引き、門で落ちた分は引き直す(落とした件数と理由を返す)。"""
    r = REF[name]
    out, dropped = [], []
    while len(out) < n:
        x = rng.normal(r["mean"], r["sd"], n - len(out))
        k, why = screen(name, x)
        out += list(k)
        dropped += why
    return np.array(out), dropped


def scene_samples():
    print("== 0. 乱数の値の門(参照分布はすべて仮定、両側 0.1 % 分位点で 1 個ずつ、集団は KS)")
    rng = np.random.default_rng(10)
    D = {}
    total_drop = 0
    pmin = 1.0
    for name, n in (("mu", N_DRIVERS), ("a_lat", N_DRIVERS), ("t_look", N_DRIVERS), ("v_bike", max(N_MC, N_IS))):
        x, why = draw(name, n, rng)
        Dk, p = ks_truncnorm(name, x)
        pmin = min(pmin, p)
        total_drop += len(why)
        r = REF[name]
        print("    %-7s %s: %d 個、落とした %d 個%s、KS D = %.4f p = %.3f" % (
            name, r["what"], len(x), len(why), ("(" + why[0] + ")") if why else "", Dk, p))
        D[name] = x
    gate("標本の門: 採った値はすべて参照の 0.1 % 点の内、集団は KS で参照と食い違わない(p > 0.001)", pmin > 0.001,
         "最小 p = %.3f、落とした %d 個" % (pmin, total_drop))
    # 門が自明でない: 物理的にありえない値と単位の誤り
    bad = {"mu": [0.78, 1.9, -0.1], "a_lat": [2.4, 12.0], "t_look": [1.1, -0.2], "v_bike": [4.0, 80 / 3.6]}
    nbad = 0
    for k, v in bad.items():
        _, why = screen(k, v)
        nbad += len(why)
        for w in why:
            print("      落とした: " + w)
    wrong = D["v_bike"][:2000] / 3.6                       # m/s をもう一度 3.6 で割った(単位の誤り)
    kept, why = screen("v_bike", wrong)
    Dw, pw = ks_truncnorm("v_bike", kept)
    print("    単位の誤り(m/s をさらに 3.6 で割った 2000 個): 1 個ずつの門で落ちたのは %d 個(%.0f %%)、残り %d 個の KS D = %.3f p = %.2g"
          % (len(why), 100 * len(why) / 2000, len(kept), Dw, pw))
    gate("門が自明でない: ありえない値 5 個は 1 個ずつの門で落ち(理由を記録)、単位の誤りは 1 個ずつの門をほぼ通るが KS で落ちる",
         nbad == 5 and len(why) < 1000 and pw < 1e-6, "落とした %d 個 / 単位の誤り p = %.2g" % (nbad, pw))
    return D


# ───────────────────────────── 1–3. カーブ ─────────────────────────────
def build_course(pieces, ds=0.25):
    """[(長さ, κ0, κ1)] の曲率が一次の区間をつないだ中央線(clothoid_points)。"""
    S, P, H, K = [0.0], [np.zeros(2)], [0.0], [pieces[0][1]]
    p, h, s0 = np.zeros(2), 0.0, 0.0
    for Ls, k0, k1 in pieces:
        n = max(int(round(Ls / ds)), 1)
        ss = np.linspace(0.0, Ls, n + 1)[1:]
        c = DL.clothoid_points(Ls, ss, kappa0=k0, kappa1=k1, start=p, heading0=h)
        S += list(s0 + ss)
        P += list(c["points"])
        H += list(c["heading"])
        K += list(c["curvature"])
        p, h, s0 = c["points"][-1], float(c["heading"][-1]), s0 + Ls
    return np.array(S), np.array(P), np.array(H), np.array(K)


A1 = R1 * math.radians(70.0)
A2 = R2 * math.radians(20.0)       # 曲がり角の円弧(両側のクロソイドの 38° ずつを足して約 96°)
PIECES = [(120.0, 0, 0), (L1, 0, 1 / R1), (A1, 1 / R1, 1 / R1), (L1, 1 / R1, 0), (70.0, 0, 0),
          (L2, 0, 1 / R2), (A2, 1 / R2, 1 / R2), (L2, 1 / R2, 0), (120.0, 0, 0)]
S_ARC1 = (120.0 + L1, 120.0 + L1 + A1)
S_CORNER = (sum(p[0] for p in PIECES[:5]), sum(p[0] for p in PIECES[:8]))
S_EVAL = sum(p[0] for p in PIECES) - 60.0          # 評価はここまで(経路の終わりは注視点が詰まる)


class Course:
    def __init__(self):
        self.S, self.P, self.H, self.K = build_course(PIECES)
        self.nrm = np.stack([-np.sin(self.H), np.cos(self.H)], 1)
        self.tp = self.P + N_TARGET * self.nrm                      # 狙う線
        self.Kt = self.K / (1.0 - N_TARGET * self.K)                # 平行な曲線の曲率
        self.St = np.r_[0.0, np.cumsum(np.hypot(*np.diff(self.tp, axis=0).T))]
        self.vmax = np.full(len(self.S), V_ROAD)
        self.zone = (self.S > S_CORNER[0] - NEAR) & (self.S < S_CORNER[1])
        self.vmax[self.zone] = JOKOU


def look_cap(Rt, v):
    """外への定常の横ずれ ≤ OFFSET_BUDGET になる注視距離の上限(2 自由度の半閉形式を二分法)。"""
    lo, hi = 3.0, min(40.0, 1.9 * Rt)
    try:
        if DL.pure_pursuit_circle_offset(Rt, hi, WB, speed=v, params=CAR)["offset"] <= OFFSET_BUDGET:
            return hi
    except ValueError:
        pass
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        try:
            off = DL.pure_pursuit_circle_offset(Rt, mid, WB, speed=v, params=CAR)["offset"]
        except ValueError:
            off = math.inf
        lo, hi = (mid, hi) if off <= OFFSET_BUDGET else (lo, mid)
    return lo


def drive(C, drv, *, plan=True, cap=True, ld_fixed=None, record=False):
    """N 人を同時に走らせる(2 輪等価モデル + pure pursuit、速さは計画どおり)。"""
    N = len(drv["mu"])
    if plan:
        V = np.array([DL.curvature_speed_plan(C.St, C.Kt, v_max=C.vmax, a_lat_max=drv["a_lat"][i], a_accel=1.5,
                                              a_decel=2.5, a_total=drv["mu"][i] * DL.G, v_start=V_ROAD)["v"]
                      for i in range(N)])
    else:
        V = np.full((N, len(C.S)), V_ROAD)
    dV = np.diff(V, axis=1) / np.diff(C.St)
    Rt1, Rt2 = R1 - N_TARGET, R2 - N_TARGET
    if cap and ld_fixed is None:
        # 円弧の中の計画の速さで、横ずれの予算に収まる注視距離の上限(運転者ごと・円弧ごと)
        cap1 = np.array([look_cap(Rt1, V[i, np.searchsorted(C.S, 0.5 * sum(S_ARC1))]) for i in range(N)])
        cap2 = np.array([look_cap(Rt2, max(V[i, np.searchsorted(C.S, 0.5 * sum(S_CORNER))], 0.6)) for i in range(N)])
    else:
        cap1 = cap2 = np.full(N, np.inf)
    X = np.zeros((N, 5))
    X[:, 0] = C.tp[0, 0] + CAR["l_r"]
    X[:, 1] = C.tp[0, 1]
    idx = np.zeros(N, int)
    cidx = np.zeros(4 * N, int)
    r = np.arange(N)
    use = np.zeros(N)
    nmin = np.full(N, 9.0)
    nmax = np.full(N, -9.0)
    vz = np.zeros(N)
    off_end = np.full(N, np.nan)
    i_end1 = int(np.searchsorted(C.St, S_ARC1[1] - 22.0))
    done = np.zeros(N, bool)
    rec = []
    t = 0.0
    while not done.all():
        c, s = np.cos(X[:, 2]), np.sin(X[:, 2])
        rear = X[:, :2] - CAR["l_r"] * np.stack([c, s], 1)
        v = np.maximum(V[r, idx], 0.6)
        iv = idx.copy()                                     # 速さを決めた点(徐行の判定はこの点で)
        sn = C.S[idx]
        if ld_fixed is not None:
            Ld = np.full(N, float(ld_fixed))
        else:
            Ld = np.maximum(3.0, drv["t_look"] * v)
            Ld = np.where((sn > S_ARC1[0] - 40) & (sn < S_ARC1[1] + 10), np.minimum(Ld, cap1), Ld)
            Ld = np.where((sn > S_CORNER[0] - 40) & (sn < S_CORNER[1] + 10), np.minimum(Ld, cap2), Ld)
        o = DL.pure_pursuit_curvature(np.c_[rear, X[:, 2]], C.tp, Ld, start_index=idx, window=30)
        idx = o["index"]
        steer = np.arctan(WB * o["kappa"])
        Xn = DL.bicycle_model_step(X, steer, v, CAR, DT)
        ay = (Xn[:, 3] - X[:, 3]) / DT + v * X[:, 4]
        ax = v * dV[r, np.minimum(idx, dV.shape[1] - 1)]
        u = DL.friction_circle_usage(ax, ay, mu=1.0) / drv["mu"]
        f = np.stack([c, s], 1)
        lft = np.stack([-s, c], 1)
        cor = np.concatenate([X[:, :2] + a * f + b * lft for a in (CAR["l_f"] + OVH, -(CAR["l_r"] + OVH))
                              for b in (0.5 * WIDTH, -0.5 * WIDTH)])
        lo = DL.lateral_offset(cor, C.P, start_index=cidx, window=40)
        cidx = lo["index"]
        nn = lo["n"].reshape(4, N)
        live = ~done
        use = np.where(live, np.maximum(use, u), use)
        nmin = np.where(live, np.minimum(nmin, nn.min(0)), nmin)
        nmax = np.where(live, np.maximum(nmax, nn.max(0)), nmax)
        vz = np.where(live & C.zone[iv], np.maximum(vz, v), vz)
        hit = live & (idx >= i_end1) & np.isnan(off_end)
        off_end = np.where(hit, -(o["lateral"]), off_end)
        if record:
            rec.append({"t": t, "X": X.copy(), "v": v.copy(), "ax": ax.copy(), "ay": ay.copy(), "s": C.St[idx].copy(),
                        "steer": steer.copy(), "goal": o["goal"].copy(), "n": nn.copy()})
        X = Xn
        t += DT
        done |= C.St[idx] >= S_EVAL
        if t > 400:
            raise RuntimeError("drive: did not finish")
    return {"use": use, "nmin": nmin, "nmax": nmax, "vzone": vz, "off_end": off_end, "V": V, "cap1": cap1,
            "rec": rec, "T": t}


def scene_curve(D):
    print("== 1–3. カーブ: 半径 %.0f m のカーブと半径 %.0f m の曲がり角(クロソイドでつなぐ)、%d 人" % (R1, R2, N_DRIVERS))
    C = Course()
    drv = {k: D[k][:N_DRIVERS] for k in ("mu", "a_lat", "t_look")}
    pj = []
    tab = []
    for R, L, Vd in ((R1, L1, V_DESIGN[0]), (R2, L2, V_DESIGN[1])):
        cd = DL.clothoid_design(R, L, speed=Vd / 3.6)
        pj.append(cd["lateral_jerk"])
        tab.append(R >= DL.ROAD_MIN_RADIUS[int(Vd)][0] and L >= DL.TRANSITION_LENGTH[int(Vd)])
        print("    クロソイド R %.0f m・L %.0f m(設計速度 %.0f km/h の表の値 R ≥ %d m・L ≥ %d m): A = %.1f m、端の角 %.1f°、円のずれ %.3f m"
              "(近似 L²/24R %.3f m)、設計速度での横加速度の変化率 %.3f m/s³" % (
                  R, L, Vd, DL.ROAD_MIN_RADIUS[int(Vd)][0], DL.TRANSITION_LENGTH[int(Vd)], cd["A"], math.degrees(cd["end_angle"]),
                  cd["shift"], cd["shift_approx"], cd["lateral_jerk"]))
    gate("道の形 = 公表値: 半径・緩和区間は道路構造令 第15・18条の表を満たし、設計速度での横加速度の変化率は解説の許容 0.5〜0.75 m/s³ の中",
         all(tab) and all(0.5 <= p <= 0.75 for p in pj), "%.3f / %.3f m/s³" % tuple(pj))
    t = time.time()
    good = drive(C, drv, plan=True, cap=True, record=True)
    print("    計画 + 注視距離の上限: %.1f s(模擬 %.0f s)" % (time.time() - t, good["T"]))
    nop = drive(C, drv, plan=False, cap=True)
    sub = {k: v[:N_SUB] for k, v in drv.items()}            # 自明でない版は先頭の N_SUB 人で(時間の予算)
    habit = drive(C, sub, plan=True, cap=False)
    fixed = drive(C, sub, plan=True, cap=False, ld_fixed=20.0)
    right = good["nmin"]
    left = LANE - good["nmax"]
    print("    計画 + 上限: 摩擦円の使用率 最大 %.2f、曲がり角の附近の最大 %.1f km/h、中央線まで最小 %.2f m、外側線まで最小 %.2f m" % (
        good["use"].max(), 3.6 * good["vzone"].max(), right.min(), left.min()))
    gate("速度計画: 計画した全員が摩擦円の中(使用率 ≤ 1)、曲がり角の附近は徐行(≤ 10 km/h)",
         good["use"].max() <= 1.0 and good["vzone"].max() <= JOKOU + 1e-9,
         "使用率 %.2f / %.1f km/h" % (good["use"].max(), 3.6 * good["vzone"].max()))
    gate("車線の中: 全員の車体の 4 隅が中央線をまたがず(S020・S024)外側線の外の路肩へ出ない(S033)",
         right.min() > 0 and left.min() > 0, "中央線まで %.2f m / 外側線まで %.2f m" % (right.min(), left.min()))
    print("    計画なし(50 km/h のまま): 使用率 最小 %.2f・最大 %.2f、中央線をまたいだ %d / %d 人" % (
        nop["use"].min(), nop["use"].max(), int((nop["nmin"] < 0).sum()), N_DRIVERS))
    over = habit["off_end"] > OFFSET_BUDGET + 0.01
    print("    注視距離の上限なし(癖のまま T·v、%d 人): 円弧の横ずれ %.2f〜%.2f m(予算 %.2f m を超えた %d 人)、中央線まで最小 %.2f m(上限ありは %.2f m)、"
          "注視距離 20 m 固定: 外側線を越えた %d 人(最大 %.2f m)" % (
              N_SUB, habit["off_end"].min(), habit["off_end"].max(), OFFSET_BUDGET, int(over.sum()), habit["nmin"].min(), right.min(),
              int((fixed["nmax"] > LANE).sum()), fixed["nmax"].max() - LANE))
    gate("門が自明でない: 計画なしは全員が摩擦円を出る、上限なしは円弧で外へ予算を超えて膨らむ人が出る、20 m 固定は曲がり角で路肩へ切れ込む",
         nop["use"].min() > 1.0 and over.any() and (fixed["nmax"] > LANE).all(),
         "%d / %d 人中 %d・%d 人" % (int((nop["use"] > 1).sum()), N_SUB, int(over.sum()), int((fixed["nmax"] > LANE).sum())))
    # 3. 定常の横ずれ: 円弧の終わりの手前(注視点がまだ円弧の上)で測った後車軸の外への横ずれ = 2 自由度の半閉形式
    i_mid = np.searchsorted(C.S, 0.5 * sum(S_ARC1))
    pred, kin = [], []
    for i in range(N_DRIVERS):
        v = max(good["V"][i, i_mid], 0.6)
        Ld = min(max(3.0, drv["t_look"][i] * v), good["cap1"][i])
        pred.append(DL.pure_pursuit_circle_offset(R1 - N_TARGET, Ld, WB, speed=v, params=CAR)["offset"])
        kin.append(DL.pure_pursuit_circle_offset(R1 - N_TARGET, Ld, WB, speed=v, understeer=K_US)["offset"])
    pred, kin = np.array(pred), np.array(kin)
    err = np.abs(good["off_end"] - pred)
    print("    円弧の終わりの手前の横ずれ: 測った %.3f〜%.3f m、2 自由度の式との差 最大 %.4f m、運動学の式は %.0f〜%.0f %% に見積もる" % (
        good["off_end"].min(), good["off_end"].max(), err.max(), 100 * (kin / pred).min(), 100 * (kin / pred).max()))
    gate("定常の横ずれ = pure_pursuit_circle_offset(2 自由度、後軸の横すべり込み)±3 cm", err.max() < 0.03, "最大の差 %.4f m" % err.max())
    return {"C": C, "drv": drv, "good": good, "nop": nop, "habit": habit, "fixed": fixed, "pred": pred, "kin": kin}


# ───────────────────────────── 4–6. 交差点 ─────────────────────────────
XC = 60.0                        # 交差道路の中心線 x
CROSS_CURB = XC - CURB           # 交差道路の左の縁石 x = 56.5
RC = 6.0                         # 隅切りの半径(仮定)
CORNER_C = np.array([CROSS_CURB - RC, CURB + RC])     # 隅切りの中心 (50.5, 9.5)
X_ENTRY = CORNER_C[0]            # 交差点の手前の縁(隅切りの始まり)
CLEAR = 1.2                      # 隅の人・自転車の場所(縁石から 0.8 m)+ 余裕 0.4 m(仮定)
Y_BIKE = CURB - 0.5              # 自転車の走る線(縁石から 0.5 m、仮定)
BIKE_L, BIKE_W, BIKE_PASS = 1.8, 0.6, 0.2
Y_KEEP = LANE - 0.25 - 0.5 * WIDTH      # 左に寄る: 車体の左側が外側線から 0.25 m
Y_CENTRE = 0.5 * LANE                   # 寄らない: 車線の中央
V_APP = 30.0 / 3.6
V_TURN = 8.0 / 3.6
R_MIN_FRONT = WB / math.sin(math.radians(35.0))   # 前車軸の中心の最小の旋回半径(舵角 35°、仮定)= 4.71 m


def turn_path(kind, y_app, Rf, cx, ds=0.05, pre=70.0, after=25.0):
    sg = 1.0 if kind == "left" else -1.0
    cy = y_app + sg * Rf
    n0 = int(round(pre / ds))
    xs = cx - pre + ds * np.arange(n0)
    P0 = np.stack([xs, np.full_like(xs, y_app)], 1)
    n = int(round(Rf * math.pi / 2 / ds))
    ph = np.linspace(0, math.pi / 2, n + 1)[1:]
    arc = np.stack([cx + Rf * np.sin(ph), cy - sg * Rf * np.cos(ph)], 1)
    ys = ds * np.arange(1, int(round(after / ds)) + 1)
    post = np.stack([np.full_like(ys, arc[-1, 0]), arc[-1, 1] + sg * ys], 1)
    return np.vstack([P0, arc, post]), n0, n0 + n


def ego_turn(kind, y_app, Rf, cx):
    """前車軸の折線 → 後車軸(追跡曲線)→ 速度計画(徐行の区間つき)→ 時刻。"""
    F, i0, i1 = turn_path(kind, y_app, Rf, cx)
    rp = DL.rear_axle_path(F, WB)
    s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(F, axis=0).T))]
    k = np.zeros(len(F))
    k[i0:i1 + 1] = 1.0 / Rf
    vmax = np.full(len(F), V_APP)
    vmax[(F[:, 0] + OVH >= X_ENTRY - 8.0) & (np.arange(len(F)) <= i1 + int(5.0 / 0.05))] = V_TURN
    pl = DL.curvature_speed_plan(s, k, v_max=vmax, a_lat_max=2.0, a_accel=1.0, a_decel=2.0, v_start=V_APP)
    return {"front": F, "rear": rp["rear"], "heading": rp["heading"], "s": s, "v": pl["v"], "time": pl["time"],
            "i0": i0, "i1": i1, "Rf": Rf, "cx": cx, "y": y_app, "kind": kind}


def traj_dict(E):
    return {"t": E["time"], "front": E["front"], "rear": E["rear"], "speed": E["v"], "width": WIDTH, "track": TRACK,
            "front_overhang": OVH, "rear_overhang": OVH}


LEFT_KW = dict(x_entry=X_ENTRY, edge_y=LANE, center_y=0.0, corner_center=CORNER_C, corner_radius=RC, clearance=CLEAR,
               side_tol=2.0, keep_tol=0.5, jokou=JOKOU)
RIGHT_KW = dict(x_entry=X_ENTRY, edge_y=LANE, center_y=0.0, intersection_center=(XC, 0.0), keep_tol=0.5, jokou=JOKOU,
                inside_tol=3.0)


def plan_left(y_app):
    """ルールベースの左折の計画: 出口の車線に入り、turn_maneuver_check を満たす円のうち、後輪の内側が最も縁に沿うもの。"""
    best = None
    for cx in np.arange(X_ENTRY - 2.0, X_ENTRY + 8.01, 0.25):
        for Rf in np.arange(R_MIN_FRONT, 12.01, 0.25):
            xo = cx + Rf
            if not (XC - LANE + 0.5 * WIDTH + 0.1 <= xo <= XC - 0.5 * WIDTH - 0.1):
                continue
            F, i0, i1 = turn_path("left", y_app, Rf, cx, ds=0.1, pre=6.0, after=8.0)
            rp = DL.rear_axle_path(F, WB)
            u = F - rp["rear"]
            u /= np.hypot(*u.T)[:, None]
            rin = rp["rear"] + 0.5 * TRACK * np.stack([-u[:, 1], u[:, 0]], 1)
            hd = np.arctan2(u[:, 1], u[:, 0])
            mid = (hd >= math.radians(10)) & (hd <= math.radians(80))
            g = np.hypot(*(rin[mid] - CORNER_C).T) - RC
            if g.min() >= CLEAR and g.max() <= LEFT_KW["side_tol"]:
                if best is None or g.max() < best[0]:
                    best = (g.max(), cx, Rf)
    if best is None:
        raise RuntimeError("plan_left: no feasible turn")
    return best[1], best[2]


def ego_at(E, t):
    """時刻 t の前車軸・後車軸の中心(弧長で補間)。"""
    s = np.interp(t, E["time"], E["s"])
    j = np.clip(np.searchsorted(E["s"], s) - 1, 0, len(E["s"]) - 2)
    a = (s - E["s"][j]) / (E["s"][j + 1] - E["s"][j])
    f = E["front"][j] + a * (E["front"][j + 1] - E["front"][j])
    r = E["rear"][j] + a * (E["rear"][j + 1] - E["rear"][j])
    return f, r, float(np.interp(s, E["s"], E["v"]))


def body_poly(f, r):
    u = (f - r) / WB
    lft = np.array([-u[1], u[0]])
    return np.array([f + OVH * u + 0.5 * WIDTH * lft, r - OVH * u + 0.5 * WIDTH * lft,
                     r - OVH * u - 0.5 * WIDTH * lft, f + OVH * u - 0.5 * WIDTH * lft])


def bike_poly(x, y, yaw=0.0):
    c, s = math.cos(yaw), math.sin(yaw)
    u, l_ = np.array([c, s]), np.array([-s, c])
    return np.array([[x, y]]) + np.array([a * u + b * l_ for a, b in ((0.9, 0.3), (-0.9, 0.3), (-0.9, -0.3), (0.9, -0.3))])


def _sat_overlap(A, B):
    """凸四角形 A (4, 2) と、並んだ凸四角形 B (M, 4, 2) の重なり(分離軸の定理)。"""
    hit = np.ones(len(B), bool)
    ea = np.roll(A, -1, 0) - A
    for k in range(4):
        ax = np.array([-ea[k, 1], ea[k, 0]])
        pa, pb = A @ ax, B @ ax
        hit &= ~((pb.max(1) < pa.min()) | (pb.min(1) > pa.max()))
    eb = np.roll(B, -1, 1) - B
    for k in range(4):
        ax = np.stack([-eb[:, k, 1], eb[:, k, 0]], 1)
        pa = ax @ A.T
        pb = np.einsum("mij,mj->mi", B, ax)
        hit &= ~((pb.max(1) < pa.min(1)) | (pb.min(1) > pa.max(1)))
    return hit


def poly_dist(A, B):
    def sd(p, a, b):
        ab = b - a
        tt = np.clip((p - a) @ ab / (ab @ ab), 0, 1)
        return np.hypot(*(p - a - tt * ab))
    if _sat_overlap(A, B[None])[0]:
        return 0.0
    return min(min(sd(p, Q[k], Q[(k + 1) % 4]) for k in range(4)) for P, Q in ((A, B), (B, A)) for p in P)


def bikes_run(E, D0, vb, dt=0.05, keep=False):
    """後ろから来る自転車(縁石から 0.5 m の線を直進)を N 本同時に。前の帯(±0.5 m)に車体があれば止まれるように減速する。

    車体が真横・後ろから帯に入ってきたら(巻き込み)避けられない。返り値: 触れたか (N,)、最小距離の近似、記録。"""
    N = len(D0)
    _, r0, _ = ego_at(E, 0.0)
    xb = r0[0] - OVH - 0.9 - D0                      # 自転車の中心
    v = vb.copy()
    hit = np.zeros(N, bool)
    T = float(E["time"][-1])
    rec = []
    t = 0.0
    while t < T:
        f, r, ve = ego_at(E, t)
        poly = body_poly(f, r)
        # 帯の中の車体の点(辺を 0.1 m ごとに)の x
        pts = np.concatenate([np.linspace(poly[k], poly[(k + 1) % 4], 25) for k in range(4)])
        band = pts[np.abs(pts[:, 1] - Y_BIKE) < 0.5 * BIKE_W + BIKE_PASS, 0]
        front = xb + 0.9
        if len(band):
            bs = np.sort(band)
            j = np.searchsorted(bs, front)
            ahead = np.where(j < len(bs), bs[np.minimum(j, len(bs) - 1)], np.inf)
        else:
            ahead = np.full(N, np.inf)
        gap = ahead - front
        need = v * v / (2 * 3.0) + 1.0
        acc = np.where(gap < need, -3.0, np.where(v < vb, 1.0, 0.0))
        v = np.clip(v + acc * dt, 0.0, vb)
        xb = xb + v * dt
        B = np.stack([bike_poly(x, Y_BIKE) for x in xb]) if N <= 64 else _bike_polys(xb)
        hit |= _sat_overlap(poly, B)
        if keep:
            rec.append({"t": t, "xb": xb.copy(), "hit": hit.copy(), "f": f, "r": r, "v": ve})
        t += dt
    return hit, rec


def _bike_polys(xb):
    base = bike_poly(0.0, Y_BIKE)
    return base[None, :, :] + np.stack([xb, np.zeros_like(xb)], 1)[:, None, :]


def scene_intersection(D):
    print("== 4. 内輪差(閉形式 = 追跡曲線)")
    for Rf in (6.0, 8.0):
        F, i0, i1 = turn_path("left", 0.0, Rf, 0.0, ds=0.01, pre=3 * WB, after=0.5)
        rp = DL.rear_axle_path(F, WB)
        cc = np.array([0.0, Rf])
        rr = np.hypot(*(rp["rear"][i1] - cc))
        cf = DL.offtracking_circle(Rf, WB, Rf * math.pi / 2, track=TRACK)
        print("    R_f %.0f m: 90° の所の後車軸の半径 追跡曲線 %.4f m / 閉形式 %.4f m、内輪差 %.2f m(定常 %.2f m = アッカーマン %.2f m)" % (
            Rf, rr, cf["rear_radius"], cf["offtracking"], cf["steady"]["offtracking"],
            DL.ackermann_steer_angles(math.sqrt(Rf * Rf - WB * WB), WB, TRACK)["offtracking"]))
        gate("内輪差: 90° の所の後車軸の半径 = offtracking_circle(R_f %.0f m)±1 mm" % Rf, abs(rr - cf["rear_radius"]) < 1e-3,
             "差 %.2e m" % abs(rr - cf["rear_radius"]))
    print("== 5. 左折(隅切り半径 %.0f m、縁石 y = %.1f m、交差道路の縁石 x = %.1f m)" % (RC, CURB, CROSS_CURB))
    t = time.time()
    cx, Rf = plan_left(Y_KEEP)
    print("    計画(%.1f s): 前車軸の中心を y = %.2f m(車体の左側が外側線から 0.25 m)、x = %.2f m から半径 %.2f m の円" % (
        time.time() - t, Y_KEEP, cx, Rf))
    E_keep = ego_turn("left", Y_KEEP, Rf, cx)
    # 内輪差を無視: 前の左の車輪が隅切りから CLEAR の所を沿う(隅切りと同心の円)
    Rn = RC + CLEAR + 0.5 * TRACK
    E_naive = ego_turn("left", CORNER_C[1] - Rn, Rn, CORNER_C[0])
    E_centre = ego_turn("left", Y_CENTRE, Rf + (Y_KEEP - Y_CENTRE) * 0.0, cx)
    waiting = bike_poly(*(CORNER_C + (RC + 0.45) * np.array([math.cos(-math.pi / 4), math.sin(-math.pi / 4)])), math.pi / 4)
    res = {}
    for name, E in (("keep", E_keep), ("naive", E_naive), ("centre", E_centre)):
        chk = DL.turn_maneuver_check(traj_dict(E), kind="left", **LEFT_KW)
        dmin = min(poly_dist(body_poly(E["front"][i], E["rear"][i]), waiting) for i in range(0, len(E["front"]), 4))
        res[name] = (chk, dmin)
        print("    %s: %s、隅で待つ自転車まで最小 %.2f m%s" % (
            {"keep": "左に寄って計画の円", "naive": "前輪で隅に沿う(内輪差を無視)", "centre": "寄らない(車線の中央)"}[name],
            "違反なし" if chk["ok"] else "違反 " + " / ".join(chk["violations"]), dmin,
            "" if "rear_inner_gap_min" not in chk["metrics"] else "(後輪の内側と縁 %.2f〜%.2f m)" % (
                chk["metrics"]["rear_inner_gap_min"], chk["metrics"]["rear_inner_gap_max"])))
    gate("左折: 左に寄った計画は turn_maneuver_check で違反なし(S092)、隅で待つ自転車に触れない(S091)",
         res["keep"][0]["ok"] and res["keep"][1] > 0.2, "最小 %.2f m" % res["keep"][1])
    gate("門が自明でない: 前輪で隅に沿うと「内輪差で隅に入った」で自転車に触れる、寄らないと「左端に寄っていない」",
         any("内輪差" in v for v in res["naive"][0]["violations"]) and res["naive"][1] <= 0.0
         and any("寄っていない" in v for v in res["centre"][0]["violations"]),
         "前輪で沿う: 最小 %.2f m" % res["naive"][1])
    # 後ろから来る自転車: 素朴なモンテカルロと重要度サンプリング
    vb_all = D["v_bike"]
    rng = np.random.default_rng(55)
    D_LO, D_HI = 15.0, 400.0                       # 合図の時点でミラーに映らない(15 m より後ろ)〜 400 m(仮定、一様)
    T_end = float(E_centre["time"][-1])
    D_Q = min(D_HI, float(vb_all.max()) * T_end + 5.0)          # これより遠い自転車は終わるまでに追いつけない
    print("    後ろの自転車: 距離 D0 ~ U(%.0f, %.0f) m、速さ = 標本の門を通った値。試し打ちの D0 の範囲 %.0f〜%.0f m(追いつける上限 "
          "= 最速 %.1f km/h × %.1f s)" % (D_LO, D_HI, D_LO, D_Q, 3.6 * vb_all.max(), T_end))
    out = {}
    t = time.time()
    vg = np.linspace(vb_all.min(), vb_all.max(), 25)
    MARGIN = 3.0
    for name, E in (("keep", E_keep), ("centre", E_centre)):
        # 試し打ち(速さ 25 段 × 距離 0.25 m 刻み): 速さごとに巻き込みが起きうる D0 の帯を見つけ、提案分布をその ± 3 m に絞る。
        # 頻度が低いだけの出来事(ちょうど曲がる時に追いつく自転車)は落とさず、重み p/q で数える。
        dg = np.arange(D_LO, D_Q, 0.25)
        Dg, Vg = np.meshgrid(dg, vg)
        hg, _ = bikes_run(E, Dg.ravel(), Vg.ravel())
        hg = hg.reshape(Dg.shape)
        lo_g = np.array([dg[h].min() if h.any() else np.nan for h in hg])
        if hg.any():
            print("      試し打ち: 巻き込みが起きる速さ %.1f〜%.1f km/h、D0 の帯の幅 %.2f〜%.2f m" % (
                3.6 * vg[hg.any(1)].min(), 3.6 * vg[hg.any(1)].max(),
                np.nanmin(np.array([dg[h].max() - dg[h].min() for h in hg if h.any()])),
                np.nanmax(np.array([dg[h].max() - dg[h].min() for h in hg if h.any()]))))
        hi_g = np.array([dg[h].max() if h.any() else np.nan for h in hg])

        def band(v):
            j = np.clip(np.searchsorted(vg, v) - 1, 0, len(vg) - 2)
            lo = np.fmin(lo_g[j], lo_g[j + 1]) - MARGIN
            hi = np.fmax(hi_g[j], hi_g[j + 1]) + MARGIN
            none = np.isnan(lo)                      # 両隣の速さで巻き込みが 1 つも無い = その速さでは起きない(仮定、MC で確かめる)
            lo = np.where(none, D_LO, np.maximum(lo, D_LO))
            hi = np.where(none, D_LO, np.minimum(hi, D_HI))
            return lo, hi
        d_mc = rng.uniform(D_LO, D_HI, N_MC)
        v_mc = vb_all[rng.integers(0, len(vb_all), N_MC)]
        h_mc, _ = bikes_run(E, d_mc, v_mc)
        plo, phi_ = band(vb_all)
        able = phi_ > plo                            # 巻き込みが起きうる速さ(提案は速さもこの集合に絞る)
        frac = float(able.mean())
        pool = vb_all[able] if able.any() else vb_all
        v_is = pool[rng.integers(0, len(pool), N_IS)]
        qlo, qhi = band(v_is)
        d_is = np.where(qhi > qlo, rng.uniform(qlo, np.maximum(qhi, qlo + 1e-9)), D_LO)
        h_is, _ = bikes_run(E, d_is, v_is)
        h_is &= qhi > qlo                            # 提案の質量が 0 の速さは数えない(重み 0)
        w = (frac if able.any() else 1.0) * (qhi - qlo) / (D_HI - D_LO)
        p_mc = h_mc.mean()
        se_mc = math.sqrt(max(p_mc, 1.0 / N_MC) * (1 - p_mc) / N_MC)
        p_is = float(np.mean(w * h_is))
        se_is = float(np.std(w * h_is) / math.sqrt(N_IS))
        mlo, mhi = band(v_mc)
        far = bool(np.any(h_mc & ((d_mc < mlo) | (d_mc > mhi))))
        out[name] = dict(p_mc=p_mc, se_mc=se_mc, p_is=p_is, se_is=se_is, far=far, n_mc=int(h_mc.sum()), n_is=int(h_is.sum()),
                         hits=(d_mc[h_mc], v_mc[h_mc]), w_mean=float(w.mean()), hits_is=(d_is[h_is], v_is[h_is]),
                         grid=(dg, vg, hg), pilot=int(hg.sum()), frac=frac)
        print("    %s: 試し打ち %d 点で巻き込み %d、起きうる速さの割合 %.3f、提案の平均の重み %.5f。素朴 MC %d 試行で巻き込み %d(p = %.5f ± %.5f)、"
              "重要度 %d 試行で %d(p = %.5f ± %.5f)、提案の外の巻き込み %s" % (
                  "左に寄る" if name == "keep" else "寄らない", hg.size, int(hg.sum()), frac, w.mean(), N_MC, out[name]["n_mc"], p_mc,
                  se_mc, N_IS, out[name]["n_is"], p_is, se_is, "あり" if far else "なし"))
    print("    (自転車の模擬 %.1f s)" % (time.time() - t))
    k, c = out["keep"], out["centre"]
    gate("左に寄ると後ろの自転車は入り込めない: 試し打ちの格子・素朴 MC・重要度サンプリングとも巻き込み 0",
         k["n_mc"] == 0 and k["n_is"] == 0 and k["pilot"] == 0,
         "%d / %d" % (k["n_mc"], k["n_is"]))
    # 素朴 MC の件数は Poisson(λ = N_MC · p_IS)。両側の正確な p 値(稀なので正規近似は使わない)
    lam = N_MC * c["p_is"]
    pmf = [math.exp(-lam)]
    for k_ in range(1, c["n_mc"] + 1):
        pmf.append(pmf[-1] * lam / k_)
    cdf = sum(pmf)
    sf = 1.0 - cdf + pmf[-1]
    p_two = min(1.0, 2.0 * min(cdf, sf))
    gate("寄らないと巻き込みが残り、素朴 MC の件数は重要度サンプリングの推定と食い違わない(Poisson の両側 p > 0.001)、"
         "提案の外の巻き込みは無い(提案分布が台を覆う)、同じ精度に要る試行が少ない",
         c["n_is"] > 10 and p_two > 0.001 and not c["far"] and c["se_is"] * math.sqrt(N_IS) < c["se_mc"] * math.sqrt(N_MC),
         "p_IS = %.5f ± %.5f → MC %d 試行の期待 %.1f 件、実際 %d 件(両側 p = %.2f)、1 試行あたりの標準偏差 %.4f vs %.4f" % (
             c["p_is"], c["se_is"], N_MC, lam, c["n_mc"], p_two, c["se_is"] * math.sqrt(N_IS), c["se_mc"] * math.sqrt(N_MC)))
    print("== 6. 右折(交差点の中心 (%.0f, 0))" % XC)
    best = None
    y_r = 0.25 + 0.5 * WIDTH
    for cxr in np.arange(X_ENTRY, XC + 0.01, 0.25):
        for Rr in np.arange(4.0, 14.01, 0.25):
            xo = cxr + Rr
            if not (XC + 0.5 * WIDTH + 0.1 <= xo <= XC + LANE - 0.5 * WIDTH - 0.1):
                continue
            ccen = np.array([cxr, y_r - Rr])
            d = np.hypot(*(np.array([XC, 0.0]) - ccen)) - Rr       # > 0 = 中心が円の外 = 軌跡の左
            if 0.3 <= d <= 1.5 and (best is None or Rr > best[2]):
                best = (d, cxr, Rr)
    _, cxr, Rr = best
    ER = ego_turn("right", y_r, Rr, cxr)
    EB = ego_turn("right", y_r, Rr, XC + 2.0)              # 大回り(中心を過ぎてから)
    EE = ego_turn("right", y_r, 4.0, X_ENTRY - 0.5)        # 早回り(手前で小さく)
    rr = {k: DL.turn_maneuver_check(traj_dict(E), kind="right", **RIGHT_KW) for k, E in (("plan", ER), ("big", EB), ("early", EE))}
    for k, v in rr.items():
        print("    %s: %s(中心まで %.2f m)" % ({"plan": "計画(中心のすぐ内側)", "big": "大回り", "early": "早回り"}[k],
                                         "違反なし" if v["ok"] else "違反 " + " / ".join(v["violations"]), v["metrics"]["center_distance"]))
    gate("右折: 中央に寄り交差点の中心のすぐ内側を徐行 —— 違反なし(S093)", rr["plan"]["ok"], "中心まで %.2f m" % rr["plan"]["metrics"]["center_distance"])
    gate("門が自明でない: 大回りは「外側を回った」、早回りは「すぐ内側でない」",
         any("外側" in v for v in rr["big"]["violations"]) and any("すぐ内側でない" in v for v in rr["early"]["violations"]))
    return {"E_keep": E_keep, "E_naive": E_naive, "E_centre": E_centre, "ER": ER, "EB": EB, "EE": EE, "waiting": waiting,
            "res": res, "mc": out, "rr": rr, "D_Q": D_Q}


# ───────────────────────────── 図(FULLSEYE_FIGURE_DIR のときだけ) ─────────────────────────────
GROUND_FAR = np.array([0.42, 0.56, 0.36])     # 草地(地平線より下で何も当たらない画素)
GRASS = (0.42, 0.56, 0.36)
WALK = (0.72, 0.72, 0.68)
YELLOW = (0.95, 0.78, 0.10)
WHITE = (0.95, 0.95, 0.92)
ROAD = (0.40, 0.41, 0.43)


def _txt(img, s, xy, anchor="lt", fs=12):
    import annotate as AN
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=max(9, fs)), dtype=np.float64)


def _box_mesh(L, W, H, z0=0.0):
    V = np.array([[x, y, z] for z in (z0, z0 + H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)])
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]])
    return V, F


def _mesh(parts):
    V = np.zeros((0, 3))
    F = np.zeros((0, 3), np.int64)
    C = []
    for v, f, c in parts:
        F = np.vstack([F, f + len(V)])
        V = np.vstack([V, v])
        C.append(np.tile(np.asarray(c, float), (len(f), 1)))
    return {"V": V, "F": F, "color": np.vstack(C)}


def bicycle_mesh():
    """自転車 + 乗る人(箱で組む。長さ 1.8 m、幅 0.5 m、高さ 1.75 m)。"""
    parts = []
    for dx in (-0.55, 0.55):
        v, f = _box_mesh(0.66, 0.06, 0.66)
        parts.append((v + [dx, 0, 0], f, (0.10, 0.10, 0.12)))
    v, f = _box_mesh(1.1, 0.06, 0.08, 0.55)
    parts.append((v, f, (0.15, 0.45, 0.85)))
    v, f = _box_mesh(0.30, 0.50, 0.62, 0.85)
    parts.append((v + [-0.05, 0, 0], f, (0.95, 0.85, 0.20)))
    v, f = _box_mesh(0.22, 0.22, 0.24, 1.48)
    parts.append((v + [0.02, 0, 0], f, (0.92, 0.92, 0.95)))
    m = _mesh(parts)
    m.update(label=14, dims=(1.8, 0.6, 1.75))
    return m


def _ribbon(P, nrm, n0, n1, z0=0.0, z1=None):
    """中心線 P (M, 2) と法線から、横 n0..n1 の帯(z1 を与えると n0 の位置の縦の壁 z0..z1)。"""
    A = P + n0 * nrm
    M = len(P)
    if z1 is None:
        B = P + n1 * nrm
        V = np.vstack([np.c_[A, np.full(M, z0)], np.c_[B, np.full(M, z0)]])
    else:
        V = np.vstack([np.c_[A, np.full(M, z0)], np.c_[A, np.full(M, z1)]])
    i = np.arange(M - 1)
    F = np.vstack([np.stack([i, i + 1, M + i + 1], 1), np.stack([i, M + i + 1, M + i], 1)])
    return V, F


def _place(V, q, h):
    c, s = math.cos(h), math.sin(h)
    return V @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]) + [q[0], q[1], 0]


def world_curve(C):
    import driveworld as DW
    w = DW._empty_world()
    k = np.arange(0, len(C.S), 4)                                  # 1 m ごと
    P, nrm = C.P[k], C.nrm[k]
    # 草地は三角形にしない(地平線より下の空の画素を render で草の色に塗る。近くの大きな三角形は描くのが遅い)
    V, F = _ribbon(P, nrm, -CURB, CURB)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    for a, b, col, nm in ((-0.08, 0.08, YELLOW, "centre"), (LANE - 0.075, LANE + 0.075, WHITE, "edge"),
                          (-LANE - 0.075, -LANE + 0.075, WHITE, "edge")):
        V, F = _ribbon(P, nrm, a, b, z0=0.006)
        DW.world_add(w, V, F, 9, col, name=nm)
    for sd in (1.0, -1.0):
        V, F = _ribbon(P, nrm, sd * CURB, sd * (CURB + 2.5), z0=0.15)
        DW.world_add(w, V, F, 1, WALK, name="walk")
        V, F = _ribbon(P, nrm, sd * CURB, 0, z0=0.0, z1=0.15)
        DW.world_add(w, V, F, 1, DW._KERB_COLOR, name="kerb")
    rng = np.random.default_rng(4)
    for j in range(0, len(C.S), 60):                                 # 15 m ごとに建物
        for sd in (1.0, -1.0):
            if rng.random() < 0.6:
                continue
            q = C.P[j] + sd * (CURB + 9.0 + rng.uniform(0, 4)) * C.nrm[j]
            V, F = _box_mesh(rng.uniform(6, 10), rng.uniform(5, 8), rng.uniform(4, 11))
            col = tuple(rng.uniform(0.5, 0.82) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
            DW.world_add(w, _place(V, q, C.H[j]), F, 6, col, name="building")
    jm = int(np.searchsorted(C.S, 0.5 * sum(S_CORNER)))           # 曲がり角の内側の塀(見通しの悪い曲がり角)
    for jj in range(jm - 120, jm + 121, 12):
        q = C.P[jj] + (CURB + 3.2) * C.nrm[jj]
        V, F = _box_mesh(3.2, 0.3, 2.0)
        DW.world_add(w, _place(V, q, C.H[jj]), F, 6, (0.62, 0.58, 0.52), name="wall")
    return w


def _corner_polys():
    polys = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x_in, y_in = XC + sx * CURB, sy * CURB
            cxf, cyf = x_in + sx * RC, y_in + sy * RC                # 隅切りの中心(歩道の側)
            th = np.linspace(0, math.pi / 2, 17)
            arc = np.stack([cxf - sx * RC * np.sin(th), cyf - sy * RC * np.cos(th)], 1)   # (cxf, y_in) → (x_in, cyf)
            polys.append(np.vstack([arc, [[x_in, sy * 90.0], [XC + sx * 90.0, sy * 90.0], [XC + sx * 90.0, y_in]]]))
    return polys


def _quad(xa, xb, ya, yb, z=0.006):
    return np.array([[xa, ya, z], [xb, ya, z], [xb, yb, z], [xa, yb, z]]), np.array([[0, 1, 2], [0, 2, 3]])


def world_cross():
    import driveworld as DW
    import driveterrain as DT
    w = DW._empty_world()
    V, F = DW._grid_plane(-80, 150, -CURB, CURB, step=2.5)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    V, F = DW._grid_plane(XC - CURB, XC + CURB, -90, 100, step=2.5, z=0.001)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    for poly in _corner_polys():
        tri = DW.polygon_triangulate(poly)
        DW.world_add(w, np.c_[poly, np.full(len(poly), 0.15)], tri, 1, WALK, name="walk")
        edge = np.vstack([poly[-1:], poly[:18]])
        for k in range(len(edge) - 1):
            a, b = edge[k], edge[k + 1]
            Vk = np.array([[a[0], a[1], 0.0], [b[0], b[1], 0.0], [b[0], b[1], 0.15], [a[0], a[1], 0.15]])
            DW.world_add(w, Vk, np.array([[0, 1, 2], [0, 2, 3]]), 1, DW._KERB_COLOR, name="kerb")
    xa_far = XC + CURB + RC
    for xa, xb in ((-80.0, X_ENTRY - 1.0), (xa_far + 1.0, 150.0)):
        for ya, yb in ((-0.075, 0.075), (LANE - 0.075, LANE + 0.075), (-LANE - 0.075, -LANE + 0.075)):
            for x0 in np.arange(xa, xb, 10.0):                        # 10 m ごとに切る(カメラの後ろの三角形は描かれない)
                V, F = _quad(x0, min(x0 + 10.0, xb), ya, yb)
                DW.world_add(w, V, F, 9, WHITE, name="line")
    for y0, y1 in ((CURB + RC + 1.0, 100.0), (-90.0, -CURB - RC - 1.0)):
        for xa, xb in ((XC - 0.075, XC + 0.075), (XC - LANE - 0.075, XC - LANE + 0.075), (XC + LANE - 0.075, XC + LANE + 0.075)):
            for ya in np.arange(y0, y1, 10.0):
                V, F = _quad(xa, xb, ya, min(ya + 10.0, y1))
                DW.world_add(w, V, F, 9, WHITE, name="line")
    rng = np.random.default_rng(8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for k in range(3):
                for m in range(2):
                    if k == 0 and m == 0:
                        continue                                     # 角は空けて見通す
                    cx = XC + sx * (CURB + 9.0 + 12.0 * k)
                    cy = sy * (CURB + 9.0 + 12.0 * m)
                    V, F = _box_mesh(8.0, 8.0, rng.uniform(5, 13), 0.15)
                    col = tuple(rng.uniform(0.5, 0.82) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
                    DW.world_add(w, V + [cx, cy, 0], F, 6, col, name="building")
    for x0 in np.arange(-40.0, X_ENTRY - 15.0, 20.0):              # 道沿いの建物
        for sy in (-1, 1):
            V, F = _box_mesh(10.0, 6.0, rng.uniform(4, 11), 0.15)
            col = tuple(rng.uniform(0.5, 0.82) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
            DW.world_add(w, V + [x0, sy * (CURB + 10.0), 0], F, 6, col, name="building")
    ids = {"bike": DT.add_mesh_object(w, bicycle_mesh(), -900.0, 0.0, 0.0, name="bike"),
           "wait": DT.add_mesh_object(w, bicycle_mesh(), -900.0, 10.0, 0.0, name="bike_wait")}
    return w, ids


def render(w, pose, K, W, H):
    import driveworld as DW
    v = DW.world_camera(w, pose, K, W, H)
    bg = v["label"] < 0
    if bg.any():
        rr, cc = np.nonzero(bg)
        d = np.stack([(cc - K[0, 2]) / K[0, 0], -(rr - K[1, 2]) / K[1, 1], -np.ones(len(rr))], 1) @ np.asarray(pose)[:3, :3]
        down = d[:, 2] < 0
        v["color"][rr[down], cc[down]] = GROUND_FAR
    return v


def eye_pose(rear, u, pitch=-0.04):
    import driveworld as DW
    lft = np.array([-u[1], u[0]])
    e = np.r_[rear + 1.55 * u - 0.37 * lft, 1.2]
    return DW.camera_pose(e, e + np.array([u[0], u[1], pitch]))


class Top:
    """上から見た 2D の図(PIL で描く)。world (x, y) → 画素。"""

    def __init__(self, W, H, xl, yl, bg=(236, 238, 232)):
        from PIL import Image, ImageDraw
        self.W, self.H = W, H
        self.s = min(W / (xl[1] - xl[0]), H / (yl[1] - yl[0]))
        self.x0, self.y1 = xl[0], yl[1]
        self.im = Image.new("RGB", (W, H), bg)
        self.d = ImageDraw.Draw(self.im)

    def p(self, P):
        P = np.atleast_2d(P)
        return [(float((x - self.x0) * self.s), float((self.y1 - y) * self.s)) for x, y in P]

    def poly(self, P, fill=None, outline=None, width=1):
        self.d.polygon(self.p(P), fill=fill, outline=outline, width=width)

    def line(self, P, fill, width=2):
        if len(P) > 1:
            self.d.line(self.p(P), fill=fill, width=width)

    def circle(self, c, r, outline=None, fill=None, width=2):
        (x, y), = self.p(c)
        rr = r * self.s
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=outline, fill=fill, width=width)

    def arr(self):
        return np.asarray(self.im, dtype=np.float64) / 255.0


def _draw_cross(T):
    """交差点の地図(上から)。"""
    T.poly(np.array([[-80, -CURB], [150, -CURB], [150, CURB], [-80, CURB]]), fill=(110, 112, 116))
    T.poly(np.array([[XC - CURB, -90], [XC + CURB, -90], [XC + CURB, 100], [XC - CURB, 100]]), fill=(110, 112, 116))
    for poly in _corner_polys():
        T.poly(poly, fill=(196, 196, 186), outline=(150, 150, 140))
    T.line(np.array([[-80, 0], [X_ENTRY - 1, 0]]), (245, 245, 235), 2)
    for e in (LANE, -LANE):
        T.line(np.array([[-80, e], [X_ENTRY, e]]), (245, 245, 235), 1)
    th = np.linspace(-math.pi / 2, 0, 25)
    ring = np.stack([np.cos(th), np.sin(th)], 1)
    T.poly(np.vstack([CORNER_C + RC * ring, (CORNER_C + (RC + CLEAR) * ring)[::-1]]), fill=(250, 214, 160))


def _inner_wheels(E):
    u = (E["front"] - E["rear"]) / WB
    lft = np.c_[-u[:, 1], u[:, 0]]
    return E["front"] + 0.5 * TRACK * lft, E["rear"] + 0.5 * TRACK * lft


def fig_dashcam(SM, CV, IX):
    """主図: 車載カメラ。場面 1 = カーブの手前で減速して車線の中で曲がる、場面 2 = 左に寄って左折(後ろの自転車は入れない)、
    場面 3 = 寄らずに左折(後ろの自転車が左に入り込み巻き込む)。"""
    import driveworld as DW
    Wv, Hv = VID_WH
    small = Wv < 500
    fsz = 9 if small else 12
    K = DW.camera_intrinsics(36.0, Wv, Hv)
    frames = []
    C = CV["C"]
    w = world_curve(C)
    rec = CV["good"]["rec"]
    i0 = int(np.argmin(CV["good"]["V"][:, int(np.searchsorted(C.S, 0.5 * sum(S_ARC1)))]))      # 円弧で最も遅い人
    mu = CV["drv"]["mu"][i0]
    s_from, s_to = S_ARC1[0] - 60.0, S_CORNER[1] + 25.0
    last_s, last_t = -1e9, -1e9
    n1 = 0
    sw = int(Wv * 0.22)
    step_s, step_t = (3.0, 1.0) if small else (1.8, 0.6)
    for r in rec:
        s = r["s"][i0]
        if s < s_from or s > s_to or (s - last_s < step_s and r["t"] - last_t < step_t):
            continue
        last_s, last_t = s, r["t"]
        X = r["X"][i0]
        u = np.array([math.cos(X[2]), math.sin(X[2])])
        rear = X[:2] - CAR["l_r"] * u
        f = render(w, eye_pose(rear, u), K, Wv, Hv)["color"].copy()
        T = Top(sw, sw, (-1.15, 1.15), (-1.15, 1.15), bg=(250, 250, 250))
        T.line(np.array([[-1.1, 0], [1.1, 0]]), (190, 190, 190), 1)
        T.line(np.array([[0, -1.1], [0, 1.1]]), (190, 190, 190), 1)
        T.circle((0, 0), 1.0, outline=(40, 40, 40), width=2)
        T.circle((0, 0), CV["drv"]["a_lat"][i0] / (mu * DL.G), outline=(120, 160, 230), width=1)
        ax_, ay_ = r["ax"][i0] / (mu * DL.G), r["ay"][i0] / (mu * DL.G)
        T.circle((-ay_, ax_), 0.07, fill=(220, 60, 40), outline=(120, 20, 10), width=1)
        f[8:8 + sw, Wv - sw - 8:Wv - 8] = T.arr()
        f = _txt(f, "摩擦円", (Wv - sw // 2 - 8, sw + 10), anchor="ct", fs=fsz - 1)
        j = int(np.searchsorted(C.S, s))
        kl = C.K[j] / (1.0 - 1.5 * C.K[j])
        n_cg = float(DL.lateral_offset(X[:2], C.P, start_index=j, window=60)["n"]) - 1.5
        he = math.atan2(math.sin(X[2] - C.H[j]), math.cos(X[2] - C.H[j]))
        vv = max(float(r["v"][i0]), 0.6)
        kv = X[4] / vv
        try:
            tl = min(DL.time_to_line_crossing(n_cg, he, kv, vv, line_offset=LANE - 1.5 - 0.5 * WIDTH, lane_curvature=kl),
                     DL.time_to_line_crossing(n_cg, he, kv, vv, line_offset=-1.5 + 0.5 * WIDTH, lane_curvature=kl))
        except ValueError:
            tl = 0.0
        if C.zone[j]:
            zone = "曲がり角の附近(徐行)"
        elif S_ARC1[0] - L1 <= s <= S_ARC1[1] + L1:
            zone = "カーブ R %.0f m" % R1
        else:
            zone = "直線"
        lines = ["場面 1: カーブの手前で減速し、車線の中で曲がる", "%5.1f km/h(計画どおり)  %s" % (3.6 * vv, zone),
                 "摩擦円の使用率 %.2f(μ %.2f)" % (math.hypot(ax_, ay_), mu),
                 "線まで 右 %.2f / 左 %.2f m  TLC %s" % (r["n"][:, i0].min(), LANE - r["n"][:, i0].max(),
                                                       "∞" if not math.isfinite(tl) else "%.1f s" % tl)]
        f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
        frames.append(np.clip(f, 0, 1))
        n1 += 1
    wc, ids = world_cross()
    dd, vv_ = IX["mc"]["centre"]["hits_is"]
    k = int(np.argmin(np.abs(vv_ - np.median(vv_))))
    D0, vb = float(dd[k]), float(vv_[k])
    wp = IX["waiting"].mean(0)
    DW.world_move(wc, ids["wait"], float(wp[0]), float(wp[1]), math.pi / 4)
    n2 = {}
    for tag, E in (("keep", IX["E_keep"]), ("centre", IX["E_centre"])):
        hit, rec2 = bikes_run(E, np.array([D0]), np.array([vb]), keep=True)
        n2[tag] = bool(hit[0])
        t_hit = next((q["t"] for q in rec2 if q["hit"][0]), None)
        fl, rl = _inner_wheels(E)
        m = E["front"][:, 0] > X_ENTRY - 16
        for q in rec2[::(6 if small else 4)]:
            if q["f"][0] < X_ENTRY - 40.0:
                continue
            if t_hit is not None and q["t"] > t_hit + 1.6:
                break
            u = (q["f"] - q["r"]) / WB
            DW.world_move(wc, ids["bike"], float(q["xb"][0]), Y_BIKE, 0.0)
            f = render(wc, eye_pose(q["r"], u), K, Wv, Hv)["color"].copy()
            T = Top(sw, int(sw * 1.1), (X_ENTRY - 16, XC + 6), (-3.5, 20))
            _draw_cross(T)
            T.poly(IX["waiting"], fill=(240, 200, 30), outline=(90, 70, 0))
            T.poly(bike_poly(q["xb"][0], Y_BIKE), fill=(240, 200, 30), outline=(90, 70, 0))
            T.line(rl[m], (40, 90, 220), 2)
            body = body_poly(q["f"], q["r"])
            T.poly(body, fill=(60, 120, 230) if not q["hit"][0] else (220, 50, 40), outline=(20, 30, 60))
            f[8:8 + T.H, Wv - sw - 8:Wv - 8] = T.arr()
            f = _txt(f, "上から" if small else "上から(青 = 後輪の内側)", (Wv - sw // 2 - 8, T.H + 10), anchor="ct", fs=fsz - 1)
            title = "場面 2: 左に寄って左折" if tag == "keep" else "場面 3: 寄らずに左折"
            gap_txt = ("左の縁石までの隙 %.2f m" % (CURB - body[:, 1].max())) if abs(u[1]) < 0.17 else "曲がっている"
            lines = [title, "%4.1f km/h  %s" % (3.6 * q["v"], gap_txt),
                     "後ろの自転車 %.0f km/h" % (3.6 * vb)]
            if q["hit"][0]:
                lines.append("巻き込み(車体が自転車に触れた)")
            elif tag == "keep" and q["xb"][0] < q["r"][0]:
                lines.append("自転車は左に入れず後ろで待つ")
            f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
            frames.append(np.clip(f, 0, 1))
    fps = 6.0
    figs.save_video("lateral_dashcam", frames, fps=fps, gif_every=2, gif_width=480,
                    caption="主図(車載カメラ %d × %d、%d コマ)。場面 1(%d コマ): 半径 %.0f m のカーブと半径 %.0f m の曲がり角"
                            "(道路構造令の設計速度 50・20 km/h の表の値、クロソイドでつなぐ)。curvature_speed_plan の計画どおりカーブの手前で減速し、"
                            "曲がり角の附近は 10 km/h、pure pursuit(注視距離は 2 自由度の定常の横ずれ ≤ %.2f m で上限)で車線の中を走る。右上 = 摩擦円"
                            "(黒 = μg、青 = この人の横加速度の上限、赤 = 今の加速度)。場面 2: 外側線から 0.25 m に寄って左折、後ろから %.0f km/h の"
                            "自転車は左に入れない(巻き込み %s)。場面 3: 車線の中央のまま左折、同じ自転車(同じ距離・速さ)が左に入り込み、"
                            "曲がる車体に触れる(巻き込み %s)。右上 = 上から見た図(青の線 = 後輪の内側の軌跡、橙 = 隅で人・自転車が待つ所)。"
                            % (Wv, Hv, len(frames), n1, R1, R2, OFFSET_BUDGET, 3.6 * vb, "あり" if n2["keep"] else "なし",
                               "あり" if n2["centre"] else "なし"))
    return n2, len(frames), n1


def fig_birdseye(CV):
    """上から見た動画: 計画した人(青)と計画なし(赤)が同じカーブを走る。下に速度の帯と摩擦円。"""
    from PIL import Image, ImageDraw
    C = CV["C"]
    good = CV["good"]
    i0 = 0
    nop_rec = drive(C, {k: v[:1] for k, v in CV["drv"].items()}, plan=False, cap=True, record=True)["rec"]
    W, H = (480, 440) if REDUCED else (720, 660)
    s_from, s_to = S_ARC1[0] - 40.0, S_CORNER[1] + 25.0
    mask = (C.S > s_from - 10) & (C.S < s_to + 10)
    xl = (C.P[mask, 0].min() - 15, C.P[mask, 0].max() + 15)
    yl = (C.P[mask, 1].min() - 15, C.P[mask, 1].max() + 15)
    Hm = int(H * 0.6)
    frames = []
    vb_lo, vb_hi = good["V"].min(0), good["V"].max(0)
    sa = np.array([q["s"][i0] for q in good["rec"]])
    sb = np.array([q["s"][0] for q in nop_rec])
    used = []
    for s in np.arange(s_from, s_to, 3.0 if REDUCED else 1.5):
        qa = good["rec"][min(int(np.searchsorted(sa, s)), len(sa) - 1)]
        qb = nop_rec[min(int(np.searchsorted(sb, s)), len(sb) - 1)]
        halves = []
        for rec_, q, col, ii, lab in ((good["rec"], qa, (60, 120, 230), i0, "計画どおり"), (nop_rec, qb, (220, 60, 40), 0, "計画なし 50 km/h")):
            X = q["X"][ii]
            u = np.array([math.cos(X[2]), math.sin(X[2])])
            rr = X[:2] - CAR["l_r"] * u
            half = 30.0
            T = Top(W // 2, Hm, (X[0] - half, X[0] + half), (X[1] - half * Hm / (W // 2), X[1] + half * Hm / (W // 2)),
                    bg=(120, 150, 100))
            T.poly(np.vstack([C.P[mask] + CURB * C.nrm[mask], (C.P[mask] - CURB * C.nrm[mask])[::-1]]), fill=(110, 112, 116))
            T.line(C.P[mask], (240, 200, 30), 2)
            T.line(C.P[mask] + LANE * C.nrm[mask], (245, 245, 235), 1)
            T.line(C.P[mask] - LANE * C.nrm[mask], (245, 245, 235), 1)
            mu = CV["drv"]["mu"][ii]
            past = [p for p in rec_[::5] if p["t"] <= q["t"] and p["t"] > q["t"] - 12.0]
            for p in past:                                   # 通った跡(青 = 摩擦円の中、赤 = 外)
                us = math.hypot(p["ax"][ii], p["ay"][ii]) / (mu * DL.G)
                T.circle(p["X"][ii][:2], 0.35, fill=(70, 140, 255) if us <= 1 else (255, 70, 50), width=0)
            T.poly(body_poly(rr + WB * u, rr), fill=col, outline=(20, 20, 20), width=2)
            img = T.arr()
            img = _txt(img, lab, (6, Hm - 6), anchor="lb", fs=11)
            halves.append(img)
        top = np.hstack(halves)
        top[:, W // 2 - 1:W // 2 + 1] = 1.0
        Wp, Hp = int(W * 0.66), H - Hm
        im = Image.new("RGB", (Wp, Hp), (255, 255, 255))
        d = ImageDraw.Draw(im)
        sx = lambda v: 40 + (v - s_from) / (s_to - s_from) * (Wp - 50)  # noqa: E731
        sy = lambda v: Hp - 20 - v * 3.6 / 60.0 * (Hp - 50)  # noqa: E731
        jj = np.nonzero((C.S >= s_from) & (C.S <= s_to))[0][::4]
        zs = C.S[C.zone]
        d.rectangle([sx(max(zs.min(), s_from)), sy(60 / 3.6), sx(min(zs.max(), s_to)), sy(0)], fill=(253, 225, 190))
        d.polygon([(sx(C.S[j]), sy(vb_hi[j])) for j in jj] + [(sx(C.S[j]), sy(vb_lo[j])) for j in jj[::-1]], fill=(190, 210, 245))
        d.line([(sx(C.S[j]), sy(good["V"][i0, j])) for j in jj], fill=(40, 90, 220), width=2)
        d.line([(sx(s_from), sy(V_ROAD)), (sx(s_to), sy(V_ROAD))], fill=(220, 60, 40), width=2)
        d.line([(sx(s), sy(0)), (sx(s), sy(60 / 3.6))], fill=(0, 0, 0), width=1)
        d.rectangle([40, 30, Wp - 10, Hp - 20], outline=(80, 80, 80))
        pl = np.asarray(im, np.float64) / 255.0
        Wf = W - Wp
        Tf = Top(Wf, Hp, (-1.35, 1.35), (-1.5, 1.2), bg=(255, 255, 255))
        Tf.circle((0, 0), 1.0, outline=(30, 30, 30), width=2)
        mu = CV["drv"]["mu"][i0]
        ub = math.hypot(qb["ax"][0], qb["ay"][0]) / (mu * DL.G)
        for q, col, ii in ((qb, (220, 60, 40), 0), (qa, (60, 120, 230), i0)):
            a, b = q["ax"][ii] / (mu * DL.G), q["ay"][ii] / (mu * DL.G)
            Tf.circle((float(np.clip(-b, -1.3, 1.3)), float(np.clip(a, -1.3, 1.3))), 0.07, fill=col, outline=(0, 0, 0), width=1)
        fr = np.vstack([top, np.hstack([pl, Tf.arr()])])
        fr = _txt(fr, "青 = 計画どおり %.0f km/h   赤 = 計画なし 50 km/h(摩擦円の使用率 %.2f%s)" % (
            3.6 * qa["v"][i0], ub, "、円の外" if ub > 1 else ""), (6, 6), fs=12 if not REDUCED else 10)
        fr = _txt(fr, "速さ 0–60 km/h と距離(帯 = %d 人の計画、橙 = 徐行の区間)" % N_DRIVERS, (44, Hm + 4), fs=10)
        fr = _txt(fr, "摩擦円", (Wp + Wf // 2, Hm + 4), anchor="ct", fs=10)
        frames.append(np.clip(fr, 0, 1))
        used.append(ub)
    figs.save_video("lateral_birdseye", frames, fps=8.0, gif_every=2, gif_width=480,
                    caption="上から見た動画(%d コマ)。同じ運転者(μ %.2f)を、curvature_speed_plan の計画どおり(上左、青)と 50 km/h のまま(上右、赤)で走らせ、"
                            "同じ道のりの所を並べる(60 m 四方、車について動く。点 = 過去 12 s の通った跡、青 = 摩擦円の中、赤 = 外)。"
                            "下左 = 速さ(青の帯 = %d 人の計画の最小〜最大、青の線 = この人、赤 = 計画なし、橙 = 曲がり角の附近の徐行の区間、黒の縦線 = 今)、"
                            "下右 = 摩擦円(加速度 / μg、横 = 横加速度(左旋回で左)・縦 = 縦加速度)。計画なしの点は曲がり角で円の外へ出る(使用率 最大 %.2f "
                            "= 線形モデルの外、実際には滑る)。" % (len(frames), CV["drv"]["mu"][i0], N_DRIVERS, max(used)))
    return len(frames), max(used)


def fig_static(SM, CV, IX):
    from PIL import Image, ImageDraw
    out = {}
    # 1. 摩擦円の散布
    W = 560
    T = Top(W, W, (-2.4, 2.4), (-2.4, 2.4), bg=(255, 255, 255))
    T.line(np.array([[-2.4, 0], [2.4, 0]]), (170, 170, 170), 1)
    T.line(np.array([[0, -2.4], [0, 2.4]]), (170, 170, 170), 1)
    mu = CV["drv"]["mu"]
    nr = drive(CV["C"], {k: v[:6] for k, v in CV["drv"].items()}, plan=False, cap=True, record=True)["rec"]
    nmax = 0.0
    for q in nr[::5]:
        for i in range(6):
            a, b = q["ax"][i] / (mu[i] * DL.G), q["ay"][i] / (mu[i] * DL.G)
            nmax = max(nmax, math.hypot(a, b))
            T.circle((float(np.clip(-b, -2.35, 2.35)), a), 0.018, fill=(220, 60, 40), width=0)
    gmax = 0.0
    rng = np.random.default_rng(0)
    for q in CV["good"]["rec"][::5]:
        for i in rng.choice(len(mu), min(12, len(mu)), replace=False):
            a, b = q["ax"][i] / (mu[i] * DL.G), q["ay"][i] / (mu[i] * DL.G)
            gmax = max(gmax, math.hypot(a, b))
            T.circle((-b, a), 0.014, fill=(60, 120, 230), width=0)
    T.circle((0, 0), 1.0, outline=(0, 0, 0), width=2)
    img = _txt(T.arr(), "摩擦円(横 = 横加速度 / μg、左旋回を左に / 縦 = 縦加速度 / μg)\n青 = 計画どおり(%d 人から 0.1 s ごとに 12 人)、"
               "赤 = 計画なし 50 km/h(6 人)" % N_DRIVERS, (6, 6), fs=12)
    figs.save("friction_circle", img, caption="摩擦円: 車の加速度を μg で割った点(横 = 横加速度(左旋回を左に描く)、縦 = 縦加速度、黒の円 = 使用率 1)。"
              "青 = curvature_speed_plan(摩擦円つき)で計画した人の 0.1 s ごとの点(この図の点の最大 %.2f、%d 人全員の最大 %.2f)。"
              "赤 = 計画なしで 50 km/h のまま走る 6 人(この図の点の最大 %.2f、%d 人では %.2f〜%.2f)—— 曲がり角で円の外(滑る)。"
              "縦の点は減速(下)と加速(上)。" % (gmax, N_DRIVERS, CV["good"]["use"].max(), nmax, N_DRIVERS, CV["nop"]["use"].min(),
                                          CV["nop"]["use"].max()))
    out["fc"] = (gmax, nmax)
    # 2. 内輪差の幾何
    W, H = 760, 640
    T = Top(W, H, (X_ENTRY - 16, XC + 6), (-3.5, 20))
    _draw_cross(T)
    T.poly(IX["waiting"], fill=(240, 200, 30), outline=(90, 70, 0))
    for E, col, colr in ((IX["E_naive"], (200, 60, 40), (230, 140, 30)), (IX["E_keep"], (40, 90, 220), (40, 160, 70))):
        fl, rl = _inner_wheels(E)
        m = E["front"][:, 0] > X_ENTRY - 16
        for i in np.nonzero(m)[0][::50]:
            T.poly(body_poly(E["front"][i], E["rear"][i]), outline=col, width=1)
        T.line(fl[m], col, 2)
        T.line(rl[m], colr, 3)
    img = T.arr()
    ck, cn = IX["res"]["keep"][0]["metrics"], IX["res"]["naive"][0]["metrics"]
    cfk = DL.offtracking_circle(IX["E_keep"]["Rf"], WB, IX["E_keep"]["Rf"] * math.pi / 2, track=TRACK)
    img = _txt(img, "左折の内輪差(上から、縦横 1 m 等倍)\n青 / 緑 = 左に寄って選んだ円(R_f %.2f m)の前 / 後ろの左の車輪\n"
               "赤 / 橙 = 前輪で隅に沿う版の前 / 後ろの左の車輪\n橙の帯 = 隅で人・自転車が待つ所、黄 = 待つ自転車" % IX["E_keep"]["Rf"],
               (6, 6), fs=12)
    figs.save("offtracking_geometry", img, caption="左折の内輪差(上から)。後輪は前輪より内を通る(rear_axle_path の追跡曲線、閉形式 offtracking_circle "
              "と一致)。左に寄って選んだ円(R_f %.2f m、x = %.2f m から)は後輪の内側が隅切りの縁から %.2f〜%.2f m(隅の場所 %.1f m の外、"
              "側端に沿う %.1f m 以内)、90° の所の内輪差 %.2f m。前輪で隅に沿う版(隅切りと同心、前の左の車輪が縁から %.1f m)は後輪の内側が"
              "縁から %.2f m まで入り、待つ自転車に触れる。" % (
                  IX["E_keep"]["Rf"], IX["E_keep"]["cx"], ck["rear_inner_gap_min"], ck["rear_inner_gap_max"], CLEAR,
                  LEFT_KW["side_tol"], cfk["offtracking"], CLEAR, cn["rear_inner_gap_min"]))
    # 3. 速度計画の帯
    C = CV["C"]
    Wp, Hp = 900, 440
    im = Image.new("RGB", (Wp, Hp), (255, 255, 255))
    d = ImageDraw.Draw(im)
    s0, s1 = 60.0, S_EVAL
    sx = lambda v: 60 + (v - s0) / (s1 - s0) * (Wp - 80)  # noqa: E731
    sy = lambda v: Hp - 50 - min(v, 70 / 3.6) * 3.6 / 70.0 * (Hp - 100)  # noqa: E731
    jj = np.nonzero((C.S >= s0) & (C.S <= s1))[0][::4]
    V = CV["good"]["V"]
    vl = np.array([DL.curvature_speed_plan(C.St, C.Kt, v_max=C.vmax, a_lat_max=a, a_accel=1.5, a_decel=2.5, a_total=m * DL.G,
                                           v_start=V_ROAD)["v_limit"] for a, m in zip(CV["drv"]["a_lat"][:20], CV["drv"]["mu"][:20])])
    zs = C.S[C.zone]
    d.rectangle([sx(max(zs.min(), s0)), sy(70 / 3.6), sx(min(zs.max(), s1)), sy(0)], fill=(253, 230, 200))
    d.polygon([(sx(C.S[j]), sy(vl[:, j].max())) for j in jj] + [(sx(C.S[j]), sy(vl[:, j].min())) for j in jj[::-1]], fill=(222, 222, 222))
    d.polygon([(sx(C.S[j]), sy(V[:, j].max())) for j in jj] + [(sx(C.S[j]), sy(V[:, j].min())) for j in jj[::-1]], fill=(170, 195, 245))
    d.line([(sx(C.S[j]), sy(np.median(V[:, j]))) for j in jj], fill=(30, 70, 200), width=2)
    d.line([(sx(s0), sy(V_ROAD)), (sx(s1), sy(V_ROAD))], fill=(220, 60, 40), width=2)
    for v in range(0, 71, 10):
        d.line([(55, sy(v / 3.6)), (60, sy(v / 3.6))], fill=(0, 0, 0))
    for s in range(100, int(s1), 50):
        d.line([(sx(s), Hp - 50), (sx(s), Hp - 45)], fill=(0, 0, 0))
    d.rectangle([60, 50, Wp - 20, Hp - 50], outline=(60, 60, 60))
    img = np.asarray(im, np.float64) / 255.0
    for v in range(0, 71, 20):
        img = _txt(img, "%d" % v, (52, int(sy(v / 3.6))), anchor="rm", fs=10)
    for s in range(100, int(s1), 100):
        img = _txt(img, "%d" % s, (int(sx(s)), Hp - 44), anchor="ct", fs=10)
    img = _txt(img, "速度計画(縦 = km/h、横 = 中央線に沿った距離 s [m])\n灰 = 上限 min(50 km/h, √(a_lat/κ), 徐行)(20 人)  青 = %d 人の計画(線 = 中央値)"
               "  赤 = 計画なし  橙 = 曲がり角の附近" % N_DRIVERS, (6, 4), fs=11)
    zmin = float(V[:, C.zone].max()) * 3.6
    figs.save("speed_plan_band", img, caption="曲率から作る速度計画(前向き・後ろ向きの 2 パス、摩擦円つき)。灰の帯 = 上限 min(50 km/h, √(a_lat/κ), 徐行)"
              "の 20 人の幅(a_lat は運転者ごと、標本の門を通った値)、青の帯 = %d 人の計画(減速 2.5・加速 1.5 m/s²、摩擦円 μg)。カーブ(R %.0f m)の"
              "手前で上限まで、曲がり角(R %.0f m)は附近 30 m 手前から 10 km/h 以下(計画の最大 %.1f km/h)に、減速を前倒しして入る。" % (
                  N_DRIVERS, R1, R2, zmin))
    # 4. 稀な出来事(重要度サンプリング)
    c = IX["mc"]["centre"]
    dg, vg, hg = c["grid"]
    W, H = 760, 460
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    gi, gj = np.nonzero(hg)
    xlo = max(15.0, float(dg[gj].min()) - 15.0) if len(gj) else 15.0
    xhi = float(dg[gj].max()) + 15.0 if len(gj) else 120.0
    px = lambda x: 60 + (x - xlo) / (xhi - xlo) * (W - 80)  # noqa: E731
    py = lambda v: H - 50 - (v * 3.6 - 3.0) / 25.0 * (H - 100)  # noqa: E731
    for a, b in zip(gi, gj):
        d.rectangle([px(dg[b]) - 1, py(vg[a]) - 4, px(dg[b]) + 1, py(vg[a]) + 4], fill=(220, 60, 40))
    dv, vv = c["hits_is"]
    for x, v in zip(dv, vv):
        d.ellipse([px(x) - 2, py(v) - 2, px(x) + 2, py(v) + 2], fill=(90, 140, 240))
    for x, v in zip(*c["hits"]):
        d.ellipse([px(x) - 7, py(v) - 7, px(x) + 7, py(v) + 7], outline=(0, 0, 0), width=2)
    d.rectangle([60, 50, W - 20, H - 50], outline=(60, 60, 60))
    img = np.asarray(im, np.float64) / 255.0
    for v in (5, 10, 15, 20, 25):
        img = _txt(img, "%d" % v, (54, int(py(v / 3.6))), anchor="rm", fs=10)
    for x in range(int(xlo // 10 * 10 + 10), int(xhi) + 1, 10):
        img = _txt(img, "%d" % x, (int(px(x)), H - 44), anchor="ct", fs=10)
    img = _txt(img, "寄らない左折で巻き込みが起きる (D0, 速さ)  横 = 後ろの距離 D0 [m]、縦 = 自転車の速さ [km/h]\n"
               "赤 = 試し打ちの格子で巻き込み、青 = 重要度サンプリングで巻き込んだ標本、黒の丸 = 素朴 MC の巻き込み", (6, 4), fs=11)
    figs.save("rare_event_map", img, caption="稀な出来事: 車線の中央のまま左折すると、後ろの自転車が左に入り込んで巻き込まれるのは、速い自転車(%.1f km/h 以上、"
              "採った速さの %.1f %%)がちょうど曲がる頃に追いつく細い帯だけ。素朴なモンテカルロ %d 試行では %d 件(p = %.5f ± %.5f)、"
              "試し打ちで帯を見つけて提案をそこに絞った重要度サンプリング %d 試行では %d 件(p = %.5f ± %.5f)。値は普通なので落とさず、"
              "重みで数える。左に寄った版は格子・MC・重要度とも 0。" % (
                  3.6 * vg[hg.any(1)].min(), 100 * c["frac"], N_MC, c["n_mc"], c["p_mc"], c["se_mc"], N_IS, c["n_is"], c["p_is"], c["se_is"]))
    # 5. 標本の門(自転車の速さと単位の誤り)
    W, H = 760, 400
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    x = SM["v_bike"] * 3.6
    wrong = SM["v_bike"][:2000] / 3.6
    kept, why = screen("v_bike", wrong)
    Dw, pw = ks_truncnorm("v_bike", kept)
    bins = np.linspace(0, 30, 61)
    h1, _ = np.histogram(x, bins)
    h2, _ = np.histogram(wrong * 3.6, bins)
    f1, f2 = h1 / len(x), h2 / len(wrong)
    hm = max(f1.max(), f2.max()) * 1.05
    bx = lambda b: 50 + b / 30.0 * (W - 70)  # noqa: E731
    by = lambda f: H - 40 - f / hm * (H - 110)  # noqa: E731
    for k in range(60):
        if f1[k] > 0:
            d.rectangle([bx(bins[k]), by(f1[k]), bx(bins[k + 1]) - 1, by(0)], fill=(120, 160, 240))
        if f2[k] > 0:
            d.rectangle([bx(bins[k]) + 2, by(f2[k]), bx(bins[k + 1]) - 3, by(0)], outline=(220, 60, 40), width=2)
    r = REF["v_bike"]
    for lim in (r["mean"] - Z999 * r["sd"], r["mean"] + Z999 * r["sd"]):
        d.line([(bx(lim * 3.6), 70), (bx(lim * 3.6), H - 40)], fill=(0, 0, 0), width=2)
    xs = np.linspace(0, 30, 300)
    pdf = np.exp(-0.5 * ((xs / 3.6 - r["mean"]) / r["sd"]) ** 2) / (r["sd"] * 3.6 * math.sqrt(2 * math.pi)) * 0.5
    d.line([(bx(a), by(b)) for a, b in zip(xs, pdf)], fill=(30, 70, 200), width=2)
    d.line([(50, H - 40), (W - 20, H - 40)], fill=(0, 0, 0))
    img = np.asarray(im, np.float64) / 255.0
    for v in range(0, 31, 5):
        img = _txt(img, "%d" % v, (int(bx(v)), H - 36), anchor="ct", fs=10)
    Dk, pk = ks_truncnorm("v_bike", SM["v_bike"])
    img = _txt(img, "自転車の速さ [km/h]  青 = 採った %d 個(KS p = %.2f)、線 = 参照 N(14.5, 3.5)、黒 = 両側 0.1 %% 点\n"
               "赤の枠 = 単位の誤り(さらに 3.6 で割った)2000 個: 1 個ずつの門で落ちるのは %d 個、KS は D = %.2f で落とす" % (
                   len(x), pk, len(why), Dw), (6, 4), fs=11)
    figs.save("sample_gate", img, caption="乱数の値の門: 自転車の速さは参照分布 N(14.5, 3.5) km/h(平均は国総研の車道の旅行速度、幅は仮定)の両側 0.1 %% 点(%.1f〜%.1f km/h)の外を 1 個ずつ"
              "落としてから採り(%d 個、KS p = %.2f)、残りを切断正規との KS で照合する。単位の誤りで全体が遅い方へずれた集団(赤の枠)は 1 個ずつの門を "
              "%d / 2000 個が通ってしまうが、KS は D = %.2f(p = %.1g)で落とす。" % (
                  3.6 * (r["mean"] - Z999 * r["sd"]), 3.6 * (r["mean"] + Z999 * r["sd"]), len(x), pk, len(kept), Dw, pw))
    # 6. 曲がり方の判定の表
    rows = []
    for k, nm in (("keep", "左折: 左に寄って計画の円"), ("naive", "左折: 前輪で隅に沿う"), ("centre", "左折: 車線の中央のまま")):
        ch = IX["res"][k][0]
        rows.append([nm, "違反なし" if ch["ok"] else " / ".join(v.split("(")[0] for v in ch["violations"]), "%.2f" % IX["res"][k][1]])
    for k, nm in (("plan", "右折: 中心のすぐ内側"), ("big", "右折: 大回り"), ("early", "右折: 早回り")):
        ch = IX["rr"][k]
        rows.append([nm, "違反なし" if ch["ok"] else " / ".join(v.split("(")[0] for v in ch["violations"]), "—"])
    figs.save_table("turn_checks", ["通り方", "turn_maneuver_check の判定", "待つ自転車まで [m]"], rows,
                    title="左折・右折の通り方の判定",
                    caption="turn_maneuver_check の判定。寄る = 車体の側面が車道の端・中央線から 0.5 m 以内、側端に沿う = 後輪の内側が隅切りの縁から "
                            "%.1f〜%.1f m、すぐ内側 = 交差点の中心が軌跡の外側で 3 m 以内、徐行 = 10 km/h(すべて仮定)。" % (CLEAR, LEFT_KW["side_tol"]))
    return out


def figures(SM, CV, IX):
    print("== 7. 図")
    t = time.time()
    n2, nf, n1 = fig_dashcam(SM, CV, IX)
    print("  車載カメラの動画 %d コマ(場面 1 は %d コマ、%.1f s)、場面 2 の巻き込み %s・場面 3 %s" % (
        nf, n1, time.time() - t, n2["keep"], n2["centre"]))
    gate("動画の場面: 同じ自転車で、左に寄ると巻き込まず、寄らないと巻き込む", (not n2["keep"]) and n2["centre"])
    t = time.time()
    nb, ub = fig_birdseye(CV)
    print("  上から見た動画 %d コマ(%.1f s)、計画なしの摩擦円の使用率 最大 %.2f" % (nb, time.time() - t, ub))
    t = time.time()
    fig_static(SM, CV, IX)
    print("  静止図(%.1f s)" % (time.time() - t))


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    print("車(仮定): 質量 %.0f kg、l_f %.1f m・l_r %.1f m、C_f %.0f・C_r %.0f N/rad → アンダーステア勾配 K = %.5f rad/(m/s²)、特性速度 %.1f km/h" % (
        CAR["mass"], CAR["l_f"], CAR["l_r"], CAR["c_f"], CAR["c_r"], K_US, 3.6 * DL.understeer_gradient(CAR)["characteristic_speed"]))
    want = figs.enabled()
    tm = {}
    t = time.time()
    SM = scene_samples()
    tm["samples"] = time.time() - t
    t = time.time()
    CV = scene_curve(SM)
    tm["curve"] = time.time() - t
    t = time.time()
    IX = scene_intersection(SM)
    tm["intersection"] = time.time() - t
    print("  区間ごとの所要 [s]: " + ", ".join("%s %.1f" % kv for kv in tm.items()))
    if want:
        figures(SM, CV, IX)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("== 結果: %d / %d 門, %.1f s(CPU %.1f s)" % (sum(OK), len(OK), time.time() - T0, time.process_time()))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
