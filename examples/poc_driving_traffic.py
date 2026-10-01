# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉙(自動運転 第 8 回): 動く交通参加者と死角 —— 路肩駐車の陰から出る子ども、すれ違いの隙間、停車中のバス、
下手な運転の車列、横断歩道で待つ人、稀な飛び出し、ふらつく自転車を、閉形式と独立な経路で採点する。

著者の発案: 「自動運転は歩行者とか外乱要素がまだまだ足りない」「自転車とかも道路上では走ってるよ」「路肩駐車してる車もいる」
「下手くそな運転してる奴もいる」「頻度は多くないけど、飛び出す奴や横切る奴もいる」「路肩駐車のある場合、対向車とのすれ違いの
タイミングを考えないといけない」「バス停車中は人の乗り降りが多く飛び出してくる人がいやすいので、追い越しは注意がいる。出来れば
発車まで待つほうが良い」「歩道で待つ人がいれば一時停止」。これまでの世界は止まっているか自車だけが動いていた。ここでは他の参加者が
動き、しかも見えない所から出てくる(部品は :mod:`drivetraffic`)。

門(真値の出どころ):
  1. **死角の見え始め**: 駐車車両の角を通る視線の閉形式(occlusion_reveal_distance)と、自車を細かく進めて視線と箱の交わりを
     自前の Liang–Barsky で調べた見え始めが、45 個の候補の全部で刻み以内。歩道の上の子は「見え → 隠れ → 見える」で、
     occlusion_visible_intervals の 2 区間が 1 cm ごとの自前の視線判定と一致。
  2. **止まれる速さ**: 隠れ場所の最悪の候補から決めた方針の速さ(occlusion_safe_speed)なら、乱数の飛び出し(位置・速さ・出る時刻)と
     立ったまま隠れている子(候補 45 点)の全試行で歩行者の手前に止まる。停止距離は drivelong.long_simulate の積分(閉形式と別の経路)。
     1.3 倍の速さだと止まれない試行が出る。
  3. **すれ違い**: passing_simulate で PET = PET_min になる対向車の距離(二分法)と閉形式 D* が rel 1e-6(30 km/h と徐行)。
  4. **待ち時間**: 対向車がポアソン流(poisson_events)のとき、隙間 τ = D*/v_on を待つ平均時間 = Adams の式 (e^{qτ} − 1 − qτ)/q、
     待たずに行ける確率 = e^{−qτ}(4.5 SE)。
  5. **バス停**: 出現率 λ(x, t)(bus_stop_rate × 停車中)の下で「止まれない帯」に入る出現の期待件数 Λ を erf の閉形式 + 時間の
     数値積分で出し、時空のポアソン過程(poisson_events_xt、格子で上限を事前検査)の MC と 4.5 SE で一致(3 方針)。待つ < 徐行で追い越す < そのまま追い越す、既定は待つ。
  6. **下手な運転の車列**: 同じ減速(10 → 8 m/s)に、careful・normal の車列は平衡車間 s_e(v)(閉形式)へ rtol 1e-3 で収束し、
     sloppy(反応遅れ > 車間時間)は振動が後ろへ育って追突する(idm_platoon_simulate は追突した車を接触の位置で止め、(時刻, 車番) を返す)。
  7. **危ない車の見分け**: 前の車の横ふらつきを 20 s 見て、ou_estimate(OU の厳密離散化の最尤)で拡散の強さ σ̂ を読むと sloppy(真値 = 付けた癖)を全部当て、
     careful・normal を 1 台も誤検出しない(位置の標本 SD では見分けられない = 印字)。見分けた車の後ろで車間時間を広げると、自車の最小 TTC が
     上がり(> 3 s)追突しない。
  8. **横断の意図**: 位置・向き・静止時間の規則で、H 秒以内に渡る人を全員止まる(見逃し 0)。沿って歩く人では止まらない。
     「縁で道を向いて止まっている」項を外すと見逃しが出る(門が自明でない証拠)。
  9. **稀な飛び出し**: poisson_events の件数の平均・分散 = ∫λ(5σ)。importance_risk_estimate は閉形式 1 − e^{−∫_W λ} と
     素朴な MC の両方に 4.5 SE で一致し、1 試行の分散が素朴な MC の 1/5 未満。
  10. **自転車**: lateral_wobble でふらつく自転車を、ou_estimate の σ̂ から追い越しの間 h に動ける幅 4.5 σ̂ √h(OU の h 秒のずれの SD ≤ σ√h、θ に依らない)を
      足した位置で追い越すと、全試行で側方間隔 ≥ C。足さないと C を割る試行が出る。C = 1.5 m は **この PoC で決めた値**(法の数値ではない)。
  11. **古典的な知覚**: 車載カメラの画像(world_camera)を、地図から同じ姿勢で描いた背景と引き算(背景差分、学習なし)して
      飛び出しに「気づいた時刻」を出す。真値(描画の面ラベルに歩行者が初めて写る時刻)からの遅れ ≤ 0.2 s、それより前の誤検知 0。
      検知を引き金にした閉ループで、歩行者の手前に止まる。
  12. **通し走行(俯瞰)**: 駐車車両・飛び出し・対向の車列・自転車・バスを 1 本の道に置いて方針どおりに走ると、どの参加者とも接触しない。

正直に書くこと:
* **仮定の値**: 運転の癖 3 種(careful / normal / sloppy の IDM の母数・反応遅れ・ふらつき)、歩行速度(既定 1.2 m/s、子どもが走る 1〜3 m/s)、
  自転車との側方間隔 1.5 m(この PoC で決めた値で、法の数値ではない)、反応 0.5 s、緊急制動 6 m/s²、余裕 0.2 m、子どもの体の半径 0.3 m、
  バス停の出現率、対向 600 台/時・40 km/h、自転車のふらつき(θ 0.4 /s、σ 0.12 m/√s)は **すべて仮定** で、一次情報で確かめた値は無い。
* **死角は 2D**(上から見た箱。目の高さ・ボンネット・子どもの背丈を持たない)で方針を決め、知覚の門は 3D の描画(子ども 1.1 m、目の高さ
  1.2 m)で測る —— 3D では立っている子の頭がボンネット越しに 2D より先に写る(full の実測: 走り出す 0.13 s 前、2D の視線より 0.5 s 早い)。
  つまり 2D の方針は 3D に対して **安全側**(より遅い速さを選ぶ)。2D の箱は無限に高い壁なので、3D が 2D より遅く見えることは無い(背の高い車ほど両者が近づく)。
* 歩道の上(駐車車両の幅の帯の外)の人は、遠くからは車と縁石の隙間越しに見え、近づくと隠れ、また見える(occlusion_visible_intervals)。
  隠れ場所の候補は車の幅の帯の中に限った(歩道の人は「見えていたら一時停止」の側で扱う)。
* 背景差分の背景は「地図から同じ姿勢で描いた絵」で、自己位置が正確という仮定に乗っている(雑音は足すが姿勢のずれは足さない)。
* はみ出しの判断は一定速度の点の車(加減速・中止の判断は持たない)。バスの「危険」は止まれない帯に入る出現の期待件数で、ぶつかるか
  どうかの横の運動は持たない。

教則の場面: S029, S039, S041, S042, S047, S053, S061, S088, S089, S159(docs/drive/kyosoku_scenarios.json、交通の方法に関する教則の再現台帳)

Run: py -3.11 examples/poc_driving_traffic.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。
FULLSEYE_POC_BUDGET=reduced(CI の既定)で試行数・動画の大きさとコマを減らす)
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
import drivetraffic as TR  # noqa: E402
import driveworld as DW  # noqa: E402
import driveterrain as DT  # noqa: E402
import drivelong as DL  # noqa: E402
import annotate as AN  # noqa: E402

#: 予算: reduced(CI の既定)は試行数を減らし、車載カメラを 320 × 180・15 fps に。展示の数字は full の実測。
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_TRIALS = 150 if REDUCED else 400            # 飛び出しの試行
N_WAIT = 4000 if REDUCED else 20000           # すれ違いの待ちの MC
N_BUS = 4000 if REDUCED else 20000            # バス停の MC
N_POIS = 8000 if REDUCED else 30000           # ポアソンの件数
N_NAIVE = 10000 if REDUCED else 40000         # 素朴な MC
N_IS = 1500 if REDUCED else 5000              # 重要度サンプリング
N_PED = 160 if REDUCED else 480               # 横断の意図の人数
N_BIKE = 100 if REDUCED else 300              # 自転車の追い越し
CAM_WH = (320, 180) if REDUCED else (640, 360)
CAM_FPS = 15.0 if REDUCED else 30.0
T0 = time.time()
OK = []

# ── 仮定の値(すべて仮定。一次情報で確かめたものは無い) ──
RHO = 0.5            # 自動運転の反応(知覚 + 判断 + 作動)[s]
B_EMG = 6.0          # 緊急制動 [m/s²](乾いた路面)
V_CRUISE = 30.0 / 3.6
EYE_BACK = 1.5       # 前端からカメラ(目)まで [m]
EYE_Z = 1.2          # 目の高さ [m]
EGO_W = 1.8
EGO_L = 4.5
Y_LANE = 1.75        # 自車線の中心(左側通行、+x 向きの車線は y ∈ [0, 3.5])
Y_PASS = -0.4        # 駐車車両の横を抜けるときの自車の中心(駐車車両と横 1.0 m)
KERB = 3.5
EYE_START = 50.0 - 4.5 / 2 - 10.0 - EYE_BACK   # 試行と閉形式の目の出発点(駐車車両の後端の 10 m 手前に前端)
CAR = (50.0, 2.4, 4.5, 1.8, 0.0)       # 路肩駐車: 中心 (50, 2.4)、4.5 × 1.8 → 内側の面 y = 1.5
R_PED = 0.3          # 歩行者の体の半径(手前に止まる余白)
MARGIN = 0.2         # 方針の余裕 [m]
ZONE_DX = (2.0, 6.0)  # 隠れ場所: 駐車車両の前端から前へ 2〜6 m
ZONE_Y = (2.0, 3.2)   # 車の陰(駐車車両の幅の帯の中、車道の上)
C_BIKE = 1.5         # 自転車との側方間隔(この PoC で決めた値。法の数値ではない)
DET_THR_SIGMA = 6.0  # 背景差分のしきい値(雑音 σ の倍数)
DET_MIN_PX = 6       # 検知とみなす画素数(孤立点を除いた後)
NOISE = 0.01         # 画像の雑音 σ(0〜1 の明るさ)

JP = {  # 画面に出す判断(英語の内部名は出さない)
    "cruise": "巡航", "slow": "死角の手前で徐行", "zone": "徐行(死角の横)", "seen": "見えた → 反応",
    "brake": "緊急制動", "stopped": "停止 → 横断を待つ", "go": "発進", "wait_oncoming": "対向車を待つ",
    "pass": "はみ出して追い越し", "follow": "追従", "wait_bus": "バスの発車を待つ", "bike": "自転車の後ろ",
}


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


# ───────────────────────────── 幾何の下請け(drivetraffic と独立な経路) ─────────────────────────────
def visible(eye, pt, box, eps=1e-9):
    """視線 eye → pt が軸平行の箱 (cx, cy, L, W) の内部を通らないか(自前の Liang–Barsky、配列で)。

    drivetraffic.occlusion_reveal_distance(角を通る視線の閉形式)とは別の経路の判定。eye, pt は (N, 2)。"""
    eye = np.atleast_2d(np.asarray(eye, float))
    pt = np.atleast_2d(np.asarray(pt, float))
    cx, cy, L, W = box[:4]
    lo = np.array([cx - L / 2 + eps, cy - W / 2 + eps])
    hi = np.array([cx + L / 2 - eps, cy + W / 2 - eps])
    d = pt - eye
    t0 = np.zeros(len(d))
    t1 = np.ones(len(d))
    for k in (0, 1):
        dk = d[:, k]
        par = np.abs(dk) < 1e-300
        outside = par & ((eye[:, k] <= lo[k]) | (eye[:, k] >= hi[k]))
        with np.errstate(divide="ignore", invalid="ignore"):
            ta = np.where(par, -np.inf, (lo[k] - eye[:, k]) / dk)
            tb = np.where(par, np.inf, (hi[k] - eye[:, k]) / dk)
        t0 = np.maximum(t0, np.minimum(ta, tb))
        t1 = np.minimum(t1, np.maximum(ta, tb))
        t1 = np.where(outside, -1.0, t1)
    return ~(t1 - t0 > 1e-12)


def stop_distance_sim(v, reaction=RHO, brake=B_EMG):
    """反応 + 一定の制動の停止距離を drivelong.long_simulate(RK4、事象で刻みを切る)で積分する(閉形式と別の経路)。"""
    p = DL.long_params(c_rr=0.0, cda=0.0, a_brake_max=10.0, mu=1.2)
    cmd = (lambda t, s, vv: (0.0, 0.0) if t < reaction else (0.0, brake))
    r = DL.long_simulate(0.0, v, cmd, t_end=reaction + v / brake + 2.0, dt=0.005, params=p, t_breaks=[reaction])
    return [e for e in r["events"] if e[0] == "stop"][0][2]


def zone_candidates():
    dx = np.linspace(*ZONE_DX, 9)
    ys = np.linspace(*ZONE_Y, 5)
    xf = CAR[0] + CAR[2] / 2
    return np.array([[xf + a, b] for a in dx for b in ys])


def policy_speed():
    """隠れ場所の候補の最悪(前端から見え始めまでの余裕が最小)で、止まれる最大速度を決める。"""
    cands = zone_candidates()
    d_eye = np.array([TR.occlusion_reveal_distance((EYE_START, Y_PASS), 0.0, CAR, e) for e in cands])
    budget = d_eye - EYE_BACK - R_PED - MARGIN
    k = int(np.argmin(budget))
    v = TR.occlusion_safe_speed(float(budget[k]), reaction=RHO, brake=B_EMG)
    return {"v": float(v), "cands": cands, "d_eye": d_eye, "worst": cands[k], "budget": float(budget[k]),
            "reveal_front": cands[:, 0] - d_eye + EYE_BACK}


def reveal_by_stepping(e, step=0.002):
    """自車の目を step ずつ進め、自前の視線判定で初めて見える目の位置 → 縦距離(閉形式の門の相手)。"""
    xs = np.arange(EYE_START, e[0], step)
    eyes = np.column_stack([xs, np.full_like(xs, Y_PASS)])
    vis = visible(eyes, np.tile(e, (len(xs), 1)), CAR)
    k = int(np.argmax(vis))
    return e[0] - xs[k] if vis[k] else math.inf


# ───────────────────────────── 1. 死角からの飛び出し ─────────────────────────────
def scene_occlusion():
    print("== 1. 死角からの飛び出し: 路肩駐車の陰の子ども、止まれる最大速度")
    POL = policy_speed()
    errs = [abs(reveal_by_stepping(e) - d) for e, d in zip(POL["cands"], POL["d_eye"])]
    print("  隠れ場所の候補 %d(前端から %.0f〜%.0f m 先、y %.1f〜%.1f m): 見え始めの縦距離 %.2f〜%.2f m(目から)" % (
        len(POL["cands"]), ZONE_DX[0], ZONE_DX[1], ZONE_Y[0], ZONE_Y[1], POL["d_eye"].min(), POL["d_eye"].max()))
    gate("死角の見え始め: 角を通る視線の閉形式 = 目を 2 mm ずつ進めた自前の視線判定(%d 候補、差 ≤ 刻み)" % len(errs),
         max(errs) <= 0.002 + 1e-9, "最大の差 %.1e m" % max(errs))
    v_pol = POL["v"]
    s_pol = stop_distance_sim(v_pol)
    print("  最悪の候補 (%.2f, %.2f): 目から %.2f m で見え始め → 前端の余裕 %.2f m(体 %.1f + 余裕 %.1f を引いた後)→ 止まれる最大速度 "
          "%.2f m/s = %.1f km/h(反応 %.1f s、制動 %.0f m/s²。積分した停止距離 %.4f m)" % (
              POL["worst"][0], POL["worst"][1], POL["d_eye"].min(), POL["budget"], R_PED, MARGIN, v_pol, 3.6 * v_pol, RHO,
              B_EMG, s_pol))
    # 試行: 隠れ場所・走る速さ・走り出す時刻を乱数に。自車は方針の速さ(一定)で近づく
    rng = np.random.default_rng(29)
    xf = CAR[0] + CAR[2] / 2
    X_START = CAR[0] - CAR[2] / 2 - 10.0               # 前端の出発点(駐車車両の後端の 10 m 手前)
    dt = 0.005
    trials = []
    for _ in range(N_TRIALS):
        xp = xf + rng.uniform(*ZONE_DX)
        y0 = rng.uniform(*ZONE_Y)
        u = rng.uniform(1.0, 3.0)                      # 歩く〜走る子ども(縁石の向こうから車道を横切る向き)
        trials.append((xp, y0, u, rng.uniform(0.0, 1.0)))
    trials += [(e[0], e[1], 0.0, 0.0) for e in POL["cands"]]      # 立ったまま隠れている子(候補 45 点)も試行に入れる
    res = {}
    for mult in (1.0, 1.3):
        v = v_pol * mult
        s_stop = stop_distance_sim(v)
        gaps, n_late = [], 0
        for xp, y0, u, frac in trials:
            T_arr = (xp - X_START) / v
            ts = max(0.0, (xp - 12.0 * frac - X_START) / v)   # 自車の前端が子どもの線の 12 m 手前〜目の前に来た時に走り出す
            t = np.arange(0.0, T_arr, dt)
            front = X_START + v * t
            eye = np.column_stack([front - EYE_BACK, np.full_like(t, Y_PASS)])
            py = np.maximum(y0 - u * np.maximum(0.0, t - ts), -5.0)
            ped = np.column_stack([np.full_like(t, xp), py])
            vis = visible(eye, ped, CAR)
            if not vis.any():
                n_late += 1
                continue
            k = int(np.argmax(vis))
            gaps.append(xp - R_PED - (front[k] + s_stop))
        res[mult] = (np.array(gaps), n_late, s_stop)
    g1, nl1, _ = res[1.0]
    g13, _, s13 = res[1.3]
    gate("止まれる速さ: 方針の %.1f km/h なら、乱数の飛び出し + 立ったまま隠れる子の %d 試行の全部で歩行者(体 %.1f m)の手前に止まる"
         "(停止距離は long_simulate)" % (3.6 * v_pol, len(g1), R_PED), len(g1) == len(trials) - nl1 and len(g1) > 0 and g1.min() >= 0.0,
         "最小の余白 %.3f m、見えないまま着いた試行 %d" % (g1.min(), nl1))
    gate("門が自明でない: 1.3 倍の %.1f km/h だと止まれない試行が出る" % (3.6 * 1.3 * v_pol), (g13 < 0).sum() > 0,
         "%d / %d 試行で歩行者の線を越える(最悪 %.2f m、停止距離 %.2f m)" % ((g13 < 0).sum(), len(g13), -g13.min(), s13))
    # 横の間隔を変えると止まれる速さがどう変わるか(図と印字)
    lat = []
    for y_e in np.linspace(0.6, -1.6, 12):
        d = min(TR.occlusion_reveal_distance((EYE_START, y_e), 0.0, CAR, e) for e in POL["cands"])
        lat.append((CAR[1] - CAR[3] / 2 - (y_e + EGO_W / 2), 3.6 * TR.occlusion_safe_speed(max(0.0, d - EYE_BACK - R_PED - MARGIN),
                                                                                         reaction=RHO, brake=B_EMG)))
    print("  駐車車両との横の間隔 → 止まれる最大速度: %s" % ", ".join("%.1f m → %.1f km/h" % r for r in lat[::3]))
    # 歩道の上(車の幅の帯の外)の子は「見え → 隠れ → 見える」: occlusion_visible_intervals と自前の視線判定を 1 cm ごとに比べる
    e_sw = (CAR[0] + CAR[2] / 2 + 2.5, 4.0)
    s0 = -60.0
    iv = TR.occlusion_visible_intervals((s0, Y_PASS), 0.0, CAR, e_sw, e_sw[0] - s0)
    ss = np.arange(0.0, e_sw[0] - s0, 0.01)
    vis = visible(np.column_stack([s0 + ss, np.full_like(ss, Y_PASS)]), np.tile(e_sw, (len(ss), 1)), CAR)
    near_end = np.array([min(abs(x - b) for ab in iv for b in ab) < 0.01 for x in ss])
    inside = np.array([any(a <= x <= b for a, b in iv) for x in ss])
    mism = int(np.sum((inside != vis) & ~near_end))
    print("  歩道の子 (%.2f, %.1f) を目の x = %.0f から: 見える区間 %s(目の x)" % (
        e_sw[0], e_sw[1], s0, ", ".join("%.2f〜%.2f" % (s0 + a, s0 + b) for a, b in iv)))
    gate("歩道の子は「見え → 隠れ → 見える」: occlusion_visible_intervals の 2 区間 = 1 cm ごとの自前の視線判定(端の 1 cm を除き不一致 0)",
         len(iv) == 2 and mism == 0, "隠れている区間 %.2f m" % (iv[1][0] - iv[0][1] if len(iv) == 2 else float("nan")))
    return {"POL": POL, "v_pol": v_pol, "lat": lat, "g1": g1, "g13": g13, "X_START": X_START}


# ───────────────────────────── 2. 対向車とのすれ違い ─────────────────────────────
def adams_wait(q, tau):
    return (math.exp(q * tau) - 1.0 - q * tau) / q


def scene_passing(v_pol):
    print("== 2. 対向車とのすれ違い: 駐車車両を避けてはみ出す境目と待ち時間")
    V_ON = 40.0 / 3.6
    geo = dict(parked_len=4.5, margin_front=3.0, margin_back=5.0)
    rows, errs = [], []
    for name, ve in (("30 km/h", V_CRUISE), ("徐行 %.1f km/h" % (3.6 * v_pol), v_pol)):
        kw = dict(lane_change_time=2.0, ego_length=EGO_L)
        req = TR.passing_gap_required(geo["parked_len"], geo["margin_front"], geo["margin_back"], ve, V_ON, pet_min=1.0, **kw)
        Ds = req["d_required"]
        # 独立な経路: passing_simulate の PET が 1.0 s になる距離を二分法で
        lo, hi = 0.5 * Ds, 2.0 * Ds
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            pet = TR.passing_simulate(mid, geo["parked_len"], geo["margin_front"], geo["margin_back"], ve, V_ON, dt=0.01, **kw)["pet"]
            lo, hi = (mid, hi) if pet < 1.0 else (lo, mid)
        D_sim = 0.5 * (lo + hi)
        flip = (TR.passing_decision(Ds * (1 - 1e-9), geo["parked_len"], geo["margin_front"], geo["margin_back"], ve, V_ON, pet_min=1.0, **kw),
                TR.passing_decision(Ds * (1 + 1e-9), geo["parked_len"], geo["margin_front"], geo["margin_back"], ve, V_ON, pet_min=1.0, **kw))
        errs.append(abs(D_sim - Ds) / Ds)
        rows.append((name, ve, Ds, D_sim, req["t_occupy"], flip))
        print("  %s: はみ出す時間 %.2f s、境目 D* = %.3f m(閉形式)/ %.3f m(PET = 1 s を二分法)、D*∓ で %s / %s" % (
            name, req["t_occupy"], Ds, D_sim, *flip))
    gate("すれ違い: passing_simulate の PET = 1 s の境目 = 閉形式 D*(2 条件、rel 1e-6)、D* の前後で wait / go が切り替わる",
         max(errs) < 1e-6 and all(r[5] == ("wait", "go") for r in rows), "最大 rel %.1e" % max(errs))
    # 待ち時間: 対向車の流れをポアソン(時刻の軸に poisson_events)、到着した瞬間から隙間 τ が来るまで
    q = 600.0 / 3600.0
    rng = np.random.default_rng(2929)
    waits = {}
    for name, ve, Ds, _, _, _ in rows:
        tau = Ds / V_ON
        horizon = 40.0 * tau + 400.0
        w = np.empty(N_WAIT)
        for i in range(N_WAIT):
            arr = TR.poisson_events(lambda x: np.full_like(x, q), horizon, rate_max=q, seed=rng)
            t_now, j = 0.0, 0
            while True:
                nxt = arr[j] if j < len(arr) else math.inf
                if nxt - t_now >= tau:
                    break
                t_now, j = nxt, j + 1
            w[i] = t_now
        se = w.std(ddof=1) / math.sqrt(N_WAIT)
        p0 = float(np.mean(w == 0.0))
        waits[name] = (tau, adams_wait(q, tau), float(w.mean()), se, p0, math.exp(-q * tau))
        print("  %s: 必要な隙間 τ = %.2f s、平均の待ち = %.2f s(Adams)/ %.2f ± %.2f s(MC %d 回)、待たずに行ける %.3f / e^{−qτ} %.3f" % (
            name, tau, waits[name][1], waits[name][2], se, N_WAIT, p0, waits[name][5]))
    ok = all(abs(m - a) < 4.5 * se and abs(p0 - pe) < 4.5 * math.sqrt(pe * (1 - pe) / N_WAIT) + 1e-12
             for tau, a, m, se, p0, pe in waits.values())
    gate("待ち時間: 対向 600 台/時のポアソン流で、平均の待ち = Adams の式、待たずに行ける確率 = e^{−qτ}(4.5 SE、2 条件)", ok,
         "; ".join("%s %.1f s" % (k, v[1]) for k, v in waits.items()))
    return {"rows": rows, "waits": waits, "q": q, "V_ON": V_ON}


# ───────────────────────────── 3. バス停 ─────────────────────────────
BUS = {"rear": 100.0, "front": 110.5, "base": 2e-5, "peak": 2e-3, "spread": 2.0, "t_dep": 15.0}


def bus_rate_xt(x, t):
    """λ(x, t) [件/(m·s)] = bus_stop_rate(x) × [t < 発車] + base(停車中は前後の山、発車後は一様だけ)。"""
    g = TR.bus_stop_rate(x, bus_rear=BUS["rear"], bus_front=BUS["front"], base=0.0, peak=BUS["peak"], spread=BUS["spread"])
    return BUS["base"] + g * (np.asarray(t) < BUS["t_dep"])


def bus_band_rate(x0, x1, t):
    """∫_{x0}^{x1} λ(x, t) dx の閉形式(ガウス 2 つの erf + 一様)。λ = bus_stop_rate × [t < 発車] + base × [t ≥ 発車]。"""
    b = BUS
    base = b["base"] * (x1 - x0)
    if t >= b["t_dep"]:
        return base
    s = b["spread"] * math.sqrt(2.0)
    g = 0.0
    for c in (b["rear"], b["front"]):
        g += b["spread"] * math.sqrt(math.pi / 2.0) * (math.erf((x1 - c) / s) - math.erf((x0 - c) / s))
    return base + b["peak"] * g


def bus_policy(name):
    """方針ごとの自車の前端の軌跡(時刻の配列と位置)。歩行者は止まれない帯 [前端, 前端 + 停止距離] に出ると危ない。"""
    if name == "wait":           # 発車まで待ち(後ろで停止)、発車後 30 km/h で通過
        t = np.linspace(0.0, BUS["t_dep"] + 8.0, 4001)
        x = np.where(t < BUS["t_dep"], BUS["rear"] - 3.0, BUS["rear"] - 3.0 + V_CRUISE * (t - BUS["t_dep"]))
        v = np.where(t < BUS["t_dep"], 0.0, V_CRUISE)
    else:
        vv = 10.0 / 3.6 if name == "slow" else V_CRUISE
        t = np.linspace(0.0, (BUS["front"] + 25.0 - (BUS["rear"] - 15.0)) / vv, 4001)
        x = BUS["rear"] - 15.0 + vv * t
        v = np.full_like(t, vv)
    return t, x, v


def scene_bus():
    print("== 3. バス停: 停車中は前後から人が出てくる。発車まで待つ / 徐行で追い越す / そのまま追い越す")
    out = {}
    rng = np.random.default_rng(303)
    X_MAX = 160.0
    for name in ("wait", "slow", "fast"):
        t, x, v = bus_policy(name)
        s = v * RHO + v * v / (2 * B_EMG)                   # 止まれない帯の長さ(閉形式、v = 0 なら 0)
        dens = np.array([bus_band_rate(xi, xi + si, ti) for ti, xi, si in zip(t, x, s)])
        Lam = float(np.trapezoid(dens, t)) if hasattr(np, "trapezoid") else float(np.trapz(dens, t))
        # MC: 時空のポアソン過程 λ(x, t) を poisson_events_xt で直接引く(格子 161 × 31 で上限を事前に検査)
        T_end = float(t[-1])
        n_hit = np.empty(N_BUS)
        for i in range(N_BUS):
            ev = TR.poisson_events_xt(bus_rate_xt, X_MAX, T_end, rate_max=BUS["base"] + 2 * BUS["peak"], seed=rng, n_grid=(161, 31))
            ex, et = ev[:, 0], ev[:, 1]
            xe = np.interp(et, t, x)
            se = np.interp(et, t, s)
            n_hit[i] = np.sum((ex >= xe) & (ex <= xe + se))
        m, sd = float(n_hit.mean()), float(n_hit.std(ddof=1)) / math.sqrt(N_BUS)
        wait = BUS["t_dep"] if name == "wait" else 0.0
        out[name] = (Lam, m, sd, wait, 1.0 - math.exp(-Lam), float(np.mean(n_hit > 0)))
        print("  %-4s: 止まれない帯に入る出現の期待件数 Λ = %.5f(erf + 時間の積分)/ %.5f ± %.5f(MC %d 回)、P(1 件以上) %.4f、待ち %.0f s" % (
            {"wait": "待つ", "slow": "徐行", "fast": "30km"}[name], Lam, m, sd, N_BUS, 1 - math.exp(-Lam), wait))
    gate("バス停: 期待件数 Λ の閉形式 = 時空のポアソン過程(poisson_events_xt)の MC(3 方針、4.5 SE)",
         all(abs(v[0] - v[1]) < 4.5 * v[2] + 1e-12 for v in out.values()))
    choice = "wait" if out["wait"][0] < out["slow"][0] else "slow"
    gate("バス停: 待つ < 徐行で追い越す < そのまま追い越す(期待される危険)。既定の判断は「発車まで待つ」",
         out["wait"][0] < out["slow"][0] < out["fast"][0] and choice == "wait",
         "Λ %.5f < %.5f < %.5f、待ちの代償 %.0f s" % (out["wait"][0], out["slow"][0], out["fast"][0], BUS["t_dep"]))
    return out


# ───────────────────────────── 4. 下手な運転の車列 ─────────────────────────────
def ttc_min(r, i):
    g = r["gap"][:, i]
    dv = r["v"][:, i] - r["v"][:, i - 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        ttc = np.where(dv > 1e-6, g / np.where(dv > 1e-6, dv, 1.0), np.inf)
    return float(ttc.min())


def scene_platoon():
    print("== 4. 下手な運転の車列: careful / normal / sloppy の 6 台に、先頭が 10 → 8 m/s に落とす")
    lead = lambda t: 10.0 if t < 5.0 else 8.0                                          # noqa: E731
    runs = {}
    for k in TR.DRIVER_KINDS:
        p = dict(TR.driver_style(k), speed_noise=0.0)
        r = TR.idm_platoon_simulate(lead, 5, params_per_vehicle=p, dt=0.05, t_end=120.0)
        se = TR.idm_equilibrium_gap(8.0, v0=p["v0"], T=p["T"], s0=p["s0"])
        rel = float(np.max(np.abs(r["gap"][-1, 1:] - se) / se))
        runs[k] = (r, se, rel)
        print("  %-7s: 反応 %.1f s / 車間時間 %.1f s → %s、最後の車間と平衡 s_e(8) = %.3f m の差 rel %.1e、速度の振れ(最後 10 s)%.3f m/s" % (
            k, p["reaction_delay"], p["T"], "追突 t = %.1f s" % r["collision_time"] if r["collision"] else "追突なし", se, rel,
            float(np.ptp(r["v"][-200:, 1:]))))
    gate("車列: careful・normal は平衡車間 s_e(v) = (s0 + vT)/√(1 − (v/v0)^δ) に rtol 1e-3 で収束、sloppy は振動が育って追突",
         all(not runs[k][0]["collision"] and runs[k][2] < 1e-3 for k in ("careful", "normal")) and runs["sloppy"][0]["collision"])
    # 見分け: 混ざった車列(乱数の癖)の横ふらつきを 20 s(10 Hz)見る。2 つの読み方:
    #   (a) 位置の標本 SD(定常 SD σ/√(2θ) の推定)—— sloppy は θ が小さく(相関 4 s)、20 s では標本が実質 5 個しかない
    #   (b) ou_estimate の σ̂(厳密離散化の最尤。拡散の強さ σ を 199 個の増分で読む)。φ̂ ≥ 1(平均へ戻って見えない)で
    #       読めなければ fail-closed で「危ない」側に倒す
    rng = np.random.default_rng(404)
    kinds = [TR.DRIVER_KINDS[int(i)] for i in rng.integers(0, 3, 60)]
    rows = []
    for j, k in enumerate(kinds):
        st = TR.driver_style(k, seed=1000 + j)
        w = TR.lateral_wobble(200, 0.1, theta=st["wobble_theta"], sigma=st["wobble_sigma"], seed=2000 + j)
        try:
            sig = TR.ou_estimate(w, 0.1)["sigma"]
        except ValueError:
            sig = math.inf                                    # 読めない = 危ない側(fail-closed)
        rows.append((k, float(w.std(ddof=1)), float(sig), st["wobble_sigma"]))
    thr_sd, thr = 0.18, 0.145
    res = {}
    for name, col, th in (("SD", 1, thr_sd), ("sigma", 2, thr)):
        flag = [r[col] > th for r in rows]
        res[name] = (sum(f and r[0] == "sloppy" for f, r in zip(flag, rows)), sum(f and r[0] != "sloppy" for f, r in zip(flag, rows)))
    n_s = sum(r[0] == "sloppy" for r in rows)
    rng_txt = lambda c: " / ".join("%s %.3f〜%.3f" % (k, min(r[c] for r in rows if r[0] == k), max(r[c] for r in rows if r[0] == k))  # noqa: E731
                                   for k in TR.DRIVER_KINDS)
    print("  (a) 位置の標本 SD [m]: %s → しきい値 %.2f で sloppy %d / %d、誤検出 %d" % (rng_txt(1), thr_sd, res["SD"][0], n_s, res["SD"][1]))
    n_unread = sum(1 for r in rows if not math.isfinite(r[2]))
    print("  (b) ou_estimate の σ̂ [m/√s]: %s → しきい値 %.3f で sloppy %d / %d、誤検出 %d(読めずに危ない側へ倒した %d 台)" % (
        rng_txt(2), thr, res["sigma"][0], n_s, res["sigma"][1], n_unread))
    tp, fp = res["sigma"]
    gate("危ない車の見分け: 横ふらつきから ou_estimate で読んだ σ̂ > %.3f で sloppy(真値 = 付けた癖)を全部当て、ほかを誤検出しない(%d 台、20 s)" % (thr, len(rows)),
         tp == n_s and fp == 0 and n_s > 0, "sloppy %d / %d、誤検出 %d(位置の SD だと %d / %d)" % (tp, n_s, fp, res["SD"][0], n_s))
    # 自車が sloppy の後ろ: 車間時間 1.5 s のままと 2.5 s に広げた場合
    lead2 = lambda t: 10.0 if t < 5.0 else (max(2.0, 10.0 - 2.0 * (t - 5.0)))         # noqa: E731
    ego = {}
    for T_e in (1.5, 2.5):
        ps = [dict(TR.driver_style("careful", seed=5), speed_noise=0.0), dict(TR.driver_style("sloppy", seed=6), speed_noise=0.0),
              dict(v0=13.9, T=T_e, a=1.4, b=2.0, s0=2.0 if T_e < 2 else 4.0, reaction_delay=0.3)]
        r = TR.idm_platoon_simulate(lead2, 3, params_per_vehicle=ps, dt=0.05, t_end=60.0)
        ego[T_e] = (ttc_min(r, 3), float(r["gap"][:, 3].min()), ttc_min(r, 2), r)
    print("  自車(反応 0.3 s)が sloppy の後ろ、先頭が 10 → 2 m/s に 2 m/s² で落とす: 車間時間 1.5 s → 最小 TTC %.2f s・最小車間 %.2f m /"
          " 2.5 s に広げる → %.2f s・%.2f m(sloppy 自身の最小 TTC %.2f s)" % (ego[1.5][0], ego[1.5][1], ego[2.5][0], ego[2.5][1], ego[2.5][2]))
    gate("車間を広げる: 見分けた sloppy の後ろで車間時間 2.5 s にすると、自車の最小 TTC が上がり(> 3 s)追突しない",
         ego[2.5][0] > ego[1.5][0] and ego[2.5][0] > 3.0 and ego[2.5][1] > 0,
         "TTC %.2f → %.2f s" % (ego[1.5][0], ego[2.5][0]))
    return {"runs": runs, "rows": rows, "thr": thr, "ego": ego, "res": res}


# ───────────────────────────── 5. 横断の意図 ─────────────────────────────
def judge_cross(xy, heading, dt, H, use_dwell=True):
    """観測(最近 1 s の位置と向き、雑音つき)から「H 秒以内に車道に入る」と判断するか(止まるか)。規則だけ、学習なし。

    * 動いている(速さ > 0.3 m/s)で、向きが車道へ(+π/2 ± 45°)、縁 y = −0.3 に着くまでの時間 ≤ H → 止まる。
    * 1 s の平均では止まっていて、縁から 1 m 以内で車道を向き、最近 0.5 s で離れていく途中でない → 止まる(歩道で待つ人が
      いれば一時停止。待ちから動き出した瞬間も 1 s 平均では「止まっている」側に入るので、ここで拾う)。"""
    v = (xy[-1] - xy[0]) / (dt * (len(xy) - 1))
    sp = float(np.hypot(*v))
    y = float(xy[-1, 1])
    toward = abs(((float(heading[-1]) - math.pi / 2) + math.pi) % (2 * math.pi) - math.pi) < math.pi / 4
    if sp > 0.3:
        hd = math.atan2(v[1], v[0])
        mv_toward = abs(((hd - math.pi / 2) + math.pi) % (2 * math.pi) - math.pi) < math.pi / 4
        if mv_toward and toward and (-0.3 - y) / max(v[1], 1e-6) <= H + 0.5:     # 0.5 s の安全側の余裕
            return True
        return y > -0.3 and mv_toward
    if not use_dwell:
        return False
    v_recent = (xy[-1] - xy[-6]) / (5 * dt)                                 # 最近 0.5 s(止まっている / 動き出した)
    return y > -1.3 and toward and v_recent[1] > -0.3                       # 縁の近くで道を向き、離れていく途中でない


def scene_intent():
    print("== 5. 横断歩道の手前の歩行者の意図: 位置・向き・静止時間の規則で止まるか決める")
    rng = np.random.default_rng(505)
    H = 3.0
    dt = 0.1
    recs = []
    kinds = ("cross", "wait_then_cross", "walk_along", "stand")
    for i in range(N_PED):
        kind = kinds[i % 4]
        y0 = -rng.uniform(1.0, 4.0)
        sp = rng.uniform(0.9, 1.6)
        if kind == "walk_along":
            y0 = -rng.uniform(0.5, 2.5)
            tr = TR.pedestrian_crossing("walk_along", start_xy=(0.0, y0), speed=sp, along_heading=float(rng.choice([0.0, math.pi])),
                                        dt=dt, t_end=12.0)
        elif kind == "stand":            # 縁で道を向いて立つが渡らない(バス待ち・連れ待ち)
            tr = TR.pedestrian_crossing("stand_no_cross", start_xy=(0.0, y0), speed=sp, dt=dt, t_end=12.0)
        else:
            tr = TR.pedestrian_crossing(kind, start_xy=(0.0, y0), speed=sp, wait_time=rng.uniform(1.0, 6.0), dt=dt, t_end=20.0)
        K = len(tr["t"])
        k_end = K - 1 if tr["t_cross_end"] is None else min(K - 1, int(tr["t_cross_end"] / dt) - 1)   # 渡り終えた後は数えない
        k = int(rng.integers(10, max(11, min(k_end, int(12.0 / dt)))))
        xy = tr["xy"][k - 10:k + 1] + rng.normal(0.0, 0.05, (11, 2))
        hd = tr["heading"][k - 10:k + 1] + rng.normal(0.0, math.radians(10.0), 11)
        t_now = tr["t"][k]
        tcs = tr["t_cross_start"]
        truth = (tcs is not None) and (tcs <= t_now + H) and (tr["t_cross_end"] > t_now)
        recs.append((kind, truth, judge_cross(xy, hd, dt, H), judge_cross(xy, hd, dt, H, use_dwell=False)))
    truth = np.array([r[1] for r in recs])
    dec = np.array([r[2] for r in recs])
    dec_nd = np.array([r[3] for r in recs])
    miss = int(np.sum(truth & ~dec))
    miss_nd = int(np.sum(truth & ~dec_nd))
    fp_along = int(sum(r[2] and not r[1] for r in recs if r[0] == "walk_along"))
    fp_stand = int(sum(r[2] and not r[1] for r in recs if r[0] == "stand"))
    fp_other = int(sum(r[2] and not r[1] for r in recs if r[0] in ("cross", "wait_then_cross")))
    agree = float(np.mean(truth == dec))
    print("  %d 人(4 種 × %d)、判断の時刻は乱数、位置の雑音 5 cm・向きの雑音 10°、H = %.0f s: 一致率 %.3f、見逃し %d、誤って止まる %d"
          "(沿って歩く %d / 縁で立つだけの人 %d / 渡る人の待ちが H より長い %d)" % (
              len(recs), len(recs) // 4, H, agree, miss, int(np.sum(~truth & dec)), fp_along, fp_stand, fp_other))
    gate("横断の意図: H 秒以内に渡る人は全員止まる(見逃し 0)、沿って歩く人では止まらない", miss == 0 and fp_along == 0 and truth.sum() > 0,
         "渡る %d 人、一致率 %.3f" % (int(truth.sum()), agree))
    gate("門が自明でない: 「縁で道を向いて止まっている」項を外すと見逃しが出る", miss_nd > 0, "見逃し %d 人" % miss_nd)
    # 混同行列(真値 4 種 × 判断)
    cm = {k: (sum(1 for r in recs if r[0] == k and r[2]), sum(1 for r in recs if r[0] == k and not r[2])) for k in kinds}
    cmt = {(a, b): int(np.sum((truth == a) & (dec == b))) for a in (True, False) for b in (True, False)}
    return {"cm": cm, "cmt": cmt, "agree": agree, "miss": miss, "miss_nd": miss_nd, "fp_stand": fp_stand, "n": len(recs), "H": H}


# ───────────────────────────── 6. 稀な飛び出し ─────────────────────────────
def scene_rare():
    print("== 6. 稀な飛び出し: 出現の件数 = ∫λ、事故確率を重要度サンプリングで")
    rate = lambda x: TR.bus_stop_rate(x, bus_rear=900.0, bus_front=910.5, base=5e-4, peak=2e-3, spread=3.0)  # noqa: E731
    X = 2000.0
    rmax = 5e-4 + 2 * 2e-3
    xg = np.linspace(0.0, X, 200001)
    Lam = float(np.trapezoid(rate(xg), xg)) if hasattr(np, "trapezoid") else float(np.trapz(rate(xg), xg))
    Lam_cf = 5e-4 * X + 2e-3 * 3.0 * math.sqrt(2 * math.pi) * 2
    rng = np.random.default_rng(606)
    n = np.array([len(TR.poisson_events(rate, X, rate_max=rmax, seed=rng)) for _ in range(N_POIS)])
    m, v = float(n.mean()), float(n.var(ddof=1))
    se_m = math.sqrt(Lam_cf / N_POIS)
    se_v = math.sqrt((Lam_cf + 2 * Lam_cf ** 2) / N_POIS)
    print("  2 km の道、バス停 1 つ: ∫λ = %.4f(閉形式)/ %.4f(数値積分)、件数の平均 %.4f・分散 %.4f(%d 本)" % (Lam_cf, Lam, m, v, N_POIS))
    gate("ポアソン: 件数の平均 = 分散 = ∫λ(5σ)", abs(m - Lam_cf) < 5 * se_m and abs(v - Lam_cf) < 5 * se_v and abs(Lam - Lam_cf) < 1e-6,
         "平均 %.3f σ、分散 %.3f σ" % ((m - Lam_cf) / se_m, (v - Lam_cf) / se_v))
    W = (902.0, 905.0)          # 止まれない窓(この区間に出たら間に合わない、という仮定の窓)
    s2 = 3.0 * math.sqrt(2.0)
    Lam_w = 5e-4 * (W[1] - W[0]) + sum(2e-3 * 3.0 * math.sqrt(math.pi / 2) * (math.erf((W[1] - c) / s2) - math.erf((W[0] - c) / s2))
                                       for c in (900.0, 910.5))
    pw = 1.0 - math.exp(-Lam_w)
    sim = lambda ev, r: float(np.any((ev >= W[0]) & (ev <= W[1])))                     # noqa: E731
    boost = lambda x: rate(x) * np.where((x > W[0] - 2) & (x < W[1] + 2), 40.0, 1.0)  # noqa: E731
    t = time.time()
    naive = TR.importance_risk_estimate(sim, rate, rate, N_NAIVE, 61, x_max=X, boosted_rate_max=rmax)
    t_n = time.time() - t
    t = time.time()
    isr = TR.importance_risk_estimate(sim, rate, boost, N_IS, 62, x_max=X, boosted_rate_max=40 * rmax)
    t_i = time.time() - t
    print("  事故確率(窓 %.0f〜%.0f m に出る): 閉形式 %.5f / 素朴な MC %.5f ± %.5f(%d 本、%.1f s)/ 重要度 %.5f ± %.5f(%d 本、%.1f s、"
          "重みの平均 %.3f)" % (W[0], W[1], pw, naive["estimate"], naive["std_error"], N_NAIVE, t_n, isr["estimate"], isr["std_error"], N_IS,
                           t_i, isr["mean_weight"]))
    gate("重要度サンプリング: 閉形式と素朴な MC の両方に 4.5 SE で一致し、1 試行の分散が素朴の 1/5 未満",
         abs(isr["estimate"] - pw) < 4.5 * isr["std_error"] and abs(naive["estimate"] - pw) < 4.5 * naive["std_error"]
         and isr["per_run_var"] < naive["per_run_var"] / 5,
         "分散の比 %.1f 倍、同じ SE に要る本数 %.0f 分の 1" % (naive["per_run_var"] / isr["per_run_var"], naive["per_run_var"] / isr["per_run_var"]))
    return {"pw": pw, "naive": naive, "is": isr}


# ───────────────────────────── 7. 自転車 ─────────────────────────────
BIKE = {"y": KERB - 0.75, "half": 0.3, "len": 1.8, "v": 4.0, "theta": 0.4, "sigma": 0.12}


def bike_sigma(obs, dt):
    """観測した横ふらつきから σ̂ を ou_estimate で読む。φ̂ ≥ 1(短い観測で平均へ戻って見えない)なら、θ を使わない
    増分の推定 √(mean(Δx²)/dt)(ou_estimate の sigma_increment と同じ式。E[Δx²] = σ²(1−φ)/θ ≤ σ² dt なので σ を
    小さめに読む向き —— 余裕 k を 4.5 と大きめに取っているのはこのため)。"""
    try:
        return float(TR.ou_estimate(obs, dt)["sigma"])
    except ValueError:
        return float(np.sqrt(np.mean(np.diff(obs) ** 2) / dt))


def bike_allowance(sig_hat, h, k=4.5):
    """追い越しの間(h 秒)に自転車が今の位置から横に動ける幅の上限 k σ̂ √h。

    OU の h 秒後のずれの SD は SD_∞ √(1 − e^{−2θh}) ≤ σ √h(θ に依らない)なので、σ だけ測れば足りる。σ は増分の 2 乗平均から
    精度よく読める(θ は長い観測が要る)。k = 4.5 は「h の間の最大」まで含めた余裕(反射原理で 2·P(Z > 4.5) ≈ 7e-6)。"""
    return k * sig_hat * math.sqrt(h)


def scene_bike():
    print("== 7. 自転車: 車道の左端をふらつきながら走る自転車を追い越す(側方間隔 %.1f m は PoC で決めた値、法の数値ではない)" % C_BIKE)
    sd_true = BIKE["sigma"] / math.sqrt(2 * BIKE["theta"])
    dt = 0.05
    v_rel = V_CRUISE - BIKE["v"]
    n_obs, n_lat = int(5.0 / dt), int(2.0 / dt)                        # 後ろで 5 s 見る → 2 s で横へ寄る → 重なる区間
    n_ov = int(math.ceil((EGO_L + BIKE["len"] + 2.0) / v_rel / dt))
    h = (n_lat + n_ov) * dt
    out, allow, n_fb = {}, [], 0
    for k_sd in (4.5, 0.0):
        mins = []
        for i in range(N_BIKE):
            w = TR.lateral_wobble(n_obs + n_lat + n_ov + 5, dt, theta=BIKE["theta"], sigma=BIKE["sigma"], seed=7000 + i)
            sig_hat = bike_sigma(w[:n_obs], dt)
            if k_sd > 0:
                try:
                    TR.ou_estimate(w[:n_obs], dt)
                except ValueError:
                    n_fb += 1
            a = bike_allowance(sig_hat, h, k_sd)
            if k_sd > 0:
                allow.append(a)
            y_ego = BIKE["y"] + w[n_obs - 1] - BIKE["half"] - C_BIKE - a - EGO_W / 2     # 決めた時の自転車の位置から
            seg = w[n_obs + n_lat:n_obs + n_lat + n_ov]
            gap = (BIKE["y"] + seg - BIKE["half"]) - (y_ego + EGO_W / 2)
            mins.append(float(gap.min()))
        mins = np.array(mins)
        out[k_sd] = mins
        print("  余裕 %.1f σ̂√h(h = %.1f s): 側方間隔の最小 %.3f m(%d 試行のうち %.1f m 未満 %d)" % (
            k_sd, h, mins.min(), N_BIKE, C_BIKE, int(np.sum(mins < C_BIKE))))
    print("  余裕の幅 %.2f〜%.2f m(定常 SD %.3f m の 5 倍 = %.2f m と比べて)。5 s では φ̂ ≥ 1 で ou_estimate が読めず増分の推定に倒した試行 %d / %d" % (
        min(allow), max(allow), sd_true, 5 * sd_true, n_fb, N_BIKE))
    gate("自転車: ou_estimate で読んだ σ̂ で余裕 4.5 σ̂ √h を足して追い越すと、全試行で側方間隔 ≥ %.1f m" % C_BIKE, out[4.5].min() >= C_BIKE,
         "最小 %.3f m" % out[4.5].min())
    gate("門が自明でない: 余裕を足さないと %.1f m を割る試行が出る" % C_BIKE, np.sum(out[0.0] < C_BIKE) > 0,
         "%d / %d 試行" % (int(np.sum(out[0.0] < C_BIKE)), N_BIKE))
    return {"mins": out, "sd": sd_true, "h": h, "allow": (min(allow), max(allow))}


# ───────────────────────────── 8. 古典的な知覚(車載カメラ) + 主図 ─────────────────────────────
def _box_mesh(L, W, H, z0=0.0):
    V = np.array([[x, y, z] for z in (z0, z0 + H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)])
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]])
    return V, F


def build_street():
    """死角の場面の世界: 片側 1 車線の道・中央線・縁石・歩道・ブロック塀・路肩駐車の車・隠れた子ども。"""
    w = DW._empty_world()
    V, F = DW._grid_plane(-10.0, 120.0, -3.5, KERB, step=2.0)
    DW.world_add(w, V, F, 0, DW._ROAD_COLOR, name="road")
    for side in (1.0, -1.0):
        V, F = DW._grid_plane(-10.0, 120.0, 0.0, 3.0, step=2.0, z=0.15)
        V[:, 1] = side * (KERB + V[:, 1])
        DW.world_add(w, V, F if side > 0 else F[:, ::-1], 1, (0.70, 0.70, 0.66), name="sidewalk")
        V, F = _box_mesh(130.0, 0.2, 1.6)
        DW.world_add(w, V + np.array([55.0, side * (KERB + 3.2), 0.0]), F, 6, (0.62, 0.60, 0.56), name="wall")
        V, F = _box_mesh(130.0, 0.15, 0.15)
        DW.world_add(w, V + np.array([55.0, side * KERB, 0.0]), F, 1, DW._KERB_COLOR, name="kerb")
    for x0 in np.arange(-10.0, 120.0, 8.0):                                     # 中央線(白の破線 5 m・間 3 m)
        DW.world_add(w, np.array([[x0, -0.075, 0.006], [x0 + 5, -0.075, 0.006], [x0 + 5, 0.075, 0.006], [x0, 0.075, 0.006]]),
                     np.array([[0, 1, 2], [0, 2, 3]]), 9, DW._LINE_COLOR, name="center")
    for yl in (KERB - 0.2, -KERB + 0.2):                                          # 車道外側線
        DW.world_add(w, np.array([[-10, yl - 0.075, 0.006], [120, yl - 0.075, 0.006], [120, yl + 0.075, 0.006], [-10, yl + 0.075, 0.006]]),
                     np.array([[0, 1, 2], [0, 2, 3]]), 9, DW._LINE_COLOR, name="edge")
    car = DW.add_asset(w, "sedan", CAR[0], CAR[1], 0.0, paint="white")
    DW.add_asset(w, "suv", 85.0, CAR[1], 0.0)                                    # 遠くにもう 1 台
    ped = DT.add_mesh_object(w, DT.pedestrian_mesh(1.1, color=(0.95, 0.75, 0.10)), 0.0, 0.0, -math.pi / 2, name="child")
    return w, car, ped


def set_child(w, ped, x, y, stride):
    o = w["objects"][ped]
    m = DT.pedestrian_mesh(1.1, color=(0.95, 0.75, 0.10), stride=stride)
    v0, v1 = o["verts"]
    w["V"][v0:v1] = DW.place_mesh(m["V"], x, y, -math.pi / 2, 0.0)
    o["pose"] = (x, y, -math.pi / 2)


def scene_perception(OCC):
    print("== 8. 古典的な知覚: 車載カメラの画像を地図の背景と引き算して、飛び出しに気づく(学習なし)")
    w, car, ped = build_street()
    Wc, Hc = CAM_WH
    K = DW.camera_intrinsics(55.0, Wc, Hc)
    v_pol = OCC["v_pol"]
    xf = CAR[0] + CAR[2] / 2
    XP, Y0, U = xf + 2.5, 3.0, 2.5                    # 子ども: 駐車車両の前端の 2.5 m 先、車の幅の帯の中に隠れ、2.5 m/s で走り出す
    TRIG = XP - 9.5                                    # 自車の前端がここに来たら走り出す
    zone0 = float(OCC["POL"]["reveal_front"].min()) - 1.0
    dt = 1.0 / CAM_FPS
    rng = np.random.default_rng(808)
    st = {"x": zone0 - 30.0, "v": V_CRUISE, "mode": "cruise", "t_ped": None, "t_det": None, "t_truth": None, "t_geo": None,
          "t_stop": None, "t_clear": None}
    log, frames_raw = [], []
    a_c = 2.0
    t = 0.0
    y_ped = Y0
    false_alarm = 0
    t_end_after = None
    while True:
        # 歩行者
        if st["t_ped"] is None and st["x"] >= TRIG:
            st["t_ped"] = t
        if st["t_ped"] is not None:
            y_ped = max(-KERB - 1.0, Y0 - U * (t - st["t_ped"]))
        stride = 0.25 * math.sin(2 * math.pi * 2.0 * (t - st["t_ped"])) if st["t_ped"] is not None and y_ped > -KERB - 1.0 else 0.0
        set_child(w, ped, XP, y_ped, stride)
        eye = (st["x"] - EYE_BACK, Y_PASS, EYE_Z)
        Pc = DW.camera_pose(eye, (eye[0] + 20.0, Y_PASS + 0.3, 0.9))
        view = DW.world_camera(w, Pc, K, Wc, Hc)
        img = np.clip(view["color"] + rng.normal(0.0, NOISE, view["color"].shape), 0, 1)
        set_child(w, ped, -500.0, 0.0, 0.0)                                       # 地図(歩行者なし)= 背景
        bg = np.clip(DW.world_camera(w, Pc, K, Wc, Hc)["color"] + rng.normal(0.0, NOISE, view["color"].shape), 0, 1)
        set_child(w, ped, XP, y_ped, stride)
        diff = np.abs(img - bg).max(axis=2)
        mask = diff > DET_THR_SIGMA * NOISE * math.sqrt(2.0)
        # 孤立点を除く(8 近傍に 2 つ以上の仲間)
        mp = np.pad(mask, 1)
        nb = sum(np.roll(np.roll(mp, a, 0), b, 1) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0))[1:-1, 1:-1]
        mask2 = mask & (nb >= 2)
        npx = int(mask2.sum())
        n_label = int((view["label"] == 7).sum())
        if st["t_truth"] is None and n_label > 0:
            st["t_truth"] = t
        if st["t_geo"] is None and bool(visible([[eye[0], eye[1]]], [[XP, y_ped]], CAR)[0]):
            st["t_geo"] = t
        detected = npx >= DET_MIN_PX
        if detected and st["t_det"] is None:
            st["t_det"] = t
            if st["t_truth"] is None:
                false_alarm += 1
        frames_raw.append((t, st["x"], st["v"], st["mode"], view["color"], mask2, y_ped, n_label, Pc))   # 表示は雑音を足す前の絵
        log.append((t, st["x"], st["v"], st["mode"], npx, n_label, y_ped))
        # 自車(反応 RHO の後に緊急制動、止まったら横断を待つ、歩行者が自車の通り道を抜けたら発進)
        x_lim_v = V_CRUISE if st["x"] < zone0 - 30 else min(V_CRUISE, math.sqrt(v_pol ** 2 + 2 * a_c * max(0.0, zone0 - st["x"])))
        if st["t_det"] is None:
            v_cmd = x_lim_v if st["x"] < zone0 else v_pol
            st["mode"] = "cruise" if st["x"] < zone0 - 12 else ("slow" if st["x"] < zone0 else "zone")
            st["v"] = max(v_cmd, st["v"] - a_c * dt) if st["v"] > v_cmd else min(v_cmd, st["v"] + 1.0 * dt)
            st["x"] += st["v"] * dt
        elif t < st["t_det"] + RHO:
            st["mode"] = "seen"
            st["x"] += st["v"] * dt
        elif st["v"] > 0:
            st["mode"] = "brake"
            v_new = max(0.0, st["v"] - B_EMG * dt)
            st["x"] += (st["v"] ** 2 - v_new ** 2) / (2 * B_EMG)
            st["v"] = v_new
            if v_new == 0.0:
                st["t_stop"] = t + dt
        else:
            if y_ped > Y_PASS - EGO_W / 2 - 0.5:
                st["mode"] = "stopped"
            else:
                if st["t_clear"] is None:
                    st["t_clear"] = t
                st["mode"] = "go"
                if t > st["t_clear"] + 0.5:
                    st["v"] = min(v_pol, st["v"] + 1.0 * dt)
                    st["x"] += st["v"] * dt
                    if t_end_after is None:
                        t_end_after = t
        t += dt
        if (t_end_after is not None and t > t_end_after + 1.5) or t > 40.0:
            break
    stop_x = [r[1] for r in log if r[3] == "stopped"]
    stop_gap = XP - R_PED - (stop_x[0] if stop_x else max(r[1] for r in log))
    d_truth = XP - next(r[1] for r in log if r[0] >= st["t_truth"]) if st["t_truth"] is not None else float("nan")
    print("  車載カメラ %d × %d・%.0f fps、雑音 σ %.2f、しきい値 %.0f σ、孤立点を除いて %d 画素以上で検知" % (Wc, Hc, CAM_FPS, NOISE, DET_THR_SIGMA, DET_MIN_PX))
    print("  子どもが走り出す t = %.2f s → 描画に写る(真値) t = %.3f s(前端から %.2f m)/ 2D の視線(体の中心)t = %s / 背景差分の検知 t = %s"
          " → 遅れ %.3f s(%.0f コマ)、それより前の誤検知 %d" % (
              st["t_ped"], st["t_truth"], d_truth, "%.3f s" % st["t_geo"] if st["t_geo"] is not None else "-",
              "%.3f s" % st["t_det"] if st["t_det"] is not None else "-", (st["t_det"] - st["t_truth"]) if st["t_det"] else float("nan"),
              round((st["t_det"] - st["t_truth"]) / dt) if st["t_det"] else -1, false_alarm))
    delay = (st["t_det"] - st["t_truth"]) if (st["t_det"] is not None and st["t_truth"] is not None) else math.inf
    gate("知覚: 背景差分の検知は真値(面ラベルに歩行者が写る時刻)から遅れ ≤ 0.2 s、それより前の誤検知 0",
         0.0 <= delay <= 0.2 and false_alarm == 0, "遅れ %.3f s" % delay)
    gate("知覚の閉ループ: 検知 + 反応 %.1f s + 制動 %.0f m/s² で、走り出した子どもの手前(体 %.1f m)に止まる" % (RHO, B_EMG, R_PED),
         stop_gap >= 0.0 and st["t_stop"] is not None, "止まった前端と子どもの線 %.2f m" % (stop_gap + R_PED))
    return {"frames": frames_raw, "st": st, "XP": XP, "K": K, "delay": delay, "stop_gap": stop_gap, "v_pol": v_pol, "d_truth": d_truth}


# ───────────────────────────── 9. 通し走行(俯瞰) ─────────────────────────────
def street_run(OCC, PAS):
    """1 本の道に参加者を全部置いて方針どおりに走る(俯瞰の動画の中身 + 接触の検査)。"""
    print("== 9. 通し走行: 駐車車両と飛び出し・対向の車列・自転車・バス停を 1 本の道に置く")
    v_pol = OCC["v_pol"]
    V_ON = PAS["V_ON"]
    dt = 0.05
    t_end = 95.0
    n = int(t_end / dt) + 1
    tt = np.arange(n) * dt
    # 対向の車列(西向き、混ざった癖)。先頭は 11 m/s、途中で 7 m/s に落として戻す
    styles = ["normal", "sloppy", "careful", "normal", "sloppy", "normal"]
    ps = [dict(TR.driver_style(k, seed=90 + i), speed_noise=0.0) for i, k in enumerate(styles[1:])]
    for p in ps:
        p["v0"] = max(p["v0"], 12.5)
    lead = np.where(tt < 8.0, V_ON, np.where(tt < 12.0, V_ON - 1.0 * (tt - 8.0), np.minimum(V_ON, 7.1 + 1.0 * (tt - 12.0))))
    pr = TR.idm_platoon_simulate(lead, len(ps), params_per_vehicle=ps, dt=dt, t_end=t_end)
    X_ON0 = 190.0
    on_x = X_ON0 - pr["x"]                                    # (n, 6) 前端(西向きなので前端 = x の小さい側)
    on_y = np.column_stack([-Y_LANE + TR.lateral_wobble(n, dt, theta=TR.driver_style(k)["wobble_theta"],
                                                       sigma=TR.driver_style(k)["wobble_sigma"], seed=300 + i) for i, k in enumerate(styles)])
    # 遅れて来る 2 台(一定速度)
    late = [770.0, 800.0]                                   # t = 0 の位置(自転車を追い越す頃に来る 2 台)
    on_x = np.column_stack([on_x] + [np.full(n, x0) - V_ON * tt for x0 in late])
    on_y = np.column_stack([on_y, np.full((n, 2), -Y_LANE)])
    on_style = styles + ["normal", "normal"]
    # 自転車: t = 30 s に x = 120 の脇道から出て 4 m/s、x = 260 で脇道へ去る
    bike_w = TR.lateral_wobble(n, dt, theta=BIKE["theta"], sigma=BIKE["sigma"], seed=77)
    BT0, BX0 = 30.0, 120.0
    # バス: x 300〜310.5 に停車、t = 75 s に発車(1 m/s² で 8 m/s)
    BUS_R, BUS_L, T_DEP = 300.0, 10.5, 75.0
    # 子ども(駐車車両の場面と同じ)と、バスの前を渡る乗客(停車中に 3 人)
    xf = CAR[0] + CAR[2] / 2
    XP, Y0, U = xf + 2.5, 3.0, 2.5
    pax = [(BUS_R + BUS_L + 1.5, 62.0), (BUS_R + BUS_L + 2.2, 66.5), (BUS_R + BUS_L + 1.2, 71.0)]   # (x, 渡り始める時刻)
    st = {"x": 0.0, "v": V_CRUISE, "y": Y_LANE, "t_ped": None, "t_seen": None, "pass_car": False, "pass_bike": False,
          "car_done": False, "bike_done": False, "ped_clear": False}
    rec = []
    min_d = {"ped": math.inf, "oncoming_pet": math.inf, "bike": math.inf, "car": math.inf, "bus": math.inf, "pax": math.inf}
    pass_log = []
    for k in range(n):
        t = tt[k]
        # 参加者の今
        ped_y = Y0 if st["t_ped"] is None else max(-6.0, Y0 - U * (t - st["t_ped"]))
        bx = BX0 + BIKE["v"] * (t - BT0) if t >= BT0 else -1e9
        bike_on = BT0 <= t and bx < 260.0
        by = BIKE["y"] + bike_w[k]
        bus_x = BUS_R if t < T_DEP else BUS_R + 0.5 * 1.0 * min(t - T_DEP, 8.0) ** 2 + 8.0 * max(0.0, t - T_DEP - 8.0)
        bus_v = 0.0 if t < T_DEP else min(8.0, t - T_DEP)
        pax_y = [3.0 - 1.2 * max(0.0, t - t0) for _, t0 in pax]
        # 自車の目と前端
        front = st["x"]
        eye = np.array([front - EYE_BACK, st["y"]])
        if st["t_ped"] is None and st["pass_car"] and front >= XP - 6.0:      # 横を抜け始めた所で走り出す
            st["t_ped"] = t
        if st["t_seen"] is None and st["t_ped"] is not None and front < XP and bool(visible([eye], [[XP, ped_y]], CAR)[0]):
            st["t_seen"] = t
        # 対向車の最寄り(前端より前で、まだすれ違っていない)
        ahead = on_x[k][on_x[k] > front]
        D_on = float(ahead.min() - front) if ahead.size else math.inf          # 対向車なし = inf(passing_decision が go)
        mode = "cruise"
        v_des = V_CRUISE
        leader = (math.inf, 0.0)                          # (前の物までの車間, その速さ)
        # 駐車車両(死角): 徐行 + すれ違いの判断
        car_r = CAR[0] - CAR[2] / 2
        zone0 = float(OCC["POL"]["reveal_front"].min()) - 1.0
        if not st["car_done"]:
            if front < zone0:
                v_des = min(V_CRUISE, math.sqrt(v_pol ** 2 + 2 * 2.0 * (zone0 - front)))
                mode = "slow" if front > zone0 - 15 else "cruise"
            else:
                v_des, mode = v_pol, "zone"
            if not st["pass_car"]:
                if front >= car_r - 5.0 - 3.0:
                    dec = TR.passing_decision(D_on, 4.5, 3.0, 5.0, v_pol, V_ON, lane_change_time=2.0, ego_length=EGO_L, pet_min=1.0)
                    if dec == "go":
                        st["pass_car"] = True
                        pass_log.append(("car", t, D_on))
                    else:
                        mode = "wait_oncoming"
                if not st["pass_car"]:
                    leader = (car_r - front, 0.0)
            if front > xf + 3.0 + 1.0:
                st["car_done"] = True
        # 自転車: 後ろについて、隙間が来たら追い越す
        if bike_on and not st["bike_done"] and bx - BIKE["len"] > front - 1.0:
            if not st["pass_bike"]:
                gap_b = bx - BIKE["len"] - front
                if gap_b < 12.0:
                    v_rel = max(0.5, V_CRUISE - BIKE["v"])
                    dec = TR.passing_decision(D_on, BIKE["len"], 2.0, 2.0, V_CRUISE, V_ON, lane_change_time=2.0, ego_length=EGO_L,
                                              pet_min=1.0, v_obstacle=BIKE["v"])
                    if dec == "go" and st["car_done"]:
                        st["pass_bike"] = True
                        k0 = max(1, int(round((t - BT0) / dt)))
                        obs = bike_w[k - min(k0, 100):k + 1]
                        sig_hat = bike_sigma(obs, dt)
                        h_b = 2.0 + (2.0 + BIKE["len"] + gap_b + EGO_L) / v_rel
                        st["bike_y_t"] = by - BIKE["half"] - C_BIKE - bike_allowance(sig_hat, h_b) - EGO_W / 2
                        pass_log.append(("bike", t, D_on))
                    else:
                        mode = "bike"
                if not st["pass_bike"]:
                    leader = min(leader, (gap_b, BIKE["v"]))
        if st["pass_bike"] and bike_on and front - EGO_L > bx + 2.0:
            st["bike_done"] = True
        # バス: 停車中は後ろで待つ(既定)、発車したら追従
        gap_bus = bus_x - front
        if gap_bus > -2.0:
            leader = min(leader, (gap_bus, bus_v))
            if t < T_DEP and gap_bus < 30.0:
                mode = "wait_bus"
        # 縦: 速度の指令(徐行の上限)と、前の物への IDM の項の小さい方
        a_free = float(np.clip(1.0 * (v_des - st["v"]), -3.0, 1.5))
        a = a_free
        if leader[0] < 200.0:
            a = min(a, TR.idm_accel(st["v"], max(leader[0], 0.05), st["v"] - leader[1], v0=V_CRUISE + 0.5, T=1.5, a=1.5, b=2.0, s0=2.5))
        # 見えた子どもへの緊急制動(反応の後)と、渡り切るまでの停止
        if st["t_seen"] is not None and not st["ped_clear"]:
            if ped_y < Y_PASS - EGO_W / 2 - 0.5 if st["pass_car"] else ped_y < Y_LANE - EGO_W / 2 - 0.5:
                st["ped_clear"] = True
            elif t >= st["t_seen"] + RHO:
                a = -B_EMG if st["v"] > 0 else 0.0
                mode = "brake" if st["v"] > 0 else "stopped"
            else:
                mode = "seen"
        if st["pass_car"] and not st["car_done"] and mode not in ("brake", "stopped", "seen"):
            mode = "pass"
        if st["pass_bike"] and not st["bike_done"]:
            mode = "pass"
        a = max(a, -B_EMG)
        v_new = max(0.0, st["v"] + a * dt)
        st["x"] += 0.5 * (st["v"] + v_new) * dt
        st["v"] = v_new
        # 横: 追い越し中は目標の位置へ 1.0 m/s で寄る
        if st["pass_car"] and not st["car_done"]:
            y_t = Y_PASS
        elif st["pass_bike"] and not st["bike_done"]:
            y_t = st["bike_y_t"]
        else:
            y_t = Y_LANE
        st["y"] += float(np.clip(y_t - st["y"], -1.0 * dt, 1.0 * dt))
        # 接触の検査(自車の箱 [front − L, front] × [y ± W/2])
        ex0, ex1, ey0, ey1 = front - EGO_L, front, st["y"] - EGO_W / 2, st["y"] + EGO_W / 2

        def dist_box(x0, x1, y0, y1):
            dx = max(0.0, x0 - ex1, ex0 - x1)
            dy = max(0.0, y0 - ey1, ey0 - y1)
            return math.hypot(dx, dy)
        min_d["ped"] = min(min_d["ped"], dist_box(XP - R_PED, XP + R_PED, ped_y - R_PED, ped_y + R_PED))
        min_d["car"] = min(min_d["car"], dist_box(CAR[0] - 2.25, CAR[0] + 2.25, CAR[1] - 0.9, CAR[1] + 0.9))
        if bike_on:
            min_d["bike"] = min(min_d["bike"], dist_box(bx - BIKE["len"], bx, by - BIKE["half"], by + BIKE["half"]))
        min_d["bus"] = min(min_d["bus"], dist_box(bus_x, bus_x + BUS_L, 1.0, 3.5))
        for (px, _), py in zip(pax, pax_y):
            min_d["pax"] = min(min_d["pax"], dist_box(px - R_PED, px + R_PED, py - R_PED, py + R_PED))
        for j in range(on_x.shape[1]):
            min_d["oncoming_pet"] = min(min_d["oncoming_pet"], dist_box(on_x[k, j], on_x[k, j] + 4.5, on_y[k, j] - 0.9, on_y[k, j] + 0.9))
        rec.append({"t": t, "x": front, "y": st["y"], "v": st["v"], "mode": mode, "ped_y": ped_y, "bx": bx if bike_on else None, "by": by,
                    "bus_x": bus_x, "pax_y": pax_y, "on_x": on_x[k].copy(), "on_y": on_y[k].copy(), "D_on": D_on})
        if st["x"] > 335.0:
            break
    print("  走行 %.1f s、%.0f m。追い越しの判断: %s" % (rec[-1]["t"], rec[-1]["x"], ", ".join(
        "%s t = %.1f s(%s)" % ({"car": "駐車車両", "bike": "自転車"}[a], b, "対向車まで %.0f m" % c if math.isfinite(c) else "対向車なし")
        for a, b, c in pass_log)))
    print("  最小の距離 [m]: 子ども %.2f / 駐車車両 %.2f / 対向車 %.2f / 自転車 %.2f / バス %.2f / 乗客 %.2f" % (
        min_d["ped"], min_d["car"], min_d["oncoming_pet"], min_d["bike"], min_d["bus"], min_d["pax"]))
    gate("通し走行: 駐車車両・飛び出し・対向の車列・自転車・バスのどれとも接触せず、自転車とは側方 %.1f m 以上、終点に着く" % C_BIKE,
         all(v > 0.0 for v in min_d.values()) and min_d["bike"] >= C_BIKE and rec[-1]["x"] > 330.0 and len(pass_log) == 2,
         "最小 %.2f m" % min(min_d.values()))
    return {"rec": rec, "on_style": on_style, "XP": XP, "BUS": (BUS_R, BUS_L, T_DEP), "pax": pax, "min_d": min_d, "pass_log": pass_log}


# ───────────────────────────── 図 ─────────────────────────────
def _txt(img, s, xy, anchor="lt", fs=12):
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs), dtype=np.float64)


def fig_dashcam(PER):
    frames = []
    st = PER["st"]
    Hc, Wc = PER["frames"][0][4].shape[:2]
    fsz = 11 if Wc < 400 else 14
    h2, w2 = Hc // 3, Wc // 3                       # 右下の拡大窓(3 倍)
    ch, cw = h2 // 3, w2 // 3
    last_c = None
    for t, x, v, mode, img, mask, y_ped, nlab, Pc in PER["frames"]:
        f = img.copy()
        det = st["t_det"] is not None and t >= st["t_det"] and mask.any()
        if det:
            rr, cc = np.nonzero(mask)
            r0, r1, c0, c1 = max(0, rr.min() - 4), min(Hc - 1, rr.max() + 4), max(0, cc.min() - 4), min(Wc - 1, cc.max() + 4)
            for (a0, a1, b0, b1) in ((r0, r0 + 1, c0, c1 + 1), (r1, r1 + 1, c0, c1 + 1), (r0, r1 + 1, c0, c0 + 1), (r0, r1 + 1, c1, c1 + 1)):
                f[max(0, a0 - 1):a1 + 1, max(0, b0 - 1):b1 + 1] = (1.0, 0.15, 0.1)
            last_c = (0.5 * (rr.min() + rr.max()), 0.5 * (cc.min() + cc.max()))
        # 拡大窓の中心: 検知した後は差分の塊、その前は駐車車両の前端の先(子どもが出てくる辺り)
        if det or (last_c is not None and st["t_det"] is not None and t >= st["t_det"]):
            rc, ccn = last_c
        else:
            col, row, dep = DW.world_project_points(np.array([[PER["XP"], 2.4, 0.6]]), Pc, PER["K"])
            rc, ccn = (float(row[0]), float(col[0])) if dep[0] > 0 else (Hc / 2, Wc / 2)
        r0 = int(np.clip(round(rc - ch / 2), 0, Hc - ch))
        c0 = int(np.clip(round(ccn - cw / 2), 0, Wc - cw))
        crop = img[r0:r0 + ch, c0:c0 + cw].copy()
        mc = mask[r0:r0 + ch, c0:c0 + cw]
        crop[mc] = crop[mc] * 0.3 + 0.7 * np.array([1.0, 0.1, 0.1])
        big = np.repeat(np.repeat(crop, 3, axis=0), 3, axis=1)
        f[Hc - big.shape[0] - 4:Hc - 4, Wc - big.shape[1] - 4:Wc - 4] = big
        f[Hc - big.shape[0] - 5, Wc - big.shape[1] - 5:Wc - 3] = 1.0
        f[Hc - big.shape[0] - 5:Hc - 3, Wc - big.shape[1] - 5] = 1.0
        txt = "t = %4.1f s   速度 %4.1f km/h\n止まれる最大速度 %4.1f km/h(死角の横)\n判断: %s" % (t, 3.6 * v, 3.6 * PER["v_pol"], JP[mode])
        if st["t_det"] is not None and t >= st["t_det"]:
            txt += "\n背景差分で検知 t = %.2f s" % st["t_det"]
        f = _txt(f, txt, (6, 6), fs=fsz)
        f = _txt(f, "拡大 3 倍(赤 = 背景との差)" if Wc >= 400 else "拡大(赤 = 差)", (Wc - 4, Hc - big.shape[0] - 7), anchor="rb",
                 fs=10 if Wc < 400 else 11)
        frames.append(np.clip(f, 0, 1))
    every = 3 if CAM_FPS >= 30 else 2
    figs.save_video("dashcam_occlusion", frames, fps=CAM_FPS, gif_every=every, gif_width=480,
                    caption="主図(車載カメラ、%d × %d・%.0f fps): 路肩駐車の白い車の前に子ども(1.1 m)が隠れている。自車は死角の手前で、隠れ場所の"
                            "最悪の候補から閉形式で決めた止まれる最大速度 %.1f km/h まで落として横を抜ける。子どもは t = %.2f s に走り出す(描画では立っている"
                            "子の頭がボンネット越しに t = %.2f s から写る = 真値)。地図から同じ姿勢で描いた背景との差(右下の拡大窓の赤、学習なし)が %d 画素を"
                            "越えた時刻 t = %.2f s に検知(赤い枠)、真値からの遅れ %.3f s。"
                            "反応 %.1f s の後に %.0f m/s² で止まり、子どもの線の %.2f m 手前で停止、渡り切ってから発進。表示は雑音を足す前の絵"
                            "(検知は σ %.2f の雑音つきの絵で行う)。" % (
                                Wc, Hc, CAM_FPS, 3.6 * PER["v_pol"], st["t_ped"], st["t_truth"], DET_MIN_PX, st["t_det"], PER["delay"], RHO, B_EMG,
                                PER["stop_gap"] + R_PED, NOISE))


def _rect(img, T, x0, x1, y0, y1, col, alpha=1.0):
    H, W = img.shape[:2]
    c0, r1 = T(x0, y0)
    c1, r0 = T(x1, y1)
    c0, c1 = int(max(0, math.floor(min(c0, c1)))), int(min(W, math.ceil(max(c0, c1))))
    r0, r1 = int(max(0, math.floor(min(r0, r1)))), int(min(H, math.ceil(max(r0, r1))))
    if c1 > c0 and r1 > r0:
        img[r0:r1, c0:c1] = (1 - alpha) * img[r0:r1, c0:c1] + alpha * np.asarray(col)


def _disk(img, T, x, y, r, col):
    H, W = img.shape[:2]
    c, rr = T(x, y)
    rp = r * T.scale
    r0, r1 = int(max(0, rr - rp - 1)), int(min(H, rr + rp + 2))
    c0, c1 = int(max(0, c - rp - 1)), int(min(W, c + rp + 2))
    if r1 <= r0 or c1 <= c0:
        return
    yy, xx = np.mgrid[r0:r1, c0:c1]
    m = (xx + 0.5 - c) ** 2 + (yy + 0.5 - rr) ** 2 <= rp * rp
    img[r0:r1, c0:c1][m] = col


class _View:
    def __init__(self, x0, x1, y0, y1, scale, top):
        self.x0, self.y1, self.scale, self.top = x0, y1, scale, top

    def __call__(self, x, y):
        return (x - self.x0) * self.scale, self.top + (self.y1 - y) * self.scale


STYLE_COL = {"careful": (0.20, 0.65, 0.35), "normal": (0.85, 0.85, 0.88), "sloppy": (1.0, 0.55, 0.10)}


def fig_overhead(RUN):
    rec = RUN["rec"]
    BUS_R, BUS_L, T_DEP = RUN["BUS"]
    SC = 12.0
    W, top = 960, 64
    YV = (-7.0, 7.5)
    H = top + int((YV[1] - YV[0]) * SC) + 4
    frames = []
    step = 2 if REDUCED else 1
    xs_grid = None
    for r in rec[::step * 2]:                  # 10 fps(reduced 5 fps)
        x0 = r["x"] - 30.0
        T = _View(x0, x0 + W / SC, YV[0], YV[1], SC, top)
        img = np.full((H, W, 3), 0.33)
        img[:top] = 0.12
        _rect(img, T, x0, x0 + 200, -KERB, KERB, (0.42, 0.43, 0.45))
        _rect(img, T, x0, x0 + 200, KERB, 6.5, (0.70, 0.70, 0.66))
        _rect(img, T, x0, x0 + 200, -6.5, -KERB, (0.70, 0.70, 0.66))
        for xd in np.arange(math.floor(x0 / 8) * 8, x0 + 120, 8.0):
            _rect(img, T, xd, xd + 5, -0.08, 0.08, (0.95, 0.95, 0.92))
        # 死角(駐車車両とバスの陰): 目から見えない所を暗く
        eye = np.array([r["x"] - EYE_BACK, r["y"]])
        if xs_grid is None:
            cc, rr_ = np.meshgrid(np.arange(W) + 0.5, np.arange(top, H) + 0.5)
            xs_grid = (cc, rr_)
        cc, rr_ = xs_grid
        wx = x0 + cc / SC
        wy = YV[1] - (rr_ - top) / SC
        pts = np.column_stack([wx.ravel(), wy.ravel()])
        for box in (CAR, ((r["bus_x"] + BUS_L / 2), 2.25, BUS_L, 2.5)):
            if box[0] - box[2] / 2 > x0 + W / SC or box[0] + box[2] / 2 + 40 < x0:
                continue
            sel = (pts[:, 0] > box[0] - box[2] / 2) & (pts[:, 0] < box[0] + box[2] / 2 + 40.0) & (pts[:, 1] > box[1] - box[3] / 2)
            if sel.any():
                vis = visible(np.tile(eye, (int(sel.sum()), 1)), pts[sel], box)
                sh = np.zeros(len(pts), bool)
                sh[np.nonzero(sel)[0][~vis]] = True
                sh = sh.reshape(cc.shape)
                img[top:][sh] = img[top:][sh] * 0.45 + np.array([0.15, 0.05, 0.25]) * 0.55
        _rect(img, T, CAR[0] - 2.25, CAR[0] + 2.25, CAR[1] - 0.9, CAR[1] + 0.9, (0.92, 0.92, 0.92))
        _rect(img, T, r["bus_x"], r["bus_x"] + BUS_L, 1.0, 3.5, (0.20, 0.55, 0.40))
        for j in range(len(r["on_x"])):
            _rect(img, T, r["on_x"][j], r["on_x"][j] + 4.5, r["on_y"][j] - 0.9, r["on_y"][j] + 0.9, STYLE_COL[RUN["on_style"][j]])
        if r["bx"] is not None:
            _rect(img, T, r["bx"] - BIKE["len"], r["bx"], r["by"] - 0.25, r["by"] + 0.25, (0.55, 0.30, 0.80))
            _disk(img, T, r["bx"] - 0.8, r["by"], 0.3, (0.75, 0.55, 0.95))
        _disk(img, T, RUN["XP"], r["ped_y"], R_PED, (0.95, 0.75, 0.10))
        for (px, _), py in zip(RUN["pax"], r["pax_y"]):
            if py > -6.0:
                _disk(img, T, px, py, R_PED, (1.0, 0.3, 0.3))
        _rect(img, T, r["x"] - EGO_L, r["x"], r["y"] - 0.9, r["y"] + 0.9, (0.15, 0.40, 0.95))
        _disk(img, T, eye[0], eye[1], 0.25, (1.0, 1.0, 1.0))
        txt = "t = %5.1f s   %4.1f km/h   x = %5.1f m   判断: %s" % (r["t"], 3.6 * r["v"], r["x"], JP[r["mode"]])
        if math.isfinite(r["D_on"]) and r["mode"] in ("wait_oncoming", "bike"):
            txt += "(対向車まで %.0f m)" % r["D_on"]
        img = _txt(img, txt, (6, 5), fs=13)
        img = _txt(img, "青 = 自車  白 = 駐車車両  緑の長い箱 = バス  対向車: 灰 = 普通 / 緑 = 慎重 / 橙 = 荒い運転  紫 = 自転車  黄 = 子ども  赤 = 乗客  紫の影 = 死角",
                   (6, 34), fs=10)
        frames.append(np.clip(img, 0, 1))
    fps = 10.0 if not REDUCED else 5.0
    figs.save_video("overhead_street", frames, fps=fps, gif_every=3 if not REDUCED else 2, gif_width=None,
                    caption="俯瞰(通し走行 %.0f s・%.0f m): 自車(青)は路肩駐車の死角の手前で %.1f km/h に落とし、対向の車列(橙 = 荒い運転、横にふらつく)"
                            "が過ぎて隙間 D* が空くまで待ってからはみ出す。陰から走り出た子ども(黄)に止まり、渡り切ってから発進。脇道から出た"
                            "自転車(紫)の後ろにつき、対向車が過ぎたら側方 %.1f m + 追い越しの間にふらつける幅 4.5 σ̂ √h を空けて追い越す。停車中のバス(緑)の前を乗客(赤)が"
                            "渡るので追い越さずに発車まで待つ。紫の影は自車の目から見えない所。最小の距離: 子ども %.2f m・自転車 %.2f m・対向車 %.2f m。" % (
                                rec[-1]["t"], rec[-1]["x"], 3.6 * RUN.get("v_pol", 0.0), C_BIKE, RUN["min_d"]["ped"], RUN["min_d"]["bike"],
                                RUN["min_d"]["oncoming_pet"]))


def fig_platoon(PLT):
    import fullseye as fs
    panels, caps = [], []
    for k in TR.DRIVER_KINDS:
        r, se, rel = PLT["runs"][k]
        jk = {"careful": "慎重な運転", "normal": "普通の運転", "sloppy": "荒い運転"}[k]
        t = r["t"]
        rx = r["x"] - r["x"][:, :1]
        w, h = 420, 330
        img = np.full((h, w, 3), 1.0)
        # 追突した車の線はその時刻で打ち切る(積分は車間を 1 mm に留めて続くが、重なった後の位置に意味は無い)
        t_hit = np.full(rx.shape[1], np.inf)
        for tc, i in r["collisions"]:                  # idm_platoon_simulate が返す (時刻, 車番)。追突した車はそこで止まる
            t_hit[i] = tc
        m60 = t <= 60.0
        yl = (float(min(rx[m60 & (t <= t_hit[i]), i].min() for i in range(rx.shape[1]))) - 5, 5.0)
        xl = (0.0, 60.0)
        rect = (60, 20, w - 80, h - 90)
        ax = fs.axes_transform(rect, xl, yl)
        img = np.asarray(fs.grid_lines(img, ax, xticks=fs.nice_ticks(*xl, 6), yticks=fs.nice_ticks(*yl, 5), alpha=0.25))
        img = np.asarray(fs.axes_frame(img, ax, width=1))
        img = np.asarray(fs.ticks(img, ax, xticks=fs.nice_ticks(*xl, 6), yticks=fs.nice_ticks(*yl, 5), tick_len=4, font_size=10))
        for i in range(rx.shape[1]):
            m = m60 & (t <= t_hit[i])
            img = np.asarray(fs.plot_series(img, ax, t[m], rx[m, i], kind="line", color="wrong" if (k == "sloppy" and i > 0) else "reference", width=2))
            if np.isfinite(t_hit[i]) and t_hit[i] <= 60:
                kk = int(np.nonzero(t == t_hit[i])[0][0])
                xpx = rect[0] + (t[kk] - xl[0]) / (xl[1] - xl[0]) * (rect[2] - 1)
                ypx = rect[1] + (rect[3] - 1) - (rx[kk, i] - yl[0]) / (yl[1] - yl[0]) * (rect[3] - 1)
                for d in range(-6, 7):
                    for (a, b_) in ((d, d), (d, -d)):
                        yy, xx = int(round(ypx + a)), int(round(xpx + b_))
                        for e in (-1, 0, 1):
                            if 0 <= yy + e < h and 0 <= xx < w:
                                img[yy + e, xx] = (0.85, 0.0, 0.0)
        img = _txt(img, "横 = 時刻 [s]、縦 = 先頭車からの位置 [m]", (60, h - 6), anchor="lb", fs=10)
        panels.append(img)
        caps.append("%s(反応 %.1f s / 車間時間 %.1f s)%s" % (jk, TR.driver_style(k)["reaction_delay"], TR.driver_style(k)["T"],
                                                           "  ×= 追突" if r["collision"] else ""))
    figs.save_grid("platoon_spacetime", panels, captions=caps, ncols=3, title="下手な運転の車列(先頭が t = 5 s に 10 → 8 m/s)",
                   caption="時空図(縦 = 先頭車からの位置、横 = 時刻、線 = 6 台)。慎重(careful)・普通(normal)は平衡車間 s_e(8 m/s) = %.1f / %.1f m に収まり、"
                           "反応遅れ 1.3 s が車間時間 1.0 s より長い荒い運転(sloppy)は振動が後ろへ育って t = %.1f s に最初の追突(赤の ×、"
                           "追突した車の線はそこで打ち切る)。" % (
                               PLT["runs"]["careful"][1], PLT["runs"]["normal"][1], PLT["runs"]["sloppy"][0]["collision_time"]))


def fig_intent(INT):
    kinds = ("cross", "wait_then_cross", "walk_along", "stand")
    names = {"cross": "そのまま渡る", "wait_then_cross": "縁で待ってから渡る", "walk_along": "歩道に沿って歩く", "stand": "縁で立つが渡らない"}
    W, Hh = 640, 350
    img = np.full((Hh, W, 3), 1.0)
    x0, y0, cw, ch = 210, 70, 180, 46
    n_per = INT["n"] // 4
    img = _txt(img, "意図の真値(行)× 規則の判断(列)、各 %d 人" % n_per, (10, 8), fs=13)
    img = _txt(img, "止まる", (x0 + cw // 2, y0 - 8), anchor="cb", fs=12)
    img = _txt(img, "止まらない", (x0 + cw + cw // 2, y0 - 8), anchor="cb", fs=12)
    for i, k in enumerate(kinds):
        img = _txt(img, names[k], (x0 - 8, y0 + ch * i + ch // 2), anchor="rm", fs=12)
        for j, val in enumerate(INT["cm"][k]):
            frac = val / max(1, n_per)
            col = np.array([0.95, 0.55, 0.35]) if j == 0 else np.array([0.35, 0.65, 0.95])
            img[y0 + ch * i + 2:y0 + ch * (i + 1) - 2, x0 + cw * j + 2:x0 + cw * (j + 1) - 2] = 1.0 - frac * (1.0 - col)
            img = _txt(img, "%d" % val, (x0 + cw * j + cw // 2, y0 + ch * i + ch // 2), anchor="cm", fs=13)
    c = INT["cmt"]
    img = _txt(img, "H = %.0f s 以内に渡るか(真値)で数えると: 渡る人で止まる %d・見逃し %d / 渡らない人で止まる %d・止まらない %d" % (
        INT["H"], c[(True, True)], c[(True, False)], c[(False, True)], c[(False, False)]), (10, Hh - 34), anchor="lb", fs=10)
    img = _txt(img, "一致率 %.3f。縁で立つ人に止まるのは方針(歩道で待つ人がいれば一時停止)" % INT["agree"], (10, Hh - 10), anchor="lb", fs=10)
    figs.save("intent_confusion", img,
              caption="横断の意図の混同行列(%d 人、判断の時刻は乱数、位置の雑音 5 cm・向き 10°)。規則 = 車道へ向かって動き H = %.0f s 以内に縁に着く、"
                      "または(1 s の平均では止まっていて)縁から 1 m 以内で道を向き、離れていく途中でない → 止まる。渡る人の見逃し %d。縁で立つだけの人 %d 人に止まるのは誤検出だが"
                      "方針として受け入れる(待つ項を外すと見逃しが %d 人出る)。" % (INT["n"], INT["H"], INT["miss"], INT["fp_stand"], INT["miss_nd"]))


def figures(OCC, PAS, BUSR, PLT, INT, RARE, BIK, PER, RUN):
    print("== 10. 図")
    t = time.time()
    fig_dashcam(PER)
    print("  車載カメラの動画 %d コマ(%.1f s)" % (len(PER["frames"]), time.time() - t))
    t = time.time()
    RUN["v_pol"] = OCC["v_pol"]
    fig_overhead(RUN)
    print("  俯瞰の動画(%.1f s)" % (time.time() - t))
    fig_platoon(PLT)
    fig_intent(INT)
    figs.save_plot("lateral_clearance_speed", [("止まれる最大速度", [r[0] for r in OCC["lat"]], [r[1] for r in OCC["lat"]]),
                                                ("この PoC(横 1.0 m)", [1.0], [3.6 * OCC["v_pol"]])],
                   kinds=["line", "scatter"], xlabel="駐車車両との横の間隔 [m]", ylabel="km/h", title="死角の横を抜ける速さ",
                   caption="駐車車両との横の間隔を広げるほど、陰の子どもが早く見え、止まれる最大速度が上がる(閉形式: 隠れ場所の最悪の候補、"
                           "反応 %.1f s・制動 %.0f m/s²)。この PoC の 1.0 m で %.1f km/h。" % (RHO, B_EMG, 3.6 * OCC["v_pol"]))
    q = np.linspace(100, 900, 17) / 3600.0
    ser = []
    for name, (tau, a, m, se, p0, pe) in PAS["waits"].items():
        ser.append(("%s(τ = %.1f s)" % (name, tau), q * 3600, [adams_wait(qq, tau) for qq in q]))
    ser.append(("MC(600 台/時)", [600.0] * len(PAS["waits"]), [v[2] for v in PAS["waits"].values()]))
    figs.save_plot("passing_wait", ser, kinds=["line"] * len(PAS["waits"]) + ["scatter"], xlabel="対向車の流量 [台/時]", ylabel="平均の待ち [s]",
                   title="駐車車両を避けるはみ出しの待ち時間", caption="対向車がポアソン流のとき、はみ出しに要る隙間 τ = D*/v_on を待つ平均時間"
                   "(Adams の式)。徐行ではみ出す時間が延び、τ が長くなるので待ちが急に伸びる。点は MC(%d 回)。" % N_WAIT)
    rows = [[{"wait": "発車まで待つ", "slow": "徐行(10 km/h)で追い越す", "fast": "30 km/h で追い越す"}[k], "%.5f" % v[0], "%.5f ± %.5f" % (v[1], v[2]),
             "%.4f" % v[4], "%.0f" % v[3]] for k, v in BUSR.items()]
    figs.save_table("bus_stop_risk", ["方針", "期待件数 Λ(閉形式)", "MC", "P(1 件以上)", "待ち [s]"], rows, title="バス停: 止まれない帯に入る出現",
                    caption="停車中のバスの前後で出現率が高い(bus_stop_rate)。止まれない帯 [前端, 前端 + 停止距離] に人が出る期待件数。"
                            "待つと危険は徐行の %.0f 分の 1、代償は %.0f s。" % (BUSR["slow"][0] / BUSR["wait"][0], BUSR["wait"][3]))
    mins = BIK["mins"]
    hist = []
    for k_sd, lab in ((4.5, "余裕 4.5 σ̂√h を足す"), (0.0, "足さない")):
        hgt, edges = np.histogram(mins[k_sd], bins=np.linspace(0.8, 3.4, 53))
        hist.append((lab, 0.5 * (edges[1:] + edges[:-1]), hgt))
    hist.append(("C = %.1f m" % C_BIKE, [C_BIKE, C_BIKE], [0, max(h[2].max() for h in hist)]))
    figs.save_plot("bike_clearance", hist, kinds=["line", "line", "line"], xlabel="追い越しの間の側方間隔の最小 [m]", ylabel="試行の数",
                   title="ふらつく自転車の追い越し", caption="自転車の横ふらつき(OU、定常 SD %.3f m)を 5 s 見て、ou_estimate(OU の厳密離散化の最尤、読めなければ増分の推定)で拡散の強さ σ̂ を読み、"
                   "追い越しの間 h = %.1f s に動ける幅 4.5 σ̂ √h(%.2f〜%.2f m)を足して寄せると、%d 試行の全部で側方間隔 ≥ %.1f m(この PoC で決めた値)。"
                   "足さないと %d 試行で割る。" % (BIK["sd"], BIK["h"], BIK["allow"][0], BIK["allow"][1], N_BIKE, C_BIKE, int(np.sum(mins[0.0] < C_BIKE))))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        OK.append(False)


def main() -> int:
    """PoC の本体。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    print("仮定: 反応 %.1f s、緊急制動 %.0f m/s²、子どもの体の半径 %.1f m、余裕 %.1f m、目は前端の %.1f m 後ろ・高さ %.1f m" % (
        RHO, B_EMG, R_PED, MARGIN, EYE_BACK, EYE_Z))
    tm = {}
    t = time.time()
    OCC = scene_occlusion()
    tm["occ"] = time.time() - t
    t = time.time()
    PAS = scene_passing(OCC["v_pol"])
    tm["pass"] = time.time() - t
    t = time.time()
    BUSR = scene_bus()
    tm["bus"] = time.time() - t
    t = time.time()
    PLT = scene_platoon()
    tm["plt"] = time.time() - t
    t = time.time()
    INT = scene_intent()
    tm["int"] = time.time() - t
    t = time.time()
    RARE = scene_rare()
    tm["rare"] = time.time() - t
    t = time.time()
    BIK = scene_bike()
    tm["bike"] = time.time() - t
    t = time.time()
    PER = scene_perception(OCC)
    tm["per"] = time.time() - t
    t = time.time()
    RUN = street_run(OCC, PAS)
    tm["run"] = time.time() - t
    print("  区間ごとの所要 [s]: " + ", ".join("%s %.1f" % kv for kv in tm.items()))
    if figs.enabled():
        figures(OCC, PAS, BUSR, PLT, INT, RARE, BIK, PER, RUN)
    print("== 結果: %d / %d 門, %.1f s" % (sum(OK), len(OK), time.time() - T0))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
