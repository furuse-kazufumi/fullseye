# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉜(自動運転 第 11 回): 踏切と交差点の優先 —— 踏切の直前で止まって左右を確かめ、警報中・向こう側が詰まっているときは
入らない、見通しの悪い踏切で「見えない列車」の危険を数える、狭い道から広い道へは徐行して譲る、横断歩道の手前の停止車両の
横では一度止まる・30 m 以内で前に出ない、駐停車禁止の距離を守って止まる、を条文と公表値と独立な経路で採点する。

方針(ユーザーの決定): **部品はルールベースに限る**。学習・ニューラルネットは使わない。部品(:mod:`drivecrossing`)は閉形式・
幾何・公表値・条文の判定・古典的な数値計算で、どれも独立な経路の検算(門)が立つ。手続きで作った世界は採点用の真値で、訓練には
使わない。AI は部品の組み合わせを考える側 —— ここでは「解釈基準の 30 秒と渡り切る時間の閉形式で、警報の直前に入っても安全と
言える理由を示す」「見通しの三角形と必要な見通し距離で、左右確認が効かない踏切を数える」「進行妨害の減速度の閉形式で譲る
判断をする」が組み合わせの例。

門(真値の出どころ):
  0. **乱数の値の門**: 列車の速さ・発進の加速度・交差道路の車の速さ・左右を見る時間・歩く速さは、参照分布(仮定)の両側 0.1 %
     分位点の外を 1 個ずつ落とし(理由を記録)、集団は切断正規分布との KS 検定で照合する。物理的にありえない値は落ち、単位の誤り
     (km/h を m/s と取り違えて 3.6 でもう一度割った速さ)は 1 個ずつの門をほぼ通るが KS で落ちる。稀な出来事(見えない列車が
     渡り切る前に着く)は落とさず、重要度サンプリングの重みで扱う。
  1. **踏切の時刻**: 解釈基準(国交省 鉄道局)の 15 秒・20 秒・30 秒(最小 10・15・20 秒)。始動点を固定すると遅い列車ほど
     警報が長い(5(4)「速度等により大きく異なるものでない」に反する)、速度を測って始動を遅らせる制御で揃う。
  2. **踏切を渡る**(S120, S122, S123, S124): ルールの運転者は全員 crossing_stop_check で違反なし、列車が着くとき車体が線路に無い、
     やや中央寄りで車輪が踏切の板から落ちない。止まらない・確かめない・警報中に入る・向こう側が詰まっているのに入る・左に寄りすぎる、
     はそれぞれの違反として数えられる(門が自明でない)。
  3. **見通しの悪い踏切**(S120、教則 6-1-1(2)): 角の建物で見える距離 = sight_triangle_distance(光線の総当たりと一致)。
     見えない列車が渡り切る前に着く確率 = 閉形式 = 素朴なモンテカルロ = 重要度サンプリング。見通しがよければ 0。
  4. **交差点の優先**(S098, S099): 優先道路・明らかに広い道路へは徐行(≤ 10 km/h)して、交差道路の車に減速を一切させない。
     同じ幅なら左方から来る車だけに譲る。譲った後の動きを細かい刻みで再生して、衝突の領域を同時に占めない。
  5. **横断歩道**(S043, S044): 停止車両の横は前に出る前に一時停止、隠れていた歩行者に触れない。30 m 以内で車の前に出ない
     (自転車は除外)。
  6. **駐停車禁止**(S105, S106, S107, S108, S109): 44 条の距離の区間を格子で数えた答えと一致、ルールの運転者は全員が適法の場所。

正直に書くこと:
* **仮定の値**: 参照分布(列車 N(80, 20) km/h、発進 N(1.5, 0.3) m/s²、交差道路の車 N(40, 6) km/h、見る時間 N(1.0, 0.25) s、
  歩く速さ N(1.4, 0.2) m/s)、列車 4 両 80 m、列車の本数(片方向 1 時間に 6 本)、遮断の降下の開始 7 秒・降下 8 秒・上昇 6 秒、
  踏切の長さ 10 m(複線)、踏切の板の幅 6 m、「直前」2 m、進行妨害の「急に」2.0 m/s²、「明らかに広い」= 幅の比 1.5、徐行 10 km/h。
  出典と状態は drivecrossing.SOURCES と NOTES.md。
* 交差道路の車・列車は一定の速さ(譲るときだけ一定の減速)。人の判断の遅れは左右を見る時間だけ。
* 列車の非常ブレーキ・踏切障害物検知装置は描かない(「列車が着くときに車体が線路の上にある」を危険として数えるだけ)。

教則の場面: S043, S044, S098, S099, S105, S106, S107, S108, S109, S120, S122, S123, S124(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_crossing.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
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
import drivecrossing as DC  # noqa: E402

#: 予算: reduced(CI の既定)は人数・試行数を減らす。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_DRIVERS = 60 if REDUCED else 240           # 踏切を渡る運転者
N_SIGHT = 400 if REDUCED else 2000           # 見通しの悪い踏切の運転者
N_MC = 100000 if REDUCED else 600000         # 素朴なモンテカルロ(見えない列車)
N_IS = 2000 if REDUCED else 10000            # 重要度サンプリング
N_INT = 60 if REDUCED else 240               # 交差点の場面
N_CW = 60 if REDUCED else 240                # 横断歩道の場面
N_PARK = 200 if REDUCED else 1000            # 止まりたい場所
VID_WH = (320, 180) if REDUCED else (640, 360)
T0 = time.time()
OK = []
DT = 0.05

# ── 車(仮定) ──
CAR_L, CAR_W, TRACK_W = 4.5, 1.8, 1.55       # 車長・車幅・輪距
EYE_BACK = 2.05                              # 前端から運転者の目まで
JOKOU = 10.0 / 3.6                           # 徐行(仮定)
DECEL = 2.0                                  # 普通の減速(仮定)

# ── 踏切(座標: 道は x、自車は +x へ、自車線 y ∈ [0, 3]。線路は y 方向) ──
SL = 0.0                     # 停止線
CS, CLEN = 3.0, 10.0         # 踏切(線路の危険な範囲)の手前の端・長さ(複線、仮定)
CE = CS + CLEN
TRK = (CS + 2.5, CS + 7.5)   # 2 本の線路の中心の x
GAUGE = 1.067
DECK_HALF = 3.0              # 踏切の板の半幅(道の中心から、仮定 6 m)
V_APP = 30.0 / 3.6
V_GO = 20.0 / 3.6            # 踏切の中の上限(低速ギアのまま、仮定)
TRAIN_L = 80.0               # 4 両(仮定)
T_LOWER, D_LOWER, D_RAISE = 7.0, 8.0, 6.0     # 警報から降下の開始・降下・上昇 [s](仮定。降下の終わり = 15 s = 標準)
T_WARN = DC.CROSSING_TIMING["warn_to_closed_std"] + DC.CROSSING_TIMING["closed_to_arrival_std"]   # 遮断機: 15 + 20 = 35 s
V_LINE = 130.0 / 3.6         # 線区の最高速度(仮定。解釈基準 1 の 130 km/h に合わせた)
Y_LANE = 1.2                 # やや中央寄り(車線の中央 1.5 から 0.3 m、教則 6-1-1(5)、仮定)
GAP, BEYOND = 1.0, 0.5
BRAKE_MAX = 4.0              # 警報の開始時に止まれるかの判定の減速度(仮定)

# ── 乱数の参照分布(すべて仮定。出典の候補は NOTES.md)と標本の門 ──
Z999 = 3.2905267314919255     # 標準正規の 99.95 % 点(両側 0.1 %)
REF = {
    "v_train": {"mean": 75.0 / 3.6, "sd": 16.0 / 3.6, "unit": "m/s", "what": "列車の速さ"},   # 0.1 % 点 127.6 km/h < 線区の 130
    "a_go": {"mean": 1.5, "sd": 0.3, "unit": "m/s²", "what": "発進の加速度"},
    "v_cross": {"mean": 40.0 / 3.6, "sd": 6.0 / 3.6, "unit": "m/s", "what": "交差道路の車の速さ"},
    "t_look": {"mean": 1.0, "sd": 0.25, "unit": "s", "what": "片側を見る時間"},
    "v_walk": {"mean": 1.4, "sd": 0.2, "unit": "m/s", "what": "歩く速さ"},
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
    rng = np.random.default_rng(11)
    D = {}
    total_drop, pmin = 0, 1.0
    nmax = max(N_DRIVERS, N_SIGHT, N_INT, N_CW)
    for name, n in (("v_train", nmax), ("a_go", nmax), ("v_cross", 4 * N_INT), ("t_look", 2 * nmax), ("v_walk", N_CW)):
        x, why = draw(name, n, rng)
        Dk, p = ks_truncnorm(name, x)
        pmin = min(pmin, p)
        total_drop += len(why)
        r = REF[name]
        print("    %-8s %s: %d 個、落とした %d 個%s、KS D = %.4f p = %.3f" % (
            name, r["what"], len(x), len(why), ("(" + why[0] + ")") if why else "", Dk, p))
        D[name] = x
    gate("標本の門: 採った値はすべて参照の 0.1 % 点の内、集団は KS で参照と食い違わない(p > 0.001)", pmin > 0.001,
         "最小 p = %.3f、落とした %d 個" % (pmin, total_drop))
    bad = {"v_train": [80 / 3.6, 500 / 3.6, -3.0], "a_go": [1.4, 9.0], "t_look": [1.0, -0.5], "v_walk": [1.3, 6.0]}
    nbad = 0
    for k, v in bad.items():
        _, why = screen(k, v)
        nbad += len(why)
        for w in why:
            print("      落とした: " + w)
    wrong = D["v_cross"][:min(2000, len(D["v_cross"]))] / 1.25    # 係数の取り違え(全体が 20 % 遅い方へずれた集団)
    kept, why = screen("v_cross", wrong)
    Dw, pw = ks_truncnorm("v_cross", kept)
    print("    系統の誤り(交差道路の車の速さを 1.25 で割った %d 個 = 換算係数の取り違え): 1 個ずつの門で落ちたのは %d 個(%.0f %%)、残り %d 個の KS D = %.3f p = %.2g"
          % (len(wrong), len(why), 100 * len(why) / len(wrong), len(kept), Dw, pw))
    gate("門が自明でない: ありえない値 5 個は 1 個ずつの門で落ち(理由を記録)、系統の誤りは 1 個ずつの門をほぼ通るが KS で落ちる",
         nbad == 5 and len(why) < 0.5 * len(wrong) and pw < 1e-6, "落とした %d 個 / 単位の誤り p = %.2g" % (nbad, pw))
    D["_wrong"] = (wrong, kept, Dw, pw)
    return D


# ───────────────────────────── 1. 踏切の時刻 ─────────────────────────────
def scene_timing(SM):
    print("== 1. 踏切の時刻(解釈基準 Ⅶ-9 の遮断機: 警報→遮断 15 s(≥ 10)、遮断→到達 20 s(≥ 15)。警報機だけの踏切は警報→到達 30 s(≥ 20))")
    vt = SM["v_train"][:N_DRIVERS]
    t_closed = T_LOWER + D_LOWER
    d_fixed = T_WARN * V_LINE                                  # 始動点を固定: 線区の最高速度 130 km/h(仮定)の列車で 35 s
    t_arr_fixed = d_fixed / vt
    fx = DC.crossing_timing_check(np.zeros_like(vt), np.full_like(vt, t_closed), t_arr_fixed)
    # 警報時間制御(解釈基準 7): 2 点で速さを測り、到達の T_WARN 前に始動を遅らせる(ここでは測った速さ = 本当の速さ)
    t_arr_ctl = np.full_like(vt, T_WARN)
    ct = DC.crossing_timing_check(np.zeros_like(vt), np.full_like(vt, t_closed), t_arr_ctl)
    v_crit = d_fixed / (t_closed + DC.CROSSING_TIMING["closed_to_arrival_min"])   # これより速いと遮断→到達が最小を割る
    over = DC.crossing_timing_check(0.0, t_closed, d_fixed / (160.0 / 3.6))     # 線区の速度を超えた列車(160 km/h)
    print("    始動点を固定(%.0f m、130 km/h で %.0f s): 警報→到達 %.1f〜%.1f s(ばらつき %.1f s)、最小を満たす %d / %d" % (
        d_fixed, T_WARN, t_arr_fixed.min(), t_arr_fixed.max(), fx["spread"], int(np.sum(fx["meets_minimum"])), len(vt)))
    print("    速さで始動を制御: 警報→到達 %.1f s(ばらつき %.2f s)、遮断→到達 %.1f s" % (T_WARN, ct["spread"], T_WARN - t_closed))
    print("    固定の始動点で最小を割る速さ = 始動点の距離 / (遮断の終わり + 15 s) = %.0f km/h。160 km/h の列車なら遮断→到達 %.1f s → 最小を満たす %s" % (
        3.6 * v_crit, over["closed_to_arrival"], over["meets_minimum"]))
    gate("時刻の門: 線区の速度以下の列車は、始動点の固定でも制御でも最小(10 / 15 s)を満たす",
         bool(np.all(fx["meets_minimum"])) and bool(np.all(ct["meets_minimum"])))
    gate("門が自明でない: 固定は遅い列車ほど警報が長い(ばらつき > 30 s)、制御で揃う(< 0.01 s)、速度超過は最小を割る",
         fx["spread"] > 30.0 and ct["spread"] < 0.01 and not over["meets_minimum"], "%.1f s → %.2f s" % (fx["spread"], ct["spread"]))
    return {"t_arr_fixed": t_arr_fixed, "vt": vt, "fx": fx, "d_fixed": d_fixed}


# ───────────────────────────── 2. 踏切を渡る ─────────────────────────────
def gate_of(sc):
    return dict(t_warning=sc["t_w"], t_lower_start=sc["t_w"] + T_LOWER, lower_duration=D_LOWER, t_clear=sc["t_clr"],
                raise_duration=D_RAISE)


def make_scenario(i, SM, rng, *, t_stop_est):
    """運転者 i の場面: 警報の始まり(到着の前後、一様 = 仮定)、列車、向こう側の列(35 % の確率、一様 = 仮定)。"""
    vt = float(SM["v_train"][i])
    t_w = t_stop_est + rng.uniform(-45.0, 25.0)
    t_arr = t_w + T_WARN
    t_pass = (TRAIN_L + CLEN) / vt
    sc = {"i": i, "v_train": vt, "t_w": t_w, "t_arr": t_arr, "t_clr": t_arr + t_pass, "a_go": float(SM["a_go"][i]),
          "t_look": (float(SM["t_look"][2 * i]), float(SM["t_look"][2 * i + 1])), "queue": None}
    if rng.random() < 0.35:
        sc["queue"] = (CE + rng.uniform(1.0, 13.0), t_stop_est + rng.uniform(0.0, 30.0))    # (後端の位置, 列が去る時刻)
    return sc


def queue_at(sc, t):
    if sc["queue"] is None or t >= sc["queue"][1]:
        return math.inf
    return sc["queue"][0]


def sim_crossing(sc, policy="rule", t_end=None, x0=-60.0):
    """1 人の運転者を DT 刻みで走らせる。policy: rule / no_stop / no_look / ignore_warning / ignore_queue。
    返り値: t, x, v, looks(見た時刻と側), 状態の記録。"""
    gp = gate_of(sc)
    stop_at = SL - 0.5
    a_go = sc["a_go"]
    tl = sc["t_look"]
    t_end = t_end or (sc["t_clr"] + 60.0)
    x, v, t = x0, V_APP, 0.0
    v_cruise = 15.0 / 3.6 if policy == "no_stop" else V_APP      # 止まらない人は 15 km/h まで落として通る
    mode = "approach"
    looks = []
    look_k, look_t0 = 0, None
    n_restop, hold = 0, None
    T, X, V, M = [], [], [], []

    def idle(tt):
        return int(DC.crossing_gate_state(np.array([tt]), **gp)["state"][0]) == 0

    def room(tt):
        return policy == "ignore_queue" or bool(DC.exit_room_check(queue_at(sc, tt), CE, CAR_L, gap=GAP, beyond=BEYOND)["ok"])

    def step_to(target, vcap, acc):
        """target の手前で止まれる速さ √(2·DECEL·残り) と vcap を超えないよう、acc で加速して 1 刻み進む。"""
        nonlocal x, v
        rest = target - x
        if rest < 0.02:
            x, v = (target if math.isfinite(target) else x), 0.0
            return
        vn = min(v + acc * DT, vcap, math.sqrt(2.0 * DECEL * rest) if math.isfinite(rest) else vcap)
        vn = max(vn, v - 3.0 * DECEL * DT, 0.0)
        x = min(x + 0.5 * (v + vn) * DT, target)
        v = vn

    while t < t_end:
        T.append(t)
        X.append(x)
        V.append(v)
        M.append(mode)
        if mode == "approach":
            d = stop_at - x
            if policy == "no_stop" and d <= v * v / (2 * DECEL) + 0.5 and idle(t) and room(t):
                mode = "go"                                   # 止まらずに入る(前の車に続く)。下の go で同じ刻みを進める
            elif v > v_cruise and d > v * v / (2 * DECEL) + 3.0:
                v = max(v - DECEL * DT, v_cruise)
                x += v * DT
            else:
                step_to(stop_at, v_cruise, 0.0)
                if v == 0.0 and x >= stop_at - 1e-9:
                    mode = "stopped"
                    look_k, look_t0 = 0, None
        if mode == "restop":
            # 発進した後、踏切の手前で警報が始まった: 止まれるなら(4 m/s² 以内)止まり、もう一度待って確かめる
            step_to(hold, V_GO, 0.0)
            if v == 0.0:
                mode = "stopped"
                look_k, look_t0 = 0, None
        elif mode == "stopped":
            ok = (policy == "ignore_warning" or idle(t)) and room(t)
            if not ok:
                look_k, look_t0 = 0, None
            elif policy == "no_look":
                mode = "go"
            else:
                if look_t0 is None:
                    look_t0 = t
                if t - look_t0 >= tl[look_k] - 1e-9:
                    looks.append((t, ("left", "right")[look_k]))
                    look_k += 1
                    look_t0 = t
                    if look_k == 2:
                        mode = "go"
        elif mode == "go":
            if policy != "ignore_warning" and x < CS and not idle(t) and v * v / (2 * BRAKE_MAX) <= CS - x:
                hold = min(x + v * v / (2 * DECEL), CS - 0.02)        # 普通の減速で、無理なら踏切の端の手前まで強めに
                mode = "restop"
                n_restop += 1
                step_to(hold, V_GO, 0.0)
            else:
                step_to(queue_at(sc, t) - GAP, V_GO, a_go)
            if x > CE + 40.0:
                break
        t += DT
    return {"t": np.array(T), "x": np.array(X), "v": np.array(V), "looks": looks, "mode": M, "restops": n_restop}


def check_run(sc, R):
    """crossing_stop_check で採点 + 列車が着くときの車体の位置。"""
    gp = gate_of(sc)
    forb = [(sc["t_w"], sc["t_clr"] + D_RAISE)]
    te = None
    k = np.flatnonzero(R["x"] >= CS)
    if k.size:
        te = float(R["t"][k[0]])
    q = queue_at(sc, te) if te is not None else None
    chk = DC.crossing_stop_check(R, stop_line=SL, crossing_start=CS, crossing_end=CE, car_length=CAR_L, look_events=R["looks"],
                                 forbidden_intervals=forb, queue_rear=None if q is None or not math.isfinite(q) else q,
                                 gap=GAP, beyond=BEYOND, brake_max=BRAKE_MAX)
    # 列車が踏切にいる間 [t_arr, t_clr]、車体が線路の危険な範囲 [CS, CE] にかかっているか
    on = (R["x"] > CS) & (R["x"] - CAR_L < CE)
    tr = (R["t"] >= sc["t_arr"]) & (R["t"] <= sc["t_clr"])
    hit = bool(np.any(on & tr))
    # 列車の到達まで、車体が線路を出てからの余裕
    off = np.flatnonzero((R["x"] - CAR_L >= CE) & (R["t"] <= sc["t_arr"]))
    del gp
    return chk, hit, off


POLICIES = (("rule", "ルール(止まる・左右・警報・余地)"), ("no_stop", "止まらない(前の車に続く)"), ("no_look", "左右を確かめない"),
            ("ignore_warning", "警報中でも入る"), ("ignore_queue", "向こう側が詰まっていても入る"))


def scene_crossing(SM):
    print("== 2. 踏切を渡る(S120, S122, S123, S124): %d 人 × 方針 %d 通り" % (N_DRIVERS, len(POLICIES)))
    rng = np.random.default_rng(21)
    t_stop_est = (SL - 0.5 - (-60.0) - V_APP * V_APP / (2 * DECEL)) / V_APP + V_APP / DECEL
    scs = [make_scenario(i, SM, rng, t_stop_est=t_stop_est) for i in range(N_DRIVERS)]
    res = {}
    for pol, nm in POLICIES:
        rows = []
        for sc in scs:
            R = sim_crossing(sc, pol)
            chk, hit, _ = check_run(sc, R)
            rows.append((chk, hit, R))
        viol = {}
        for chk, _, _ in rows:
            for v in chk["violations"]:
                viol[v] = viol.get(v, 0) + 1
        nhit = sum(h for _, h, _ in rows)
        nent = sum(c["entered"] for c, _, _ in rows)
        nun = sum(c["unavoidable"] for c, _, _ in rows)
        res[pol] = {"rows": rows, "viol": viol, "hit": nhit, "entered": nent, "unavoidable": nun,
                    "restops": sum(R["restops"] for _, _, R in rows)}
        print("    %-30s 渡った %3d 人、違反 %s、列車が着くとき線路の上 %d 人、止まれない位置で警報(例外)%d 人、発進後に止まり直した %d 人" % (
            nm, nent, ", ".join("%s %d" % kv for kv in sorted(viol.items())) or "なし", nhit, nun, res[pol]["restops"]))
    r0 = res["rule"]
    # ルールの人の、線路を出てから列車が着くまでの余裕(警報の直前に入った人ほど小さい)
    margins = []
    for sc, (chk, hit, R) in zip(scs, r0["rows"]):
        te = chk["t_entry"]
        if te is None:
            continue
        k = np.flatnonzero(R["x"] - CAR_L >= CE)
        if k.size and sc["t_arr"] > te:
            margins.append(sc["t_arr"] - float(R["t"][k[0]]))
    margins = np.array(margins)
    clr = DC.crossing_clear_time(CS - (SL - 0.5), CLEN, CAR_L, beyond=0.0, accel=float(SM["a_go"][:N_DRIVERS].min()), v_max=V_GO)
    print("    ルール: 全員が渡った %d / %d、線路を出てから列車が着くまで 最小 %.1f s(渡り切る時間の閉形式 最大 %.1f s ≪ 警報→到達 %.0f s)" % (
        r0["entered"], N_DRIVERS, margins.min() if margins.size else math.nan, clr["time"], T_WARN))
    gate("踏切を渡る: ルールの全員が違反なし(33 条 1・2 項、50 条 2 項、止まらずに渡る)・全員が渡り切る・列車が着くとき車体が線路に無い",
         not r0["viol"] and r0["entered"] == N_DRIVERS and r0["hit"] == 0, "余裕 最小 %.1f s" % (margins.min() if margins.size else -1))
    exp = {"no_stop": "no_stop", "no_look": "no_look", "ignore_warning": "entered_while_forbidden", "ignore_queue": "no_exit_room"}
    det = []
    okv = True
    for pol, v in exp.items():
        n = res[pol]["viol"].get(v, 0)
        others = {k: c for k, c in res[pol]["viol"].items() if k not in (v, "stopped_inside")}
        det.append("%s %d" % (v, n))
        okv &= n > 0 and not others
    # 警報中に入った人の数を別の経路で: 軌跡が踏切の端を越えた刻みの時刻での状態機械の状態(≥ 1)を数え、止まれない
    # 位置で警報が始まった人(例外)を引く
    n_warn_at_stop = 0
    for sc, (chk, hit, R) in zip(scs, res["ignore_warning"]["rows"]):
        if chk["t_entry"] is not None and not chk["unavoidable"]:
            st = DC.crossing_gate_state(np.array([chk["t_entry"]]), **gate_of(sc))["state"]
            n_warn_at_stop += int(st[0] >= 1)
    stuck = res["ignore_queue"]["viol"].get("stopped_inside", 0)
    print("    警報中に入った %d 人(踏切の端を越えた時刻に状態機械が警報〜上昇中だった人 %d 人)、詰まりで踏切の中に止まった %d 人、"
          "警報中に入った人で列車が着くとき線路の上 %d 人" % (
              res["ignore_warning"]["viol"].get("entered_while_forbidden", 0), n_warn_at_stop, stuck, res["ignore_warning"]["hit"]))
    gate("門が自明でない: 止まらない・確かめない・警報中に入る・詰まっていても入る、はそれぞれ自分の違反だけで数えられる",
         okv and n_warn_at_stop == res["ignore_warning"]["viol"].get("entered_while_forbidden", 0) and stuck > 0, " / ".join(det))
    # S124: やや中央寄り → 車輪と踏切の板の端
    m_mid = DECK_HALF - (Y_LANE + 0.5 * TRACK_W)
    m_left = DECK_HALF - (2.6 + 0.5 * TRACK_W)               # 左に寄りすぎ(車体の左が車線の端 3.0 に 0.4 m)
    print("    踏切の板(半幅 %.1f m)の端と左の車輪: やや中央寄り(y = %.1f)%.2f m、左に寄りすぎ(y = 2.6)%.2f m" % (DECK_HALF, Y_LANE, m_mid, m_left))
    gate("S124: やや中央寄りなら左の車輪が踏切の板の端から 0.5 m 以上内(仮定の余裕)、左に寄りすぎると 0.5 m を切る", m_mid >= 0.5 > m_left,
         "%.2f / %.2f m" % (m_mid, m_left))
    return {"scs": scs, "res": res, "margins": margins, "clear": clr}


# ───────────────────────────── 3. 見通しの悪い踏切 ─────────────────────────────
LAMBDA = 6.0 / 3600.0          # 片方向の列車の本数(1 時間に 6 本、仮定)
BLD_RIGHT = (4.5, 4.0)         # 右の角の建物: 道の中心から右へ 4.5 m、手前の線路の中心から 4.0 m(仮定)


def sight_geometry():
    """第 4 種踏切(警報機なし): 目と線路、右の角の建物。sight_triangle_distance の座標は「線路 = x 軸、右 = +x」。

    自車は左の車線(道の中心から左 1.5 m)、運転席は右(車の中心から右 0.37 m)→ 目は道の中心から左 1.13 m = x = −1.13。
    返り値 (目から手前の線路の中心まで, 目の x, 右に見える距離)。"""
    front = CS - 1.0                                     # 踏切の直前で止まる(前端が危険な範囲の 1 m 手前)
    eye_x = front - EYE_BACK
    eye_to_track = TRK[0] - eye_x
    eye_off = -(1.5 - 0.37)
    xr = DC.sight_triangle_distance(eye_off, eye_to_track, BLD_RIGHT[0], BLD_RIGHT[1])
    return eye_to_track, eye_off, xr


def scene_sight(SM):
    print("== 3. 見通しの悪い踏切(第 4 種、S120、教則 6-1-1(2)): 見えない列車が渡り切る前に着く確率")
    eye_to_track, eye_off, x_vis = sight_geometry()
    # 光線の総当たり(独立な経路): 線路の上の点ごとに、目からの線分を 801 点で調べ、建物に入るか
    xs = np.linspace(BLD_RIGHT[0], 3.0 * x_vis, 30001)
    E = np.array([eye_off, -eye_to_track])
    s = np.linspace(0.0, 1.0, 801)[:, None]
    vis_far = 0.0
    for chunk in np.array_split(xs, 30):
        X = E[0] + s * (chunk[None, :] - E[0])
        Y = E[1] + s * (0.0 - E[1])
        blocked = np.any((X >= BLD_RIGHT[0]) & (Y <= -BLD_RIGHT[1]), axis=0)
        if (~blocked).any():
            vis_far = max(vis_far, float(chunk[~blocked].max()))
    print("    目から手前の線路まで %.2f m、右の角の建物(道の中心から %.1f m、線路から %.1f m): 見える距離 閉形式 %.2f m / 光線の総当たり %.2f m" % (
        eye_to_track, BLD_RIGHT[0], BLD_RIGHT[1], x_vis, vis_far))
    gate("見通しの三角形 = 光線の総当たり(±0.05 m)", abs(vis_far - x_vis) < 0.05, "%.2f / %.2f m" % (x_vis, vis_far))
    n = N_SIGHT
    vt = SM["v_train"][:n]
    a = SM["a_go"][:n]
    tl = SM["t_look"][:2 * n].reshape(n, 2)
    clr = np.array([DC.crossing_clear_time(1.0, CLEN, CAR_L, beyond=0.0, accel=float(ai), v_max=V_GO)["time"] for ai in a])
    VIS_OPEN = 600.0                                      # 建物のない側(仮定: 線路の曲がりで 600 m)
    # 方針: 右を見てから左を見て発進(右の情報は左を見る時間だけ古い)。列車は右から(この側に建物)
    cases = {
        "open": (np.full(n, VIS_OPEN), tl[:, 1]),                       # 見通しよし
        "building": (np.full(n, x_vis), tl[:, 1]),                       # 建物で見通し悪い、見直す
        "no_relook": (np.full(n, x_vis), tl[:, 1] + 8.0),                # 反対の列車が過ぎた後、見直さず 8 s 前の確認で発進
    }
    out = {}
    rng = np.random.default_rng(31)
    for k, (vis, age) in cases.items():
        need = DC.track_sight_distance(vt, clr, margin=0.0) + vt * age      # 見た時点から渡り切るまでに列車が進む距離
        w = np.maximum(0.0, (need - vis) / vt)                               # 危険な窓の長さ [s](見えない所から間に合ってしまう)
        p_cf = 1.0 - np.exp(-LAMBDA * w)                                     # 閉形式(Poisson)
        P = float(p_cf.mean())
        # 素朴なモンテカルロ: 運転者を選び、見た時点の後の最初の列車の到達時刻を指数分布で引く
        idx = rng.integers(0, n, N_MC)
        t1 = rng.exponential(1.0 / LAMBDA, N_MC)
        lo = vis[idx] / vt[idx]
        hi = lo + w[idx]
        # 見た時点で見える範囲に列車がいない(t1 > lo)ことは条件(Poisson の独立増分で lo からの最初の到達も指数)
        hit_mc = float(np.mean(t1 < w[idx]))
        se_mc = math.sqrt(max(hit_mc * (1 - hit_mc), 1e-300) / N_MC)
        # 重要度サンプリング: 到達の時刻を危険な窓を覆う一様分布 [0, 2·max(w)] から引き、重み p/q
        jdx = rng.integers(0, n, N_IS)
        Wm = max(float(w.max()), 1e-9)
        tq = rng.uniform(0.0, 2.0 * Wm, N_IS)
        wt = LAMBDA * np.exp(-LAMBDA * tq) * (2.0 * Wm)
        f = (tq < w[jdx]) * wt
        hit_is = float(f.mean())
        se_is = float(f.std(ddof=1) / math.sqrt(N_IS))
        out[k] = {"P": P, "mc": hit_mc, "se_mc": se_mc, "is": hit_is, "se_is": se_is, "w": w, "need": need, "vis": vis,
                  "hits": int(np.sum(t1 < w[idx])), "lo": lo, "hi": hi}
        print("    %-10s 見える %.0f m、危険な窓 平均 %.2f s(0 の人 %d / %d)、P(閉形式) = %.2e、MC %.2e ± %.1e(%d / %d 回)、IS %.2e ± %.1e(%d 回)"
              % (k, float(vis.mean()), float(w.mean()), int(np.sum(w == 0)), n, P, hit_mc, se_mc, out[k]["hits"], N_MC, hit_is, se_is, N_IS))
    o, b, r = out["open"], out["building"], out["no_relook"]
    gate("見通しがよければ見えない列車の危険は 0(閉形式・MC とも)", o["P"] == 0.0 and o["hits"] == 0)
    zs = [abs(c["is"] - c["P"]) / max(c["se_is"], 1e-30) for c in (b, r)] + [abs(c["mc"] - c["P"]) / max(c["se_mc"], 1e-30) for c in (b, r)]
    gate("見えない列車の確率: 重要度サンプリング = 閉形式 = 素朴なモンテカルロ(各 4σ 以内)", max(zs) < 4.0, "最大 %.1fσ" % max(zs))
    gate("門が自明でない: 建物で見通しが悪いと > 0、見直さずに古い確認で発進するとさらに大きい(教則 6-1-1(2))",
         0.0 < b["P"] < r["P"], "%.2e < %.2e" % (b["P"], r["P"]))
    eff = (b["se_mc"] / max(b["se_is"], 1e-30)) ** 2 * N_MC / N_IS
    print("    同じ精度に要る試行の比(MC / IS)≈ %.0f 倍" % eff)
    return {"out": out, "x_vis": x_vis, "eye_to_track": eye_to_track, "clr": clr}


# ───────────────────────────── 4. 交差点の優先 ─────────────────────────────
XC = 0.0                         # 交差道路の中心線
LANE_C = 3.25                    # 交差道路の車線の幅(仮定)
V_EGO = 30.0 / 3.6
A_EGO = 1.5
MARGIN_T = 1.0                   # 交差道路の車が領域に入るのは自分が出てから 1 s 後以降(仮定の余裕)


def int_zones(own_width):
    """自分の進路(x)の上の 2 つの衝突の領域: 手前の車線(右から来る車)・向こうの車線(左から来る車)。"""
    hw = 0.5 * CAR_W + 0.3
    return {"right": (XC - 0.5 * LANE_C - hw, 2 * hw), "left": (XC + 0.5 * LANE_C - hw, 2 * hw)}


def scene_priority(SM):
    print("== 4. 交差点の優先(S098, S099): %d 場面 × 2 つの道の組み" % N_INT)
    rng = np.random.default_rng(41)
    vc = SM["v_cross"]
    combos = {"wide": ({"width": 4.0}, {"width": 2 * LANE_C + 0.5}), "same": ({"width": 5.0}, {"width": 5.5})}
    out = {}
    for ck, (own, cross) in combos.items():
        pr = DC.priority_rule(own, cross)
        Z = int_zones(own["width"])
        entry = XC - LANE_C - 0.5                           # 交差道路の端(自分の止まる線)
        res = {"rule": [], "naive": []}
        for e in range(N_INT):
            # 交差道路の車: 各方向に Poisson(1 時間 600 台、仮定)で、自分が線に着く時刻の前後 ±30 s
            cars = []
            for side in ("right", "left"):
                n = rng.poisson(600.0 / 3600.0 * 60.0)
                tarr = rng.uniform(-30.0, 30.0, n)
                for j in range(n):
                    v = float(vc[(4 * e + j + (0 if side == "right" else 2)) % len(vc)])
                    cars.append({"side": side, "v": v, "t_zone": float(tarr[j])})   # 自分が線に着いた時刻 0 に領域へ着く時刻
            for pol in ("rule", "naive"):
                res[pol].append(drive_int(pol, pr, Z, entry, cars))
        out[ck] = {"pr": pr, "res": res, "Z": Z, "entry": entry}
        r, nv = res["rule"], res["naive"]
        a_r = [x["a_need_prior"] for x in r]
        a_n = [x["a_need_prior"] for x in nv]
        print("    %s: 自分 %.1f m / 交差 %.1f m → %s(%s)、徐行 %s" % (
            ck, own["width"], cross["width"], pr["yield_to"], pr["article"], "要" if pr["must_slow"] else "不要"))
        print("      ルール: 譲る相手に要らせた減速度 最大 %.2f m/s²、線での速さ 最大 %.1f km/h、待ち 平均 %.1f s、衝突の領域の重なり %d 件" % (
            max(a_r), 3.6 * max(x["v_entry"] for x in r), float(np.mean([x["wait"] for x in r])), sum(x["overlap"] for x in r)))
        print("      素朴(30 km/h のまま): 進行妨害(> 2.0 m/s²)%d / %d 場面、最大 %.1f m/s²、線での速さ %.0f km/h" % (
            sum(x["obstruct"] for x in nv), N_INT, max(a_n) if a_n else 0.0, 3.6 * nv[0]["v_entry"]))
        if ck == "same":
            n_right_yield = sum(x["right_yielded"] for x in r)
            print("      左方優先: 右から来る車が譲った(減速した)場面 %d、左から来る車に減速させた場面 %d" % (
                n_right_yield, sum(x["a_need_prior"] > 0 for x in r)))
    w, s = out["wide"]["res"], out["same"]["res"]
    gate("S098: 広い道へは徐行(線で ≤ 10 km/h)し、交差道路の車に減速を一切させない(36 条 2・3 項)",
         out["wide"]["pr"]["yield_to"] == "cross" and max(x["v_entry"] for x in w["rule"]) <= JOKOU + 1e-9
         and max(x["a_need_prior"] for x in w["rule"]) == 0.0)
    gate("S099: 同じ幅では左から来る車だけに譲る(36 条 1 項)—— 右から来る車が譲る場面もある(全部に譲る自明な答えでない)",
         out["same"]["pr"]["yield_to"] == "left" and max(x["a_need_prior"] for x in s["rule"]) == 0.0
         and sum(x["right_yielded"] for x in s["rule"]) > 0)
    gate("譲った後の動きを 1 ms 刻みで再生: 衝突の領域を同時に占めた場面は 0", sum(x["overlap"] for x in w["rule"] + s["rule"]) == 0)
    gate("門が自明でない: 素朴な運転は進行妨害(> 2.0 m/s²)の場面がある",
         sum(x["obstruct"] for x in w["naive"]) > 0, "%d / %d" % (sum(x["obstruct"] for x in w["naive"]), N_INT))
    return out


def drive_int(pol, pr, Z, entry, cars):
    """1 場面: 自分は線の 30 m 手前から。rule = 徐行で線へ、譲るべき車に一切減速させない時刻まで線で待つ。naive = 30 km/h のまま。"""
    # 線での速さ: ルールは徐行(36 条 3 項。左方優先の組でも 36 条 4 項の「できる限り安全な速度」として同じにした = 仮定)
    v_entry = V_EGO if pol == "naive" else JOKOU
    v0, t0, wait = v_entry, 0.0, 0.0
    prior = [c for c in cars if pr["yield_to"] == "cross" or (pr["yield_to"] == "left" and c["side"] == "left")]
    other = [c for c in cars if c not in prior]
    cz = CAR_W + 0.6                                         # 交差道路の車の進路の上の領域の長さ(自分の幅 + 余裕)

    def needs(tg, v_start, group, slack):
        """発進時刻 tg に、group の車が自分の出た時刻 + slack まで領域に入らないのに要る減速度の最大。"""
        amax = 0.0
        for c in group:
            if c["t_zone"] + (cz + CAR_L) / c["v"] < tg:
                continue                                     # もう領域を過ぎ去った
            zs, zl = Z[c["side"]]
            iv = DC.conflict_zone_intervals(zs - entry, zl, CAR_L, v0=v_start, accel=A_EGO if v_start < V_EGO else 0.0, v_max=V_EGO)
            d = c["v"] * (c["t_zone"] - tg)                  # 発進時刻に、その車の領域までの距離
            amax = max(amax, float(DC.obstruction_decel(d, c["v"], iv["t_out"] + slack)["decel"]))
        return amax

    if pol == "naive":
        tg = 0.0
        a_prior = needs(tg, v0, prior, 0.0)
        a_other = needs(tg, v0, other, 0.0)
    else:
        tg = t0
        v_start = v0
        while True:
            a_prior = needs(tg, v_start, prior, MARGIN_T)
            a_other = needs(tg, v_start, other, MARGIN_T)
            if a_prior == 0.0 and a_other <= 2.0:
                break
            tg += 0.1
            v_start = 0.0
            if tg > 300:
                break
        wait = tg
        v0 = v_start
        a_prior = needs(tg, v0, prior, 0.0)
    # 再生: 自分と、減速が要る車を一定の減速で、1 ms 刻みで進め、同じ領域を同時に占めないか
    overlap = 0
    for c in prior + other:
        zs, zl = Z[c["side"]]
        iv = DC.conflict_zone_intervals(zs - entry, zl, CAR_L, v0=v0, accel=A_EGO if v0 < V_EGO else 0.0, v_max=V_EGO)
        d0 = c["v"] * (c["t_zone"] - tg)
        if d0 + cz + CAR_L < 0:
            continue
        a = float(DC.obstruction_decel(d0, c["v"], iv["t_out"] + (MARGIN_T if pol == "rule" else 0.0))["decel"]) if d0 > 0 else 0.0
        if not math.isfinite(a):
            a = 0.0
        # 1 ms 刻みで速さを積分して位置を出す(閉形式の到達時刻とは別の経路)
        tt = np.arange(0.0, iv["t_out"] + 0.001, 0.001)
        vv = np.maximum(c["v"] - a * tt, 0.0)
        dist = np.concatenate([[0.0], np.cumsum(0.5 * (vv[1:] + vv[:-1]) * 0.001)])
        front = dist - d0                                   # その車の前端の、領域の入口からの位置(> 0 で中)
        inside_c = (front > 0) & (front < cz + CAR_L)
        inside_e = (tt >= iv["t_in"]) & (tt <= iv["t_out"])
        overlap += int(bool(np.any(inside_c & inside_e)))
    right_yielded = int(pol == "rule" and pr["yield_to"] == "left" and a_other > 0.0)
    return {"v_entry": v_entry, "wait": wait, "a_need_prior": a_prior, "obstruct": a_prior > 2.0, "overlap": overlap,
            "right_yielded": right_yielded, "tg": tg, "v0": v0, "cars": cars, "prior": [c in prior for c in cars]}


# ───────────────────────────── 5. 横断歩道 ─────────────────────────────
CW0, CW1 = 0.0, 4.0              # 横断歩道
STOPPED_FRONT = CW0 - 1.5        # 左の車線で止まっている車の前端(直前)
Y_LEFT, Y_RIGHT = 4.5, 1.5       # 車線の中心(片側 2 車線、左の車線 y ∈ [3, 6])
V_CW = 40.0 / 3.6


def ped_visible(eye, ped, box):
    """目から歩行者への線分が止まっている車の箱 (x0, x1, y0, y1) を通るか(サンプリングで)。"""
    s = np.linspace(0.0, 1.0, 200)
    X = eye[0] + s * (ped[0] - eye[0])
    Y = eye[1] + s * (ped[1] - eye[1])
    return not bool(np.any((X > box[0]) & (X < box[1]) & (Y > box[2]) & (Y < box[3])))


def sim_cw(pol, v_walk, t_ped0, dt=DT):
    """横断歩道の 1 場面。歩行者は左の歩道(y = 7)から x = CW0 + 1.5 を -y へ。rule = 停止車の前端の手前で一時停止 → 歩行者が
    自分の車線を出るまで待つ → 発進。naive = 40 km/h のまま、見えたら 0.75 s 後に 6 m/s² で止まる。"""
    box = (STOPPED_FRONT - CAR_L, STOPPED_FRONT, Y_LEFT - 0.9, Y_LEFT + 0.9)
    xp = CW0 + 1.5
    x, v, t = -80.0, V_CW, 0.0
    stop_at = STOPPED_FRONT - 0.5
    T, X, V, PY = [], [], [], []
    seen_t = None
    stopped_once = False
    stage = 0
    hit = False
    while t < 40.0 and x < 40.0:
        py = 7.0 - v_walk * max(0.0, t - t_ped0)
        T.append(t)
        X.append(x)
        V.append(v)
        PY.append(py)
        ped_in_lane = (py < 3.0 + 0.3) and (py > -0.3)
        ped_in_my = (py < Y_RIGHT + 0.9 + 0.3) and (py > Y_RIGHT - 0.9 - 0.3)
        if (x > xp - 0.3) and (x - CAR_L < xp + 0.3) and ped_in_my:
            hit = True
        eye = (x - EYE_BACK, Y_RIGHT - 0.37)
        vis = (py < 7.0) and ped_visible(eye, (xp, py), box)
        if vis and seen_t is None:
            seen_t = t
        if pol == "rule":
            # 段 0: 停止車の前端の 0.5 m 手前で一時停止(38 条 2 項)→ 段 1: 徐行で横断歩道の直前(前端 CW0 − 0.5)へ →
            # 段 2: そこで止まり、歩行者が見えて自分の進路を渡り終えるまで待つ(見えない間も待つ)→ 段 3: 発進
            if stage == 0 or stage == 1:
                tgt, vcap = (stop_at, V_CW) if stage == 0 else (CW0 - 0.5, JOKOU)
                rest = tgt - x
                if rest < 0.02:
                    x, v = tgt, 0.0
                    stage += 1
                    stopped_once = True
                else:
                    vn = min(v + 1.0 * dt, vcap, math.sqrt(2.0 * 2.5 * rest))
                    vn = max(vn, v - 6.0 * dt, 0.0)
                    x = min(x + 0.5 * (v + vn) * dt, tgt)
                    v = vn
            elif stage == 2:
                v = 0.0
                if vis and py <= Y_RIGHT - 1.2:
                    stage = 3
            else:
                vn = min(v + 1.5 * dt, V_CW)
                x += 0.5 * (v + vn) * dt
                v = vn
        else:
            if seen_t is not None and t >= seen_t + 0.75 and ped_in_lane:
                vn = max(v - 6.0 * dt, 0.0)
                x += 0.5 * (v + vn) * dt
                v = vn
            else:
                x += v * dt
        t += dt
    return {"t": np.array(T), "x": np.array(X), "v": np.array(V), "py": np.array(PY), "hit": hit, "seen_t": seen_t}


def sim_overtake(pol, kind, v_o, gap0, dt=DT):
    """38 条 3 項: 自分(右の車線、50 km/h)と左の車線の前の車(v_o)。rule = 前に出る位置が [CW0 − 30, CW1] に入るなら
    相手より遅くして、相手が横断歩道を過ぎてから前に出る(自転車は除外なので止めない)。"""
    xe, ve, xo, t = -150.0, 50.0 / 3.6, -150.0 + gap0, 0.0
    T, XE, XO, VE = [], [], [], []
    while t < 60.0 and xe < 60.0:
        T.append(t)
        XE.append(xe)
        XO.append(xo)
        VE.append(ve)
        target = 50.0 / 3.6
        if pol == "rule" and kind not in DC.EXEMPT_KINDS and xe < xo:
            if ve > v_o:
                tp = (xo - xe) / (ve - v_o)
                x_pass = xe + ve * tp
                if CW0 - 30.0 - 1.0 <= x_pass <= CW1 + 1.0 or (CW0 - 31.0 <= xo <= CW1 + 1.0):
                    target = 0.9 * v_o
            elif CW0 - 31.0 <= xo <= CW1 + 1.0:
                target = 0.9 * v_o
        ve = min(ve + 1.5 * dt, target) if ve < target else max(ve - 3.0 * dt, target)
        xe += ve * dt
        xo += v_o * dt
        t += dt
    return {"t": np.array(T), "x": np.array(XE), "v": np.array(VE), "xo": np.array(XO)}


def scene_crosswalk(SM):
    print("== 5. 横断歩道(S043, S044): 停止車両の横 %d 場面、30 m 以内の追い越し %d 場面" % (N_CW, N_CW))
    rng = np.random.default_rng(51)
    vw = SM["v_walk"]
    out = {"rule": [], "naive": []}
    for e in range(N_CW):
        t_ped0 = rng.uniform(5.0, 9.5)                      # 歩き出す時刻(一様 = 仮定、自分が着く前後に重なるように)
        for pol in ("rule", "naive"):
            R = sim_cw(pol, float(vw[e]), t_ped0)
            chk = DC.crosswalk_stopped_vehicle_check(R, [{"x": STOPPED_FRONT, "t0": 0.0, "t1": 1e3}], crosswalk_start=CW0,
                                                     crosswalk_end=CW1)
            out[pol].append({"chk": chk, "hit": R["hit"], "R": R, "t_ped0": t_ped0, "v_walk": float(vw[e])})
    nr = sum(not x["chk"]["ok"] for x in out["rule"])
    nn = sum(not x["chk"]["ok"] for x in out["naive"])
    hr = sum(x["hit"] for x in out["rule"])
    hn = sum(x["hit"] for x in out["naive"])
    print("    停止車両の横: ルール 違反 %d・歩行者に触れた %d / %d、素朴 違反 %d・触れた %d / %d" % (nr, hr, N_CW, nn, hn, N_CW))
    gate("S043: 停止車両の横は前に出る前に一時停止(38 条 2 項)、隠れていた歩行者に触れない", nr == 0 and hr == 0)
    gate("門が自明でない: 止まらずに横を抜けると全場面が 38 条 2 項の違反、隠れていた歩行者に触れる場面がある", nn == N_CW and hn > 0,
         "触れた %d / %d" % (hn, N_CW))
    ov = {"rule": {"car": 0, "bicycle": 0}, "naive": {"car": 0, "bicycle": 0}}
    passes = {"rule": {"car": 0, "bicycle": 0}, "naive": {"car": 0, "bicycle": 0}}
    for e in range(N_CW):
        gap0 = rng.uniform(10.0, 120.0)
        for kind, v_o in (("car", 25.0 / 3.6), ("bicycle", 15.0 / 3.6)):
            for pol in ("rule", "naive"):
                R = sim_overtake(pol, kind, v_o, gap0)
                other = {"t": R["t"], "x": R["xo"], "kind": kind}
                c = DC.crosswalk_overtake_check(R, [other], crosswalk_start=CW0, crosswalk_end=CW1)
                ov[pol][kind] += int(not c["ok"])
                passes[pol][kind] += sum(ev["in_zone"] for ev in c["events"])
    print("    30 m 以内: ルール 違反 車 %d・自転車 %d(自転車を区間内で抜いた %d 場面)、素朴 違反 車 %d(区間内で抜いた 車 %d・自転車 %d)" % (
        ov["rule"]["car"], ov["rule"]["bicycle"], passes["rule"]["bicycle"], ov["naive"]["car"], passes["naive"]["car"],
        passes["naive"]["bicycle"]))
    gate("S044: 横断歩道の手前 30 m 以内で車の前に出ない(38 条 3 項)、自転車は除外(抜いてよい)",
         ov["rule"]["car"] == 0 and ov["rule"]["bicycle"] == 0 and passes["rule"]["bicycle"] > 0)
    gate("門が自明でない: 速さを変えない運転は区間内で車の前に出る場面がある", ov["naive"]["car"] > 0, "%d / %d" % (ov["naive"]["car"], N_CW))
    return {"cw": out, "ov": ov}


# ───────────────────────────── 6. 駐停車禁止 ─────────────────────────────
STREET = [{"kind": "intersection", "start": 40.0, "end": 52.0}, {"kind": "crosswalk", "start": 54.0, "end": 58.0},
          {"kind": "bus_stop", "at": 110.0}, {"kind": "safety_zone", "start": 150.0, "end": 162.0},
          {"kind": "corner", "start": 205.0, "end": 205.0}, {"kind": "railway_crossing", "start": 250.0, "end": 260.0},
          {"kind": "crosswalk", "start": 300.0, "end": 304.0}]
STREET_LEN = 340.0


def scene_parking(SM):
    print("== 6. 駐停車禁止の距離(S105–S109、44 条 1 項): 止まりたい場所 %d 件(一様、仮定)" % N_PARK)
    z = DC.no_stopping_zones(STREET)
    M = z["merged"]
    xs = np.linspace(0.0, STREET_LEN, 340001)
    ref = np.zeros(xs.shape, bool)
    dd = {"intersection": 5, "crosswalk": 5, "bus_stop": 10, "safety_zone": 10, "corner": 5, "railway_crossing": 10}
    for f in STREET:
        s0 = f.get("start", f.get("at"))
        s1 = f.get("end", f.get("at"))
        ref |= (xs >= s0 - dd[f["kind"]]) & (xs <= s1 + dd[f["kind"]])
    got = np.zeros(xs.shape, bool)
    for a, b in M:
        got |= (xs >= a) & (xs <= b)
    print("    禁止の区間(併せて %d): %s" % (len(M), ", ".join("[%.0f, %.0f]" % tuple(r) for r in M)))
    gate("44 条の区間 = 号ごとの距離を格子(1 mm)で直接塗った答え", bool(np.array_equal(got, ref)), "%d 格子点" % xs.size)
    S = DC.legal_stop_intervals(M, 0.0, STREET_LEN, CAR_L)
    rng = np.random.default_rng(61)
    want = rng.uniform(0.0, STREET_LEN - CAR_L, N_PARK)
    naive_bad, reasons, walk, rule_bad = 0, {}, [], 0
    for w in want:
        c = DC.parking_position_check(w, w + CAR_L, z)
        if not c["ok"]:
            naive_bad += 1
            for k, _ in c["reasons"]:
                reasons[k] = reasons.get(k, 0) + 1
        cand = np.clip(w, S[:, 0], S[:, 1])
        j = int(np.argmin(np.abs(cand - w)))
        r = float(cand[j])
        walk.append(abs(r - w))
        rule_bad += int(not DC.parking_position_check(r, r + CAR_L, z)["ok"])
    walk = np.array(walk)
    print("    素朴(止まりたい所に止まる): 違反 %d / %d(%s)、ルール(いちばん近い適法の場所): 違反 %d、余分に歩く 平均 %.1f m・最大 %.1f m" % (
        naive_bad, N_PARK, ", ".join("%s %d" % kv for kv in sorted(reasons.items())), rule_bad, walk.mean(), walk.max()))
    gate("S105–S109: ルールの全員が適法の場所(車体が禁止の区間に重ならない)", rule_bad == 0)
    gate("門が自明でない: 止まりたい所に止まると違反があり、6 種類すべての禁止に当たる", naive_bad > 0 and len(reasons) == 6,
         "%d 件、%d 種類" % (naive_bad, len(reasons)))
    return {"z": z, "S": S, "want": want, "walk": walk, "reasons": reasons}


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    want = figs.enabled()
    tm = {}
    t = time.time()
    SM = scene_samples()
    tm["samples"] = time.time() - t
    out = {"SM": SM}
    for key, fn in (("timing", scene_timing), ("crossing", scene_crossing), ("sight", scene_sight), ("priority", scene_priority),
                    ("crosswalk", scene_crosswalk), ("parking", scene_parking)):
        t = time.time()
        out[key] = fn(SM)
        tm[key] = time.time() - t
    print("  区間ごとの所要 [s]: " + ", ".join("%s %.1f" % kv for kv in tm.items()))
    if want:
        figures(out)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("== 結果: %d / %d 門, %.1f s(CPU %.1f s)" % (sum(OK), len(OK), time.time() - T0, time.process_time()))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


# ───────────────────────────── 7. 図 ─────────────────────────────
GROUND_FAR = np.array([0.42, 0.56, 0.36])     # 草地(地平線より下で何も当たらない画素)
WALK = (0.72, 0.72, 0.68)
YELLOW = (0.95, 0.78, 0.10)
WHITE = (0.95, 0.95, 0.92)
ROAD = (0.40, 0.41, 0.43)
BLACK = (0.08, 0.08, 0.09)
LAMP_ON, LAMP_OFF = np.array([1.0, 0.12, 0.06]), np.array([0.22, 0.05, 0.05])
FOV = 40.0                                    # 縦の画角 [度](横は 16:9 で約 66°)


def _txt(img, s, xy, anchor="lt", fs=12):
    import annotate as AN
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=max(9, fs)), dtype=np.float64)


def _box_mesh(L, W, H, z0=0.0):
    """x 長さ L・y 幅 W・高さ H の箱(底面の中心が原点、z0 から)。頂点の順 = z, y, x の入れ子(0/1)。"""
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
    return V, F, np.vstack(C)


def _quad(xa, xb, ya, yb, z=0.006):
    return np.array([[xa, ya, z], [xb, ya, z], [xb, yb, z], [xa, yb, z]]), np.array([[0, 1, 2], [0, 2, 3]])


def _vquad_x(x, ya, yb, za, zb):
    """x = 一定の縦の面(法線 ±x)。"""
    return np.array([[x, ya, za], [x, yb, za], [x, yb, zb], [x, ya, zb]]), np.array([[0, 1, 2], [0, 2, 3]])


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


def eye_pose(front_x, y, yaw_off=0.0, pitch=-0.02):
    """運転者の目(前端から 2.05 m 後ろ、右ハンドルで車の中心から右 0.37 m、高さ 1.2 m)。yaw_off = 首を振った角(左 +)。"""
    import driveworld as DW
    e = np.array([front_x - EYE_BACK, y - 0.37, 1.2])
    d = np.array([math.cos(yaw_off), math.sin(yaw_off), pitch])
    return DW.camera_pose(e, e + d), e


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

    def rect(self, xa, xb, ya, yb, fill=None, outline=None, width=1):
        self.d.polygon(self.p(np.array([[xa, ya], [xb, ya], [xb, yb], [xa, yb]])), fill=fill, outline=outline, width=width)

    def line(self, P, fill, width=2):
        if len(P) > 1:
            self.d.line(self.p(P), fill=fill, width=width)

    def circle(self, c, r, outline=None, fill=None, width=2):
        (x, y), = self.p(c)
        rr = r * self.s
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=outline, fill=fill, width=width)

    def arr(self):
        return np.asarray(self.im, dtype=np.float64) / 255.0


# ── 踏切の世界 ──
POSTS = ((CS - 1.2, 3.7), (CE + 1.2, -3.7))          # 遮断機つき警報機の柱(自分の側の左、向こう側の右)
BOOM_L = 3.3


def _rot_x(V, ang, about):
    c, s = math.cos(ang), math.sin(ang)
    R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return (V - about) @ R.T + about


def boom_vertices(pivot, sgn, theta, n_seg=4):
    """遮断かん(4 区間の箱)の頂点。theta = π/2 で上、0 で水平(道を横切る向き = y 方向に sgn)。"""
    d = np.array([0.0, sgn * math.cos(theta), math.sin(theta)])
    nrm = np.array([0.0, -sgn * math.sin(theta), math.cos(theta)])
    e = np.array([1.0, 0.0, 0.0])
    h = 0.045
    out = []
    for k in range(n_seg):
        a0, a1 = BOOM_L * k / n_seg, BOOM_L * (k + 1) / n_seg
        for b in (-h, h):
            for cx in (-h, h):
                for a in (a0, a1):
                    out.append(pivot + a * d + cx * e + b * nrm)
    return np.array(out)


def train_mesh():
    """4 両の列車(+y に進む、先頭の端が y = 0、車体は y < 0 へ)。"""
    parts = []
    for k in range(4):
        yc = -(k + 0.5) * 20.0
        v, f = _box_mesh(2.9, 19.6, 3.4, 0.45)
        parts.append((v + [0, yc, 0], f, (0.80, 0.82, 0.84)))
        for sx in (-1, 1):
            v, f = _box_mesh(0.04, 18.0, 0.7, 2.1)
            parts.append((v + [sx * 1.47, yc, 0], f, (0.12, 0.14, 0.18)))
            v, f = _box_mesh(0.04, 19.4, 0.25, 1.3)
            parts.append((v + [sx * 1.47, yc, 0], f, (0.10, 0.50, 0.30)))
    v, f = _box_mesh(2.5, 0.05, 1.0, 2.0)                    # 先頭の窓
    parts.append((v + [0, 0.01, 0], f, (0.12, 0.14, 0.18)))
    return _mesh(parts)


def world_crossing():
    import driveworld as DW
    w = DW._empty_world()
    V, F = DW._grid_plane(-120, 120, -3.6, 3.6, step=4.0)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    for xa in np.arange(CS, CE, 2.0):                        # 踏切の板(明るい舗装)
        V, F = _quad(xa, xa + 2.0, -DECK_HALF, DECK_HALF, z=0.004)
        DW.world_add(w, V, F, 0, (0.56, 0.55, 0.51), name="deck")
    for xt in TRK:
        for y0 in np.arange(-300.0, 300.0, 10.0):
            if abs(y0 + 5.0) < 9.0:
                continue
            V, F = _quad(xt - 1.6, xt + 1.6, y0, y0 + 10.0, z=0.003)
            DW.world_add(w, V, F, 0, (0.46, 0.43, 0.39), name="ballast")
        for xr in (xt - GAUGE / 2, xt + GAUGE / 2):
            for y0 in np.arange(-300.0, 300.0, 10.0):
                flush = abs(y0 + 5.0) < 9.0                     # 踏切の板の中のレールは板と同じ高さ(溝だけ見える)
                v, f = _box_mesh(0.07, 10.0, 0.012 if flush else 0.14)
                DW.world_add(w, v + [xr, y0 + 5.0, 0], f, 8, (0.30, 0.30, 0.32) if flush else (0.62, 0.62, 0.64), name="rail")
    for xa, xb in ((-120.0, SL - 0.6), (CE + 4.0, 120.0)):          # 白線(10 m ごとに切る)
        for ya, yb in ((-0.06, 0.06), (2.94, 3.06), (-3.06, -2.94)):
            for x0 in np.arange(xa, xb, 10.0):
                V, F = _quad(x0, min(x0 + 10.0, xb), ya, yb)
                DW.world_add(w, V, F, 9, WHITE, name="line")
    V, F = _quad(SL - 0.45, SL, 0.0, 3.0, z=0.007)
    DW.world_add(w, V, F, 9, WHITE, name="stop_line")
    V, F = _quad(CE + 3.0, CE + 3.45, -3.0, 0.0, z=0.007)
    DW.world_add(w, V, F, 9, WHITE, name="stop_line")
    ids = {"lamps": {}, "booms": []}
    for pi, (px, py) in enumerate(POSTS):
        parts = []
        v, f = _box_mesh(0.16, 0.16, 3.3)
        parts.append((v + [px, py, 0], f, YELLOW))
        for z0 in np.arange(0.2, 1.8, 0.5):
            v, f = _box_mesh(0.17, 0.17, 0.25, z0)
            parts.append((v + [px, py, 0], f, BLACK))
        v, f = _box_mesh(0.10, 1.10, 0.10, 2.48)
        parts.append((v + [px, py, 0], f, BLACK))
        for ang in (0.7, -0.7):                              # クロスマーク(黄と黒)
            v, f = _box_mesh(0.05, 1.3, 0.20, -0.10)
            v = _rot_x(v, ang, np.zeros(3)) + [px, py, 3.05]
            parts.append((v, f, YELLOW))
        Vp, Fp, Cp = _mesh(parts)
        DW.world_add(w, Vp, Fp, 3, Cp, name="post")
        for face in (-1.0, 1.0):
            for side, dy in (("L", 0.35), ("R", -0.35)):
                # 自分(+x へ進む)から見て左 = +y。向こう側を向く面(+x)では左右が入れ替わるが、ここでは y の側で呼ぶ
                V, F = _vquad_x(px + face * 0.09, py + dy - 0.15, py + dy + 0.15, 2.08, 2.38)
                i = DW.world_add(w, V, F, 3, LAMP_OFF, name="lamp")
                ids["lamps"][(pi, face, side)] = w["objects"][i]["faces"]
                V, F = _vquad_x(px + face * 0.085, py + dy - 0.2, py + dy + 0.2, 2.03, 2.43)
                DW.world_add(w, V, F, 3, BLACK, name="lamp_back")
        sgn = -1.0 if py > 0 else 1.0
        pivot = np.array([px, py + 0.0 * sgn, 1.0])
        Vb = boom_vertices(pivot, sgn, 0.5 * math.pi)
        Fb = np.vstack([_box_mesh(1, 1, 1)[1] + 8 * k for k in range(4)])
        Cb = np.vstack([np.tile(YELLOW if k % 2 == 0 else BLACK, (12, 1)) for k in range(4)])
        i = DW.world_add(w, Vb, Fb, 4, Cb, name="boom")
        ids["booms"].append((i, pivot, sgn))
    rng = np.random.default_rng(5)
    for x0 in list(np.arange(-90.0, -12.0, 14.0)) + list(np.arange(26.0, 100.0, 14.0)):
        for sy in (-1, 1):
            if rng.random() < 0.3:
                continue
            v, f = _box_mesh(10.0, 8.0, rng.uniform(4, 11))
            col = tuple(rng.uniform(0.5, 0.82) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
            DW.world_add(w, v + [x0, sy * rng.uniform(11.0, 16.0), 0], f, 6, col, name="building")
    Vt, Ft, Ct = train_mesh()
    i = DW.world_add(w, Vt + [TRK[0], -900.0, 0], Ft, 6, Ct, name="train")
    ids["train"] = (i, Vt)
    ids["queue"] = DW.add_asset(w, "sedan", -900.0, 1.5, 0.0)
    return w, ids


def set_crossing_state(w, ids, sc, t, fps):
    """時刻 t の遮断かん・警報灯・列車を世界に書き込む。返り値 (状態, 左右の灯の明るさ)。"""
    g = DC.crossing_gate_state(np.array([t]), **gate_of(sc))
    st = int(g["state"][0])
    th = float(g["boom_angle"][0])
    for i, pivot, sgn in ids["booms"]:
        v0, v1 = w["objects"][i]["verts"]
        w["V"][v0:v1] = boom_vertices(pivot, sgn, th)
    lam = DC.crossing_lamp_signal(np.array([t]), t_on=sc["t_w"], t_off=sc["t_clr"], exposure=0.5 / fps)[0]
    for (pi, face, side), (f0, f1) in ids["lamps"].items():
        k = 0 if side == "L" else 1
        w["face_color"][f0:f1] = LAMP_OFF + (LAMP_ON - LAMP_OFF) * lam[k]
    i, Vt = ids["train"]
    v0, v1 = w["objects"][i]["verts"]
    yf = -DECK_HALF + sc["v_train"] * (t - sc["t_arr"])
    yf = yf if -700 < yf < 700 else -900.0
    w["V"][v0:v1] = Vt + [TRK[0], yf, 0]
    return st, lam, yf


def look_yaw(R, t):
    """左右を見る首の角(見る区間の中で sin の山、左 +70°、右 −70°)。"""
    for tl_end, side in R["looks"]:
        k = 0 if side == "left" else 1
        dur = R["t_look"][k]
        if tl_end - dur <= t <= tl_end:
            u = (t - (tl_end - dur)) / dur
            return (1 if side == "left" else -1) * math.radians(70.0) * math.sin(math.pi * u), side
    return 0.0, None


STATE_JA = ("警報なし", "警報中(灯が交互に点滅)", "遮断かん 降下中", "遮断中", "遮断かん 上昇中")


def demo_crossing_scenarios(SM):
    """主図の場面: (1) ルール、警報が止まった直後に始まる (2) 向こう側が詰まっているのに入る。"""
    t_stop = (SL - 0.5 + 60.0 - V_APP * V_APP / (2 * DECEL)) / V_APP + V_APP / DECEL
    base = {"i": -1, "v_train": 80.0 / 3.6, "a_go": 1.5, "t_look": (1.4, 1.4), "queue": None}
    s1 = dict(base, t_w=t_stop + 3.0)
    s1["t_arr"] = s1["t_w"] + T_WARN
    s1["t_clr"] = s1["t_arr"] + (TRAIN_L + CLEN) / s1["v_train"]
    s2 = dict(base, queue=(CE + 2.5, 1e9), t_w=t_stop + 9.0)
    s2["t_arr"] = s2["t_w"] + T_WARN
    s2["t_clr"] = s2["t_arr"] + (TRAIN_L + CLEN) / s2["v_train"]
    return s1, s2


def fig_dashcam_crossing(out):
    """主図: 車載カメラ(運転者の目)。場面 1 = 止まって警報を待ち、列車が過ぎて遮断かんが上がってから左右を見て一気に渡る。
    場面 2 = 向こう側が詰まっているのに入り、踏切の中で止まったところで警報が始まる。"""
    import driveworld as DW
    Wv, Hv = VID_WH
    small = Wv < 500
    fsz = 9 if small else 12
    fps = 2.5 if small else 4.0
    K = DW.camera_intrinsics(FOV, Wv, Hv)
    w, ids = world_crossing()
    s1, s2 = demo_crossing_scenarios(out["SM"])
    R1 = sim_crossing(s1, "rule")
    R1["t_look"] = s1["t_look"]
    chk1, hit1, _ = check_run(s1, R1)
    frames, lampL, lampR, lamp_t = [], [], [], []
    t0 = float(np.interp(-45.0, R1["x"], R1["t"]))
    t1 = float(np.interp(CE + 12.0, R1["x"], R1["t"]))
    sw = int(Wv * 0.27)
    # 計る灯: 向こう側の柱(右)の、こちらを向く面(-x)の 2 灯
    lamp_pts = {s: np.array([POSTS[1][0] - 0.09, POSTS[1][1] + dy, 2.23]) for s, dy in (("L", 0.35), ("R", -0.35))}
    for t in np.arange(t0, t1, 1.0 / fps):
        x = float(np.interp(t, R1["t"], R1["x"]))
        v = float(np.interp(t, R1["t"], R1["v"]))
        st, lam, yf = set_crossing_state(w, ids, s1, t, fps)
        yaw, side = look_yaw(R1, t)
        pose, eye = eye_pose(x, Y_LANE, yaw)
        f = render(w, pose, K, Wv, Hv)["color"].copy()
        # 列車が来ると向こう側の柱の灯を隠す(画素が車体の色になる)ので、読むのは警報の 1 s 前から到達まで
        if side is None and abs(v) < 1e-6 and s1["t_w"] - 1.0 <= t <= s1["t_arr"]:
            vals = []
            for s in ("L", "R"):
                c, r, dep = DW.world_project_points(lamp_pts[s][None, :], pose, K)
                cc, rr = int(round(float(c[0]))), int(round(float(r[0])))
                rad = 0 if small else 1
                vals.append(float(f[max(rr - rad, 0):rr + rad + 1, max(cc - rad, 0):cc + rad + 1, 0].mean()))
            lampL.append(vals[0])
            lampR.append(vals[1])
            lamp_t.append(t)
        T = Top(sw, sw, (-12.0, 22.0), (-17.0, 17.0), bg=(222, 228, 214))
        T.rect(-12, 22, -3.6, 3.6, fill=(110, 112, 116))
        for xt in TRK:
            T.rect(xt - 1.6, xt + 1.6, -17, 17, fill=(120, 108, 96))
        T.rect(CS, CE, -DECK_HALF, DECK_HALF, fill=(150, 148, 140))
        for (i, pivot, sgn) in ids["booms"]:
            g = DC.crossing_gate_state(np.array([t]), **gate_of(s1))
            L = BOOM_L * math.cos(float(g["boom_angle"][0]))
            T.line(np.array([pivot[:2], pivot[:2] + [0, sgn * max(L, 0.3)]]), (240, 200, 30), 3)
        for (pi, face, sd), _ in ids["lamps"].items():
            if face < 0:
                k = 0 if sd == "L" else 1
                px, py = POSTS[pi]
                c = tuple(int(255 * q) for q in (LAMP_OFF + (LAMP_ON - LAMP_OFF) * lam[k]))
                T.circle((px - 0.6, py + (0.8 if sd == "L" else -0.8)), 0.55, fill=c, outline=(40, 0, 0), width=1)
        if -40 < yf < 120:
            T.rect(TRK[0] - 1.45, TRK[0] + 1.45, yf - TRAIN_L, yf, fill=(200, 205, 210), outline=(40, 60, 50))
        T.rect(x - CAR_L, x, Y_LANE - 0.9, Y_LANE + 0.9, fill=(60, 120, 230), outline=(20, 30, 60))
        f[Hv - sw - 8:Hv - 8, Wv - sw - 8:Wv - 8] = T.arr()
        f = _txt(f, "上から", (Wv - sw // 2 - 8, Hv - sw - 10), anchor="cb", fs=fsz - 1)
        lines = ["場面 1: 直前で止まり、警報の間は待ち、左右を見て一気に渡る" if not small else "場面 1: 止まる・待つ・左右・一気に",
                 "%s  %4.1f km/h" % (STATE_JA[st], 3.6 * v)]
        if s1["t_w"] <= t <= s1["t_arr"]:
            lines.append("警報から %.1f s ・ 列車の到達まで %.1f s" % (t - s1["t_w"], s1["t_arr"] - t))
        if side:
            lines.append("%s を見る(目と耳で確かめる)" % ("左" if side == "left" else "右"))
        if R1["mode"][min(int(np.searchsorted(R1["t"], t)), len(R1["mode"]) - 1)] == "restop":
            lines.append("発進した直後に警報 → 止まり直す")
        f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
        frames.append(np.clip(f, 0, 1))
    n1 = len(frames)
    # 場面 2: 向こう側が詰まっている
    R2 = sim_crossing(s2, "ignore_queue", t_end=s2["t_w"] + 14.0)
    chk2, _, _ = check_run(s2, R2)
    DW.world_move(w, ids["queue"], s2["queue"][0] + 0.5 * CAR_L, Y_LANE + 0.3, 0.0)
    room = DC.exit_room_check(s2["queue"][0], CE, CAR_L, gap=GAP, beyond=BEYOND)
    t0 = float(np.interp(-30.0, R2["x"], R2["t"]))
    for t in np.arange(t0, R2["t"][-1], 1.0 / fps):
        x = float(np.interp(t, R2["t"], R2["x"]))
        v = float(np.interp(t, R2["t"], R2["v"]))
        st, lam, yf = set_crossing_state(w, ids, s2, t, fps)
        pose, eye = eye_pose(x, Y_LANE, 0.0)
        f = render(w, pose, K, Wv, Hv)["color"].copy()
        on_track = x > CS and x - CAR_L < CE
        lines = ["場面 2: 向こう側が詰まっているのに入る", "向こう側の余地 %.1f m < 必要 %.1f m(50 条 2 項)" % (room["room"], room["need"]),
                 "%s  %4.1f km/h%s" % (STATE_JA[st], 3.6 * v, "  踏切の中で止まった" if on_track and v < 0.05 else "")]
        if st >= 1:
            lines.append("列車の到達まで %.1f s" % (s2["t_arr"] - t))
        f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
        frames.append(np.clip(f, 0, 1))
    DW.world_move(w, ids["queue"], -900.0, 1.5, 0.0)
    figs.save_video("crossing_dashcam", frames, fps=2 * fps, gif_every=1 if small else 2, gif_width=480,
                    caption="主図(運転者の目 %d × %d、%d コマ、%.1f 倍速)。場面 1(%d コマ): 停止線の直前で止まり(33 条 1 項)、左右を見て発進した直後"
                            "(止まってから %.0f s)に警報が始まり、踏切の手前で止まり直す。"
                            "解釈基準の遮断機の時刻(警報→遮断の終わり %.0f s、遮断→到達 %.0f s)どおりに遮断かんが降り、%.0f km/h・%.0f m の列車が過ぎ、"
                            "かんが上がり切ってから左・右を見て(首を振る)一気に渡る。crossing_stop_check の判定 = %s。右下 = 上から見た図"
                            "(赤い丸 = 交互に点く警報灯)。場面 2: 向こう側の余地 %.1f m(車長 + 車間 + 余裕 = %.1f m が要る)なのに入り、踏切の中で止まる"
                            "(判定 = %s)。そこへ警報が始まる。" % (
                                Wv, Hv, len(frames), 2.0, n1, s1["t_w"] - float(R1["t"][np.flatnonzero(R1["v"] == 0)[0]]),
                                T_LOWER + D_LOWER, T_WARN - T_LOWER - D_LOWER, 3.6 * s1["v_train"], TRAIN_L,
                                "違反なし" if chk1["ok"] else ", ".join(chk1["violations"]), room["room"], room["need"],
                                ", ".join(chk2["violations"]) or "違反なし"))
    return {"n": len(frames), "n1": n1, "chk1": chk1, "chk2": chk2, "lampL": np.array(lampL), "lampR": np.array(lampR),
            "lamp_t": np.array(lamp_t), "fps": fps, "s1": s1, "R1": R1}


# ── 横断歩道の世界 ──
def world_cw():
    import driveworld as DW
    import driveterrain as DT
    w = DW._empty_world()
    V, F = DW._grid_plane(-120, 80, -6.0, 6.0, step=4.0)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    for sy in (1, -1):
        V, F = DW._grid_plane(-120, 80, 6.0, 9.0, step=4.0, z=0.15) if sy > 0 else DW._grid_plane(-120, 80, -9.0, -6.0, step=4.0, z=0.15)
        DW.world_add(w, V, F, 1, WALK, name="walk")
    for ya, yb, col in ((-0.1, -0.02, YELLOW), (0.02, 0.1, YELLOW), (2.95, 3.05, WHITE), (5.85, 5.95, WHITE), (-5.95, -5.85, WHITE),
                        (-3.05, -2.95, WHITE)):
        for x0 in np.arange(-120.0, 80.0, 10.0):
            if CW0 - 1.0 < x0 + 10.0 and x0 < CW1 + 1.0:
                continue
            V, F = _quad(x0, x0 + 10.0, ya, yb)
            DW.world_add(w, V, F, 9, col, name="line")
    cm = DT.crosswalk_mesh((CW1, -6.0), (CW1, 6.0), length=CW1 - CW0)
    DW.world_add(w, cm["V"], cm["F"], 12, cm["color"], name="crosswalk")
    rng = np.random.default_rng(9)
    for x0 in list(np.arange(-100.0, -4.0, 12.0)) + list(np.arange(10.0, 80.0, 12.0)):
        for sy in (1, -1):
            v, f = _box_mesh(10.0, 7.0, rng.uniform(5, 12))
            col = tuple(rng.uniform(0.5, 0.82) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
            DW.world_add(w, v + [x0, sy * 13.5, 0.15], f, 6, col, name="building")
    ids = {"stopped": DW.add_asset(w, "suv", STOPPED_FRONT - 0.5 * 4.7, Y_LEFT, 0.0),
           "ped": DT.add_mesh_object(w, DT.pedestrian_mesh(1.7), CW0 + 1.5, 7.0, -0.5 * math.pi, name="ped")}
    return w, ids


def fig_dashcam_crosswalk(out):
    import driveworld as DW
    Wv, Hv = VID_WH
    small = Wv < 500
    fsz = 9 if small else 12
    fps = 4.0 if small else 6.0
    K = DW.camera_intrinsics(FOV, Wv, Hv)
    w, ids = world_cw()
    cw = out["crosswalk"]["cw"]
    hits = [k for k, e in enumerate(cw["naive"]) if e["hit"]]
    k = hits[0] if hits else int(np.argmin([abs(e["t_ped0"] - 7.0) for e in cw["naive"]]))
    ep = cw["rule"][k]
    frames = []
    nseg = {}
    for pol in ("rule", "naive"):
        R = sim_cw(pol, ep["v_walk"], ep["t_ped0"])
        chk = DC.crosswalk_stopped_vehicle_check(R, [{"x": STOPPED_FRONT, "t0": 0.0, "t1": 1e3}], crosswalk_start=CW0, crosswalk_end=CW1)
        t0 = float(np.interp(-45.0, R["x"], R["t"]))
        t_end = float(R["t"][-1]) if pol == "rule" else min(float(R["t"][-1]), (R["seen_t"] or 10.0) + 3.5)
        if pol == "rule":
            t_end = min(t_end, float(np.interp(CW1 + 8.0, R["x"], R["t"])))
        n0 = len(frames)
        t_hit = None
        for t in np.arange(t0, t_end, 1.0 / fps):
            x = float(np.interp(t, R["t"], R["x"]))
            v = float(np.interp(t, R["t"], R["v"]))
            py = float(np.interp(t, R["t"], R["py"]))
            DW.world_move(w, ids["ped"], CW0 + 1.5, py, -0.5 * math.pi)
            pose, eye = eye_pose(x, Y_RIGHT, 0.0)
            f = render(w, pose, K, Wv, Hv)["color"].copy()
            in_my = (Y_RIGHT - 1.2 < py < Y_RIGHT + 1.2)
            touch = in_my and (x > CW0 + 1.5 - 0.3) and (x - CAR_L < CW0 + 1.5 + 0.3)
            if touch and t_hit is None:
                t_hit = t
            title = ("場面 1: 止まっている車の横は、前に出る前に一時停止(38 条 2 項)" if pol == "rule"
                     else "場面 2: 止まらずに横を抜ける(%s)" % ("違反" if not chk["ok"] else "—"))
            vis = py < 7.0 and ped_visible((x - EYE_BACK, Y_RIGHT - 0.37), (CW0 + 1.5, py),
                                           (STOPPED_FRONT - CAR_L, STOPPED_FRONT, Y_LEFT - 0.9, Y_LEFT + 0.9))
            lines = [title, "%4.1f km/h  歩行者 %s" % (3.6 * v, "見える" if vis else "止まっている車の陰")]
            if touch or (t_hit is not None and t > t_hit):
                lines.append("歩行者に触れた")
            f = _txt(f, "\n".join(lines), (6, 6), fs=fsz)
            frames.append(np.clip(f, 0, 1))
        nseg[pol] = (len(frames) - n0, chk["ok"], R["hit"])
    figs.save_video("crosswalk_dashcam", frames, fps=fps, gif_every=1 if small else 2, gif_width=480,
                    caption="車載カメラ(%d × %d、%d コマ)。片側 2 車線、左の車線の SUV が横断歩道の直前で止まっている(歩行者 %.2f m/s が陰から渡る)。"
                            "場面 1(%d コマ): 横に並ぶ前に一時停止、徐行で横断歩道の直前へ出て、歩行者が見えて渡り終えるまで待つ —— "
                            "crosswalk_stopped_vehicle_check = %s、触れた = %s。場面 2(%d コマ): 40 km/h のまま横を抜け、見えてから 0.75 s 後に 6 m/s² で止まろうとする"
                            " —— 判定 = %s、触れた = %s。" % (
                                Wv, Hv, len(frames), ep["v_walk"], nseg["rule"][0], "違反なし" if nseg["rule"][1] else "違反",
                                "はい" if nseg["rule"][2] else "いいえ", nseg["naive"][0], "違反なし" if nseg["naive"][1] else "38 条 2 項の違反",
                                "はい" if nseg["naive"][2] else "いいえ"))
    return {"n": len(frames), "seg": nseg, "k": k}


def fig_birdseye_crossing(out):
    """上から見た動画: 同じ場面(向こう側が詰まり、まもなく警報)をルール・詰まっていても入る・警報中でも入る の 3 人で。"""
    C = out["crossing"]
    scs, res = C["scs"], C["res"]
    best = None
    for j, sc in enumerate(scs):
        a = res["ignore_queue"]["rows"][j]
        b = res["ignore_warning"]["rows"][j]
        R = a[2]
        stuck = (R["x"] > CS) & (R["x"] - CAR_L < CE) & (R["v"] < 0.05)
        warn_in_stuck = bool(np.any(stuck & (R["t"] >= sc["t_w"]) & (R["t"] <= sc["t_w"] + 1.0)))
        score = 3 * warn_in_stuck + 2 * bool(stuck.any()) + ("entered_while_forbidden" in " / ".join(b[0]["violations"])) + b[1]
        if best is None or score > best[0]:
            best = (score, j)
    j = best[1]
    sc = scs[j]
    pols = ("rule", "ignore_queue", "ignore_warning")
    Rs = {p: sim_crossing(sc, p) for p in pols}
    chks = {p: check_run(sc, Rs[p]) for p in pols}
    W, H = (720, 300) if REDUCED else (1200, 520)
    pw = W // 3
    frames = []
    t_end = min(max(float(np.interp(26.0, R["x"], R["t"])) for R in Rs.values()) + 2.0, sc["t_clr"] + D_RAISE + 20.0)
    t_beg = max(0.0, min(float(np.interp(-16.0, R["x"], R["t"])) for R in Rs.values()))
    step = 1.0 if REDUCED else 0.5
    for t in np.arange(t_beg, t_end, step):
        img = np.ones((H, W, 3))
        g = DC.crossing_gate_state(np.array([t]), **gate_of(sc))
        st = int(g["state"][0])
        lam = DC.crossing_lamp_signal(np.array([t]), t_on=sc["t_w"], t_off=sc["t_clr"])[0]
        yf = -DECK_HALF + sc["v_train"] * (t - sc["t_arr"])
        for k, p in enumerate(pols):
            R = Rs[p]
            T = Top(pw, H, (-16.0, 26.0), (-26.0, 26.0), bg=(222, 228, 214))
            T.rect(-16, 26, -3.6, 3.6, fill=(110, 112, 116))
            for xt in TRK:
                T.rect(xt - 1.6, xt + 1.6, -30, 30, fill=(120, 108, 96))
            T.rect(CS, CE, -DECK_HALF, DECK_HALF, fill=(150, 148, 140))
            T.line(np.array([[SL, 0], [SL, 3]]), (250, 250, 250), 2)
            for pi, (px, py) in enumerate(POSTS):
                sgn = -1.0 if py > 0 else 1.0
                L = BOOM_L * math.cos(float(g["boom_angle"][0]))
                T.line(np.array([[px, py], [px, py + sgn * max(L, 0.3)]]), (240, 200, 30), 3)
                for sd, dy in (("L", 0.8), ("R", -0.8)):
                    kk = 0 if sd == "L" else 1
                    c = tuple(int(255 * q) for q in (LAMP_OFF + (LAMP_ON - LAMP_OFF) * lam[kk]))
                    T.circle((px - 0.9, py + dy), 0.6, fill=c, outline=(40, 0, 0), width=1)
            if -60 < yf < 140:
                T.rect(TRK[0] - 1.45, TRK[0] + 1.45, yf - TRAIN_L, yf, fill=(200, 205, 210), outline=(40, 60, 50), width=2)
            q = queue_at(sc, t)
            if math.isfinite(q):
                T.rect(q, q + CAR_L, Y_LANE - 0.6, Y_LANE + 1.2, fill=(150, 150, 160), outline=(40, 40, 40))
            x = float(np.interp(t, R["t"], R["x"]))
            on = x > CS and x - CAR_L < CE
            danger = on and st >= 1
            T.rect(x - CAR_L, x, Y_LANE - 0.9, Y_LANE + 0.9, fill=(220, 50, 40) if danger else (60, 120, 230), outline=(20, 30, 60),
                   width=2)
            pan = T.arr()
            name = {"rule": "ルール", "ignore_queue": "詰まっていても入る", "ignore_warning": "警報中でも入る"}[p]
            ch, hit, _ = chks[p]
            pan = _txt(pan, "%s\n%s" % (name, ", ".join(ch["violations"]) or "違反なし"), (6, 6), fs=11 if not REDUCED else 9)
            img[:, k * pw:(k + 1) * pw] = pan[:, :pw]
        img = _txt(img, "t = %.1f s  %s%s" % (t, STATE_JA[st], ("  列車の到達まで %.0f s" % (sc["t_arr"] - t)) if sc["t_w"] <= t < sc["t_arr"] else ""),
                   (W // 2, H - 6), anchor="cb", fs=12 if not REDUCED else 9)
        frames.append(np.clip(img, 0, 1))
    figs.save_video("crossing_birdseye", frames, fps=2.0 / step, gif_every=1, gif_width=W if W <= 720 else 720,
                    caption="上から見た動画(%d コマ、%.1f 秒ごと)。乱数の場面 #%d(列車 %.0f km/h、向こう側の列の後端 = 踏切の端から %.1f m)を 3 人で。"
                            "左 = ルール(%s)、中 = 向こう側が詰まっていても入る(%s)、右 = 警報中でも入る(%s、列車が着くとき線路の上 = %s)。"
                            "赤い車 = 警報〜上昇中に車体が踏切の上。" % (
                                len(frames), step, j, 3.6 * sc["v_train"], (sc["queue"][0] - CE) if sc["queue"] else float("nan"),
                                ", ".join(chks["rule"][0]["violations"]) or "違反なし", ", ".join(chks["ignore_queue"][0]["violations"]) or "違反なし",
                                ", ".join(chks["ignore_warning"][0]["violations"]) or "違反なし", "はい" if chks["ignore_warning"][1] else "いいえ"))
    return {"n": len(frames), "j": j}


def fig_birdseye_priority(out):
    """上から見た動画: 狭い道から広い道へ(S098)。ルール(徐行して譲る)と素朴(30 km/h のまま)を同じ交差道路の車で。"""
    P = out["priority"]["wide"]
    res = P["res"]
    Z, entry = P["Z"], P["entry"]
    cand = [e for e in range(len(res["naive"])) if res["naive"][e]["obstruct"] and math.isfinite(res["naive"][e]["a_need_prior"])]
    e = cand[0] if cand else 0
    W, H = (640, 340) if REDUCED else (960, 500)
    pw = W // 2
    cz = CAR_W + 0.6
    frames = []
    info = {}
    for pol in ("rule", "naive"):
        r = res[pol][e]
        tg, v0 = r["tg"], r["v0"]
        iv = {s: DC.conflict_zone_intervals(Z[s][0] - entry, Z[s][1], CAR_L, v0=v0, accel=A_EGO if v0 < V_EGO else 0.0, v_max=V_EGO)
              for s in ("right", "left")}
        acc = []
        for c in r["cars"]:
            d0 = c["v"] * (c["t_zone"] - tg)
            a = 0.0
            if d0 > 0 and c["t_zone"] + (cz + CAR_L) / c["v"] >= tg:
                a = float(DC.obstruction_decel(d0, c["v"], iv[c["side"]]["t_out"] + (MARGIN_T if pol == "rule" else 0.0))["decel"])
            acc.append(a if math.isfinite(a) else 0.0)
        info[pol] = (r, acc)
    tg_max = max(info[p][0]["tg"] for p in info)
    for t in np.arange(-3.0, tg_max + 6.0, 0.2 if not REDUCED else 0.4):
        img = np.ones((H, W, 3))
        for k, pol in enumerate(("rule", "naive")):
            r, acc = info[pol]
            tg, v0 = r["tg"], r["v0"]
            T = Top(pw, H, (-30.0, 22.0), (-26.0, 26.0), bg=(222, 228, 214))
            T.rect(-30, 22, -1.0, 3.0, fill=(120, 122, 126))                      # 狭い道(幅 4 m)
            T.rect(XC - LANE_C, XC + LANE_C, -26, 26, fill=(100, 102, 106))       # 広い道
            T.line(np.array([[XC, -26], [XC, 26]]), (240, 220, 120), 1)
            T.line(np.array([[entry, -1.0], [entry, 3.0]]), (250, 250, 250), 2)
            # 自分
            if t < 0:
                x = entry + (JOKOU if pol == "rule" else V_EGO) * t
            elif t < tg:
                x = entry
            else:
                tau = t - tg
                if v0 < V_EGO:
                    ta = (V_EGO - v0) / A_EGO
                    x = entry + (v0 * tau + 0.5 * A_EGO * tau * tau if tau < ta else v0 * ta + 0.5 * A_EGO * ta * ta + V_EGO * (tau - ta))
                else:
                    x = entry + V_EGO * tau
            T.rect(x - CAR_L, x, 0.1, 1.9, fill=(60, 120, 230), outline=(20, 30, 60), width=2)
            worst = 0.0
            for c, a in zip(r["cars"], acc):
                # 交差道路の車の前端の、領域の入口までの距離 d(t)
                if t < tg:
                    d = c["v"] * (c["t_zone"] - t)
                else:
                    d0 = c["v"] * (c["t_zone"] - tg)
                    tau = t - tg
                    if a > 0:
                        ts = c["v"] / a
                        trav = c["v"] * tau - 0.5 * a * tau * tau if tau < ts else c["v"] * ts - 0.5 * a * ts * ts
                    else:
                        trav = c["v"] * tau
                    d = d0 - trav
                    if a > 0 and tau < c["v"] / a:
                        worst = max(worst, a)
                y_in = 1.0 - 0.5 * cz if c["side"] == "right" else 1.0 + 0.5 * cz
                xc = XC - 0.5 * LANE_C if c["side"] == "right" else XC + 0.5 * LANE_C
                if c["side"] == "right":
                    yf = y_in - d
                    ya, yb = yf - CAR_L, yf
                else:
                    yf = y_in + d
                    ya, yb = yf, yf + CAR_L
                if yb < -30 or ya > 30:
                    continue
                col = (220, 50, 40) if a > 2.0 else ((240, 160, 40) if a > 0 else (170, 170, 175))
                T.rect(xc - 0.9, xc + 0.9, ya, yb, fill=col, outline=(30, 30, 30))
            pan = T.arr()
            nm = "ルール: 徐行して譲る" if pol == "rule" else "素朴: 30 km/h のまま"
            pan = _txt(pan, "%s\n交差道路の車に要った減速度 最大 %.1f m/s²" % (nm, max(acc) if acc else 0.0), (6, 6), fs=11 if not REDUCED else 9)
            img[:, k * pw:(k + 1) * pw] = pan[:, :pw]
        img = _txt(img, "t = %.1f s(自分が線に着いた時刻 = 0)  赤 = 急な減速(> 2.0 m/s²)、橙 = 減速" % t, (W // 2, H - 6), anchor="cb",
                   fs=11 if not REDUCED else 9)
        frames.append(np.clip(img, 0, 1))
    rr, an = info["rule"][0], info["naive"][1]
    figs.save_video("priority_birdseye", frames, fps=5.0 if not REDUCED else 2.5, gif_every=1, gif_width=W if W <= 720 else 720,
                    caption="上から見た動画(%d コマ)。狭い道(4 m)から広い道(%.1f m)へ(S098、36 条 2・3 項)。場面 #%d の同じ交差道路の車で、左 = ルール"
                            "(線で徐行 10 km/h、%.1f s 待ってから、交差道路の車に減速を一切させない時刻に発進)、右 = 30 km/h のまま入る(交差道路の車に要った"
                            "減速度 最大 %.1f m/s² = 進行妨害)。" % (len(frames), 2 * LANE_C + 0.5, e, rr["tg"], max(an) if an else 0.0))
    return {"n": len(frames), "e": e}


def fig_static(out, A):
    from PIL import Image, ImageDraw
    res = {}
    # 1. 踏切の時刻の線図(主図の場面 1)
    s1 = A["s1"]
    t = np.arange(s1["t_w"] - 5.0, s1["t_clr"] + D_RAISE + 5.0, 0.02)
    g = DC.crossing_gate_state(t, **gate_of(s1))
    lam = DC.crossing_lamp_signal(t, t_on=s1["t_w"], t_off=s1["t_clr"])
    tt = t - s1["t_w"]
    figs.save_plot("crossing_timeline", [("遮断かんの角 / 90°", tt, g["boom_angle"] / (0.5 * math.pi)),
                                         ("左の灯 + 1.2", tt, lam[:, 0] + 1.2), ("右の灯 + 2.4", tt, lam[:, 1] + 2.4),
                                         ("状態 / 4", tt, g["state"] / 4.0)],
                   xlabel="警報の開始からの時刻 [s]", ylabel="", title="踏切の状態機械(crossing_gate_state / crossing_lamp_signal)",
                   caption="主図の場面 1 の時刻。警報 0 s → 降下の開始 %.0f s(仮定)→ 遮断の終わり %.0f s(解釈基準 4(3) の標準 15 s)→ 列車の到達 %.0f s"
                           "(遮断→到達 %.0f s = 4(5) の標準)→ 列車が過ぎて警報が止まり %.1f s、かんが上がり切る %.1f s。灯は 1 灯あたり毎分 %.0f 回"
                           "(二次資料、未確認)で左右が交互。" % (T_LOWER, T_LOWER + D_LOWER, T_WARN, T_WARN - T_LOWER - D_LOWER,
                                                           s1["t_clr"] - s1["t_w"], s1["t_clr"] + D_RAISE - s1["t_w"], DC.LAMP_FLASH_PER_MIN),
                   size=(720, 360))
    # 2. 動画から測った灯の明るさ
    if A["lampL"].size >= 16:
        lt = A["lamp_t"] - s1["t_w"]
        figs.save_plot("lamp_pixels", [("左の灯の画素(R)", lt, A["lampL"]), ("右の灯の画素(R)", lt, A["lampR"])],
                       xlabel="警報の開始からの時刻 [s]", ylabel="R の値", title="動画のコマから測った警報灯の明るさ",
                       caption="主図の車載カメラのコマ(%.1f fps、運転者が前を向いて止まっている間、列車が灯を隠す前まで)で、向こう側の柱の 2 灯の画素を読んだ時系列。"
                               "flash_frequency = %.3f Hz(真 %.3f Hz)、lamp_pair_phase の位相差 = %.2f rad(交互 = π)。" % (
                                   A["fps"], A["f_est"], DC.LAMP_FLASH_PER_MIN / 60.0, A["phase"]), kinds=["scatter", "scatter"], size=(720, 320))
    # 3. 標本の門(交差道路の車の速さ)
    SM = out["SM"]
    wrong, kept, Dw, pw = SM["_wrong"]
    x = np.sort(SM["v_cross"]) * 3.6
    xk = np.sort(kept) * 3.6
    r = REF["v_cross"]
    grid = np.linspace(min(x.min(), xk.min()), x.max(), 200)
    Fref = (_ncdf((grid / 3.6 - r["mean"]) / r["sd"]) - _ncdf(-Z999)) / (_ncdf(Z999) - _ncdf(-Z999))
    figs.save_plot("sample_gate", [("参照(切断正規)", grid, Fref), ("採った値の経験分布", x, np.arange(1, len(x) + 1) / len(x)),
                                   ("係数の誤り(1 個ずつの門は通過)", xk, np.arange(1, len(xk) + 1) / len(xk))],
                   xlabel="交差道路の車の速さ [km/h]", ylabel="累積", title="乱数の値の門: 1 個ずつ(0.1 % 点)と集団(KS)",
                   caption="参照 N(40, 6) km/h(仮定)。採った %d 個の KS p は門を通る。全体を 1.25 で割った集団は 1 個ずつの門を %d / %d 個が通るが、"
                           "KS は D = %.2f(p = %.1g)で落とす。" % (len(x), len(kept), len(wrong), Dw, pw), size=(720, 360))
    # 4. 見えない列車: 推定の収束
    S = out["sight"]["out"]["building"]
    rng = np.random.default_rng(77)
    n = min(N_IS, 5000)
    w = out["sight"]["out"]["building"]["w"]
    idx = rng.integers(0, len(w), n)
    t1 = rng.exponential(1.0 / LAMBDA, n)
    mc = np.cumsum(t1 < w[idx]) / np.arange(1, n + 1)
    Wm = float(w.max())
    tq = rng.uniform(0.0, 2.0 * Wm, n)
    f = (tq < w[rng.integers(0, len(w), n)]) * LAMBDA * np.exp(-LAMBDA * tq) * 2.0 * Wm
    isr = np.cumsum(f) / np.arange(1, n + 1)
    k = np.arange(1, n + 1)
    figs.save_plot("hidden_train_estimates", [("閉形式", k, np.full(n, S["P"])), ("素朴なモンテカルロ", k, mc), ("重要度サンプリング", k, isr)],
                   xlabel="試行の数", ylabel="見えない列車が渡り切る前に着く確率", title="見通しの悪い踏切(右の角に建物)",
                   caption="見える距離 %.1f m(sight_triangle_distance = 光線の総当たり)。列車は片方向 1 時間に %.0f 本(仮定)。閉形式 P = %.2e、"
                           "本文の試行数で MC %.2e ± %.1e、IS %.2e ± %.1e。図はその頭の %d 回の累積平均。" % (
                               out["sight"]["x_vis"], LAMBDA * 3600, S["P"], S["mc"], S["se_mc"], S["is"], S["se_is"], n), size=(720, 360))
    # 5. 駐停車禁止の帯
    Pk = out["parking"]
    W, H = 1200, 300
    im = Image.new("RGB", (W, H), (238, 240, 234))
    d = ImageDraw.Draw(im)
    sx = (W - 40) / STREET_LEN
    X = lambda v: 20 + v * sx  # noqa: E731
    d.rectangle([X(0), 110, X(STREET_LEN), 170], fill=(110, 112, 116))
    for a, b in Pk["z"]["merged"]:
        d.rectangle([X(a), 100, X(b), 108], fill=(220, 60, 50))
    for a, b in Pk["S"]:
        d.rectangle([X(a), 172, X(b + CAR_L), 180], fill=(60, 170, 80))
    names = {"intersection": "交差点", "crosswalk": "横断歩道", "bus_stop": "バス停", "safety_zone": "安全地帯", "corner": "曲がり角",
             "railway_crossing": "踏切"}
    for f_ in STREET:
        s0 = f_.get("start", f_.get("at"))
        s1_ = f_.get("end", f_.get("at"))
        col = {"intersection": (90, 92, 96), "crosswalk": (250, 250, 250), "bus_stop": (40, 90, 200), "safety_zone": (240, 200, 40),
               "corner": (120, 80, 40), "railway_crossing": (60, 50, 40)}[f_["kind"]]
        d.rectangle([X(s0) - (2 if s0 == s1_ else 0), 112, X(s1_) + (2 if s0 == s1_ else 0), 168], fill=col)
    n_bad = 0
    for wv in Pk["want"][:80]:
        c = DC.parking_position_check(wv, wv + CAR_L, Pk["z"])
        n_bad += int(not c["ok"])
        d.ellipse([X(wv + CAR_L / 2) - 3, 200 - 3, X(wv + CAR_L / 2) + 3, 200 + 3], fill=(220, 60, 50) if not c["ok"] else (60, 120, 230))
    arr = np.asarray(im, np.float64) / 255.0
    for k_, f_ in enumerate(STREET):
        arr = _txt(arr, names[f_["kind"]], (X(f_.get("start", f_.get("at"))), 30 + 22 * (k_ % 3)), fs=12)
    arr = _txt(arr, "赤の帯 = 44 条の禁止の区間、緑の帯 = 車体が丸ごと入る場所、点 = 止まりたい場所(赤 = そのまま止まると違反)", (20, 230), fs=13)
    for a, b in Pk["z"]["merged"]:
        arr = _txt(arr, "%.0f" % a, (X(a), 88), anchor="cb", fs=10)
    n_all = sum(1 for wv in Pk["want"] if not DC.parking_position_check(wv, wv + CAR_L, Pk["z"])["ok"])
    figs.save("no_stopping_strip", arr, caption="44 条 1 項の駐停車禁止の区間(no_stopping_zones)と、車長 %.1f m の車体が丸ごと入る場所(legal_stop_intervals)。"
                                                 "止まりたい場所(一様、仮定)%d 件のうち、そのまま止まると違反 %d 件(%s)、いちばん近い適法の場所へ移ると余分に歩くのは"
                                                 "平均 %.1f m。図の点は先頭の 80 件(違反 %d)。"
              % (CAR_L, N_PARK, n_all, ", ".join("%s %d" % kv for kv in sorted(Pk["reasons"].items())), Pk["walk"].mean(), n_bad))
    # 6. 判定の表
    C = out["crossing"]
    rows = [[nm, "%d" % C["res"][p]["entered"], ", ".join("%s %d" % kv for kv in sorted(C["res"][p]["viol"].items())) or "なし",
             "%d" % C["res"][p]["hit"]] for p, nm in POLICIES]
    figs.save_table("crossing_policies", ["方針", "渡った", "crossing_stop_check の違反(人数)", "列車が着くとき線路の上"], rows,
                    title="踏切: %d 人 × 5 通りの方針" % N_DRIVERS,
                    caption="同じ %d 人(列車の速さ・発進・見る時間は標本の門を通った値)を 5 通りの方針で。違反の名前: no_stop = 33 条 1 項(直前で止まらない)、"
                            "no_look = 同(最後の停止の間に左右を見ない)、entered_while_forbidden = 33 条 2 項、no_exit_room = 50 条 2 項、"
                            "stopped_inside = 踏切の中で止まった(教則 6-1-1(5))。" % N_DRIVERS)
    pr = out["priority"]
    rows = []
    for ck, nm in (("wide", "狭い道 4 m → 広い道 7 m"), ("same", "5 m と 5.5 m")):
        P_ = pr[ck]
        for pol in ("rule", "naive"):
            rr = P_["res"][pol]
            rows.append([nm, "ルール" if pol == "rule" else "素朴", P_["pr"]["article"],
                         "%d / %d" % (sum(x["obstruct"] for x in rr), len(rr)), "%.1f" % float(np.mean([x["wait"] for x in rr]))])
    figs.save_table("priority_results", ["道の組", "運転", "priority_rule", "進行妨害の場面", "待ち 平均 [s]"], rows,
                    title="交差点の優先(36 条)", caption="進行妨害 = 譲るべき相手に 2.0 m/s²(仮定)を超える減速を要らせた場面(obstruction_decel)。")
    return res


def figures(out):
    print("== 7. 図")
    t = time.time()
    A = fig_dashcam_crossing(out)
    fr = DD_flash(A)
    A.update(fr)
    print("  踏切の車載カメラ %d コマ(場面 1 は %d コマ、%.1f s)、場面 1 の判定 %s、場面 2 の判定 %s" % (
        A["n"], A["n1"], time.time() - t, A["chk1"]["violations"] or "違反なし", A["chk2"]["violations"]))
    if A["lampL"].size >= 16:
        print("  動画の画素の灯: %d コマ、flash_frequency %.3f Hz(真 %.3f Hz、窓の分解能 %.3f Hz)、位相差 %.2f rad、"
              "コマを %d 枚に 1 枚(%.2f fps)にすると %.3f Hz(折り返しの閉形式 %.3f Hz)" % (
                  A["lampL"].size, A["f_est"], DC.LAMP_FLASH_PER_MIN / 60.0, A["bin"], A["phase"], A["k_sub"], A["fps"] / A["k_sub"], A["f_sub"],
                  A["f_alias"]))
        gate("動画の画素から: 点滅の周波数 = 毎分 50 回(± 窓の分解能)、2 灯の位相差 = π(交互)",
             abs(A["f_est"] - DC.LAMP_FLASH_PER_MIN / 60.0) <= A["bin"] and A["alternating"], "%.3f Hz / %.2f rad" % (A["f_est"], A["phase"]))
        gate("コマを間引くと見かけの周波数は aliased_frequency の閉形式に折り返る", abs(A["f_sub"] - A["f_alias"]) <= A["bin_sub"],
             "%.3f / %.3f Hz" % (A["f_sub"], A["f_alias"]))
    gate("動画の場面: ルールは違反なし(発進の直後の警報で止まり直す)、詰まっていても入ると 50 条 2 項の違反で踏切の中に止まる",
         A["chk1"]["ok"] and A["R1"]["restops"] == 1 and "no_exit_room" in " / ".join(A["chk2"]["violations"]) and "stopped_inside" in " / ".join(A["chk2"]["violations"]))
    t = time.time()
    B = fig_dashcam_crosswalk(out)
    print("  横断歩道の車載カメラ %d コマ(%.1f s)、場面 #%d: ルール %s、素朴 %s" % (B["n"], time.time() - t, B["k"], B["seg"]["rule"], B["seg"]["naive"]))
    t = time.time()
    Cb = fig_birdseye_crossing(out)
    print("  踏切の上から見た動画 %d コマ(%.1f s)、場面 #%d" % (Cb["n"], time.time() - t, Cb["j"]))
    t = time.time()
    Db = fig_birdseye_priority(out)
    print("  交差点の上から見た動画 %d コマ(%.1f s)、場面 #%d" % (Db["n"], time.time() - t, Db["e"]))
    t = time.time()
    fig_static(out, A)
    print("  静止図(%.1f s)" % (time.time() - t))


def DD_flash(A):
    """動画から測った灯の時系列を drivedecide.flash_frequency / aliased_frequency と lamp_pair_phase で読む。"""
    import drivedecide as DD
    L, R, fps = A["lampL"], A["lampR"], A["fps"]
    if L.size < 16:
        return {}
    ff = DD.flash_frequency(L, fps)
    ph = DC.lamp_pair_phase(L, R, fps)
    f_true = DC.LAMP_FLASH_PER_MIN / 60.0
    # 間引きの幅: 間引いた fps が 2·f より小さく(本当に折り返す)、見かけの周波数が 0 と fps/2 から離れる最小の k
    k = next(k for k in range(2, 9) if fps / k < 2 * f_true and 0.15 < DD.aliased_frequency(f_true, fps / k) / (fps / k / 2) < 0.85)
    sub = L[::k]
    fs = DD.flash_frequency(sub, fps / k)
    return {"f_est": ff["frequency"], "bin": ff["bin_width"], "phase": ph["phase"], "alternating": ph["alternating"], "k_sub": k,
            "f_sub": fs["frequency"], "bin_sub": fs["bin_width"], "f_alias": float(DD.aliased_frequency(f_true, fps / k))}


if __name__ == "__main__":
    sys.exit(main())
