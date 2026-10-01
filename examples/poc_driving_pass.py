# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉝(自動運転 第 12 回): 追越しと見えない所 —— 対向車が来るかもしれない道で、見通しが「追越しに要る距離 D*」に届くまで
待ってから追い越し、前の車の全体がルームミラーに映ってから戻る。進路を変えるときは後ろの車に急ブレーキを踏ませない。環状交差点では
環道の車を妨げずに入り、出口の 1 つ手前で左の合図を出す。坂の頂上の手前では「見えない距離」が D* に足りない。カーブミラーの中の車は
本当よりずっと遠くに見える —— を条文・公表値・閉形式と、それとは別の経路の検算で採点する。

方針(ユーザーの決定): **部品はルールベースに限る**。学習・ニューラルネットは使わない。部品(:mod:`drivepass`)は閉形式・幾何・
公表値・条文の判定・古典的な数値計算で、どれも独立な経路の検算(門)が立つ。手続きで作った世界は採点用の真値で、訓練には使わない。
AI は部品の組み合わせを考える側 —— ここでは「凸形縦断曲線の見通しの水平線走査と、追越しの閉形式 D* を突き合わせて、頂上の手前で
追い越せない理由を距離で示す」「ルームミラーの幾何で戻る位置を決め、それを D* に入れる」「凸面鏡の結像に Coddington の斜入射の式を
足して、T 字路の斜めのミラーで縦と横の読みが分かれることを示す」が組み合わせの例。

門(真値の出どころ):
  0. **乱数の値の門**: 前の車の速さ・追越しの加速度・車間時間・対向車の速さ・後続車の速さと反応時間・環道の車の速さは、参照分布
     (仮定)の両側 0.1 % 分位点の外を 1 個ずつ落とし(理由を記録)、集団は切断正規分布との KS 検定で照合する。物理的にありえない値は
     落ち、換算係数の取り違え(1.25 で割った集団)は 1 個ずつの門をほぼ通るが KS で落ちる。
  1. **追越し**(S079, S081, S085, S086): 規則の運転者は overtake_permitted で「見えている距離 ≥ D*」「禁止区間に掛からない」を
     確かめてから追い越し、ルームミラーに前の車の全体が映る車間(overtake_return_gap)で戻る。条文を 1 点ずつ当てる総当たりで禁止区間
     に入っていないこと、対向車との PET ≥ 2 s、戻る車間 = ミラーの車間。D* は 1 ms 刻みの時間の行進と照合。ミラーの車間は Fermat の
     最短経路の走査と照合。素朴(数百 m 先に対向車が見えなければ行く・前の車を抜いたらすぐ戻る)は違反・ヒヤリ・割り込みが数えられる。
  2. **進路変更**(S067, S072): 後続車に要る減速度の閉形式 = 2 台の時間の行進で最小車間が s₀。「急に」(2.0 m/s²、仮定)の判定 =
     2.0 m/s² で行進したときに s₀ を割るか。規則は急ブレーキを強いない・約 3 秒前に合図。
  3. **環状交差点**(S069, S102): 環道の車に要る減速度 = 円周の行進で入口の点に t_clear ちょうどに着く。規則は進行妨害 0・徐行。
     出口の合図は roundabout_signal_point の角で点き、位置ベクトルの外積で数えた「1 つ手前の出口の通過」と同じ時刻(事象の再生)。
  4. **坂の頂上**(S065, S081): crest_sight_distance が道路構造令の表(19・22 条)の 3 行を 1 % 以内で再現(公表値)。PoC の道の頂上で
     見通し線を総当たりで走査した最短の視距 = 閉形式。頂上の付近では見通しが D* に届かない(追越しが禁止される理由を距離で)。
  5. **カーブミラー**(S064): 凸面鏡の近軸の読み k·a = 3 次元の厳密な光線追跡(反射点を Newton で)。斜めに見る T 字路では
     縦と横の読みが Coddington の式 k_s = 1 + 2e cos i / R・k_t = 1 + 2e/(R cos i) に分かれる(光線追跡と 0.5 % 以内)。速さの 3 通りの
     読みを有限差分で照合。道の上で映る範囲 = 密な光線の走査、手前の死角。

正直に書くこと:
* **仮定の値**: 参照分布(前の車 N(40, 4) km/h、加速 N(1.2, 0.25) m/s²、車間時間 N(1.8, 0.35) s、対向車 N(55, 6) km/h、後続車
  N(62, 6) km/h、反応 N(1.0, 0.2) s、環道の車 N(20, 3) km/h)、対向車の流れ 1 時間 150 台(Poisson)、上限 60 km/h、戻りの時間 3 s、
  PET の下限 2 s、対向車の速さの見積もり = 参照の 0.1 % 点(74.7 km/h)、対向車の見える高さ 1.2 m、素朴の「空いている」= 300 m 先まで
  見えない、車線 3.25 m・前の車の幅 1.8 m。drivepass の仮定(30 条 1 号の「付近」30 m・「勾配の急な」10 %・「急に」2.0 m/s²・
  徐行 10 km/h・27 条の増速 0.2 m/s・ルームミラーの寸法)は drivepass.SOURCES と NOTES.md。
* **施行令 21 条(合図の時期)は未確認**(e-Gov 保守中)。3 秒・出口の 1 つ手前は教則の値。
* 対向車・後続車・環道の車は一定の速さ(譲るときだけ一定の減速)。素朴な運転者は追越しを途中でやめない(最悪の場合)。
* カーブミラーの像は、鏡の中心に置いたカメラの画像を反射の向きで引き、深度で視差を 3 回直した近似(門: 車のメッシュの頂点の厳密な
  光線追跡と画素で照合)。鏡は球面(R 3 m、直径 0.8 m)、反射率 0.9(仮定)。T 字路の寸法(主の道 5 m、塀 2 m、鏡の高さ 2.5 m)も仮定。

教則の場面: S064, S065, S067, S069, S072, S079, S081, S085, S086, S102
(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_pass.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
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
import drivepass as DP  # noqa: E402

#: 予算: reduced(CI の既定)は人数・試行数を減らす。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_DRIVERS = 60 if REDUCED else 240           # 追い越したい運転者
N_LC = 60 if REDUCED else 240                # 進路変更の場面
N_RB = 60 if REDUCED else 240                # 環状交差点に入る場面
VID_WH = (320, 180) if REDUCED else (640, 360)
T0 = time.time()
OK = []

# ── 車と道(仮定) ──
CAR_L, CAR_W = 4.5, 1.8
EYE_BACK = 2.05                              # 前端から運転者の目まで
LANE = 3.25                                  # 車線の幅
Y_EGO, Y_ONC = 0.5 * LANE, -0.5 * LANE       # 自車線(左)・対向車線の中心
V_MAX = 60.0 / 3.6                           # 最高速度
T_LC = 3.0                                   # 戻りの時間
PET_MIN = 2.0                                # 対向車との PET の下限(仮定)
ONC_RATE = 150.0 / 3600.0                    # 対向車の流れ(Poisson、仮定)
D_NAIVE = 300.0                              # 素朴な運転者の「空いている」(仮定)
GAP_NAIVE = 2.0                              # 素朴な運転者が戻る車間
H_ONC = 1.2                                  # 対向車の見える高さ(仮定)
JOKOU = DP.CRAWL_SPEED
X_START, X_END = 520.0, 2350.0               # 前の車の前端の初めの位置・場面の終わり(自車の前端)

# ── 乱数の参照分布(すべて仮定)と標本の門 ──
Z999 = 3.2905267314919255                    # 標準正規の 99.95 % 点(両側 0.1 %)
REF = {
    "v_lead": {"mean": 40.0 / 3.6, "sd": 4.0 / 3.6, "unit": "m/s", "what": "前の遅い車の速さ"},
    "a_pass": {"mean": 1.2, "sd": 0.25, "unit": "m/s²", "what": "追越しの加速度"},
    "headway": {"mean": 1.8, "sd": 0.35, "unit": "s", "what": "前の車との車間時間"},
    "v_on": {"mean": 55.0 / 3.6, "sd": 6.0 / 3.6, "unit": "m/s", "what": "対向車の速さ"},
    "v_follow": {"mean": 62.0 / 3.6, "sd": 6.0 / 3.6, "unit": "m/s", "what": "進路変更先の後続車の速さ"},
    "t_react": {"mean": 1.0, "sd": 0.2, "unit": "s", "what": "後続車の反応時間"},
    "v_ring": {"mean": 20.0 / 3.6, "sd": 3.0 / 3.6, "unit": "m/s", "what": "環道の車の速さ"},
}
#: 対向車の速さの見積もり = 参照の上側 0.1 % 点(標本の門で、これより速い値は採らない)
V_ON_ASSUMED = REF["v_on"]["mean"] + Z999 * REF["v_on"]["sd"]


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
    rng = np.random.default_rng(12)
    D = {}
    total_drop, pmin = 0, 1.0
    sizes = (("v_lead", N_DRIVERS), ("a_pass", N_DRIVERS), ("headway", N_DRIVERS), ("v_on", 40 * N_DRIVERS),
             ("v_follow", N_LC), ("t_react", N_LC + N_DRIVERS), ("v_ring", 8 * N_RB))
    for name, n in sizes:
        x, why = draw(name, n, rng)
        Dk, p = ks_truncnorm(name, x)
        pmin = min(pmin, p)
        total_drop += len(why)
        print("    %-8s %s: %d 個、落とした %d 個%s、KS D = %.4f p = %.3f" % (
            name, REF[name]["what"], len(x), len(why), ("(" + why[0] + ")") if why else "", Dk, p))
        D[name] = x
    assert sum(len(D[k]) for k, _ in sizes) == sum(n for _, n in sizes)
    gate("標本の門: 採った値はすべて参照の 0.1 % 点の内、集団は KS で参照と食い違わない(p > 0.001)", pmin > 0.001,
         "最小 p = %.3f、落とした %d 個" % (pmin, total_drop))
    bad = {"v_lead": [40 / 3.6, 140 / 3.6, -2.0], "a_pass": [1.1, 6.0], "v_on": [50 / 3.6, 200 / 3.6], "t_react": [-0.3]}
    nbad = 0
    for k, v in bad.items():
        _, why = screen(k, v)
        nbad += len(why)
        for w in why:
            print("      落とした: " + w)
    wrong = D["v_on"][:2000] / 1.25                     # 換算係数の取り違え(全体が 20 % 遅い方へずれた集団)
    kept, why = screen("v_on", wrong)
    Dw, pw = ks_truncnorm("v_on", kept)
    print("    系統の誤り(対向車の速さを 1.25 で割った %d 個): 1 個ずつの門で落ちたのは %d 個(%.0f %%)、残り %d 個の KS D = %.3f p = %.2g"
          % (len(wrong), len(why), 100 * len(why) / len(wrong), len(kept), Dw, pw))
    gate("門が自明でない: ありえない値 5 個は 1 個ずつの門で落ち(理由を記録)、系統の誤りは 1 個ずつの門をほぼ通るが KS で落ちる",
         nbad == 5 and len(why) < 0.5 * len(wrong) and pw < 1e-6, "落とした %d 個 / 係数の誤り p = %.2g" % (nbad, pw))
    D["_wrong"] = (wrong, kept, Dw, pw)
    return D


# ───────────────────────────── 道の縦断と見通し ─────────────────────────────
#: 縦断: 0〜600 平ら、600〜640 凹(0 → +4 %)、640〜820 +4 %、820〜980 凸形縦断曲線(+4 % → −4 %、L 160 m、R 2000 m)、
#: 980〜1160 −4 %、1160〜1200 凹(−4 % → 0)、その先は平ら。頂上 = 900 m(仮定)
GRADE_PTS = [(0.0, 0.0), (600.0, 0.0), (640.0, 0.04), (820.0, 0.04), (980.0, -0.04), (1160.0, -0.04), (1200.0, 0.0), (3600.0, 0.0)]
CREST = {"x": 900.0, "g1": 0.04, "g2": -0.04, "L": 160.0}
PROF_DX = 0.05
_PX = np.arange(0.0, 3600.0 + PROF_DX / 2, PROF_DX)
_PG = np.interp(_PX, [p[0] for p in GRADE_PTS], [p[1] for p in GRADE_PTS])
_PZ = np.concatenate([[0.0], np.cumsum(0.5 * (_PG[1:] + _PG[:-1]) * PROF_DX)])


def road_z(x):
    return np.interp(x, _PX, _PZ)


def road_grade(x):
    return np.interp(x, _PX, _PG)


def sight_scan(x_eye, h_obj, step=0.5, reach=1000.0):
    """見通し線の総当たり(閉形式と別の経路): 目(高さ 1.2 m)から前方の道の点への勾配の累積最大(水平線)を取り、高さ h_obj の物の
    頂点への勾配がそれ以上なら見える。前から連続して見える最遠の距離を返す(配列可)。"""
    xe = np.atleast_1d(np.asarray(x_eye, float))
    d = np.arange(step, reach + step / 2, step)
    out = np.empty(xe.size)
    for i0 in range(0, xe.size, 256):
        xs = xe[i0:i0 + 256, None]
        ze = road_z(xs) + DP.SIGHT_EYE_HEIGHT
        zr = road_z(xs + d[None, :])
        s_road = (zr - ze) / d[None, :]
        hor = np.maximum.accumulate(s_road, axis=1)
        hor = np.concatenate([np.full((xs.shape[0], 1), -np.inf), hor[:, :-1]], axis=1)
        vis = (zr + h_obj - ze) / d[None, :] >= hor
        first_hidden = np.where(vis.all(axis=1), d.size, np.argmin(vis, axis=1))
        out[i0:i0 + 256] = np.where(first_hidden == 0, 0.0, d[np.maximum(first_hidden - 1, 0)])
    return out


# ───────────────────────────── 1. 追越し ─────────────────────────────
#: 道に沿った施設(30 条)。上り坂の頂上、交差点、横断歩道、標識による禁止。下り坂は 4 % で「急な」に当たらない(除外の例)
FEATURES = [{"kind": "crest", "at": CREST["x"]}, {"kind": "downhill", "start": 980.0, "end": 1160.0, "grade": -0.04},
            {"kind": "intersection", "start": 1500.0, "end": 1510.0}, {"kind": "crosswalk", "start": 1900.0, "end": 1904.0},
            {"kind": "sign", "start": 2100.0, "end": 2250.0}]


def zone_rule_brute(x):
    """30 条の文言を 1 点ずつ当てる(no_overtaking_zones と別の経路)。x の点ごとに禁止なら True。"""
    x = np.asarray(x, float)
    hit = np.zeros(x.shape, bool)
    for f in FEATURES:
        k = f["kind"]
        if k == "crest":                                         # 1 号: 上り坂の頂上付近(前後 30 m、仮定)
            hit |= np.abs(x - f["at"]) <= DP.VICINITY["crest"]
        elif k == "downhill":                                    # 1 号: 勾配の急な下り坂(10 % 以上、仮定)
            if abs(f["grade"]) >= DP.STEEP_GRADE:
                hit |= (x >= f["start"]) & (x <= f["end"])
        elif k in ("intersection", "crosswalk"):                 # 3 号: 手前の側端から前に 30 m 以内とその中
            hit |= (x >= f["start"] - 30.0) & (x <= f["end"])
        elif k == "sign":
            hit |= (x >= f["start"]) & (x <= f["end"])
    return hit


def fermat_return_gap(lane_offset, lead_width, E=(0.0, -0.35), M=(0.55, 0.0), w=0.125, er=2.8):
    """ルームミラーで前の車の前の 2 隅が映る最小の車間を、Fermat の最短経路(鏡の上の点を密に走査して道のりを最小にする)で
    二分法(overtake_return_gap の閉形式と別の経路)。"""
    import drivedecide as DD
    E, M = np.asarray(E, float), np.asarray(M, float)
    n = DD.mirror_aim_normal(E, M, np.array([-1.0, 0.0]))
    t = np.array([-n[1], n[0]])
    s = np.linspace(-0.6, 0.6, 24001)
    S = M[None, :] + s[:, None] * t[None, :]

    def visible(P):
        L = np.linalg.norm(S - E, axis=1) + np.linalg.norm(S - P, axis=1)
        return abs(s[int(np.argmin(L))]) <= w and float(np.dot(P - M, n)) > 0

    def both(gap):
        xf = -er - gap
        return all(visible(np.array([xf, y])) for y in (lane_offset - lead_width / 2, lane_offset + lead_width / 2))
    lo, hi = 0.0, 200.0
    assert not both(lo) and both(hi)
    for _ in range(36):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if both(mid) else (mid, hi)
    return hi


def oncoming_stream(rng, t_end):
    """対向車: Poisson(1 時間 150 台、仮定)で x = 3600 m の先から −x へ。返り値 (x0 = 時刻 0 の前端の位置, 速さ)。"""
    vs = []
    xs = []
    v_on = OVS["v_on"]
    t = -400.0                                         # 場面の始まりにもう道の上にいる車を作るため、手前の時刻から流す
    while t < t_end:
        t += rng.exponential(1.0 / ONC_RATE)
        v = float(v_on[OVS["k"] % len(v_on)])
        OVS["k"] += 1
        xs.append(3600.0 - v * t)                         # 時刻 t に x = 3600 を通る車の、時刻 0 の位置
        vs.append(v)
    return np.array(xs), np.array(vs)


OVS = {"k": 0, "v_on": None}


def ego_kin(t, v0, a, vmax):
    """自車の前端の進んだ距離と速さ(初速 v0、a で vmax まで)。配列可。"""
    t = np.asarray(t, float)
    if a <= 0:
        return v0 * t, np.full(t.shape, v0)
    ta = (vmax - v0) / a
    s = np.where(t <= ta, v0 * t + 0.5 * a * t * t, v0 * ta + 0.5 * a * ta * ta + vmax * (t - ta))
    v = np.where(t <= ta, v0 + a * t, vmax)
    return s, v


def drive_pass(drv, policy, zres, G_MIR, S_vis_fn, record=False):
    """1 人の追越し。policy: rule / naive。前の車は一定の速さ。自車は追いつて車間 gb で付いて走り、許されたら(rule)/ 空いて
    見えたら(naive)対向車線に出て a で V_MAX まで加速、前の車の前端から gap_front 先に後端が出たら T_LC で戻る。

    返り値: started、t_s(出た時刻)、t_r(戻り始め)、t_e(戻り切り)、x_s・x_e(前端の位置)、gap_ret(戻り始めの車間)、pets(対向車ごと)、
    wait(付いて走った時間)、req(規則の閉形式)。"""
    vL, a, gb = drv["vL"], drv["a"], drv["gb"]
    xo0, vo = drv["onc"]
    xL0 = X_START
    req = DP.overtake_requirement(vL, vL, lead_length=CAR_L, ego_length=CAR_L, gap_back=gb, gap_front=G_MIR, accel=a, v_max=V_MAX,
                                  lane_change_time=T_LC, v_oncoming=V_ON_ASSUMED, pet_min=PET_MIN)
    dt = 0.2
    t = 0.0
    t_s = None
    n_checks = 0
    while True:
        xf = xL0 + vL * t - CAR_L - gb                      # 付いて走る自車の前端
        if xf > X_END - 260.0:
            break
        xo = xo0 - vo * t
        ahead = xo - xf
        S_eye = float(S_vis_fn(xf - EYE_BACK))
        vis = (ahead > 0) & (ahead + EYE_BACK <= S_eye)
        near = float(ahead[vis].min()) if vis.any() else math.inf
        if policy == "rule":
            dist = min(near, S_eye - EYE_BACK)
            pm = DP.overtake_permitted(maneuver_start=xf, maneuver_end=xf + req["ego_distance"], zones_result=zres,
                                       dist_oncoming=dist, requirement=req)
            n_checks += 1
            go = pm["ok"]
        else:
            go = near > D_NAIVE
        if go:
            t_s = t
            break
        t += dt
    out = {"started": t_s is not None, "req": req, "wait": t if t_s is None else t_s, "checks": n_checks}
    if t_s is None:
        return out
    xs = xL0 + vL * t_s - CAR_L - gb
    # 追越し: 1/50 s 刻み(戻り始めの判定がある素朴のため、規則も同じ刻みで走らせ、閉形式と照合する)
    h = 0.02
    k = 0
    gap_f = G_MIR if policy == "rule" else GAP_NAIVE
    t_r = None
    while True:
        tau = k * h
        s, v = ego_kin(tau, vL, a, V_MAX)
        x = xs + float(s)
        xl = xL0 + vL * (t_s + tau)                         # 前の車の前端
        gap = (x - CAR_L) - xl
        if policy == "rule":
            back = gap >= gap_f
        else:
            xo = xo0 - vo * (t_s + tau)
            meet = (xo - x) / np.maximum(vo + float(v), 1e-9)
            close = bool(np.any((xo - x > 0) & (meet < 4.0)))
            back = gap >= gap_f or (gap >= 0.0 and close)
        if back:
            t_r = t_s + tau
            break
        k += 1
        if k > 200000:
            break
    tr_rel = t_r - t_s
    s_r, v_r = ego_kin(tr_rel, vL, a, V_MAX)
    gap_ret = (xs + float(s_r) - CAR_L) - (xL0 + vL * t_r)
    t_e = t_r + T_LC
    s_e, _ = ego_kin(t_e - t_s, vL, a, V_MAX)
    xe = xs + float(s_e)
    # 対向車との PET: 戻り切った時刻 t_e の自車の前端の位置 xe に、対向車の前端が着く時刻 − t_e(負 = 対向車線にいる間に出会った)
    xo_s = xo0 - vo * t_s
    rel = xo_s > xs                                          # 出た時刻に自車より前にいた対向車
    pets = ((xo0[rel] - xe) / vo[rel]) - t_e
    out.update({"t_s": t_s, "t_r": t_r, "t_e": t_e, "x_s": xs, "x_e": xe, "gap_ret": gap_ret, "pets": pets,
                "v_ret": float(v_r), "pet_min": float(pets.min()) if pets.size else math.inf})
    return out


def march_occupy(vL, a, gb, gf, h=1e-3):
    """閉形式 D* と別の経路: 1 ms 刻みで自車と前の車を進め、後端が前の車の前端から gf 先に出る時刻 + T_LC と、その間の道のり。"""
    x, v, xl, t = 0.0, vL, CAR_L + gb, 0.0
    while (x - CAR_L) - xl < gf:
        vn = min(v + a * h, V_MAX)
        x += 0.5 * (v + vn) * h
        v = vn
        xl += vL * h
        t += h
    n = int(round(T_LC / h))
    for _ in range(n):
        vn = min(v + a * h, V_MAX)
        x += 0.5 * (v + vn) * h
        v = vn
    return t + n * h, x


def scene_overtake(SM):
    print("== 1. 追越し(S079, S081, S085, S086): %d 人 × 規則 / 素朴、対向車 1 時間 %.0f 台" % (N_DRIVERS, ONC_RATE * 3600))
    G_MIR = DP.overtake_return_gap(lane_offset=LANE, lead_width=CAR_W)["gap"]
    G_FER = fermat_return_gap(LANE, CAR_W)
    print("    ルームミラーに前の車の全体が映る車間: 閉形式 %.2f m / Fermat の走査 %.2f m(車線 %.2f m、前の車の幅 %.1f m)" % (G_MIR, G_FER, LANE, CAR_W))
    gate("ルームミラーの車間(overtake_return_gap)= Fermat の最短経路の走査(±0.02 m)", abs(G_MIR - G_FER) < 0.02, "%.2f / %.2f m" % (G_MIR, G_FER))
    zres = DP.no_overtaking_zones(FEATURES)
    xg = np.arange(0.0, 3000.0, 0.25)
    ref = zone_rule_brute(xg)
    got = np.zeros(xg.shape, bool)
    for lo_, hi_ in zres["merged"]:
        got |= (xg >= lo_) & (xg <= hi_)
    print("    30 条の禁止区間: %s(下り坂 4 %% は「急な」10 %%(仮定)に当たらず除外)" % ", ".join(
        "[%.0f, %.0f] %s" % (z[0], z[1], z[3]) for z in zres["zones"]))
    gate("禁止区間 = 条文を 0.25 m ごとに当てた総当たり", bool(np.array_equal(got, ref)), "%d 点" % xg.size)
    # 見通し(対向車の高さ 1.2 m)を 0.5 m 格子で前もって走査
    grid = np.arange(X_START - 200.0, X_END + 50.0, 0.5)
    S_grid = sight_scan(grid, H_ONC)

    def S_vis_fn(x):
        return np.interp(x, grid, S_grid)
    OVS["v_on"] = SM["v_on"]
    OVS["k"] = 0
    rng = np.random.default_rng(31)
    drivers = []
    for i in range(N_DRIVERS):
        vL = float(SM["v_lead"][i])
        drivers.append({"i": i, "vL": vL, "a": float(SM["a_pass"][i]), "gb": float(SM["headway"][i]) * vL,
                        "onc": oncoming_stream(rng, (X_END - X_START) / vL + 60.0)})
    res = {}
    for pol in ("rule", "naive"):
        rows = [drive_pass(d, pol, zres, G_MIR, S_vis_fn) for d in drivers]
        st = [r for r in rows if r["started"]]
        zone_hit = 0
        for r in st:
            fp = np.arange(r["x_s"], r["x_e"], 0.25)
            zone_hit += int(np.any(zone_rule_brute(fp)))
        pets = np.array([r["pet_min"] for r in st if math.isfinite(r["pet_min"])])
        res[pol] = {"rows": rows, "started": len(st), "zone_hit": zone_hit,
                    "near": int(np.sum(pets < PET_MIN)), "conflict": int(np.sum(pets < 0.0)),
                    "pet_min": float(pets.min()) if pets.size else math.inf,
                    "cut": sum(r["gap_ret"] < G_MIR - 0.05 for r in st),
                    "gap_ret": np.array([r["gap_ret"] for r in st]), "wait": np.array([r["wait"] for r in rows])}
        R_ = res[pol]
        print("    %-5s 追い越した %3d / %d 人(付いて走った時間 平均 %.0f s)、禁止区間に掛かった %d、対向車との PET 最小 %.2f s・"
              "PET < %.0f s(ヒヤリ)%d・PET < 0(対向車線で出会う)%d、戻りの車間 < ミラーの車間(割り込み)%d(戻りの車間 中央値 %.1f m)" % (
                  "規則" if pol == "rule" else "素朴", R_["started"], N_DRIVERS, float(R_["wait"].mean()), R_["zone_hit"], R_["pet_min"],
                  PET_MIN, R_["near"], R_["conflict"], R_["cut"], float(np.median(R_["gap_ret"])) if R_["gap_ret"].size else math.nan))
    r0, rn = res["rule"], res["naive"]
    D_star = np.array([r["req"]["d_required"] for r in r0["rows"]])
    print("    規則の D*(要る見通し): %.0f〜%.0f m(中央値 %.0f m)。素朴が「空いている」とみなす距離 %.0f m" % (
        D_star.min(), D_star.max(), np.median(D_star), D_NAIVE))
    gate("規則: 禁止区間(条文の総当たり)に掛からず、対向車との PET ≥ 2 s、戻りの車間 = ミラーの車間、半数以上が追い越せた",
         r0["zone_hit"] == 0 and r0["pet_min"] >= PET_MIN and r0["cut"] == 0 and r0["started"] >= N_DRIVERS // 2
         and bool(np.all(np.abs(r0["gap_ret"] - G_MIR) < 0.2)), "PET 最小 %.2f s、%d 人" % (r0["pet_min"], r0["started"]))
    # D* の閉形式 = 時間の行進(先頭の 12 人)
    errs = []
    for d in drivers[:12]:
        req = DP.overtake_requirement(d["vL"], d["vL"], lead_length=CAR_L, ego_length=CAR_L, gap_back=d["gb"], gap_front=G_MIR,
                                      accel=d["a"], v_max=V_MAX, lane_change_time=T_LC, v_oncoming=V_ON_ASSUMED, pet_min=PET_MIN)
        tm, sm = march_occupy(d["vL"], d["a"], d["gb"], G_MIR)
        errs.append(max(abs(tm - req["t_occupy"]) / req["t_occupy"], abs(sm - req["ego_distance"]) / req["ego_distance"]))
    assert len(errs) == 12
    gate("追越しの閉形式(占有の時間・道のり)= 1 ms 刻みの時間の行進(相対 2e-3)", max(errs) < 2e-3, "最大 %.1e" % max(errs))
    # 規則の追越しで、刻み 0.02 s で走らせた占有の時間 = 閉形式
    dts = [abs((r["t_e"] - r["t_s"]) - r["req"]["t_occupy"]) for r in r0["rows"] if r["started"]]
    gate("規則の追越しを走らせた占有の時間 = 閉形式の t_occupy(刻み 0.02 s)", len(dts) > 0 and max(dts) <= 0.021, "最大 %.3f s" % max(dts))
    gate("門が自明でない: 素朴は禁止区間に掛かり、対向車とのヒヤリ(PET < 2 s)があり、全員がミラーの車間より前で戻る(割り込み)",
         rn["zone_hit"] > 0 and rn["near"] > 0 and rn["cut"] == rn["started"] > 0,
         "禁止 %d・ヒヤリ %d・割り込み %d / %d" % (rn["zone_hit"], rn["near"], rn["cut"], rn["started"]))
    # 割り込まれた前の車に要る減速度(26 条の 2 の判定を、戻る側に当てる)
    nd = []
    for d, r in zip(drivers, rn["rows"]):
        if r["started"]:
            b = DP.lane_change_follower_decel(r["gap_ret"], d["vL"], r["v_ret"], reaction=float(SM["t_react"][N_LC + d["i"]]))["decel"]
            nd.append(b)
    nd = np.array(nd)
    hw = rn["gap_ret"] / np.array([d["vL"] for d, r in zip(drivers, rn["rows"]) if r["started"]])
    print("    素朴の割り込み: 前の車に要る減速度 最大 %.2f m/s²(自車の方が速いので急ブレーキは要らない)、戻ったときの車間時間 中央値 %.2f s・"
          "最小 %.2f s(規則は %.2f s)" % (float(nd.max()) if nd.size else 0.0, float(np.median(hw)), float(hw.min()),
                                       float(np.median(r0["gap_ret"] / np.array([d["vL"] for d, r in zip(drivers, r0["rows"]) if r["started"]])))))
    # 27 条: 追い越される側が速度を増すと、占有の時間がどれだけ延びるか(閉形式で前の車の速さを上げた場合)
    d0 = drivers[0]
    tr = np.arange(0.0, 20.0, 0.1)
    vv = d0["vL"] + np.clip(tr - 5.0, 0, None) * 0.4
    c_bad = DP.overtaken_conduct_check({"t": tr, "v": vv}, t_caught=0.0, t_passed=15.0)
    c_ok = DP.overtaken_conduct_check({"t": tr, "v": np.full(tr.shape, d0["vL"])}, t_caught=0.0, t_passed=15.0)
    print("    27 条 1 項(追い越される側は速度を増さない): 一定の前の車 = %s、0.4 m/s² で増速した前の車 = %s(増した量 %.1f m/s)" % (
        "違反なし" if c_ok["ok"] else c_ok["violations"], c_bad["violations"], c_bad["increase"]))
    gate("27 条 1 項: 一定の前の車は違反なし、追い越されながら増速すると speed_increased", c_ok["ok"] and c_bad["violations"] == ["speed_increased"])
    return {"G_MIR": G_MIR, "zres": zres, "res": res, "drivers": drivers, "S_grid": (grid, S_grid), "D_star": D_star, "S_vis_fn": S_vis_fn}


# ───────────────────────────── 2. 進路変更 ─────────────────────────────
S0_LC = 2.0                                  # 残す車間(仮定)
V_EGO_LC = 50.0 / 3.6


def march_follower(gap, vf, ve, tau, b, h=1e-3, T=30.0):
    """2 台の時間の行進(閉形式と別の経路): 後続車は tau の間は一定、その後 b で減速(止まったら止まる)、自車は一定。
    最小の車間(後続車の前端と自車の後端)を返す。配列可。"""
    gap, vf, ve, tau, b = np.broadcast_arrays(*(np.asarray(v, float) for v in (gap, vf, ve, tau, b)))
    xf = -gap.copy()
    v = vf.copy()
    xe = np.zeros(gap.shape)
    mn = gap.copy()
    t = 0.0
    while t < T:
        acc = np.where(t >= tau, -b, 0.0)
        vn = np.maximum(v + acc * h, 0.0)
        xf += 0.5 * (v + vn) * h
        v = vn
        xe += ve * h
        t += h
        mn = np.minimum(mn, xe - xf)
        if np.all((v <= ve) & (t > tau)):
            break
    return mn


def scene_lane_change(SM):
    print("== 2. 進路変更(S067, S072、26 条の 2・53 条): %d 場面、自車 %.0f km/h、残す車間 %.1f m(仮定)" % (N_LC, V_EGO_LC * 3.6, S0_LC))
    rng = np.random.default_rng(41)
    vf = SM["v_follow"][:N_LC]
    tau = SM["t_react"][:N_LC]
    gap = rng.uniform(4.0, 50.0, N_LC)
    b = np.array([DP.lane_change_follower_decel(float(g), float(v), V_EGO_LC, reaction=float(t), min_gap=S0_LC)["decel"]
                  for g, v, t in zip(gap, vf, tau)])
    fin = np.isfinite(b) & (b > 0.2)                     # 0.2 m/s² 未満は止まるまで数分かかるので行進から外す(数は印字)
    Tm = float(np.max(tau[fin] + (vf[fin] - V_EGO_LC) / b[fin])) + 0.5
    mn = march_follower(gap[fin], vf[fin], V_EGO_LC, tau[fin], b[fin], T=Tm)
    mn_lo = march_follower(gap[fin], vf[fin], V_EGO_LC, tau[fin], 0.97 * b[fin], T=Tm + 2.0)
    print("    要る減速度: 0 = %d、0〜0.2 = %d、0.2 以上で有限 = %d(行進で照合)、∞(反応の間に割る)= %d。行進の最小車間 − s₀: 最大のずれ %.4f m、0.97 倍の減速では全件 s₀ を割る = %s" % (
        int(np.sum(b == 0)), int(np.sum((b > 0) & (b <= 0.2))), int(fin.sum()), int(np.sum(~np.isfinite(b))), float(np.max(np.abs(mn - S0_LC))), bool(np.all(mn_lo < S0_LC))))
    gate("後続車に要る減速度の閉形式 = 2 台の時間の行進で最小車間が s₀(±0.01 m)、少しでも弱いと割る(境目が鋭い)",
         fin.sum() > 20 and float(np.max(np.abs(mn - S0_LC))) < 0.01 and bool(np.all(mn_lo < S0_LC)))
    m2 = march_follower(gap, vf, V_EGO_LC, tau, np.full(gap.shape, DP.SUDDEN_DECEL))
    obs = b > DP.SUDDEN_DECEL
    clear = np.abs(b - DP.SUDDEN_DECEL) > 1e-3
    agree = np.array_equal(obs[clear], (m2 < S0_LC)[clear])
    gate("「急に」の判定(閉形式 b > 2.0)= 2.0 m/s² で行進して s₀ を割るか(%d 場面すべて)" % int(clear.sum()), agree and obs.sum() > 0 and (~obs).sum() > 0,
         "急 %d / %d" % (int(obs.sum()), N_LC))
    rows = {"rule": [], "naive": []}
    for i in range(N_LC):
        fol = {"gap": float(gap[i]), "v_follow": float(vf[i]), "v_ego": V_EGO_LC, "reaction": float(tau[i]), "min_gap": S0_LC}
        # 規則: ミラー → 約 3 秒前に合図 → 後続車に急ブレーキを強いないなら変える(強いるなら待つ)
        ev_rule = [{"t": -4.0, "kind": "mirror"}, {"t": -3.2, "kind": "signal_on"}, {"t": 0.0, "kind": "start"}, {"t": 3.0, "kind": "end"},
                   {"t": 3.6, "kind": "signal_off"}]
        pr = DP.lane_change_permitted(follower=fol, signal_events=ev_rule)
        rows["rule"].append(pr)
        ev_nv = [{"t": -1.4, "kind": "mirror"}, {"t": -1.0, "kind": "signal_on"}, {"t": 0.0, "kind": "start"}, {"t": 3.0, "kind": "end"},
                 {"t": 3.4, "kind": "signal_off"}]
        rows["naive"].append(DP.lane_change_permitted(follower=fol, signal_events=ev_nv))
    done = [p for p in rows["rule"] if p["ok"]]
    wait = [p for p in rows["rule"] if not p["ok"]]
    rsn_rule = {k for p in wait for k, _ in p["reasons"]}
    cnt = {}
    for p in rows["naive"]:
        for k, _ in p["reasons"]:
            cnt[k] = cnt.get(k, 0) + 1
    print("    規則: 変えた %d、待った %d(理由 %s)。素朴(約 1 秒前に合図、後ろを見ずに変える): %s" % (
        len(done), len(wait), ", ".join(sorted(rsn_rule)) or "なし", ", ".join("%s %d" % kv for kv in sorted(cnt.items()))))
    gate("規則は後続車に急ブレーキ(> 2.0 m/s²、仮定)を強いず、合図は約 3 秒前(待つのは後続車の理由だけ)",
         all(p["decel"] <= DP.SUDDEN_DECEL for p in done) and rsn_rule <= {"follower_sudden_decel"} and len(done) > 0)
    gate("門が自明でない: 素朴は全場面で合図が遅く、後続車に急ブレーキを強いる場面がある",
         cnt.get("signal_signal_timing", 0) == N_LC and cnt.get("follower_sudden_decel", 0) > 0,
         "急ブレーキ %d / %d" % (cnt.get("follower_sudden_decel", 0), N_LC))
    return {"gap": gap, "vf": vf, "tau": tau, "b": b, "obs": obs}


# ───────────────────────────── 3. 環状交差点 ─────────────────────────────
R_RING = 14.0                                # 環道の車線の中心の半径(仮定)
ARMS = np.array([-0.5 * math.pi, math.pi, 0.5 * math.pi, 0.0])   # 南(入口)・西・北・東
A_GO = 1.5                                   # 止まった所からの発進(仮定)
D_CLEAR = 2.0 + CAR_L + 2.0                   # 譲る線から、後端が衝突の点を抜けるまで


def t_clear_from(v0, vcap):
    """譲る線から D_CLEAR 進む時間(初速 v0、A_GO で vcap まで)。"""
    if v0 >= vcap:
        return D_CLEAR / vcap
    ta = (vcap - v0) / A_GO
    da = v0 * ta + 0.5 * A_GO * ta * ta
    if da >= D_CLEAR:
        return (-v0 + math.sqrt(v0 * v0 + 2 * A_GO * D_CLEAR)) / A_GO
    return ta + (D_CLEAR - da) / vcap


def ring_cars(rng, vr, k0):
    """環道の車: Poisson(平均 2.2 台)を一様な角に、互いの弧 ≥ 12 m で。速さは標本の門を通った値。"""
    n = min(int(rng.poisson(2.2)), 5)                    # 円周 88 m に 12 m 間隔で入る数で切る
    th = []
    while len(th) < n:
        c = rng.uniform(0, 2 * math.pi)
        if all(R_RING * abs((c - o + math.pi) % (2 * math.pi) - math.pi) >= 12.0 for o in th):
            th.append(c)
    return [{"theta": c, "speed": float(vr[(k0 + j) % len(vr)])} for j, c in enumerate(th)]


def ring_at(cars, t):
    return [{"theta": c["theta"] - c["speed"] / R_RING * t, "speed": c["speed"]} for c in cars]


def march_ring(arc, v, b, T, h=1e-3):
    """円周の行進(閉形式と別の経路): 弧 arc 手前の車を速さ v・減速 b で進め、時刻 T までに進んだ弧と、着いた時刻(着かなければ inf)。"""
    s, vv, t = 0.0, v, 0.0
    t_at = math.inf
    while t < T - 1e-12:
        vn = max(vv - b * h, 0.0)
        s += 0.5 * (vv + vn) * h
        vv = vn
        t += h
        if s >= arc and t_at == math.inf:
            t_at = t
    return s, t_at


def ring_progress(v, t_in, t_end, dt=0.1):
    t = np.arange(t_in, t_end, dt)
    return t, v / R_RING * (t - t_in)


def replay_exit_events(prog):
    """事象の再生(signal_point と別の経路): 環道の上の位置ベクトル p(t) と各枝の向き a_i の外積の符号が変わり、内積が正の刻みを
    「その枝の側方を通過」とする(剰余を使わない)。返り値 [(刻み, 枝)]。"""
    th = ARMS[0] - prog                                   # 右回り = 角が減る
    P = np.stack([np.cos(th), np.sin(th)], 1)
    ev = []
    for j, a in enumerate(ARMS):
        if j == 0:
            continue
        A = np.array([math.cos(a), math.sin(a)])
        cr = P[:, 0] * A[1] - P[:, 1] * A[0]
        dot = P @ A
        k = np.flatnonzero((np.sign(cr[:-1]) != np.sign(cr[1:])) & (dot[1:] > 0))
        ev += [(int(i + 1), j) for i in k]
    return sorted(ev)


def scene_roundabout(SM):
    print("== 3. 環状交差点(S069, S102、37 条の 2・35 条の 2・53 条 2 項): %d 場面、環道の半径 %.0f m(仮定)" % (N_RB, R_RING))
    rng = np.random.default_rng(51)
    vr = SM["v_ring"]
    out = {"rule": [], "naive": []}
    march_err, march_n = 0.0, 0
    cls_ok, cls_n = True, 0
    sig_err, sig_n = 0.0, 0
    for e in range(N_RB):
        cars = ring_cars(rng, vr, 8 * e)
        ex = int(rng.integers(1, 4))
        for pol in ("rule", "naive"):
            if pol == "rule":
                t, v_in = 0.0, JOKOU
                while t < 300.0:
                    tc = t_clear_from(JOKOU if t == 0.0 else 0.0, JOKOU)
                    chk = DP.roundabout_entry_check(ARMS[0], R_RING, ring_at(cars, t), t_clear=tc, entry_speed=JOKOU)
                    if not any(c["obstructs"] for c in chk["cars"]):
                        break
                    t += 0.1
                t_go = t
            else:
                t_go, v_in = 0.0, 20.0 / 3.6
                tc = t_clear_from(v_in, v_in)
                chk = DP.roundabout_entry_check(ARMS[0], R_RING, ring_at(cars, 0.0), t_clear=tc, entry_speed=v_in)
            # 円周の行進: 減速が要る車は、その減速度でちょうど t_clear に入口の点に着く
            for c in chk["cars"]:
                if 0 < c["decel"] < math.inf and march_n < 60:
                    sp0 = ring_at(cars, t_go)[chk["cars"].index(c)]["speed"]
                    s, t_at = march_ring(c["arc"], sp0, c["decel"], tc + 2.0)
                    if tc <= 2.0 * c["arc"] / sp0:                 # 減速しながら t_clear ちょうどに着く
                        march_err = max(march_err, abs(t_at - tc))
                    else:                                          # 入口の点の手前で止まる(v²/2d)
                        march_err = max(march_err, abs(s - c["arc"]) / sp0)
                    march_n += 1
                if math.isfinite(c["decel"]) and abs(c["decel"] - DP.SUDDEN_DECEL) > 1e-2 and c["arc"] > 0:
                    sp = ring_at(cars, t_go)[chk["cars"].index(c)]["speed"]
                    _, t_at = march_ring(c["arc"], sp, DP.SUDDEN_DECEL, tc)
                    cls_ok &= (t_at < tc) == bool(c["obstructs"])
                    cls_n += 1
            # 環道の中: 規則は徐行で、合図は出口の 1 つ手前(入った直後の出口なら入ったとき)から。素朴は 20 km/h、出口で合図(遅い)・
            # 右へ回る出口では入るときに右の合図
            sp = DP.roundabout_signal_point(ARMS, 0, ex)
            v_ring_ego = JOKOU if pol == "rule" else 20.0 / 3.6
            tt, prog = ring_progress(v_ring_ego, 0.0, (sp["exit_angle"] + 0.05) * R_RING / v_ring_ego + 0.3)
            if pol == "rule":
                left = prog >= sp["signal_angle"]
                right = np.zeros(prog.shape, bool)
            else:
                left = prog >= sp["exit_angle"] - 0.12
                right = (prog < 0.6) if ex == 3 else np.zeros(prog.shape, bool)
            sc = DP.roundabout_signal_check(prog, left, arm_angles=ARMS, entry=0, exit=ex, right_on=right)
            if pol == "rule":
                evs = replay_exit_events(prog)
                before = [k for k, j in evs if j != ex and prog[k] < sp["exit_angle"]]
                k_on = int(np.argmax(left))
                want = before[-1] if before else 0
                sig_err = max(sig_err, abs(tt[k_on] - tt[want]))
                sig_n += 1
            out[pol].append({"chk": chk, "t_go": t_go, "sig": sc, "exit": ex, "cars": cars, "sp": sp})
    ob = {p: sum(any(c["obstructs"] for c in r["chk"]["cars"]) for r in out[p]) for p in out}
    nc = {p: sum("not_crawling" in [k for k, _ in r["chk"]["reasons"]] for r in out[p]) for p in out}
    sv = {p: {} for p in out}
    for p in out:
        for r in out[p]:
            for v in r["sig"]["violations"]:
                sv[p][v] = sv[p].get(v, 0) + 1
    wt = np.array([r["t_go"] for r in out["rule"]])
    print("    規則: 進行妨害 %d、徐行でない %d、待った場面 %d(待ち 平均 %.1f s・最大 %.1f s)、合図の違反 %s" % (
        ob["rule"], nc["rule"], int(np.sum(wt > 0)), wt.mean(), wt.max(), sv["rule"] or "なし"))
    print("    素朴(20 km/h のまま入る、出口で合図): 進行妨害 %d / %d、徐行でない %d、合図の違反 %s" % (
        ob["naive"], N_RB, nc["naive"], ", ".join("%s %d" % kv for kv in sorted(sv["naive"].items()))))
    print("    円周の行進: %d 台で、要る減速度で走ると入口の点に着く時刻 − t_clear 最大 %.4f s。「急に」の判定と 2.0 m/s² の行進の一致 %d 台" % (
        march_n, march_err, cls_n))
    gate("環道の車に要る減速度 = 円周の行進でちょうど t_clear に入口の点(±0.01 s)、急かどうか = 2.0 m/s² の行進",
         march_n > 10 and march_err < 0.01 and cls_ok and cls_n > 50, "%d / %d 台" % (march_n, cls_n))
    gate("S102: 規則は進行妨害 0・徐行(37 条の 2 第 1・2 項)、待つ場面がある(全部素通りの自明な答えでない)",
         ob["rule"] == 0 and nc["rule"] == 0 and int(np.sum(wt > 0)) > 0)
    gate("S069: 規則の左の合図 = 事象の再生で数えた「出口の 1 つ手前の出口の通過」の時刻(±0.1 s)、roundabout_signal_check で違反なし",
         sig_n == N_RB and sig_err <= 0.1 + 1e-9 and not sv["rule"], "最大のずれ %.2f s" % sig_err)
    gate("門が自明でない: 素朴は進行妨害・徐行でない・合図の遅れと右の合図が数えられる",
         ob["naive"] > 0 and nc["naive"] == N_RB and sv["naive"].get("left_late", 0) > 0 and sv["naive"].get("right_signal", 0) > 0)
    return out


# ───────────────────────────── 4. 坂の頂上 ─────────────────────────────
def scene_crest(OV):
    print("== 4. 坂の頂上(S065, S081、道路構造令 2 条 24 号・19 条・22 条、30 条 1 号・42 条 2 号)")
    rows = []
    for v in sorted(DP.CREST_RADIUS_TABLE):
        s = DP.crest_sight_distance(radius=DP.CREST_RADIUS_TABLE[v])["sight"]
        rows.append((v, DP.CREST_RADIUS_TABLE[v], s, DP.SIGHT_DISTANCE_TABLE[v]))
        print("    設計速度 %3d km/h: 凸形縦断曲線の半径 %6.0f m → 視距 %.1f m(構造令の表 %.0f m)" % rows[-1])
    assert len(rows) == 3
    gate("公表値: 構造令 22 条の半径と 2 条 24 号の高さ(1.2 m・10 cm)で 19 条の視距の表 3 行を 1 % 以内で再現",
         all(abs(s - t) / t < 0.01 for _, _, s, t in rows), ", ".join("%.1f/%.0f" % (s, t) for _, _, s, t in rows))
    c = CREST
    xs = np.arange(c["x"] - 400.0, c["x"] + 200.0, 0.5)
    out = {}
    for h2, nm in ((DP.SIGHT_OBJECT_HEIGHT, "物 10 cm"), (H_ONC, "対向車 1.2 m")):
        cf = DP.crest_sight_distance(grade_in=c["g1"], grade_out=c["g2"], length=c["L"], object_height=h2)
        sc = sight_scan(xs, h2, step=0.25, reach=700.0)
        out[nm] = (cf, sc)
        print("    PoC の道の頂上(±4 %%、L %.0f m、R %.0f m)、%s: 閉形式の視距 %.2f m / 見通し線の走査の最短 %.2f m(%s)" % (
            c["L"], cf["radius"], nm, cf["sight"], sc.min(), "S ≤ L" if cf["within_curve"] else "S > L"))
    gate("PoC の道の頂上: 見通し線を総当たりで走査した最短の視距 = crest_sight_distance(物 10 cm・対向車 1.2 m、±0.5 m)",
         all(abs(cf["sight"] - sc.min()) <= 0.5 for cf, sc in out.values()))
    # 頂上の手前で追い越せない理由: 見通しが D* に届かない区間
    grid, S = OV["S_grid"]
    Dm = float(np.median(OV["D_star"]))
    short = S < Dm
    reg = grid[short & (grid > c["x"] - 600) & (grid < c["x"] + 300)]
    zone = DP.no_overtaking_zones([{"kind": "crest", "at": c["x"]}])["merged"][0]
    frac = float(np.mean((reg >= zone[0]) & (reg <= zone[1]))) if reg.size else 0.0
    sp = DP.crest_safe_speed(out["物 10 cm"][0]["sight"], reaction=1.0, brake=DP.G * 0.35 * 1.0)
    print("    D* の中央値 %.0f m に見通しが届かない区間(頂上の前後): [%.0f, %.0f] m、長さ %.0f m。30 条 1 号の「付近」(前後 30 m、仮定)が"
          "覆うのはその %.0f %%(残りは 28 条 4 項の D* の判定で止める)" % (Dm, reg.min(), reg.max(), reg.size * 0.5, 100 * frac))
    print("    頂上の視距 %.1f m(物 10 cm)の中で止まれる上限の速さ(反応 1.0 s・減速 0.35 g、仮定)= %.1f km/h。42 条 2 号は速さによらず"
          "頂上付近で徐行(10 km/h、仮定)を求める" % (out["物 10 cm"][0]["sight"], sp["speed_kmh"]))
    started_short = [r for r in OV["res"]["rule"]["rows"] if r["started"] and float(OV["S_vis_fn"](r["x_s"] - EYE_BACK)) - EYE_BACK < r["req"]["d_required"]]
    gate("頂上の手前では見通しが D* に届かない区間が 30 条の「付近」より長く、規則は見通しが D* に足りない所で 1 人も追越しを始めない",
         reg.size * 0.5 > zone[1] - zone[0] and not started_short, "%.0f m > %.0f m" % (reg.size * 0.5, zone[1] - zone[0]))
    return {"rows": rows, "out": out, "Dm": Dm, "reg": reg, "zone": zone}


# ───────────────────────────── 5. カーブミラー ─────────────────────────────
MIR_R, MIR_D = 3.0, 0.8                      # 凸面鏡の半径・直径(仮定)
ROAD_W = 5.0                                 # 主の道(T 字路の横の道)の幅: 2.5 m × 2(仮定)
X_NEAR = 1.25                                # 右から来る車の車線の中心
EYE3 = np.array([-0.3 - EYE_BACK, 1.25 - 0.37, 1.2])     # 停止線(x = −0.3)で止まった運転者の目(右ハンドル)
MIR3 = np.array([5.4, -0.62, 2.5])                         # 鏡の中心(向こう側の歩道、高さ 2.5 m)
AIM3 = np.array([X_NEAR, -25.0, 0.8])                      # 鏡が狙う点: 右 25 m の車線の中心
V_CAR_MIR = 30.0 / 3.6


def _unit(v):
    return v / np.linalg.norm(v)


def mirror_normal3():
    import drivedecide as DD
    return np.asarray(DD.mirror_aim_normal(EYE3, MIR3, AIM3 - MIR3), float)


def refl_point(E, C, R, X, iters=60):
    """球面の凸面鏡(中心 C、半径 R)の上で E → P → X が反射の法則を満たす P(Newton、接平面の 2 変数、直線探索つき)。
    近軸の閉形式と別の経路の、3 次元の厳密な光線追跡。返り値 (P, 残差)。"""
    u0 = _unit(_unit(E - C) + _unit(X - C))
    a = np.cross(u0, [0.0, 0.0, 1.0])
    if np.linalg.norm(a) < 1e-6:
        a = np.cross(u0, [0.0, 1.0, 0.0])
    a = _unit(a)
    b = np.cross(u0, a)

    def G(p):
        uu = _unit(u0 + p[0] * a + p[1] * b)
        P = C + R * uu
        s = _unit(E - P) + _unit(X - P)
        return np.array([s @ (a - (a @ uu) * uu), s @ (b - (b @ uu) * uu)])
    p = np.zeros(2)
    for _ in range(iters):
        g = G(p)
        hh = 1e-8
        J = np.c_[(G(p + [hh, 0]) - g) / hh, (G(p + [0, hh]) - g) / hh]
        d = np.linalg.solve(J, -g)
        lam = 1.0
        while lam > 1e-4 and np.linalg.norm(G(p + lam * d)) > np.linalg.norm(g):
            lam *= 0.5
        p = p + lam * d
        if np.linalg.norm(d) < 1e-15:
            break
    P = C + R * _unit(u0 + p[0] * a + p[1] * b)
    return P, float(np.linalg.norm(G(p)))


def _ang(E, P, Q):
    return math.acos(float(np.clip(_unit(P - E) @ _unit(Q - E), -1.0, 1.0)))


def reading(E, C, R, X0, ax, h):
    """X0 を中心に向き ax の長さ h の線分の像の見かけの大きさ → 平面鏡のつもりで読む距離 (h/2)/tan(θ/2) − e。"""
    P1, r1 = refl_point(E, C, R, X0 + ax * h / 2)
    P2, r2 = refl_point(E, C, R, X0 - ax * h / 2)
    th = _ang(E, P1, P2)
    e = float(np.linalg.norm(E - (C + R * _unit(_unit(E - C) + _unit(X0 - C)))))
    return (h / 2) / math.tan(th / 2) - e, th, max(r1, r2)


def scene_mirror():
    print("== 5. カーブミラー(S064): 凸面鏡 R %.0f m・直径 %.1f m(仮定)" % (MIR_R, MIR_D))
    R = MIR_R
    # (a) 近軸(眼が鏡の軸の上、物は眼の後ろ)の読み k a = 3 次元の厳密な光線追跡
    e, h = 8.0, 1.45
    M0 = np.zeros(3)
    n0 = np.array([1.0, 0.0, 0.0])
    C0 = M0 - R * n0
    E0 = M0 + e * n0
    rows = []
    for a in (10.0, 30.0, 60.0):
        ah, th, res = reading(E0, C0, R, np.array([a, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), h)
        im = DP.convex_mirror_image(a, R, eye_distance=e, object_size=h)
        rows.append((a, ah, im["flat_equivalent_distance"], th, im["angular_size"], res))
    for a, ah, fe, th, tha, res in rows:
        print("    近軸 e = %.0f m: 本当 %.0f m → 光線追跡の読み %.2f m / 閉形式 k·a = %.2f m(k = %.3f)、見かけの大きさ %.4f° / %.4f°" % (
            e, a, ah, fe, 1 + 2 * e / R, math.degrees(th), math.degrees(tha)))
    gate("凸面鏡の近軸: 大きさから読む距離 k·a(k = 1 + 2e/R)= 3 次元の厳密な光線追跡(反射点を Newton、相対 0.5 %)",
         all(abs(ah - fe) / fe < 5e-3 and abs(th - tha) / tha < 5e-3 and res < 1e-9 for a, ah, fe, th, tha, res in rows),
         "30 m → %.1f m" % rows[1][1])
    # (b) 速さの 3 通りの読み = 光線追跡の有限差分
    v, dt = 10.0, 1e-3
    mis = DP.convex_mirror_misjudge(30.0, v, R, eye_distance=e)

    def size(dist):
        return reading(E0, C0, R, np.array([dist, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), h)[1]
    th0, th1 = size(30.0 + v * dt), size(30.0 - v * dt)
    ahat = lambda th: (h / 2) / math.tan(th / 2) - e      # noqa: E731
    v_cons = -(ahat(th1) - ahat(th0)) / (2 * dt)
    dflat = (h / 2) / ((e + 30.0) ** 2 + (h / 2) ** 2) * 2
    v_anch = ((th1 - th0) / (2 * dt)) / dflat

    def lat(y):
        P, _ = refl_point(E0, C0, R, np.array([30.0, y, 0.0]))
        return math.atan2((P - E0)[1], -(P - E0)[0])
    om = (lat(0.3 + v * dt) - lat(0.3 - v * dt)) / (2 * dt)
    v_lat = abs(om) * (e + 30.0)
    print("    速さ 10 m/s の読み: 大きさから矛盾なく %.1f m/s(閉形式 %.1f)、本当の距離に錨 %.2f m/s(%.2f)、横切る動き %.2f m/s(%.2f)。"
          "見かけの到達時間 %.2f s / 本当 %.2f s" % (v_cons, mis["speed_size_consistent"], v_anch, mis["speed_size_anchored"], v_lat,
                                              mis["speed_lateral_anchored"], mis["tau_apparent"], mis["tau_true"]))
    gate("速さの 3 通りの読み(速く・遅く・遅く)= 光線追跡の有限差分(相対 1 %)",
         abs(v_cons / mis["speed_size_consistent"] - 1) < 0.01 and abs(v_anch / mis["speed_size_anchored"] - 1) < 0.01
         and abs(v_lat / mis["speed_lateral_anchored"] - 1) < 0.01 and mis["speed_size_anchored"] < v < mis["speed_size_consistent"])
    # (c) T 字路の斜めの鏡: Coddington の式(縦 = サジタル、横 = タンジェンシャル)
    n3 = mirror_normal3()
    C3 = MIR3 - R * n3
    eT = float(np.linalg.norm(EYE3 - MIR3))
    inc = math.acos(float(np.clip(_unit(EYE3 - MIR3) @ n3, -1, 1)))
    k_s = 1 + 2 * eT * math.cos(inc) / R
    k_t = 1 + 2 * eT / (R * math.cos(inc))
    k_p = 1 + 2 * eT / R
    rT = []
    d_aim = _unit(AIM3 - MIR3)
    for a in (15.0, 30.0, 60.0):
        X0 = MIR3 + a * d_aim
        side = _unit(np.cross(d_aim, np.cross(_unit(EYE3 - MIR3), d_aim)))    # 入射面の中で視線に直交
        perp = _unit(np.cross(d_aim, side))
        rv, _, r1 = reading(EYE3, C3, R, X0, perp if abs(perp[2]) > abs(side[2]) else side, h)
        rh, _, r2 = reading(EYE3, C3, R, X0, side if abs(perp[2]) > abs(side[2]) else perp, h)
        rT.append((a, rv, k_s * a, rh, k_t * a, max(r1, r2)))
    print("    T 字路の鏡: 目から鏡 %.2f m、入射角 %.1f°。近軸の k = %.2f、縦(サジタル)k_s = %.2f、横(タンジェンシャル)k_t = %.2f" % (
        eT, math.degrees(inc), k_p, k_s, k_t))
    for a, rv, cs, rh, ct, res in rT:
        print("      本当 %.0f m → 縦の大きさの読み %.1f m(k_s·a %.1f)、横の大きさの読み %.1f m(k_t·a %.1f)、近軸なら %.1f m" % (a, rv, cs, rh, ct, k_p * a))
    gate("斜めに見る鏡: 縦・横の読み = Coddington の式 k_s·a・k_t·a(3 次元の光線追跡と相対 0.5 %)、縦 < 近軸 < 横(像が横に潰れる)",
         all(abs(rv / cs - 1) < 5e-3 and abs(rh / ct - 1) < 5e-3 and res < 1e-9 and rv < k_p * a < rh for a, rv, cs, rh, ct, res in rT),
         "30 m → 縦 %.0f m・横 %.0f m" % (rT[1][1], rT[1][3]))
    # (d) 道の上で映る範囲(上から見た 2 次元)
    E2, M2 = EYE3[:2], MIR3[:2]
    n2 = _unit(n3[:2])
    cov = DP.mirror_road_coverage(E2, M2, n2, MIR_D, mirror_radius=R, road_point=(X_NEAR, 0.0), road_direction=(0.0, -1.0))
    t2 = np.array([-n2[1], n2[0]])
    phim = math.asin(MIR_D / 2 / R)
    phi = np.linspace(-phim, phim, 20001)
    N = np.cos(phi)[:, None] * n2[None, :] + np.sin(phi)[:, None] * t2[None, :]
    P = (M2 - R * n2)[None, :] + R * N
    d = P - E2[None, :]
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    rr = d - 2 * np.sum(d * N, 1, keepdims=True) * N
    with np.errstate(divide="ignore", invalid="ignore"):
        s_ = (X_NEAR - P[:, 0]) / rr[:, 0]
        lam = -(P[:, 1] + s_ * rr[:, 1])                    # 道の向き (0, −1)、λ = 右へ測った距離
    ok = (s_ > 0) & np.isfinite(lam)
    lo, hi = cov["interval"]
    print("    道の上で映る範囲(右から来る車の車線の中心で、脇道の中心線の延長から右へ測る。脇道の右の端は 2.5 m): [%.2f, %s] m。手前の死角 %.2f m(密な光線 %d 本の走査 [%.2f, %s])" % (
        lo, "∞" if math.isinf(hi) else "%.1f" % hi, cov["blind_near"], int(ok.sum()), lam[ok].min(),
        "∞" if (~ok).any() or lam[ok].max() > 1e3 else "%.1f" % lam[ok].max()))
    gate("道の上で映る範囲 = 密な光線(20001 本)の走査、手前に映らない死角がある", abs(lo - lam[ok].min()) < 1e-3 and cov["blind_near"] > 0,
         "死角 %.2f m" % cov["blind_near"])
    return {"n3": n3, "C3": C3, "e": eT, "inc": inc, "k_s": k_s, "k_t": k_t, "k_p": k_p, "rT": rT, "cov": cov, "mis": mis, "rows": rows}


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    print("仮定値: 30 条 1 号の「付近」%.0f m・「勾配の急な」%.0f %%・「急に」%.1f m/s²・徐行 %.0f km/h・対向車の見積もり %.1f km/h・"
          "PET の下限 %.0f s・戻り %.0f s(施行令 21 条は未確認、合図の時期は教則の値)" % (
              DP.VICINITY["crest"], 100 * DP.STEEP_GRADE, DP.SUDDEN_DECEL, DP.CRAWL_SPEED * 3.6, V_ON_ASSUMED * 3.6, PET_MIN, T_LC))
    want = figs.enabled()
    tm = {}
    t = time.time()
    SM = scene_samples()
    tm["samples"] = time.time() - t
    out = {"SM": SM}
    t = time.time()
    out["overtake"] = scene_overtake(SM)
    tm["overtake"] = time.time() - t
    for key, fn in (("lane", scene_lane_change), ("ring", scene_roundabout)):
        t = time.time()
        out[key] = fn(SM)
        tm[key] = time.time() - t
    t = time.time()
    out["crest"] = scene_crest(out["overtake"])
    tm["crest"] = time.time() - t
    t = time.time()
    out["mirror"] = scene_mirror()
    tm["mirror"] = time.time() - t
    print("  区間ごとの所要 [s]: " + ", ".join("%s %.1f" % kv for kv in tm.items()))
    if want:
        figures(out)
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("== 結果: %d / %d 門, %.1f s(CPU %.1f s)" % (sum(OK), len(OK), time.time() - T0, time.process_time()))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


# ───────────────────────────── 6. 図 ─────────────────────────────
GROUND_FAR = np.array([0.40, 0.55, 0.33])     # 地平線より下で何も当たらない画素(草地)
WHITE = (0.95, 0.95, 0.92)
YELLOW = (0.95, 0.75, 0.08)
ROAD = (0.40, 0.41, 0.43)
GRASS = (0.40, 0.56, 0.31)
ORANGE = (0.96, 0.52, 0.08)
FOV = 40.0                                    # 縦の画角 [度]


def _txt(img, s, xy, anchor="lt", fs=12):
    import annotate as AN
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=max(9, fs)), dtype=np.float64)


def _box_mesh(L, W, H, z0=0.0):
    """x 長さ L・y 幅 W・高さ H の箱(底面の中心が原点、z0 から)。"""
    V = np.array([[x, y, z] for z in (z0, z0 + H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)], float)
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]])
    return V, F


def _quad(xa, xb, ya, yb, z=0.006):
    return np.array([[xa, ya, z], [xb, ya, z], [xb, yb, z], [xa, yb, z]], float), np.array([[0, 1, 2], [0, 2, 3]])


def render(w, pose, K, W, H, ego=None):
    """世界を撮り、地平線より下の何も当たらない画素を草地の色にする。"""
    import driveworld as DW
    v = DW.world_camera(w, pose, K, W, H, ego=ego)
    bg = v["label"] < 0
    if bg.any():
        rr, cc = np.nonzero(bg)
        d = np.stack([(cc - K[0, 2]) / K[0, 0], -(rr - K[1, 2]) / K[1, 1], -np.ones(len(rr))], 1) @ np.asarray(pose)[:3, :3]
        down = d[:, 2] < 0
        v["color"][rr[down], cc[down]] = GROUND_FAR
    return v


def place_pitch(V0, x, y, yaw, z, pitch=0.0):
    """底面の中心を原点とする頂点を、縦の傾き pitch(前が上 +)→ 向き yaw → 位置 (x, y, z) に置く(坂で車が地面に埋まらない)。"""
    c, s = math.cos(pitch), math.sin(pitch)
    X = V0[:, 0] * c - V0[:, 2] * s
    Z = V0[:, 0] * s + V0[:, 2] * c
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.c_[x + X * cy - V0[:, 1] * sy, y + X * sy + V0[:, 1] * cy, z + Z]


class Mover:
    """世界の中で動かす資産(頂点を毎コマ書き換える)。"""

    def __init__(self, w, name, dims=None, paint=None):
        import driveworld as DW
        m = DW.load_asset(name, dims, paint=paint)
        self.V0 = m["V"]
        self.w = w
        self.i = DW.world_add(w, self.V0 + [0, 0, -500.0], m["F"], m["label"], m["color"], name=name)
        self.dims = m["dims"]

    def put(self, x, y, yaw, z, pitch=0.0):
        v0, v1 = self.w["objects"][self.i]["verts"]
        self.w["V"][v0:v1] = place_pitch(self.V0, x, y, yaw, z, pitch)

    def hide(self):
        v0, v1 = self.w["objects"][self.i]["verts"]
        self.w["V"][v0:v1] = self.V0 + [0, 0, -500.0]

    def faces(self):
        return self.w["objects"][self.i]["faces"]


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
        self.d.polygon(self.p(np.asarray(P)), fill=fill, outline=outline, width=width)

    def rect(self, xa, xb, ya, yb, fill=None, outline=None, width=1):
        self.poly(np.array([[xa, ya], [xb, ya], [xb, yb], [xa, yb]]), fill=fill, outline=outline, width=width)

    def line(self, P, fill, width=2):
        if len(P) > 1:
            self.d.line(self.p(np.asarray(P)), fill=fill, width=width)

    def circle(self, c, r, outline=None, fill=None, width=2):
        (x, y), = self.p(c)
        rr = r * self.s
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=outline, fill=fill, width=width)

    def car(self, x, y, yaw, L=CAR_L, W=CAR_W, fill=(60, 120, 230), outline=(20, 30, 60), width=1):
        """中心 (x, y)・向き yaw の車の箱。返り値 = 4 隅(左前・右前・右後・左後)。"""
        u = np.array([math.cos(yaw), math.sin(yaw)])
        lft = np.array([-u[1], u[0]])
        c = np.array([x, y])
        P = np.array([c + u * L / 2 + lft * W / 2, c + u * L / 2 - lft * W / 2, c - u * L / 2 - lft * W / 2, c - u * L / 2 + lft * W / 2])
        self.poly(P, fill=fill, outline=outline, width=width)
        return P

    def arr(self):
        return np.asarray(self.im, dtype=np.float64) / 255.0


def frames_ok(frames):
    """動画の全コマの数値走査: 空(真っ黒・真っ白)・定数でないか、隣のコマと同じコマの数。"""
    st = np.array([float(np.std(f)) for f in frames])
    mean = np.array([float(np.mean(f)) for f in frames])
    diff = np.array([float(np.mean(np.abs(frames[k + 1] - frames[k]))) for k in range(len(frames) - 1)])
    return {"n": len(frames), "std_min": float(st.min()), "mean_min": float(mean.min()), "mean_max": float(mean.max()),
            "still": int(np.sum(diff < 1e-6)), "ok": bool(st.min() > 0.03 and 0.05 < mean.min() and mean.max() < 0.95)}


# ── 追越しの世界(縦断の坂つき) ──
def _profile_strip(xa, xb, ya, yb, dz, step):
    xs = np.arange(xa, xb + 1e-9, step)
    V = np.array([[x, y, float(road_z(x)) + dz] for x in xs for y in (ya, yb)])
    F = []
    for i in range(len(xs) - 1):
        a = 2 * i
        F += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
    return V, np.array(F)


def world_overtake(OV):
    import driveworld as DW
    w = DW._empty_world()
    XA, XB = 300.0, 1900.0
    for ya, yb in ((-80.0, -3.6), (3.6, 80.0)):
        V, F = _profile_strip(XA, XB, ya, yb, 0.0, 4.0)
        DW.world_add(w, V, F, 0, GRASS, name="grass")
    V, F = _profile_strip(XA, XB, -3.6, 3.6, 0.02, 2.0)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    zones = OV["zres"]["merged"]
    for yy in (-LANE, LANE):                                         # 外側線
        V, F = _profile_strip(XA, XB, yy - 0.07, yy + 0.07, 0.035, 4.0)
        DW.world_add(w, V, F, 9, WHITE, name="line")
    x = XA
    while x < XB:                                                    # 中央線: 禁止区間は黄の実線、それ以外は白の破線
        inz = any(a <= x <= b for a, b in zones)
        if inz:
            for yy in (-0.12, 0.12):
                V, F = _profile_strip(x, x + 2.0, yy - 0.06, yy + 0.06, 0.035, 2.0)
                DW.world_add(w, V, F, 9, YELLOW, name="line")
            x += 2.0
        else:
            V, F = _profile_strip(x, x + 5.0, -0.07, 0.07, 0.035, 5.0)
            DW.world_add(w, V, F, 9, WHITE, name="line")
            x += 10.0
    rng = np.random.default_rng(7)
    for xp in np.arange(XA, XB, 40.0):                               # 視線誘導の柱
        for sy in (-1, 1):
            v, f = _box_mesh(0.12, 0.12, 1.0)
            DW.world_add(w, v + [xp, sy * 4.3, float(road_z(xp))], f, 6, WHITE, name="post")
    for xt in np.arange(XA, XB, 18.0):                                # 木(箱)
        for sy in (-1, 1):
            if rng.random() < 0.45:
                continue
            xx = xt + rng.uniform(-4, 4)
            v, f = _box_mesh(2.6, 2.6, rng.uniform(4.0, 9.0))
            col = (0.16 + rng.uniform(0, 0.08), 0.36 + rng.uniform(0, 0.12), 0.16)
            DW.world_add(w, v + [xx, sy * rng.uniform(9.0, 45.0), float(road_z(xx)) - 0.2], f, 6, col, name="tree")
    ids = {"lead": Mover(w, "truck", dims=(CAR_L, CAR_W, 1.85)),
           "onc": [Mover(w, ("sedan", "suv", "taxi")[k % 3]) for k in range(8)]}
    return w, ids


def _smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def ot_state(d, r, t):
    """自車の前端 x・横 y・速さと、前の車の前端(時刻 t)。"""
    vL, gb = d["vL"], d["gb"]
    xL = X_START + vL * t
    if not r["started"] or t <= r["t_s"]:
        return xL - CAR_L - gb, Y_EGO, vL, xL
    s, v = ego_kin(t - r["t_s"], vL, d["a"], V_MAX)
    x = r["x_s"] + float(s)
    if t < r["t_r"]:
        y = Y_EGO + (Y_ONC - Y_EGO) * _smooth((t - r["t_s"]) / 1.5)
    else:
        y = Y_ONC + (Y_EGO - Y_ONC) * _smooth((t - r["t_r"]) / T_LC)
    return x, y, float(v), xL


def _pitch_at(x, sgn=1.0):
    return math.atan(sgn * float(road_grade(x)))


def profile_inset(W, H, xe, onc_x, xl, S, Dst, vis):
    """横から見た縦断(高さは誇張): 自車(青)・前の車(灰)・対向車(見える = 赤、見えない = 赤の枠)・目からの見通し線・要る D*。"""
    from PIL import Image, ImageDraw
    x0, x1 = xe - 40.0, xe + 700.0
    xs = np.linspace(x0, x1, 300)
    zs = road_z(xs)
    zlo, zhi = float(zs.min()) - 2.0, float(zs.max()) + 6.0
    im = Image.new("RGB", (W, H), (226, 236, 246))
    dr = ImageDraw.Draw(im)
    X = lambda v: (v - x0) / (x1 - x0) * W                       # noqa: E731
    Z = lambda v: H - 4 - (v - zlo) / (zhi - zlo) * (H - 22)     # noqa: E731
    dr.polygon([(X(xs[0]), H)] + [(X(a), Z(b)) for a, b in zip(xs, zs)] + [(X(xs[-1]), H)], fill=(110, 150, 90))
    dr.line([(X(a), Z(b)) for a, b in zip(xs, zs)], fill=(70, 70, 74), width=2)
    ze = float(road_z(xe - EYE_BACK)) + DP.SIGHT_EYE_HEIGHT
    xv = xe - EYE_BACK + S
    dr.line([(X(xe - EYE_BACK), Z(ze)), (X(xv), Z(float(road_z(xv)) + H_ONC))], fill=(30, 150, 60), width=2)
    for xo, vv in zip(onc_x, vis):
        if x0 < xo < x1:
            zo = float(road_z(xo))
            box = [X(xo), Z(zo + 1.6), X(xo + CAR_L) + 2, Z(zo)]
            dr.rectangle(box, fill=(220, 50, 40) if vv else None, outline=(200, 30, 30), width=2)
    for xx, col in ((xl, (150, 150, 150)), (xe, (50, 110, 230))):
        zz = float(road_z(xx))
        dr.rectangle([X(xx - CAR_L) - 1, Z(zz + 1.8), X(xx) + 1, Z(zz)], fill=col)
    yb = 6
    ok = S - EYE_BACK >= Dst
    dr.rectangle([X(xe), yb, X(min(xe + Dst, x1)), yb + 5], fill=(40, 160, 70) if ok else (220, 60, 50))
    dr.rectangle([X(xe), yb + 7, X(min(xe - EYE_BACK + S, x1)), yb + 10], fill=(30, 150, 60))
    return np.asarray(im, np.float64) / 255.0


def fig_overtake_video(out):
    """主図: 運転席から見た追越し(素朴 → 規則)、下に横から見た縦断、上にルームミラー。"""
    import driveworld as DW
    OV = out["overtake"]
    drivers, res = OV["drivers"], OV["res"]
    best = None
    for d, rn, rr in zip(drivers, res["naive"]["rows"], res["rule"]["rows"]):
        if not (rn["started"] and rr["started"]):
            continue
        score = (0.0 <= rn["pet_min"] < PET_MIN) * 5 + (rn["pet_min"] < 0) + (700 < rn["x_s"] < CREST["x"]) * 3 + (rr["x_s"] > CREST["x"] + 30) * 2 \
            - 0.02 * (rr["t_s"] - rn["t_s"])
        if best is None or score > best[0]:
            best = (score, d["i"])
    i = best[1]
    d, rn, rr = drivers[i], res["naive"]["rows"][i], res["rule"]["rows"][i]
    Wv, Hv = VID_WH
    small = Wv < 500
    fsz = 9 if small else 12
    K = DW.camera_intrinsics(FOV, Wv, Hv)
    w, ids = world_overtake(OV)
    xo0, vo = d["onc"]
    G = OV["G_MIR"]
    rg = DP.overtake_return_gap(lane_offset=LANE, lead_width=CAR_W)
    Ev, nrm = rg["virtual_eye"], rg["mirror_normal"]
    Mc = np.array([0.55, 0.0])
    tm = np.array([-nrm[1], nrm[0]])
    mw = int(Wv * 0.34)
    mh = max(12, int(mw * 0.26))
    a1, a2 = Mc + 0.125 * tm - Ev, Mc - 0.125 * tm - Ev
    hf = math.acos(float(np.clip(_unit(a1) @ _unit(a2), -1, 1)))
    vf = 2 * math.degrees(math.atan(math.tan(hf / 2) * mh / mw))
    Km = DW.camera_intrinsics(vf, mw, mh)
    ph = int(Hv * 0.27)
    frames, seg = [], {}
    req = rr["req"]
    for pol, r in (("naive", rn), ("rule", rr)):
        t_beg = rn["t_s"] - 5.0
        t_end = r["t_e"] + 3.0
        ts = []
        t = t_beg
        while t < t_end:
            ts.append(t)
            t += 1.0 if (pol == "rule" and r["t_s"] - t > 6.0) else 0.25
        n0 = len(frames)
        for t in ts:
            x, y, v, xL = ot_state(d, r, t)
            xo = xo0 - vo * t
            ids["lead"].put(xL - CAR_L / 2, Y_EGO, 0.0, float(road_z(xL - CAR_L / 2)), _pitch_at(xL - CAR_L / 2))
            near = np.argsort(np.abs(xo - x))[:8]
            for k, m in enumerate(ids["onc"]):
                j = near[k] if k < len(near) else None
                if j is None or not (x - 150 < xo[j] < x + 1000):
                    m.hide()
                    continue
                xc = xo[j] + CAR_L / 2
                m.put(xc, Y_ONC, math.pi, float(road_z(xc)), _pitch_at(xc, -1.0))
            xe_eye = x - EYE_BACK
            g = float(road_grade(xe_eye + 10.0))
            e3 = np.array([xe_eye, y - 0.35, float(road_z(xe_eye)) + 1.2])
            pose = DW.camera_pose(e3, e3 + np.array([1.0, 0.0, g - 0.03]))
            f = render(w, pose, K, Wv, Hv)["color"].copy()
            # ルームミラー(仮想の眼から鏡の中心を通して後ろを撮り、左右を反転 = 平面鏡の像)
            zc = float(road_z(xe_eye)) + 1.25
            cm = np.array([xe_eye + Ev[0], y + Ev[1], zc])
            tgt = np.array([xe_eye + Mc[0], y + Mc[1], zc - 0.01])
            mimg = render(w, DW.camera_pose(cm, tgt), Km, mw, mh)["color"][:, ::-1]
            x0m = (Wv - mw) // 2
            f[4:4 + mh, x0m:x0m + mw] = 0.12
            f[6:4 + mh - 2, x0m + 2:x0m + mw - 2] = mimg[2:-2, 2:-2]
            S = float(OV["S_vis_fn"](xe_eye))
            vis = (xo - x > 0) & (xo - xe_eye <= S)
            f[Hv - ph:, :] = profile_inset(Wv, ph, x, xo, xL, S, req["d_required"], vis)
            gap = (x - CAR_L) - xL
            if pol == "rule" and t < r["t_s"]:
                near_d = float((xo - x)[vis].min()) if vis.any() else math.inf
                pm = DP.overtake_permitted(maneuver_start=x, maneuver_end=x + req["ego_distance"], zones_result=OV["zres"],
                                           dist_oncoming=min(near_d, S - EYE_BACK), requirement=req)
                why = {"no_passing_zone": "追越し禁止の区間に掛かる", "oncoming_too_close": "見通し・対向車まで < D*"}
                st = ("待つ: " + " / ".join(why.get(k_, k_) for k_, _ in pm["reasons"])) if pm["reasons"] else "見通しが D* に届いた → 出る"
            elif t < r["t_s"]:
                st = "見えた範囲 %.0f m に対向車なし → 出る" % (S - EYE_BACK) if t >= r["t_s"] - 0.3 else "前の車に付いて走る"
            elif t < r["t_r"]:
                st = "追越し中(後端 − 前の車の前端 %+.1f m)" % gap
            elif t < r["t_e"]:
                st = ("ルームミラーに全体が映った → 戻る" if pol == "rule" else "抜いたらすぐ戻る(車間 %.1f m)" % r["gap_ret"])
            else:
                st = "戻り切った。対向車との PET %.1f s" % r["pet_min"]
            title = ("素朴: 見えなければ出る・抜いたらすぐ戻る" if pol == "naive" else "規則: 見通しが D* に届くまで待つ・ミラーで戻る")
            lines = [title if not small else ("素朴" if pol == "naive" else "規則"), st,
                     "%4.1f km/h  見えている %3.0f m / 要る D* %3.0f m" % (3.6 * v, S - EYE_BACK, req["d_required"])]
            f = _txt(f, "\n".join(lines), (6, 6 + mh + 4), fs=fsz)
            f = _txt(f, "ルームミラー", (Wv // 2, 6 + mh), anchor="ct", fs=fsz - 2)
            frames.append(np.clip(f, 0, 1))
        seg[pol] = len(frames) - n0
    chk = frames_ok(frames)
    figs.save_video("overtake_dashcam", frames, fps=8.0, gif_every=2, gif_width=480,
                    caption="主図(運転席の目 %d × %d、%d コマ、0.25 s ごと = 2 倍速。規則の待ちの長い所は 1 s ごと)。同じ運転者 #%d(前の車 %.0f km/h、"
                            "加速 %.2f m/s²)と同じ対向車の流れで、前半 %d コマ = 素朴: 頂上の手前 %.0f m で、見えた範囲(%.0f m)に対向車が無いので出て、"
                            "前の車を抜いたらすぐ戻る(車間 %.1f m)—— 対向車との PET %.1f s。後半 %d コマ = 規則: 見通しが D* = %.0f m に届かない間"
                            "(坂の頂上が隠す)と追越し禁止の区間では待ち、頂上を %.0f m 越えた所で出て、ルームミラーに前の車の全体が映る車間 %.1f m"
                            "(overtake_return_gap)で戻る —— PET %.1f s。上 = ルームミラー(仮想の眼から撮って左右を反転)、下 = 横から見た縦断"
                            "(高さを誇張。緑の線 = 目からの見通し、赤い箱 = 見えている対向車、赤い枠 = 坂に隠れた対向車、上の帯 = 要る D*(赤 = 足りない)と"
                            "見えている距離)。"
                            % (Wv, Hv, len(frames), i, 3.6 * d["vL"], d["a"], seg["naive"], CREST["x"] - rn["x_s"],
                               float(OV["S_vis_fn"](rn["x_s"] - EYE_BACK)) - EYE_BACK, rn["gap_ret"], rn["pet_min"], seg["rule"],
                               req["d_required"], rr["x_s"] - CREST["x"], G, rr["pet_min"]))
    return {"n": len(frames), "i": i, "chk": chk, "rn": rn, "rr": rr, "seg": seg}


# ── 環状交差点の俯瞰 ──
def ring_xy(th, r=R_RING):
    return np.array([r * math.cos(th), r * math.sin(th)])


def fig_roundabout_video(out):
    RB = out["ring"]
    obstr = [k for k in range(len(RB["naive"])) if any(c["obstructs"] for c in RB["naive"][k]["chk"]["cars"])]
    cand = [k for k in obstr if RB["naive"][k]["exit"] == 3 and RB["rule"][k]["t_go"] > 0] or \
        [k for k in obstr if RB["naive"][k]["exit"] == 3] or obstr
    k = cand[0]
    W, H = (960, 480) if not REDUCED else (640, 320)
    pw = W // 2
    names = {1: "出口 1(左折)", 2: "出口 2(直進)", 3: "出口 3(右折)"}
    info = {}
    for pol in ("rule", "naive"):
        r = RB[pol][k]
        v_in = JOKOU if pol == "rule" else 20.0 / 3.6
        tc = t_clear_from(0.0 if r["t_go"] > 0 else v_in, v_in)
        info[pol] = {"r": r, "v": v_in, "tc": tc, "t_ring": r["t_go"] + tc}
    t_end = max(info[p]["t_ring"] + info[p]["r"]["sp"]["exit_angle"] * R_RING / info[p]["v"] + 4.0 for p in info)
    cars = RB["rule"][k]["cars"]
    # 素朴: 進行妨害を受けた車は t = 0 から要る減速度で減速、t_clear の後は 1.0 m/s² で元の速さへ(弧を 0.01 s で積分)
    tg = np.arange(-3.0, t_end + 0.2, 0.01)
    arcs = {}
    for pol in ("rule", "naive"):
        A = []
        for j, c in enumerate(cars):
            b = info[pol]["r"]["chk"]["cars"][j]["decel"] if pol == "naive" else 0.0
            b = b if math.isfinite(b) else 0.0
            v = np.full(tg.shape, c["speed"])
            if b > 0:
                vv, cur = [], c["speed"]
                for tt in tg:
                    if 0 <= tt < info[pol]["tc"]:
                        cur = max(cur - b * 0.01, 0.0)
                    elif tt >= info[pol]["tc"]:
                        cur = min(cur + 1.0 * 0.01, c["speed"])
                    vv.append(cur)
                v = np.array(vv)
            s = np.concatenate([[0.0], np.cumsum(0.5 * (v[1:] + v[:-1]) * 0.01)])
            s -= np.interp(0.0, tg, s)
            A.append((s, b))
        arcs[pol] = A
    frames = []
    fs_ = 11 if not REDUCED else 9
    for t in np.arange(-3.0, t_end, 0.2):
        img = np.ones((H, W, 3))
        for col, pol in enumerate(("rule", "naive")):
            Iq = info[pol]
            r = Iq["r"]
            sp = r["sp"]
            T = Top(pw, H, (-40.0, 40.0), (-44.0, 36.0), bg=(222, 228, 214))
            for a in ARMS:
                u = np.array([math.cos(a), math.sin(a)])
                lft = np.array([-u[1], u[0]])
                P0 = u * 12.0
                T.poly([P0 + lft * 3.6, P0 + u * 40 + lft * 3.6, P0 + u * 40 - lft * 3.6, P0 - lft * 3.6], fill=(110, 112, 116))
            T.circle((0, 0), R_RING + 2.4, fill=(110, 112, 116), outline=None)
            T.circle((0, 0), R_RING - 2.4, fill=(150, 190, 120), outline=(240, 240, 235), width=2)
            for j in (1, 2, 3):
                (px, py), = T.p(ring_xy(ARMS[j], R_RING + 7.5))
                T.d.text((px - 3, py - 6), str(j), fill=(20, 20, 20))
            T.circle(ring_xy(ARMS[0] - sp["signal_angle"], R_RING + 3.2), 1.0, fill=(250, 200, 30), outline=(120, 90, 0), width=1)
            T.circle(ring_xy(ARMS[0] - sp["exit_angle"], R_RING + 3.2), 1.0, fill=(60, 170, 80), outline=(20, 80, 30), width=1)
            worst = 0.0
            for j, c in enumerate(cars):
                s, b = arcs[pol][j]
                th = c["theta"] - float(np.interp(t, tg, s)) / R_RING
                P = ring_xy(th)
                dec = b > 0 and 0 <= t < Iq["tc"]
                worst = max(worst, b if dec else 0.0)
                T.car(P[0], P[1], th - math.pi / 2, fill=(220, 50, 40) if dec and b > DP.SUDDEN_DECEL else
                      ((240, 160, 40) if dec else (170, 170, 175)), outline=(30, 30, 30))
            sig_l = sig_r = False
            yl = -(R_RING + 3.5)
            if t < 0:
                P, yaw = np.array([-1.8, yl + Iq["v"] * t]), math.pi / 2
            elif t < r["t_go"]:
                P, yaw = np.array([-1.8, yl]), math.pi / 2
            elif t < Iq["t_ring"]:
                u = (t - r["t_go"]) / Iq["tc"]
                P = (1 - u) * np.array([-1.8, yl]) + u * ring_xy(ARMS[0])
                yaw = math.pi / 2 + u * math.pi / 2
                sig_r = pol == "naive" and r["exit"] == 3
                sig_l = pol == "rule" and r["sp"]["signal_angle"] == 0.0
            else:
                prog = Iq["v"] / R_RING * (t - Iq["t_ring"])
                if prog < sp["exit_angle"]:
                    th = ARMS[0] - prog
                    P, yaw = ring_xy(th), th - math.pi / 2
                    if pol == "rule":
                        sig_l = prog >= sp["signal_angle"]
                    else:
                        sig_l = prog >= sp["exit_angle"] - 0.12
                        sig_r = r["exit"] == 3 and prog < 0.6
                else:
                    a = ARMS[r["exit"]]
                    u = np.array([math.cos(a), math.sin(a)])
                    lft = np.array([-u[1], u[0]])
                    dist = Iq["v"] * (t - Iq["t_ring"]) - sp["exit_angle"] * R_RING
                    P, yaw = u * (R_RING + dist) + lft * 1.8, a
                    sig_l = dist < 3.0
            Q = T.car(P[0], P[1], yaw, fill=(60, 120, 230), outline=(20, 30, 60), width=2)
            blink = (t % 0.66) < 0.33
            for on, qs in ((sig_l, (Q[0], Q[3])), (sig_r, (Q[1], Q[2]))):
                if on and blink:
                    for q in qs:
                        T.circle(q, 0.7, fill=(255, 150, 0), outline=(140, 60, 0), width=1)
            pan = T.arr()
            head = ("規則: 譲って徐行で入る・1 つ手前で左の合図" if pol == "rule" else "素朴: 20 km/h で入る・出口で合図")
            viol = ", ".join(r["sig"]["violations"] + [k_ for k_, _ in r["chk"]["reasons"]]) or "違反なし"
            st = "合図: 左 点滅中" if sig_l else ("合図: 右 点滅中" if sig_r else "合図: なし")
            pan = _txt(pan, "%s\n%s → %s\n%s  環道の車の減速 %.1f m/s²" % (head, names[r["exit"]], viol, st, worst), (6, 6), fs=fs_)
            img[:, col * pw:(col + 1) * pw] = pan[:, :pw]
        img = _txt(img, "t = %.1f s(譲る線に着いた時刻 = 0)  黄の点 = 合図を出す所、緑の点 = 出口、橙の丸 = 方向指示器、赤 = 急な減速(> 2.0 m/s²)" % t,
                   (W // 2, H - 4), anchor="cb", fs=10 if not REDUCED else 8)
        frames.append(np.clip(img, 0, 1))
    chk = frames_ok(frames)
    ri, ni = info["rule"], info["naive"]
    dmax = max(c["decel"] for c in ni["r"]["chk"]["cars"] if math.isfinite(c["decel"]))
    figs.save_video("roundabout_birdseye", frames, fps=5.0, gif_every=1, gif_width=min(W, 720),
                    caption="上から見た動画(%d コマ、0.2 s ごと = 実時間)。環状交差点(環道の半径 %.0f m、右回り)に南から入り %s へ出る場面 #%d を、同じ環道の車で。"
                            "左 = 規則: 環道の車に 2.0 m/s² を超える減速を要らせない時刻まで %.1f s 待ち、徐行(10 km/h)で入り、出口の 1 つ手前の出口の側方で"
                            "左の合図(roundabout_signal_point、黄の点)—— roundabout_signal_check = %s。右 = 素朴: 20 km/h のまま入り(環道の車に要らせた"
                            "減速度 最大 %.1f m/s² = 37 条の 2 第 1 項の進行妨害)、%s。" % (
                                len(frames), R_RING, names[ri["r"]["exit"]], k, ri["r"]["t_go"],
                                "違反なし" if ri["r"]["sig"]["ok"] else ri["r"]["sig"]["violations"], dmax,
                                "右の合図で入り、出口の直前で左に変える(right_signal, left_late)" if ni["r"]["exit"] == 3 else "出口の直前で合図(left_late)"))
    return {"n": len(frames), "k": k, "chk": chk, "dmax": dmax, "exit": ri["r"]["exit"], "t_go": ri["r"]["t_go"]}


# ── カーブミラーの T 字路 ──
WALL_X, WALL_Y = -0.2, -2.7                   # 右の角の塀(脇道の右の端 −2.5 の外、主の道の端 0 の手前)


def world_mirror(M):
    import driveworld as DW
    w = DW._empty_world()
    V, F = DW._grid_plane(-80.0, 60.0, -150.0, 60.0, step=10.0, z=-0.03)
    DW.world_add(w, V, F, 0, (0.56, 0.55, 0.50), name="ground")
    V, F = DW._grid_plane(0.0, ROAD_W, -150.0, 60.0, step=4.0)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    V, F = DW._grid_plane(-80.0, 0.0, -2.5, 2.5, step=4.0)
    DW.world_add(w, V, F, 0, ROAD, name="road")
    V, F = DW._grid_plane(ROAD_W, ROAD_W + 2.5, -150.0, 60.0, step=6.0, z=0.12)
    DW.world_add(w, V, F, 1, (0.74, 0.73, 0.70), name="walk")
    for y0 in np.arange(-150.0, 60.0, 8.0):                           # 主の道の中央の破線
        if -3.0 < y0 + 4 < 3.0:
            continue
        V, F = _quad(ROAD_W / 2 - 0.06, ROAD_W / 2 + 0.06, y0, y0 + 4.0)
        DW.world_add(w, V, F, 9, WHITE, name="line")
    V, F = _quad(-0.75, -0.3, 0.0, 2.5, z=0.008)                      # 停止線
    DW.world_add(w, V, F, 9, WHITE, name="stop_line")
    V, F = _quad(-0.75, -0.3, -0.5, 0.0, z=0.008)
    DW.world_add(w, V, F, 9, WHITE, name="stop_line")
    parts = []
    for (xa, xb, ya, yb) in ((-60.0, WALL_X, WALL_Y - 0.15, WALL_Y), (WALL_X - 0.15, WALL_X, -150.0, WALL_Y),
                             (-60.0, WALL_X, -WALL_Y, -WALL_Y + 0.15), (WALL_X - 0.15, WALL_X, -WALL_Y, 60.0)):
        v, f = _box_mesh(xb - xa, yb - ya, 2.0)
        DW.world_add(w, v + [(xa + xb) / 2, (ya + yb) / 2, 0.0], f, 6, (0.72, 0.70, 0.66), name="wall")
    rng = np.random.default_rng(3)
    for xs_, sy in ((np.arange(-50.0, -6.0, 11.0), -1), (np.arange(-50.0, -6.0, 11.0), 1)):
        for x0 in xs_:
            for yc in (np.arange(-140.0, -6.0, 12.0) if sy < 0 else np.arange(8.0, 60.0, 12.0)):
                if rng.random() < 0.35:
                    continue
                v, f = _box_mesh(8.0, 8.0, rng.uniform(5.0, 8.0))
                col = tuple(rng.uniform(0.55, 0.85) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
                DW.world_add(w, v + [x0, yc, 0.0], f, 6, col, name="house")
    for yc in np.arange(-140.0, 60.0, 11.0):
        if rng.random() < 0.3:
            continue
        v, f = _box_mesh(9.0, 8.0, rng.uniform(5.0, 9.0))
        col = tuple(rng.uniform(0.55, 0.85) * np.array([1.0, rng.uniform(0.85, 1), rng.uniform(0.75, 0.95)]))
        DW.world_add(w, v + [ROAD_W + 8.0, yc, 0.0], f, 6, col, name="house")
    del parts
    ids = {"car": Mover(w, "sedan", paint=(0.80, 0.12, 0.10))}
    nf = len(w["F"])
    # 鏡: 柱と、球面の縁の裏(橙の円板)。鏡面そのものは光線追跡で描く
    n = M["n3"]
    u1 = _unit(np.cross(n, [0.0, 0.0, 1.0]))
    u2 = np.cross(n, u1)
    back = MIR3 - n * 0.05
    v, f = _box_mesh(0.08, 0.08, back[2] - 0.45)
    DW.world_add(w, v + [back[0], back[1], 0.0], f, 6, (0.92, 0.55, 0.12), name="mirror_post")
    ang = np.linspace(0, 2 * math.pi, 33)[:-1]
    for rad, off, col in ((0.47, 0.045, ORANGE), (0.41, 0.035, (0.16, 0.16, 0.18))):
        Vd = np.vstack([MIR3 - n * off] + [MIR3 - n * off + rad * (math.cos(a) * u1 + math.sin(a) * u2) for a in ang])
        Fd = np.array([[0, 1 + k, 1 + (k + 1) % 32] for k in range(32)] + [[0, 1 + (k + 1) % 32, 1 + k] for k in range(32)])
        DW.world_add(w, Vd, Fd, 6, col, name="mirror")
    return w, ids, nf


def pix_dirs(pose, K, W, H):
    cc, rr = np.meshgrid(np.arange(W), np.arange(H))
    d = np.stack([(cc - K[0, 2]) / K[0, 0], -(rr - K[1, 2]) / K[1, 1], -np.ones(cc.shape)], -1).reshape(-1, 3) @ np.asarray(pose)[:3, :3]
    return d / np.linalg.norm(d, axis=1, keepdims=True)


class MirrorEnv:
    """鏡の中心の少し前に置いたカメラで、反射の向きの周りを撮った画像(毎コマ)。反射の光線はこれを深度で 3 回視差補正して引く。"""

    def __init__(self, M, size):
        import driveworld as DW
        n = M["n3"]
        self.n, self.C = n, M["C3"]
        self.Mc = MIR3 + 0.03 * n
        d0 = _unit(MIR3 - EYE3)
        self.r0 = d0 - 2 * (d0 @ n) * n
        # 縁の反射の向きの広がり(眼から縁の 64 点)
        u1 = _unit(np.cross(n, [0.0, 0.0, 1.0]))
        u2 = np.cross(n, u1)
        mx = 0.0
        for a in np.linspace(0, 2 * math.pi, 64, endpoint=False):
            q = math.sqrt(MIR_R ** 2 - 0.16) * n + 0.4 * (math.cos(a) * u1 + math.sin(a) * u2)
            P = self.C + q
            N = q / MIR_R
            d = _unit(P - EYE3)
            r = d - 2 * (d @ N) * N
            mx = max(mx, math.acos(float(np.clip(r @ self.r0, -1, 1))))
        self.fov = 2 * math.degrees(mx) * 1.15
        self.size = size
        self.K = DW.camera_intrinsics(self.fov, size, size)
        self.pose = DW.camera_pose(self.Mc, self.Mc + self.r0)
        self.fwd = _unit(self.r0)

    def shoot(self, wenv, ego):
        self.img = render(wenv, self.pose, self.K, self.size, self.size, ego=ego)

    def lookup(self, dirs):
        import driveworld as DW
        col, row, dep = DW.world_project_points(self.Mc[None, :] + dirs, self.pose, self.K)
        ok = np.isfinite(col) & (dep > 0)
        c = np.clip(np.rint(np.where(ok, col, 0)).astype(int), 0, self.size - 1)
        r = np.clip(np.rint(np.where(ok, row, 0)).astype(int), 0, self.size - 1)
        ok &= (np.where(ok, col, -9) >= -0.5) & (np.where(ok, col, 9e9) <= self.size - 0.5) & \
              (np.where(ok, row, -9) >= -0.5) & (np.where(ok, row, 9e9) <= self.size - 0.5)
        depth = self.img["depth"][r, c]
        dist = np.where(ok & np.isfinite(depth), depth / np.maximum(dirs @ self.fwd, 1e-6), np.inf)
        return r, c, ok, dist


def mirror_trace(E, pose, K, W, H, depth_main, env):
    """カメラの画素のうち、凸面鏡(球面、直径 0.8 m)に当たるものを、反射の光線で環境の画像から塗る。
    返り値 (当たった画素の mask (H, W), 色 (H, W, 3), 面の id (H, W)、当たらない所は −1)。"""
    d = pix_dirs(pose, K, W, H)
    C, n, R = env.C, env.n, MIR_R
    oc = E - C
    b = d @ oc
    c = oc @ oc - R * R
    disc = b * b - c
    hit = disc > 0
    t = -b - np.sqrt(np.where(hit, disc, 0.0))
    P = E[None, :] + t[:, None] * d
    q = P - C
    ax = q @ n
    rad = np.sqrt(np.maximum(np.sum(q * q, 1) - ax * ax, 0.0))
    fwd = -np.asarray(pose)[2, :3]
    hit &= (t > 0) & (ax > 0) & (rad <= MIR_D / 2) & ((P - E) @ fwd <= depth_main.ravel() + 0.02)
    idx = np.flatnonzero(hit)
    color = np.zeros((H * W, 3))
    face = np.full(H * W, -1, np.int64)
    if idx.size:
        dd, PP = d[idx], P[idx]
        N = q[idx] / R
        r = dd - 2 * np.sum(dd * N, 1, keepdims=True) * N
        dirs = r.copy()
        for _ in range(3):                                         # 視差の補正(反射点と環境のカメラの位置の違い)
            _, _, ok, dist = env.lookup(dirs)
            fin = ok & np.isfinite(dist)
            X = env.Mc[None, :] + np.where(fin, dist, 0.0)[:, None] * dirs
            tt = np.sum((X - PP) * r, 1)
            X2 = PP + np.maximum(tt, 0.05)[:, None] * r
            nd = X2 - env.Mc[None, :]
            nd /= np.linalg.norm(nd, axis=1, keepdims=True)
            dirs = np.where(fin[:, None], nd, r)
        rr, cc, ok, _ = env.lookup(dirs)
        col = env.img["color"][rr, cc]
        sky = np.where((r[:, 2] < 0)[:, None], GROUND_FAR[None, :], np.array([0.62, 0.75, 0.92])[None, :])
        color[idx] = 0.9 * np.where(ok[:, None], col, sky)            # 鏡の反射率(仮定 0.9)
        face[idx] = np.where(ok, env.img["face"][rr, cc], -1)
    return hit.reshape(H, W), color.reshape(H, W, 3), face.reshape(H, W)


def direct_visible_2d(yc):
    """上から見た 2 次元で、目から車線の中心の点 (X_NEAR, yc) への線分が右の角の塀(x = WALL_X、y < WALL_Y)を横切らないか。"""
    s = (WALL_X - EYE3[0]) / (X_NEAR - EYE3[0])
    y_at = EYE3[1] + s * (yc - EYE3[1])
    return y_at >= WALL_Y


def fig_mirror_video(out):
    """目玉の動画: 運転席から見たカーブミラーの中(光線追跡で描いた凸面鏡の像)と、上から見た本当の位置。"""
    import driveworld as DW
    from PIL import Image
    M = out["mirror"]
    if REDUCED:
        FW, FH, Z, RW = 480, 270, 270, 210
    else:
        FW, FH, Z, RW = 960, 540, 540, 420
    DH = int(RW * 9 / 16)
    TH = FH - DH
    fsz = 9 if REDUCED else 13
    w, ids, nf = world_mirror(M)
    wenv = dict(w, F=w["F"][:nf], face_color=w["face_color"][:nf], face_label=w["face_label"][:nf])
    me = DW.load_asset("sedan", paint=(0.20, 0.40, 0.85))
    ego = (place_pitch(me["V"], -0.3 - CAR_L / 2, 1.25, 0.0, 0.0), me["F"], me["color"])
    env = MirrorEnv(M, 300 if REDUCED else 640)
    eT = M["e"]
    zfov = 2 * math.degrees(math.atan((0.48 / 0.9) / eT))
    Kz = DW.camera_intrinsics(zfov, Z, Z)
    pz = DW.camera_pose(EYE3, MIR3)
    Kd = DW.camera_intrinsics(42.0, RW, DH)
    tgt = np.array([MIR3[0], MIR3[1] - 1.0, EYE3[2] + 0.45 * (MIR3[2] - EYE3[2])])
    pd = DW.camera_pose(EYE3, tgt)
    f0, f1 = ids["car"].faces()
    Vu = np.unique(np.round(ids["car"].V0, 3), axis=0)
    cov = M["cov"]
    blind = cov["blind_near"]
    # 直接見える境(上から見た 2 次元): 車線の中心の点が塀に隠れなくなる y
    yy = np.linspace(-60.0, 0.0, 60001)
    y_direct = float(yy[np.argmax([direct_visible_2d(v) for v in yy])])
    fps = 3.0 if REDUCED else 6.0
    ts = np.arange(0.0, 70.5 / V_CAR_MIR, 1.0 / fps)          # 右 70 m から、脇道の正面(y = 0.5)まで
    frames, meas = [], []
    for t in ts:
        yc = -70.0 + V_CAR_MIR * t
        ids["car"].put(X_NEAR, yc, 0.5 * math.pi, 0.0)
        env.shoot(wenv, ego)
        Xc = np.array([X_NEAR, yc, 0.72])
        a = float(np.linalg.norm(Xc - MIR3))
        # 拡大(運転席から鏡を見る)
        vz = render(w, pz, Kz, Z, Z)
        hz, cz, fz = mirror_trace(EYE3, pz, Kz, Z, Z, vz["depth"], env)
        img_z = np.where(hz[..., None], cz, vz["color"])
        car_m = hz & (fz >= f0) & (fz < f1)
        # 車のメッシュの頂点(重複を除いた全部)を厳密な光線追跡(Newton)で鏡に映し、拡大の画素へ
        Vw = place_pitch(Vu, X_NEAR, yc, 0.5 * math.pi, 0.0)
        Pc = np.array([refl_point(EYE3, M["C3"], MIR_R, X)[0] for X in Vw])
        col, row, _ = DW.world_project_points(Pc, pz, Kz)
        on_cap = np.all([np.linalg.norm((p - M["C3"]) - ((p - M["C3"]) @ M["n3"]) * M["n3"]) <= MIR_D / 2 for p in Pc])
        # 同じ所に平面鏡(鏡の中心の接平面)があったときの像: 頂点を鏡の面で折り返して拡大の画素へ
        Vf = Vw - 2.0 * ((Vw - MIR3) @ M["n3"])[:, None] * M["n3"][None, :]
        _, rowf, _ = DW.world_project_points(Vf, pz, Kz)
        frow = float(rowf.max() - rowf.min())
        if car_m.any():
            rows = np.flatnonzero(car_m.any(1))
            cols = np.flatnonzero(car_m.any(0))
            mrow, mcol = rows.max() - rows.min() + 1, cols.max() - cols.min() + 1
        else:
            mrow = mcol = 0
        meas.append({"t": t, "a": a, "yc": yc, "mrow": mrow, "mcol": mcol, "brow": float(row.max() - row.min()),
                     "bcol": float(col.max() - col.min()), "on_cap": bool(on_cap), "frow": frow})
        # 運転席の広い眺め
        vd = render(w, pd, Kd, RW, DH)
        hd, cd, fd = mirror_trace(EYE3, pd, Kd, RW, DH, vd["depth"], env)
        img_d = np.where(hd[..., None], cd, vd["color"])
        direct = int(np.sum(~hd & (vd["face"] >= f0) & (vd["face"] < f1)))
        in_mirror = int(car_m.sum())
        # 上から
        BH = 64
        yspan = 44.0
        xspan = yspan * RW / (TH - BH)
        T = Top(RW, TH - BH, (-0.42 * xspan, 0.58 * xspan), (-38.0, 6.0), bg=(214, 222, 206))
        T.rect(0.0, ROAD_W, -60, 10, fill=(110, 112, 116))
        T.rect(-60, 0.0, -2.5, 2.5, fill=(110, 112, 116))
        T.rect(ROAD_W, ROAD_W + 2.5, -60, 10, fill=(190, 188, 180))
        T.rect(ROAD_W + 3.5, 80, -60, 10, fill=(200, 184, 160))
        T.rect(-60, WALL_X, -60, WALL_Y, fill=(150, 146, 138), outline=(60, 60, 60), width=2)
        T.rect(-60, WALL_X, -WALL_Y, 10, fill=(150, 146, 138), outline=(60, 60, 60), width=2)
        T.line([(X_NEAR, 0.0), (X_NEAR, -blind)], (220, 40, 30), 4)
        T.line([(X_NEAR, -blind), (X_NEAR, -40)], (240, 150, 30), 4)
        T.line([(X_NEAR + 0.25, y_direct), (X_NEAR + 0.25, 0.0)], (40, 170, 70), 3)
        for P_, rr_ in zip(cov["edge_points"], cov["edge_rays"]):
            T.line([P_, P_ + rr_ * 45.0], (240, 150, 30), 1)
        T.circle(MIR3[:2], 0.5, fill=(245, 140, 20), outline=(90, 40, 0), width=1)
        T.circle(EYE3[:2], 0.4, fill=(40, 90, 220), outline=None)
        T.car(-0.3 - CAR_L / 2, 1.25, 0.0, fill=(50, 100, 215))
        T.car(X_NEAR, yc, 0.5 * math.pi, fill=(210, 40, 30), outline=(80, 0, 0), width=2)
        T.line([EYE3[:2], MIR3[:2], (X_NEAR, yc)], (90, 90, 200), 1)
        top = np.ones((TH, RW, 3)) * 0.97
        top[:TH - BH] = T.arr()
        # 本当の距離と鏡の読み(0〜300 m の目盛り)
        from PIL import ImageDraw
        bar = Image.new("RGB", (RW, 46), (246, 246, 242))   # 目盛り(下の 46 px)
        dr = ImageDraw.Draw(bar)
        X_ = lambda v: 8 + min(v, 300.0) / 300.0 * (RW - 16)     # noqa: E731
        dr.line([(X_(0), 30), (X_(300), 30)], fill=(60, 60, 60), width=1)
        for v in range(0, 301, 50):
            dr.line([(X_(v), 26), (X_(v), 34)], fill=(60, 60, 60), width=1)
            dr.text((X_(v) - 6, 35), "%d" % v, fill=(60, 60, 60))
        for v, c_ in ((a, (210, 40, 30)), (M["k_s"] * a, (240, 150, 30)), (M["k_t"] * a, (160, 90, 20))):
            dr.polygon([(X_(v), 28), (X_(v) - 5, 18), (X_(v) + 5, 18)], fill=c_)
        top[TH - 46:] = np.asarray(bar, np.float64) / 255.0
        sep = "\n" if REDUCED else "  "
        top = _txt(top, sep.join(["▼赤 本当 %.0f m" % a, "▼橙 鏡の縦の読み %.0f m" % (M["k_s"] * a), "▼茶 横の読み %.0f m" % (M["k_t"] * a)]),
                   (RW // 2, TH - 46), anchor="cb", fs=max(9, fsz - 4))
        # 状態
        if in_mirror > 0:
            st = "鏡に映っている"
        elif direct > 0:
            st = "直接見える(鏡にはもう映らない)"
        else:
            st = "鏡にも映らず、直接も見えない"
        if mrow > 0 and not on_cap:
            line2 = "車が鏡の縁にかかる(大きさで読めない)"
        elif mrow > 0:
            read = (eT + a) * frow / mrow - eT                     # 平面鏡なら e + a に見える大きさとの比で読む
            meas[-1]["read"] = read
            line2 = "鏡の中の高さ %d px(平面鏡なら %.0f px)\n→ 大きさで読むと %.0f m 先" % (mrow, frow, read)
        else:
            line2 = "鏡の中に車の画素なし"
        img_z = _txt(img_z, "運転席から見たカーブミラー(光線追跡)\n本当の距離(鏡から)%.1f m  %s\n%s" % (a, st, line2), (6, 6), fs=fsz)
        img_d = _txt(img_d, "運転席から", (4, 4), fs=fsz - 3)
        fr = np.ones((FH, FW, 3))
        fr[:, :Z] = img_z
        fr[:DH, Z:Z + RW] = img_d
        fr[DH:, Z:Z + RW] = top
        frames.append(np.clip(fr, 0, 1))
        meas[-1].update({"direct": direct, "in_mirror": in_mirror, "state": st})
    chk = frames_ok(frames)
    mm = [m for m in meas if m["mrow"] > 0 and m["on_cap"] and m["brow"] >= 8]
    big = min([m for m in meas if "read" in m], key=lambda m: abs(m["a"] - 30.0))
    figs.save_video("mirror_tjunction", frames, fps=fps, gif_every=1 if REDUCED else 2, gif_width=min(FW, 720),
                    caption="目玉の動画(%d コマ、実時間)。見通しの悪い T 字路(右の角は高さ 2 m の塀)で停止線に止まった運転者が、向こう側のカーブミラー"
                            "(凸面 R %.0f m・直径 %.1f m、目から %.1f m、入射角 %.0f°)を見る。左 = 運転席から見た鏡の拡大: 鏡の中は球面での反射の光線を"
                            "環境の画像から引いて描いた(視差を深度で 3 回補正、車のメッシュの頂点の厳密な光線追跡と画素で照合)。右から %.0f km/h で来る赤い車は、"
                            "鏡から %.0f m のとき鏡の中で高さ %d px(同じ所の平面鏡なら %.0f px)—— 画素の比で読むと %.0f m 先。閉形式の読みは縦 %.0f m・横 %.0f m(Coddington の式 k_s = %.2f、"
                            "k_t = %.2f。正面から見る近軸なら k = %.2f で %.0f m)。右上 = 運転席からの広い眺め、右下 = 上から見た本当の位置(赤の線 = 鏡に"
                            "映らない手前 %.1f m、橙 = 映る範囲、緑 = 塀の陰から直接見える所。下の目盛り = 本当の距離と鏡の読み)。"
                            % (len(frames), MIR_R, MIR_D, eT, math.degrees(M["inc"]), V_CAR_MIR * 3.6, big["a"], big["mrow"], big["frow"], big["read"],
                               M["k_s"] * big["a"], M["k_t"] * big["a"], M["k_s"], M["k_t"], M["k_p"], M["k_p"] * big["a"], blind))
    return {"n": len(frames), "chk": chk, "meas": meas, "mm": mm, "y_direct": y_direct, "big": big}


def fig_static(out):
    SM = out["SM"]
    # 1. 標本の門(対向車の速さ)
    wrong, kept, Dw, pw = SM["_wrong"]
    x = np.sort(SM["v_on"]) * 3.6
    xk = np.sort(kept) * 3.6
    r = REF["v_on"]
    grid = np.linspace(min(x.min(), xk.min()), x.max(), 200)
    Fref = (_ncdf((grid / 3.6 - r["mean"]) / r["sd"]) - _ncdf(-Z999)) / (_ncdf(Z999) - _ncdf(-Z999))
    figs.save_plot("sample_gate", [("参照(切断正規)", grid, Fref), ("採った値の経験分布", x, np.arange(1, len(x) + 1) / len(x)),
                                   ("係数の誤り(1 個ずつの門は通過)", xk, np.arange(1, len(xk) + 1) / len(xk))],
                   xlabel="対向車の速さ [km/h]", ylabel="累積", title="乱数の値の門: 1 個ずつ(0.1 % 点)と集団(KS)",
                   caption="参照 N(55, 6) km/h(仮定)。採った %d 個の KS p は門を通る。全体を 1.25 で割った集団は 1 個ずつの門を %d / %d 個が通るが、"
                           "KS は D = %.2f(p = %.1g)で落とす。上側 0.1 %% 点 %.1f km/h を規則の運転者が対向車の速さの見積もりに使う。" % (
                               len(x), len(kept), len(wrong), Dw, pw, V_ON_ASSUMED * 3.6), size=(720, 360))
    # 2. 見通しと D*
    OV = out["overtake"]
    g, S = OV["S_grid"]
    sel = (g > 450) & (g < 1500)
    Dm = float(np.median(OV["D_star"]))
    zone = np.zeros(g.shape)
    for a, b in OV["zres"]["merged"]:
        zone[(g >= a) & (g <= b)] = 80.0
    figs.save_plot("sight_vs_dstar", [("対向車(1.2 m)が見える距離(見通し線の走査)", g[sel], S[sel] - EYE_BACK),
                                      ("要る D*(規則の中央値)", g[sel], np.full(sel.sum(), Dm)),
                                      ("30 条の禁止区間(高さは目印)", g[sel], zone[sel]),
                                      ("道の高さ × 20", g[sel], 20 * road_z(g[sel]))],
                   xlabel="自車の前端の位置 [m](頂上 = %.0f m)" % CREST["x"], ylabel="距離 [m]",
                   title="坂の頂上の手前では、見えている距離が追越しに要る D* に届かない",
                   caption="凸形縦断曲線(±4 %%、L %.0f m、R %.0f m)の道で、運転者の目(1.2 m)から対向車(1.2 m)が見える距離。頂上の手前 %.0f m から頂上まで"
                           "見えている距離が D* の中央値 %.0f m を下回る(%.0f m の区間)。30 条 1 号の「付近」(前後 30 m、仮定)はそのうち %.0f m だけ —— 残りは"
                           "28 条 4 項(D* の閉形式)で止める。頂上を越えると見える距離は走査の上限 1000 m に張り付く。" % (CREST["L"], CREST["L"] / (CREST["g1"] - CREST["g2"]),
                                                            CREST["x"] - out["crest"]["reg"].min(), Dm, out["crest"]["reg"].size * 0.5,
                                                            out["crest"]["zone"][1] - out["crest"]["zone"][0]), size=(820, 380))
    # 3. 追越しの結果の表
    res = OV["res"]
    rows = []
    for p, nm in (("rule", "規則(D* を確かめ・ミラーで戻る)"), ("naive", "素朴(%.0f m 先まで見えなければ出る)" % D_NAIVE)):
        R_ = res[p]
        rows.append([nm, "%d / %d" % (R_["started"], N_DRIVERS), "%d" % R_["zone_hit"], "%.2f" % R_["pet_min"], "%d" % R_["near"],
                     "%d" % R_["conflict"], "%d" % R_["cut"], "%.1f" % float(np.median(R_["gap_ret"]))])
    figs.save_table("overtake_results", ["運転", "追い越した", "禁止区間", "PET 最小 [s]", "PET < 2 s", "PET < 0", "割り込み", "戻りの車間 [m]"],
                    rows, title="追越し: %d 人 × 2 通り(同じ対向車の流れ)" % N_DRIVERS,
                    caption="禁止区間 = 条文を 0.25 m ごとに当てた総当たりで、追越しの道のりが 30 条の区間に掛かった人数。PET = 戻り切った位置に対向車が着く"
                            "までの時間(負 = 対向車線にいる間に出会う)。割り込み = ルームミラーに前の車の全体が映る車間 %.1f m より前で戻った人数。" % OV["G_MIR"])
    # 4. 凸面鏡の読み
    M = out["mirror"]
    a = np.linspace(2.0, 60.0, 120)
    figs.save_plot("mirror_readings", [("本当の距離", a, a), ("近軸(正面から)k·a", a, M["k_p"] * a),
                                       ("縦の大きさの読み k_s·a", a, M["k_s"] * a), ("横の大きさの読み k_t·a", a, M["k_t"] * a)],
                   xlabel="鏡から車までの本当の距離 a [m]", ylabel="大きさから読む距離 [m]",
                   title="カーブミラーの中の車は何 m 先に見えるか(凸面 R 3 m、目から %.0f m)" % M["e"],
                   caption="平面鏡のつもりで像の大きさから距離を読むと k 倍遠い。正面から見る近軸は k = 1 + 2e/R = %.2f(30 m → %.0f m)。この T 字路の"
                           "鏡は入射角 %.0f° の斜めで、Coddington の式で縦 k_s = %.2f(30 m → %.0f m)・横 k_t = %.2f(30 m → %.0f m)に分かれる"
                           "(3 次元の光線追跡と 0.5 %% 以内)。像は横に潰れて見える。" % (
                               M["k_p"], 30 * M["k_p"], math.degrees(M["inc"]), M["k_s"], 30 * M["k_s"], M["k_t"], 30 * M["k_t"]), size=(720, 380))
    # 5. 進路変更の要る減速度
    L = out["lane"]
    fin = np.isfinite(L["b"])
    ok = fin & ~L["obs"]
    bad = fin & L["obs"] & (L["b"] <= 8.0)
    n_off = int(np.sum(fin & (L["b"] > 8.0)))
    figs.save_plot("lane_change_decel", [("後続車に急ブレーキを強いない(規則は変える)", L["gap"][ok], L["b"][ok]),
                                         ("2.0 m/s² を超える(規則は待つ)", L["gap"][bad], L["b"][bad]),
                                         ("「急に」の境 2.0 m/s²(仮定)", np.array([4.0, 50.0]), np.array([2.0, 2.0]))],
                   xlabel="変えた瞬間の車間 [m]", ylabel="後続車に要る減速度 [m/s²]", title="進路変更の先の後続車に要る減速度(26 条の 2 第 2 項)",
                   caption="%d 場面(後続車の速さ・反応は標本の門を通った値、自車 50 km/h、残す車間 2 m)。lane_change_follower_decel の閉形式で、"
                           "2 台の時間の行進で最小車間が 2 m になることを確かめた。8 m/s² を超える %d 場面と反応の間に割る(∞)%d 場面は図の外"
                           "(どれも 2.0 m/s² を超え、規則は待つ)。" % (N_LC, n_off, int(np.sum(~fin))),
                   kinds=["scatter", "scatter", "line"], size=(720, 380), ylim=(0.0, 8.0))
    # 6. 構造令の表
    rows = [["%d" % v, "%.0f" % rr, "%.1f" % s, "%.0f" % t] for v, rr, s, t in out["crest"]["rows"]]
    figs.save_table("road_structure_order", ["設計速度 [km/h]", "凸形縦断曲線の半径 [m](22 条)", "閉形式の視距 [m]", "構造令の視距 [m](19 条)"], rows,
                    title="公表値の門: 道路構造令の表を閉形式で再現",
                    caption="目の高さ 1.2 m・物の高さ 10 cm(2 条 24 号)。国交省「道路構造令について」に載る 3 行。構造令の本文(e-Gov)とは未照合。")


def figures(out):
    print("== 6. 図")
    t = time.time()
    A = fig_overtake_video(out)
    print("  追越しの運転席の動画 %d コマ(%.1f s)、運転者 #%d: 素朴 %d コマ(PET %.2f s)・規則 %d コマ(PET %.2f s)、コマの走査 %s" % (
        A["n"], time.time() - t, A["i"], A["seg"]["naive"], A["rn"]["pet_min"], A["seg"]["rule"], A["rr"]["pet_min"], A["chk"]))
    t = time.time()
    B = fig_roundabout_video(out)
    print("  環状交差点の俯瞰の動画 %d コマ(%.1f s)、場面 #%d、コマの走査 %s" % (B["n"], time.time() - t, B["k"], B["chk"]))
    t = time.time()
    C = fig_mirror_video(out)
    mm = C["mm"]
    print("  カーブミラーの動画 %d コマ(%.1f s)、コマの走査 %s" % (C["n"], time.time() - t, C["chk"]))
    for m in C["meas"][::max(1, len(C["meas"]) // 12)]:
        print("    t %.1f s  鏡から %.1f m  鏡の中の車 %d × %d px(頂点の光線追跡 %.1f × %.1f px)  直接の画素 %d  %s" % (
            m["t"], m["a"], m["mrow"], m["mcol"], m["brow"], m["bcol"], m["direct"], m["state"]))
    err = [abs(m["mrow"] - m["brow"]) / m["brow"] for m in mm]
    print("    鏡の中の車の高さ: 描いた画素 / 頂点の厳密な光線追跡 —— %d コマで相対のずれ 最大 %.2f・中央値 %.2f" % (
        len(mm), max(err) if err else math.nan, float(np.median(err)) if err else math.nan))
    gate("鏡の中の像(環境の画像を反射で引いて視差補正)の車の高さ = メッシュの頂点の厳密な光線追跡(8 px 以上のコマ、±(2 px + 6 %))",
         len(mm) >= 5 and all(abs(m["mrow"] - m["brow"]) <= 2 + 0.06 * m["brow"] for m in mm), "%d コマ、最大 %.2f" % (len(mm), max(err) if err else -1))
    rd = np.array([m["read"] / (M_["k_s"] * m["a"]) for m in mm if "read" in m]) if (M_ := out["mirror"]) else np.array([])
    print("    画素で読んだ距離(平面鏡の像との高さの比)/ Coddington の縦の読み k_s·a: %d コマで %.2f〜%.2f(中央値 %.2f)" % (
        rd.size, rd.min(), rd.max(), float(np.median(rd))))
    gate("描いた鏡の像の画素から読んだ距離(平面鏡の像との高さの比)= Coddington の縦の読み k_s·a(±10 %、近軸の k·a とは別の値)",
         rd.size >= 5 and float(np.max(np.abs(rd - 1.0))) <= 0.10, "%.2f〜%.2f" % (rd.min(), rd.max()))
    states = [m["state"] for m in C["meas"]]
    order = {"鏡に映っている": 0, "鏡にも映らず、直接も見えない": 1, "直接見える(鏡にはもう映らない)": 2}
    seq = [order[s_] for s_ in states]
    gate("動画の状態の順: 鏡に映る → (どちらにも映らない)→ 直接見える と戻らない、車が遠い間(12 m より右)は直接の画素 0(塀の陰)",
         seq[0] == 0 and seq[-1] == 2 and all(b_ >= a_ for a_, b_ in zip(seq, seq[1:]))
         and all(m["direct"] == 0 for m in C["meas"] if m["yc"] < -12.0), "状態の列 %s" % "".join(str(v) for v in seq))
    allok = A["chk"]["ok"] and B["chk"]["ok"] and C["chk"]["ok"]
    still = max(A["chk"]["still"] / A["n"], B["chk"]["still"] / B["n"], C["chk"]["still"] / C["n"])
    gate("動画 3 本の全コマの数値走査: 空・真っ黒・真っ白・定数のコマが無く、前のコマと同じコマ ≤ 10 %", allok and still <= 0.10,
         "同じコマの割合 最大 %.2f" % still)
    t = time.time()
    fig_static(out)
    print("  静止図(%.1f s)" % (time.time() - t))



if __name__ == "__main__":
    sys.exit(main())
