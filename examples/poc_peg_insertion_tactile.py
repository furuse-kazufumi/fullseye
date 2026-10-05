# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ペグ挿入を 2 本指の膜で読む —— せん断の像から接触レンチ、Whitney の接触状態、壁の摩擦、手首剛性まで(2026-10-05)。

物理シミュ × Fullseye 系列(柔らかい手首のペグ挿入 2026.195、失敗の分類 2026.201)と視触覚の 3 本(押し込み 2026.196、せん断 2026.198、
ねじり 2026.199)の集大成。2 本指の指先に弾性膜を付け、ペグが穴から受ける接触レンチを**膜の像だけ**から復元し、Whitney の接触状態
(無接触 / 面取り / 一点 / 二点、止まった時のくさび / かじり)を学習なしの規則で当てる。同じ挿入で手首剛性 k を「手首カメラのたわみ ×
触覚の力」から同定し、ペグの形の対称性(n 回対称)と装置の対称性(2 本指は回転対称でない)を同変性の門で測る。
外から来るもの:
  * **定理**: Whitney 1982(原著は有料で未読、式は著者本人の MIT OCW 2.875 Class 3 スライド本文)—— 二点接触の深さ
    l₂(θ) = (2R − r(cosθ + secθ))/tanθ、くさびの境目 θ = c/μ。閉形式の接触レンチを真値つきの合成に使う。
  * **閉形式の接触力学**(Johnson 1985): Hertz、Cattaneo–Mindlin、Cerruti、無滑りねじり、ねじりの全滑り (3π/16)μPa。
  * **群の作用**: 回した形・回した場面の答えは同じだけ回る。
  * **物理エンジン(--full)**: MuJoCo の接触点・世界系の接触力・手首の力・トルクセンサ・手首ばねの設定値(600 N/m、1.5 N·m/rad)。

門(既定 10 本は numpy で CI 向けに例の数を減らしたもの、--full は MuJoCo の 9 本 + 重い numpy の 3 本):
  1 静力学の写像の往復 / 2 膜 1 枚の往復 / 3 膜の SO(2) 同変性と規則格子の罠 / 4 接触半径のビンの罠(P̂ の傾き)/
  5 Whitney の閉形式レンチ → 状態(くさびの境目の死角と幾何の検査)/ 6 壁の μ を逆に解く / 7 止まった時のくさび / かじり /
  8 輪郭の複素フーリエから n 回対称 / 9 形の同変性と 2 次モーメントの罠 / 10 剛性の当てはめと綴り壊し;
  --full: 11 手首 RGB-D の同変性と鏡映 / 12 膜の往復と Whitney を全組で / 13 輪郭 op の登録表経由 = 直呼び /
  14 写像 vs MuJoCo の力・トルクセンサ / 15 触覚のレンチ vs MuJoCo / 16 接触状態の一致率 / 17 二点の始まりの深さ vs 閉形式 /
  18 壁の μ を触覚だけで / 19 止まった時のくさび / かじり / 20 手首カメラのたわみ / 21 手首剛性 k_t・k_r / 22 場面を 90° 回す。
図(FULLSEYE_FIGURE_DIR があるとき、等倍): 既定 5 枚 = 膜 2 枚の像と読み vs 真値、Whitney の閉形式の挿入を膜で読む動く図(GIF)、
接触半径のビンの罠、レンチだけの規則の死角(θ–μ 平面に c/θ の線)、形の向き(フーリエ位相 vs 2 次モーメント);
--full でさらに 5 枚 = 挿入の動く図(穴の断面に接触点の真値と触覚の推定、手首カメラ、膜 2 枚、状態の帯)、4 走行の時系列、
手首剛性 F = kΔx、二点の始まりの深さ(閉形式 / MuJoCo / 触覚)、場面を 90° 回した時の判定一致率の表。
正直に: 膜は MuJoCo に無く、パッド荷重は静力学の写像(把持の左右分配は対称の仮定、ペグの慣性は無視)。合成と逆算は同じ閉形式族なので
膜の模型の誤りはここでは見えない。合成は比例載荷の Mindlin と無滑りねじり。マーカーの背景(陰影)は既知とした。走行は各条件 1 回。
Run: py -3.11 examples/poc_peg_insertion_tactile.py [--full] [--workers N]        (--full は mujoco)
"""
from __future__ import annotations

import collections
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import examplefig as figs  # noqa: E402
import pegsim as PS  # noqa: E402
import pegtactile as PT  # noqa: E402
import tacsim as T  # noqa: E402

KP = PS.peg_params()
FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}
DEG = math.pi / 180.0


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail), flush=True)


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def _workers():
    if "--workers" in sys.argv:
        return int(sys.argv[sys.argv.index("--workers") + 1])
    return 3


def through_membranes(F_c, M_c, axis, pad, ctx, torsion=True):
    """世界系の接触レンチ(ペグが穴から受ける、把持点まわり)→ 2 パッドの荷重 → 膜の像 2 枚 → 読み → 世界系のレンチ。
    公開 op だけの鎖: peg_wrench_to_pad_loads → pad_tactile_frame → pad_tactile_read → pad_loads_to_peg_wrench。"""
    a = np.asarray(axis, np.float64) / np.linalg.norm(axis)
    Rw = PT._rot_z_to(a)
    Fg = np.array([0.0, 0.0, -pad["peg_mass"] * 9.81])
    cmg = -(pad["com_below_top"] - pad["grasp_below_top"]) * a
    loads = PT.peg_wrench_to_pad_loads(Rw.T @ -(np.asarray(F_c) + Fg), Rw.T @ -(np.asarray(M_c) + np.cross(cmg, Fg)), pad)
    tq = loads["R"]["torsion"] if torsion else 0.0
    rd = {}
    frames = {}
    for side in ("R", "L"):
        frames[side] = PT.pad_tactile_frame(loads[side]["P"], loads[side]["q"], pad, ctx, torsion=tq)
        rd[side] = PT.pad_tactile_read(frames[side], pad, ctx)
    tq_hat = 0.5 * (rd["R"]["torsion"] + rd["L"]["torsion"]) if torsion else 0.0
    est = PT.pad_loads_to_peg_wrench(rd["R"]["P"], rd["R"]["q"], rd["L"]["P"], rd["L"]["q"], pad, torsion=tq_hat)
    return {"F": -(Rw @ est["F"]) - Fg, "M": -(Rw @ est["M"]) - np.cross(cmg, Fg), "loads": loads, "reads": rd, "frames": frames}


# ======================================================================================================================
def numpy_part(pad, ctx) -> dict:
    print("== 1. numpy の門(静力学・膜の往復と同変性・2 つの罠・Whitney の状態と μ・対称性・剛性)")
    t_all = time.time()
    out = {}
    # ── 1. 静力学の写像
    t0 = time.time()
    rng = np.random.default_rng(1)
    err = 0.0
    for _ in range(200):
        F = rng.normal(0, 0.5, 3)
        M = rng.normal(0, 4e-3, 3)
        L = PT.peg_wrench_to_pad_loads(F, M, pad)
        W = PT.pad_loads_to_peg_wrench(L["R"]["P"], L["R"]["q"], L["L"]["P"], L["L"]["q"], pad, torsion=L["R"]["torsion"])
        err = max(err, float(np.abs(W["F"] - F).max()), float(np.abs(W["M"] - M).max()), abs(W["grip"] - pad["grip"]))
    lost = _raises(lambda: PT.peg_wrench_to_pad_loads([2 * pad["grip"] + 0.1, 0, 0], [0, 0, 0], pad))
    slip = PT.peg_wrench_to_pad_loads([0, 0, 2.2 * pad["mu"] * pad["grip"]], [0, 0, 0], pad)
    _NUM["statics_identity"] = err
    gate("門 1 静力学の写像(接触レンチ ⇄ 2 パッドの P・q・ねじり)の往復が恒等(200 組、1e-12)、パッドが離れる荷重は ValueError(fail-closed)、"
         "|q| ≥ μP は例外にせず滑りの印", err < 1e-12 and lost and (not slip["ok"]) and slip["R"]["slip_ratio"] > 1.0,
         "最大誤差 %.1e、F_x = 2G₀ + 0.1 N で拒否 %s、F_z = 2.2μG₀ で slip_ratio %.2f(%.2f s)" % (err, lost, slip["R"]["slip_ratio"], time.time() - t0))
    # ── 2. 膜 1 枚の往復(CI 用に 3 組: 中くらい + ねじり / 全滑りの手前 / ゼロのせん断、P 2 段・向き 2 つ。20 組は --full)
    t0 = time.time()
    combos = [(4.5, 0.5, 3.5, 2.0e-3), (3.5, 2.5, 3.5, 0.0), (4.5, 0.0, 0.0, 0.0)]
    assert len(combos) >= 3
    eP = eq = et = eQs = 0.0
    for P, Q, ph, tq in combos:
        q = Q * np.array([math.cos(ph), math.sin(ph)])
        rd = PT.pad_tactile_read(PT.pad_tactile_frame(P, q, pad, ctx, torsion=tq), pad, ctx)
        if Q == 0.0:
            zero_jitter = rd
        eP = max(eP, abs(rd["P"] - P) / P)
        eq = max(eq, float(np.linalg.norm(rd["q"] - q)))
        et = max(et, abs(rd["torsion"] - tq))
        eQs = max(eQs, abs(rd["Q_stick"] - Q))
    _NUM.update(roundtrip_P_rel=eP, roundtrip_q_N=eq, roundtrip_torsion_Nm=et, roundtrip_Qstick_N=eQs)
    gate("門 2 膜 1 枚の往復(合成 = Hertz の陰影 + Cattaneo–Mindlin の Cerruti 畳み込み + 無滑りねじり → 読み = 画素ごとの接触半径 + マーカー追跡 + "
         "2 成分の Mindlin + 剛体回転)、%d 組: P の相対誤差 < 0.03 %%、q < 6 mN、ねじり < 0.03 mN·m、固着核の一様変位から逆に解いた第 2 実装 Q_stick < 8 mN"
         % len(combos), eP < 3e-4 and eq < 6e-3 and et < 3e-5 and eQs < 8e-3,
         "P %.4f %%、|Δq| %.2f mN、ねじり %.3f mN·m、Q_stick %.2f mN(%.2f s)" % (100 * eP, 1e3 * eq, 1e3 * et, 1e3 * eQs, time.time() - t0))
    # ── 3. SO(2) 同変性(3 方位: 格子の軸・対角・直交の軸)+ 規則格子の罠(ジッタ側のゼロ荷重は門 2 の 1 組を使う)
    t0 = time.time()
    rows = []
    for k in range(3):
        ph = math.pi * k / 4 + 0.05
        q = 1.0 * np.array([math.cos(ph), math.sin(ph)])
        rd = PT.pad_tactile_read(PT.pad_tactile_frame(4.0, q, pad, ctx), pad, ctx)
        rows.append((math.degrees(_angdiff(rd["phi"], ph)), rd["Q"]))
    assert len(rows) >= 3
    ang = max(abs(r_[0]) for r_ in rows)
    Qs = [r_[1] for r_ in rows]
    ctx_reg = PT.pad_context(pad, jitter_px=0.0)
    reg = PT.pad_tactile_read(PT.pad_tactile_frame(4.5, (0.0, 0.0), pad, ctx_reg), pad, ctx_reg)
    zr, zj = float(np.linalg.norm(reg["q"])), float(np.linalg.norm(zero_jitter["q"]))
    _NUM.update(so2_angle_deg=ang, so2_Q_spread=float(np.ptp(Qs)), zero_load_regular_N=zr, zero_load_jitter_N=zj)
    gate("門 3 膜の SO(2) 同変性(せん断 1 N の向きを格子の軸・対角・直交の軸の 3 方位に回す → 推定の向きが同じだけ回り、大きさは不変): 向き < 0.25°、|Q| の幅 < 1.2 %"
         "(マーカー格子は C4 + ジッタなので SO(2) は近似)。罠: 規則格子は全マーカーが同じ副画素位相で重心の pixel-locking が共通モードになり、"
         "せん断ゼロでも偽の q(ジッタ 0.5 px で 1/3 以下かつ < 2 mN)", ang < 0.25 and np.ptp(Qs) < 1.2e-2 and zj < zr / 3.0 and zj < 2e-3,
         "向き最大 %.3f°、|Q| 幅 %.2f mN、ゼロ荷重の偽 |q|: 規則格子 %.2f mN → ジッタ %.2f mN(%.2f s)" % (ang, 1e3 * np.ptp(Qs), 1e3 * zr, 1e3 * zj, time.time() - t0))
    # ── 4. 接触半径のビンの罠(CI 用に 5 点、--full の図は 17 点)
    t0 = time.time()
    out["slope"] = slope_trap(pad, ctx, np.linspace(3.6, 4.4, 5))
    sb, sp, bias = out["slope"]["slope_binned"], out["slope"]["slope_pixel"], out["slope"]["bias_pixel_N"]
    _NUM.update(slope_binned=sb, slope_pixel=sp, bias_pixel_mN=1e3 * bias)
    gate("門 4 罠: 2 パッドの差 F_x = P_L − P_R は P̂ の**傾き**の誤差に効く。tacsim.contact_radius_fit(半径ビン)は a が画素ピッチをまたぐたびに偏りの符号が変わり"
         "傾きが狂う → tacsim.contact_radius_fit_pixelwise(画素ごと、縁の帯 ±1.5 px を除く)で傾き < 0.1 %・偏り < 1 mN、ビン版はその 10 倍超",
         sp < 1e-3 and sb > 10 * sp and bias < 1e-3,
         "dP̂/dP − 1 の最大(5 点、0.2 N 刻み): ビン %.1f %% → 画素 %.3f %%、偏り %.2f mN(%.2f s)" % (100 * sb, 100 * sp, 1e3 * bias, time.time() - t0))
    # ── 5〜6. Whitney の閉形式レンチ → 状態、壁の μ(レンチだけは 36 組全部、膜を通すのは CI 用に 3 組)
    t0 = time.time()
    c_ = (KP["R"] - KP["r"]) / KP["R"]
    cases = whitney_cases()
    assert len(cases) == 36
    agree_w = agree_w0 = 0
    blind, mu_err_w = [], []
    for st, th, depth, mu, f1, f2 in cases:
        ww = PT.whitney_wrench(KP, st, th, depth, mu, f1, f2)
        truth = "one_point" if st in ("one_point", "mouth") else "two_point"
        sw = PT.contact_state_from_wrench(KP, ww["F"], ww["M_g"], ww["g"], ww["tip"], ww["axis"])
        sw0 = PT.contact_state_from_wrench(KP, ww["F"], ww["M_g"], ww["g"], ww["tip"], ww["axis"], geometry=False)
        agree_w += int(sw["state"] == truth)
        agree_w0 += int(sw0["state"] == truth)
        if sw0["state"] != truth:
            blind.append((math.degrees(th), mu, c_ / th))
        if st == "two_point":
            mu_err_w.append(abs(PT.two_point_forces(KP, ww["F"], ww["M_g"], ww["g"], ww["tip"], ww["axis"])["mu"] - mu))
    out["blind"] = blind
    out["cases"] = cases
    # 膜を通す 2 組: 先端一点 / くさびの境目の二点(レンチだけの規則が外れる組)。36 組全部は --full
    sub = [("one_point", 3.0, 0.3, 0.6), ("two_point", 3.0, 0.8, 0.6)]
    assert len(sub) == 2
    agree_t, mu2_t, mu1_t = 0, [], []
    for st, thd, mu, fn in sub:
        th = thd * DEG
        l2 = PS.two_point_depth(KP, th)
        depth = KP["chamfer"] + {"one_point": 0.4, "mouth": 0.6, "two_point": 1.0}[st] * l2
        ww = PT.whitney_wrench(KP, st, th, depth, mu, fn if st != "mouth" else 0.0, {"one_point": 0.0, "mouth": fn, "two_point": 1.3 * fn}[st])
        truth = "one_point" if st in ("one_point", "mouth") else "two_point"
        tw = through_membranes(ww["F"], ww["M_g"], ww["axis"], pad, ctx)
        stt = PT.contact_state_from_wrench(KP, tw["F"], tw["M"], ww["g"], ww["tip"], ww["axis"])
        agree_t += int(stt["state"] == truth)
        if st == "two_point":
            mu2_t.append(abs(PT.two_point_forces(KP, tw["F"], tw["M"], ww["g"], ww["tip"], ww["axis"])["mu"] - mu))
        elif stt["state"] == "one_point":
            mu1_t.append(abs(PT.friction_from_single_contact(tw["F"], stt["where"], stt["c"], ww["axis"])["mu"] - mu))
    assert len(mu2_t) == 1 and len(mu1_t) >= 1
    _NUM.update(whitney_wrench_only=agree_w0, whitney_with_geometry=agree_w, whitney_tactile=agree_t, blind=blind,
                mu2_wrench=max(mu_err_w), mu2_tactile=max(mu2_t), mu1_tactile=max(mu1_t))
    gate("門 5 Whitney の閉形式の接触レンチ(θ 1.5/3/4.5° × μ 0.3/0.8 × 法線力 2 段 × 先端一点 / 胴一点 / 二点 = 36 組)→ 接触状態: レンチだけの規則は"
         "くさびの境目の帯(口と先端を結ぶ線の傾き c/θ が μ に近い |c/θ − μ| < 0.1: 先端の摩擦円錐の縁が口の接触点を通り二点が口の一点に見える)でだけ外れ、"
         "Whitney の幾何(深さ ≥ W + l₂(θ) なら二点を強制)を足すと 36/36。膜を通した 2 組(境目の二点を含む)も全一致",
         agree_w == 36 and agree_w0 < 36 and all(abs(cb - mu) < 0.1 for _, mu, cb in blind) and agree_t == len(sub),
         "レンチだけ %d/36(外れ %s)、幾何つき %d/36、膜経由 %d/%d(%.2f s)"
         % (agree_w0, ["θ %.1f° μ %.1f c/θ %.3f" % b for b in blind], agree_w, agree_t, len(sub), time.time() - t0))
    gate("門 6 壁の摩擦 μ を接触レンチから逆に解く: 二点(両点が滑る Whitney の平面釣り合い、3 式 2 未知 + μ の 1 次元探索)は真値のレンチ 12 組で < 1e-3、"
         "膜経由(法線力 0.6 N)で < 0.005、一点(先端 = |F_z|/|F_水平|、胴 = 軸方向 / 軸に垂直)は膜経由で < 0.01",
         max(mu_err_w) < 1e-3 and max(mu2_t) < 0.005 and max(mu1_t) < 0.01,
         "二点: レンチ %.1e、膜 %.4f / 一点: 膜 %.4f" % (max(mu_err_w), max(mu2_t), max(mu1_t)))
    # ── 7. 止まった時のくさび / かじり
    sv = [PT.stall_verdict(KP, (c_ / mu) * f, mu)["verdict"] for mu in (0.3, 0.8) for f in (0.98, 1.02)]
    unk = PT.stall_verdict(KP, 0.05, None)["verdict"]
    gate("門 7 二点で止まった時の Whitney の判定 θ > c/μ̂(くさび)/ ≤(かじり)が境目の ±2 %% で切り替わる(μ 0.3: c/μ = %.2f°、μ 0.8: %.2f°)、"
         "μ̂ が無ければ推測せず unknown" % (math.degrees(c_ / 0.3), math.degrees(c_ / 0.8)),
         sv == ["jamming", "wedging", "jamming", "wedging"] and unk == "unknown", "%s、μ̂ なし → %s" % (sv, unk))
    # ── 8〜9. 対称性
    t0 = time.time()
    out["symmetry"] = symmetry_part(angles=np.radians([45.0, 160.0]) + 0.1)
    got, eqrows = out["symmetry"]["orders"], out["symmetry"]["rows"]
    want = {"circle": 0, "triangle": 3, "square": 4, "hexagon": 6, "keyed": 1}
    gate("門 8 輪郭(Fullseye の threshold_sub_pix)の複素フーリエ係数(fourierdesc.contour_fourier_complex)の非零次数から n 回対称: 円 0(連続)・三角 3・"
         "四角 4・六角 6・キー付き 1", got == want, "%s" % got)
    okF = all(eqrows[k_]["F_pos"] < 0.25 and (eqrows[k_]["n"] < 2 or eqrows[k_]["F_ang"] < 0.05) for k_ in eqrows) and eqrows["keyed"]["F_ang"] < 1.0
    trapM = all(eqrows[k_]["M_ang"] > 5.0 for k_ in ("triangle", "square", "hexagon")) and eqrows["keyed"]["M_ang"] < 1.0
    _NUM["symmetry"] = {k_: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k_, v in eqrows.items()}
    gate("門 9 同変性(equivariance_check、形を 2 角度回して描き直す = 画像の補間なし): フーリエ位相の向き arg(c₁₋ₙ c₁ⁿ⁻¹)/n は n ≥ 3 で < 0.05°、"
         "n = 1 は弱い c₂ から < 1°、重心 < 0.25 px。罠: 2 次モーメントの向き(blob2d)は n ≥ 3 で慣性が等方になり 5° 超外れる(n = 1 では < 1° で使える)",
         okF and trapM, "フーリエ %s° / モーメント %s°(%.2f s)"
         % ({k_: round(v["F_ang"], 3) for k_, v in eqrows.items() if v["n"] >= 1}, {k_: round(v["M_ang"], 1) for k_, v in eqrows.items() if v["n"] >= 1},
            time.time() - t0))
    # ── 10. 剛性の当てはめと綴り壊し
    x = np.linspace(-0.6e-3, 0.6e-3, 41)
    fit = PT.wrist_stiffness_fit(x, 600.0 * x + np.random.default_rng(3).normal(0, 0.003, x.size))
    bad = [_raises(lambda: PT.wrist_stiffness_fit(np.full(10, 1e-4) + np.arange(10) * 1e-9, np.ones(10))),
           _raises(lambda: PT.whitney_wrench(KP, "tow_point", 0.05, 0.005, 0.3, 0.1)),
           _raises(lambda: PT.symmetric_peg_shape("hexagn")),
           _raises(lambda: PT.pad_tactile_frame(0.0, (0, 0), pad, ctx)),
           _raises(lambda: PT.pad_params(nu=0.6)),
           _raises(lambda: PT.pad_params(grip=40.0)),
           _raises(lambda: PT.friction_from_single_contact([0, 0, 1], "tipp", None, [0, 0, 1])),
           _raises(lambda: PT.contact_state_from_wrench(KP, [0, 0, float("nan")], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 1]))]
    _NUM["k_synthetic"] = fit["k"]
    gate("門 10 手首剛性 F = kΔx(原点を通る最小二乗)は合成 600 N/m・雑音 3 mN で < 0.5 %%、fail-closed %d 件: Δx の幅 20 µm 未満(悪条件)、状態名・形の名・"
         "接触点の名の綴り違い、P = 0 の膜、ν > 0.5、視野が 5a に足りない把持力、nan のレンチ → 全部 ValueError" % len(bad),
         abs(fit["k"] / 600 - 1) < 5e-3 and all(bad), "k̂ = %.2f N/m、拒否 %s" % (fit["k"], bad))
    print("  numpy の門: %.1f s" % (time.time() - t_all))
    return out


def whitney_cases():
    """θ 1.5/3/4.5° × μ 0.3/0.8 × 法線力 0.15/0.6 N × 先端一点 / 胴一点 / 二点 = 36 組(二点は深さ W + l₂(θ) で胴も縁に触れる)。"""
    cases = []
    for th_deg in (1.5, 3.0, 4.5):
        th = th_deg * DEG
        l2 = PS.two_point_depth(KP, th)
        for mu in (0.3, 0.8):
            for fn in (0.15, 0.6):
                cases.append(("one_point", th, KP["chamfer"] + 0.4 * l2, mu, fn, 0.0))
                cases.append(("mouth", th, KP["chamfer"] + 0.6 * l2, mu, 0.0, fn))
                cases.append(("two_point", th, KP["chamfer"] + l2, mu, fn, 1.3 * fn))
    return cases


def slope_trap(pad, ctx, Ps):
    """ビン版と画素ごとの接触半径で P̂ − P を比べる(陰影 → 法線は同じ)。"""
    eb, ep = [], []
    for P in Ps:
        fr = PT.pad_tactile_frame(float(P), (0.0, 0.3), pad, ctx)
        rec = T.membrane_recover(fr["shading"], ctx["lights"], pad["pitch"], ambient=0.03)
        ab = T.contact_radius_fit(rec["normals"], ctx["X"], ctx["Y"], pad["R"], pad["pitch"], centre_xy=(0.0, 0.0))["a"]
        apx = T.contact_radius_fit_pixelwise(rec["normals"], ctx["X"], ctx["Y"], pad["R"], ab)["a"]
        eb.append(T.hertz_force(pad["R"], pad["Es"], a=ab) - P)
        ep.append(T.hertz_force(pad["R"], pad["Es"], a=apx) - P)
    eb, ep = np.array(eb), np.array(ep)
    assert len(Ps) >= 3
    return {"P": np.asarray(Ps, float), "err_binned": eb, "err_pixel": ep, "slope_binned": float(np.abs(np.diff(eb) / np.diff(Ps)).max()),
            "slope_pixel": float(np.abs(np.diff(ep) / np.diff(Ps)).max()), "bias_pixel_N": float(np.abs(ep).max())}


def _fourier_op(img):
    so = PT.symmetry_order_contour(PT._level_contour(img))
    return so["centroid"][0], so["centroid"][1], so["angle"]


def _moment_op(img):
    import blob2d
    f = blob2d.blob_features(blob2d.blob_label(img > 0.5, 8))
    return float(f["row"][0]), float(f["col"][0]), float(f["angle"][0])


def symmetry_part(angles, size=160):
    """5 形状の n 回対称の次数と、形を回した時のフーリエ位相 / 2 次モーメントの向きの同変性。中心は画素格子からずらす。"""
    cen = ((size - 1) / 2 + 0.37, (size - 1) / 2 - 0.21)            # (col, row)
    got, rows = {}, {}
    for name in PT.SHAPES:
        img = PT.symmetric_peg_shape(name, size, 50.0, 0.3, centre=cen)
        n = PT.symmetry_order_contour(PT._level_contour(img))["n"]
        got[name] = n

        def rend(th, name=name):
            return PT.symmetric_peg_shape(name, size, 50.0, 0.3 + th, centre=cen)
        eF = PT.equivariance_check(rend, _fourier_op, angles, n, (cen[1], cen[0]))
        eM = PT.equivariance_check(rend, _moment_op, angles, 2 if n in (1, 2) else n, (cen[1], cen[0]))
        rows[name] = {"n": n, "F_pos": eF["pos_err_px"], "F_ang": eF["ang_err_deg"], "M_pos": eM["pos_err_px"], "M_ang": eM["ang_err_deg"]}
    return {"orders": got, "rows": rows}


# ======================================================================================================================
def full_numpy_part(pad, ctx, out) -> dict:
    """--full の重い numpy の門(手首 RGB-D の合成 6 枚、膜の往復と Whitney を全組、輪郭 op の登録表経由)。"""
    print("== 2. --full: 重い numpy の門")
    t0 = time.time()
    rows = []
    for th_deg in (0.0, 45.0, 90.0, 180.0, 270.0, 315.0):
        th = th_deg * DEG
        off = 1.0e-3 * np.array([math.cos(th), math.sin(th)])
        ax = np.array([math.sin(2 * DEG) * math.cos(th), math.sin(2 * DEG) * math.sin(th), math.cos(2 * DEG)])
        sy = PS.peg_synthetic_rgbd(KP, tip_xyz=(off[0], off[1], 0.004), axis=ax, width=320, height=240)
        r = PS.peg_offset_from_rgbd(sy["rgb"], sy["depth"], sy["K"], sy["R_cam_to_world"], r_peg=KP["r"], hole_radius=KP["R"] + KP["chamfer"])
        rows.append((th_deg, np.array([r["dx"], r["dy"]]) - off))
    assert len(rows) == 6
    emax = max(float(np.linalg.norm(e)) for _, e in rows)
    mirror = max(float(np.linalg.norm(rows[i][1] * np.array([1, -1]) - rows[j][1])) for i, j in ((1, 5), (2, 4)))
    _NUM.update(rgbd_equiv_um=1e6 * emax, rgbd_mirror_um=1e6 * mirror)
    gate("門 11 手首 RGB-D の相対ずれ(pegsim.peg_offset_from_rgbd)の同変性: 場面を穴の軸まわりに 6 角度回す → (dx, dy) が R(θ) で回る(< 5 µm)。残差はカメラ 1 台"
         "(−x 側)の装置が持つ鏡映 y ↔ −y どおり(45°/315° と 90°/270° で < 0.5 µm)= 装置の群は SO(2) でなく鏡映だけ",
         emax < 5e-6 and mirror < 0.5e-6, "最大 %.2f µm、鏡映の差 %.3f µm(%.1f s)" % (1e6 * emax, 1e6 * mirror, time.time() - t0))
    # 膜の往復 20 組 + Whitney 36 組を膜経由で(既定の門の母集団全部)
    t0 = time.time()
    eP = eq = et = eQs = 0.0
    n_rt = 0
    for P in (3.5, 4.5):
        for Q in (0.0, 0.05, 0.5, 2.5):
            for ph in (0.3, 3.5):
                for tq in ((0.0,) if Q != 0.5 else (0.0, 2.0e-3)):
                    q = Q * np.array([math.cos(ph), math.sin(ph)])
                    rd = PT.pad_tactile_read(PT.pad_tactile_frame(P, q, pad, ctx, torsion=tq), pad, ctx)
                    eP = max(eP, abs(rd["P"] - P) / P)
                    eq = max(eq, float(np.linalg.norm(rd["q"] - q)))
                    et = max(et, abs(rd["torsion"] - tq))
                    eQs = max(eQs, abs(rd["Q_stick"] - Q))
                    n_rt += 1
    agree_t, mu2, mu2_hi, mu1 = 0, [], [], []
    for st, th, depth, mu, f1, f2 in out["cases"]:
        ww = PT.whitney_wrench(KP, st, th, depth, mu, f1, f2)
        truth = "one_point" if st in ("one_point", "mouth") else "two_point"
        tw = through_membranes(ww["F"], ww["M_g"], ww["axis"], pad, ctx)
        stt = PT.contact_state_from_wrench(KP, tw["F"], tw["M"], ww["g"], ww["tip"], ww["axis"])
        agree_t += int(stt["state"] == truth)
        if st == "two_point":
            e2 = abs(PT.two_point_forces(KP, tw["F"], tw["M"], ww["g"], ww["tip"], ww["axis"])["mu"] - mu)
            mu2.append(e2)
            if min(f1, f2) >= 0.5:
                mu2_hi.append(e2)
        elif stt["state"] == "one_point":
            mu1.append(abs(PT.friction_from_single_contact(tw["F"], stt["where"], stt["c"], ww["axis"])["mu"] - mu))
    assert n_rt == 20 and len(mu2) == 12 and len(mu2_hi) >= 1 and len(mu1) >= 1
    _NUM.update(full_roundtrip={"P_rel": eP, "q_N": eq, "torsion_Nm": et, "Qstick_N": eQs}, full_whitney_tactile=agree_t,
                full_mu2=max(mu2), full_mu2_hi=max(mu2_hi), full_mu1=max(mu1))
    gate("門 12 母集団全部: 膜 1 枚の往復 20 組(P < 0.05 %、q < 8 mN、ねじり < 0.06 mN·m、Q_stick < 15 mN)、Whitney の 36 組を膜経由で 36/36、"
         "二点の μ は法線力 ≥ 0.5 N で < 0.01・0.15 N でも < 0.03、一点の μ < 0.03",
         eP < 5e-4 and eq < 8e-3 and et < 6e-5 and eQs < 15e-3 and agree_t == 36 and max(mu2_hi) < 0.01 and max(mu2) < 0.03 and max(mu1) < 0.03,
         "往復 P %.4f %%・q %.2f mN・ねじり %.3f mN·m・Q_stick %.2f mN、膜経由 %d/36、μ 二点 %.4f(≥ 0.5 N: %.4f)・一点 %.4f(%.1f s)"
         % (100 * eP, 1e3 * eq, 1e3 * et, 1e3 * eQs, agree_t, max(mu2), max(mu2_hi), max(mu1), time.time() - t0))
    # 輪郭 op: 登録表経由 = 直呼び
    t0 = time.time()
    import ops
    reg = {o.name: o for o in ops.REGISTRY}["threshold_sub_pix"]
    worst = 0.0
    for name in PT.SHAPES:
        img = PT.symmetric_peg_shape(name, 160, 50.0, 0.3)
        c_direct = PT._level_contour(img)
        c_reg = max(reg.fn(img, 0.6, 0.5)["cs"], key=len)
        worst = max(worst, float(np.abs(np.asarray(c_reg) - c_direct).max()) if np.shape(c_reg) == c_direct.shape else float("inf"))
    gate("門 13 輪郭は Fullseye の登録 op threshold_sub_pix(ops の登録表経由)と、pegtactile が CI の時間のために直に呼ぶ同じ実装で、5 形状とも同じ点列",
         worst == 0.0, "最大の差 %.1e px(%.1f s)" % (worst, time.time() - t0))
    return out


RUNS = {
    "A": dict(eps_mm=(0.6, 0.0), tilt_deg=3.0, t_max=5.0),
    "B": dict(eps_mm=(-0.6, 0.0), tilt_deg=3.0, t_max=5.5),
    "C": dict(eps_mm=(0.6, 0.0), tilt_deg=2.0, t_max=6.5),
    "D": dict(eps_mm=(0.6, 0.0), tilt_deg=4.0, t_max=4.5),
    "E": dict(eps_mm=(0.3, 0.0), tilt_deg=4.5, mu=0.8, release=True, t_max=6.0),
    "F": dict(eps_mm=(0.3, 0.0), tilt_deg=4.5, mu=0.3, release=True, t_max=6.0),
    "G": dict(eps_mm=(0.6, 0.0), tilt_deg=3.0, t_max=5.0, azimuth_deg=90.0),
}


def full_part(pad, ctx, out) -> dict:
    print("== 3. --full: MuJoCo の門(写像 vs 力センサ・触覚のレンチ・状態・二点の始まり・μ・くさび / かじり・手首カメラ・剛性・同変性)")
    try:
        import mujoco  # noqa: F401
    except ImportError:
        skip("門 14〜22", "mujoco が無い")
        return out
    t0 = time.time()
    figs_on = figs.enabled()
    eps = {}
    for name, cfg in RUNS.items():
        eps[name] = PT.pegtactile_episode_run(pad=pad, render_wrist=True, render_side=(figs_on and name == "A"), keep_images=(figs_on and name == "A"),
                                              frame_every=0.04 if name in ("A", "G") else 0.06, **cfg)
        print("     走行 %s: %s、%d フレーム、%.1f s(シム %.1f s)" % (name, eps[name]["status"], len(eps[name]["frames"]), eps[name]["wall_s"], eps[name]["sim_s"]),
              flush=True)
    t_sim = time.time() - t0
    t1 = time.time()
    nw = _workers()
    n_new = PT.pegtactile_prefetch(list(eps.values()), pad, ctx, workers=nw, torsion=True, log=lambda s: print("     " + s))
    n_new += PT.pegtactile_prefetch([eps["G"]], pad, ctx, workers=nw, torsion=False, log=lambda s: print("     " + s))
    t_tac = time.time() - t1
    t2 = time.time()
    res = {name: PT.pegtactile_process_episode(ep, pad, ctx) for name, ep in eps.items()}
    res["G_notorsion"] = PT.pegtactile_process_episode(eps["G"], pad, ctx, torsion=False)
    print("     膜の合成 + 読み %d 枚(%d プロセス)%.1f s、後処理 %.1f s" % (n_new, nw, t_tac, time.time() - t2), flush=True)
    out.update(eps=eps, res=res)
    main = ("A", "B", "C", "D")
    # ── 14. 写像 vs 手首の力・トルクセンサ
    dmax = dtq = dz = 0.0
    nqs = 0
    for name in main:
        for i, fr in enumerate(eps[name]["frames"]):
            if res[name]["qs"][i] and (fr["duty"] >= 0.999 or fr["duty"] == 0.0):
                dmax = max(dmax, float(np.linalg.norm((fr["sensor_force"] - fr["F_pad_w"])[:2])))
                dz = max(dz, abs(float((fr["sensor_force"] - fr["F_pad_w"])[2])))
                dtq = max(dtq, float(np.linalg.norm(fr["sensor_torque"] - (fr["M_pad_w"] + np.cross(fr["g"] - fr["top"], fr["F_pad_w"])))))
                nqs += 1
    chat = [float(np.linalg.norm(fr["sensor_force"] - fr["F_pad_w"])) for name in main for fr in eps[name]["frames"] if 0.0 < fr["duty"] < 0.999]
    _NUM.update(map_vs_sensor={"force_N": dmax, "torque_Nm": dtq, "vertical_N": dz, "n": nqs, "chatter_n": len(chat),
                               "chatter_med_N": float(np.median(chat)) if chat else None})
    gate("門 14 写像の符号と静力学を MuJoCo 自身の手首の力・トルクセンサで: 準静的なフレームで「露光平均の接触レンチ + 重力」から作ったパッドの合力 = センサ"
         "(水平 < 1 mN、トルク < 0.3 mN·m)。鉛直は手首の z ばねの振動の慣性が乗り写像の外、露光中に接触が入れ替わる跳ねる区間も対象外(数だけ)",
         nqs > 0 and dmax < 1e-3 and dtq < 3e-4,
         "準静的 %d フレーム: 水平 %.2f mN、トルク %.3f mN·m(鉛直 %.1f mN)/ 跳ねる区間 %d フレーム 中央 %.1f mN"
         % (nqs, 1e3 * dmax, 1e3 * dtq, 1e3 * dz, len(chat), 1e3 * (np.median(chat) if chat else 0.0)))
    # ── 15. 触覚のレンチ vs MuJoCo
    eF, eM = [], []
    for name in main:
        for fr, row in zip(eps[name]["frames"], res[name]["rows"]):
            if np.linalg.norm(fr["Fc"]) > 0.05:
                eF.append(float(np.linalg.norm(row["tw"]["F"] - fr["Fc"])))
                eM.append(float(np.linalg.norm(row["tw"]["M"] - fr["Mc"])))
    assert len(eF) >= 50
    _NUM.update(tactile_wrench={"F_med_mN": 1e3 * float(np.median(eF)), "F_max_mN": 1e3 * float(np.max(eF)), "M_med_mNm": 1e3 * float(np.median(eM)),
                                "M_max_mNm": 1e3 * float(np.max(eM)), "n": len(eF)})
    gate("門 15 触覚(膜 2 枚の像から)で復元した接触レンチ vs MuJoCo の接触(露光平均)、接触中の全フレーム: |ΔF| 中央 < 5 mN・最大 < 15 mN、|ΔM| 中央 < 0.05・"
         "最大 < 0.2 mN·m", np.median(eF) < 5e-3 and np.max(eF) < 15e-3 and np.median(eM) < 5e-5 and np.max(eM) < 2e-4,
         "%d フレーム: |ΔF| 中央 %.2f / 最大 %.2f mN、|ΔM| 中央 %.3f / 最大 %.3f mN·m" % (len(eF), 1e3 * np.median(eF), 1e3 * np.max(eF), 1e3 * np.median(eM), 1e3 * np.max(eM)))
    # ── 16. 接触状態の一致率
    conf, confw = collections.Counter(), collections.Counter()
    for name in main:
        for row in res[name]["rows"]:
            conf[(row["state_true"], row["st_tactile"]["state"])] += 1
            confw[(row["state_true"], row["st_wrench"]["state"])] += 1
    n_all = sum(conf.values())
    assert n_all >= 100
    acc_t = sum(v for (a, b), v in conf.items() if a == b) / n_all
    acc_w = sum(v for (a, b), v in confw.items() if a == b) / n_all
    tw_agree = sum(1 for name in main for row in res[name]["rows"] if row["st_tactile"]["state"] == row["st_wrench"]["state"]) / n_all
    _NUM.update(state_acc={"tactile": acc_t, "wrench": acc_w, "tactile_eq_wrench": tw_agree, "n": n_all,
                           "misses": {"%s>%s" % k_: v for k_, v in conf.items() if k_[0] != k_[1]}})
    gate("門 16 接触状態(無接触 / 面取り / 一点 / 二点)の一致率、4 走行(θ 2/3/4°、横ずれ ±0.6 mm)の全フレーム: 触覚 vs MuJoCo の接触 ≥ 95 %、同じ規則に"
         "真値のレンチ(上限)≥ 95 %、触覚 = 上限 ≥ 98 %", acc_t >= 0.95 and acc_w >= 0.95 and tw_agree >= 0.98,
         "%d フレーム: 触覚 %.1f %%、上限 %.1f %%、触覚 = 上限 %.1f %%、外れ %s" % (n_all, 100 * acc_t, 100 * acc_w, 100 * tw_agree, _NUM["state_acc"]["misses"]))
    # ── 17. 二点の始まりの深さ vs 閉形式
    onset = {}
    for name in main:
        rows = res[name]["rows"]
        it = next((i for i in range(len(rows) - 1) if rows[i]["st_tactile"]["state"] == "two_point" and rows[i + 1]["st_tactile"]["state"] == "two_point"), None)
        iu = next((i for i in range(len(rows) - 1) if rows[i]["state_true"] == "two_point" and rows[i + 1]["state_true"] == "two_point"), None)
        if it is None or iu is None:
            onset[name] = None
            continue
        r_ = rows[it]
        th_hat = math.atan2(math.hypot(*r_["axis_hat"][:2]), r_["axis_hat"][2])
        d_hat = -float(r_["tip_hat"][2])
        d_cf = KP["chamfer"] + PS.two_point_depth(KP, th_hat)
        onset[name] = {"theta_deg": math.degrees(th_hat), "depth_tactile_mm": 1e3 * d_hat, "depth_closed_mm": 1e3 * d_cf,
                       "depth_mujoco_mm": 1e3 * rows[iu]["depth_true"], "theta_mujoco_deg": math.degrees(rows[iu]["tilt_true"]), "err_mm": 1e3 * (d_hat - d_cf)}
    errs = [abs(v["err_mm"]) for v in onset.values() if v]
    out["onset"] = onset
    _NUM["onset"] = onset
    gate("門 17 二点接触の始まりの深さ: 触覚が二点と言い始めたフレームの推定深さ(手首カメラの軸 + k̂ で補った z 圧縮)vs Whitney の閉形式 W + l₂(θ̂)(θ̂ は手首カメラ)、"
         "4 走行で < 0.15 mm", len(errs) == 4 and max(errs) < 0.15,
         "; ".join("%s θ %.2f°: 触覚 %.3f / 閉形式 %.3f / MuJoCo %.3f mm" % (k_, v["theta_deg"], v["depth_tactile_mm"], v["depth_closed_mm"], v["depth_mujoco_mm"])
                   for k_, v in onset.items() if v))
    # ── 18. 壁の μ を触覚だけで
    mu1, mu2 = [], []
    for name in main:
        for fr, row in zip(eps[name]["frames"], res[name]["rows"]):
            st = row["st_tactile"]
            if fr["vel_z"] > -1e-4:
                continue
            if st["state"] in ("one_point", "chamfer") and np.linalg.norm(row["tw"]["F"]) > 0.1:
                m_ = PT.friction_from_single_contact(row["tw"]["F"], st["where"], st["c"], row["axis_hat"], chamfer=(st["state"] == "chamfer"))["mu"]
                if m_ is not None:
                    mu1.append(m_)
            if st["state"] == "two_point":
                tp = PT.two_point_forces(KP, row["tw"]["F"], row["tw"]["M"], row["g_hat"], row["tip_hat"], row["axis_hat"])
                if min(tp["fn_tip"], tp["fn_mouth"]) > 0.3:
                    mu2.append(tp["mu"])
    assert len(mu1) >= 20 and len(mu2) >= 20
    p90 = float(np.percentile(np.abs(np.array(mu2) - 0.3), 90))
    _NUM.update(mu_tactile={"one_point_med": float(np.median(mu1)), "one_point_n": len(mu1), "two_point_med": float(np.median(mu2)),
                            "two_point_n": len(mu2), "two_point_p90": p90})
    gate("門 18 壁の摩擦 μ(MuJoCo の friction = 0.3)を触覚だけで: 一点の滑り(面取り 45° / 壁 / 口の縁、降下中、|F| > 0.1 N)の中央値 0.3 ± 0.01、二点の滑り"
         "(両法線力 > 0.3 N)の Whitney 分解は中央値 0.3 ± 0.005・90 % が ±0.015", abs(np.median(mu1) - 0.3) < 0.01 and abs(np.median(mu2) - 0.3) < 0.005 and p90 < 0.015,
         "一点 %d フレーム 中央 %.4f、二点 %d フレーム 中央 %.4f(90 %% 点 %.4f)" % (len(mu1), np.median(mu1), len(mu2), np.median(mu2), p90))
    # ── 19. 止まった時のくさび / かじり
    verdict = {}
    for name in ("E", "F"):
        ep, r = eps[name], res[name]
        mus = []
        for fr, row in zip(ep["frames"], r["rows"]):
            st = row["st_tactile"]
            if row["phase"] == "descend" and st["state"] in ("one_point", "chamfer") and fr["vel_z"] < -1e-4 and np.linalg.norm(row["tw"]["F"]) > 0.1:
                m_ = PT.friction_from_single_contact(row["tw"]["F"], st["where"], st["c"], row["axis_hat"], chamfer=(st["state"] == "chamfer"))["mu"]
                if m_ is not None:
                    mus.append(m_)
        stl = next((row for row in r["rows"] if row["phase"] == "stalled"), None)
        mu_hat = float(np.median(mus)) if mus else None
        th_hat = math.atan2(math.hypot(*stl["axis_hat"][:2]), stl["axis_hat"][2]) if stl else float("nan")
        v_hat = PT.stall_verdict(KP, th_hat, mu_hat)["verdict"] if stl else "no_stall"
        v_true = "wedging" if (stl and PS.wedging_check(dict(KP, mu=RUNS[name]["mu"]), stl["tilt_true"])["possible"]) else "jamming"
        verdict[name] = {"mu_hat": mu_hat, "n_mu": len(mus), "theta_deg": math.degrees(th_hat), "verdict": v_hat, "truth": v_true, "status": ep["status"]}
    _NUM["stall_verdict"] = verdict
    gate("門 19 二点で止まった時のくさび / かじり: 同じ挿入の一点の滑りで触覚から読んだ μ̂ と手首カメラの θ̂ で θ̂ > c/μ̂ → 真値(MuJoCo の friction と傾きで"
         " Whitney の wedging_check)と一致(μ 0.8 → くさび、μ 0.3 → かじり)",
         all(v["verdict"] == v["truth"] for v in verdict.values()) and all(v["status"] == "stalled" for v in verdict.values()),
         "; ".join("%s: μ̂ %s(%d)θ̂ %.2f° → %s(真 %s)" % (k_, ("%.3f" % v["mu_hat"]) if v["mu_hat"] is not None else "—", v["n_mu"], v["theta_deg"], v["verdict"], v["truth"])
                   for k_, v in verdict.items()))
    # ── 20〜21. 手首カメラと手首剛性
    ks, ktf, krs = {}, {}, {}
    dxe = the = 0.0
    for name in main:
        r = res[name]
        ks[name], ktf[name], krs[name] = r["k_fit"]["k"], r["k_fit_true_force"]["k"], r["kr_fit"]["k"]
        for fr, row in zip(eps[name]["frames"], r["rows"]):
            dxe = max(dxe, float(np.abs(row["p0"] - row["p0_true"]).max()))
            the = max(the, abs(math.degrees(row["cam"]["tilt_y"] - fr["q_hinge"][1])))
    kt_err = max(abs(v / KP["k_trans"] - 1) for v in ks.values())
    kr_err = max(abs(v / KP["k_rot"] - 1) for v in krs.values())
    _NUM.update(wrist_cam={"dx_um": 1e6 * dxe, "tilt_deg": the}, k_t=ks, k_t_true_force=ktf, k_r=krs, k_t_err=kt_err, k_r_err=kr_err)
    gate("門 20 手首カメラ(RGB-D 1 枚 → 既知半径の円柱 → 軸の直線を z = 0 で切る)の手首のたわみ vs MuJoCo の関節値: < 3 µm、傾き < 0.01°", dxe < 3e-6 and the < 0.01,
         "最大 %.2f µm、傾き最大 %.4f°" % (1e6 * dxe, the))
    gate("門 21 手首剛性の画像同定(F = 触覚の接触力、Δx = 手首カメラ、触覚が 3 フレーム続けて二点と言ったフレーム = 跳ねない区間): k_t は 4 走行とも設定値 %.0f N/m の ±1 %%、"
         "回転 k_r(触覚のモーメント + 推定ヒンジ)は %.1f N·m/rad の ±3 %%" % (KP["k_trans"], KP["k_rot"]), kt_err < 0.01 and kr_err < 0.03,
         "k_t %s(真値の力なら %s)、k_r %s" % ({k_: round(v, 1) for k_, v in ks.items()}, {k_: round(v, 1) for k_, v in ktf.items()}, {k_: round(v, 3) for k_, v in krs.items()}))
    # ── 22. 場面を 90° 回す
    fa = [float(np.linalg.norm(fr["Fc"])) for fr in eps["A"]["frames"]]
    fg = [float(np.linalg.norm(fr["Fc"])) for fr in eps["G"]["frames"]]
    nmin = min(len(fa), len(fg))
    assert nmin >= 20
    dfa = np.abs(np.array(fa[:nmin]) - np.array(fg[:nmin]))
    phys = float(np.median(dfa[np.array(fa[:nmin]) > 0.05]))
    st_same = sum(1 for i in range(nmin) if eps["A"]["frames"][i]["state"] == eps["G"]["frames"][i]["state"]) / nmin

    def acc(r):
        return sum(1 for row in r["rows"] if row["st_tactile"]["state"] == row["state_true"]) / len(r["rows"])
    accA, accG, accG0 = acc(res["A"]), acc(res["G"]), acc(res["G_notorsion"])
    trat = max(row["tw"]["loads"]["R"]["torsion_ratio"] for row in res["G"]["rows"])
    out["equiv"] = {"accA": accA, "accG": accG, "accG0": accG0, "phys_N": phys, "state_same": st_same, "torsion_ratio": trat}
    _NUM["equivariance_runs"] = out["equiv"]
    gate("門 22 同変性(MuJoCo): 場面をグリッパに対して 90° 回す。物理は同変(36 角形の穴は 90° で自分に重なる): |F| の差の中央 < 5 mN・状態列 ≥ 97 % 一致。"
         "触覚はモーメントがせん断の偶力からパッドの**ねじり**へ移るので、ねじりを読めば 0° の走行と ±3 %、捨てると 10 ポイント超落ちる(二本指は回転対称でない)",
         phys < 5e-3 and st_same >= 0.97 and abs(accG - accA) < 0.03 and accG0 < accG - 0.1,
         "|ΔF| 中央 %.2f mN、状態列 %.1f %%、触覚 0°: %.1f %% / 90°: %.1f %% / 90° ねじり無し: %.1f %%、ねじりの全滑り比 最大 %.2f"
         % (1e3 * phys, 100 * st_same, 100 * accA, 100 * accG, 100 * accG0, trat))
    _NUM["mujoco_s"] = {"runs": t_sim, "tactile": t_tac, "total": time.time() - t0}
    print("  MuJoCo の門: %.1f s(走行 %.1f + 膜 %.1f)" % (time.time() - t0, t_sim, t_tac))
    return out


# ======================================================================================================================
# 図(examplefig = Fullseye の annotate 族で組む。等倍、縮小・減色しない)
_COL = {"none": (0.6, 0.6, 0.6), "chamfer": (0.35, 0.63, 0.9), "one_point": (0.94, 0.67, 0.16), "two_point": (0.86, 0.24, 0.24),
        "unknown": (0.47, 0.24, 0.63), "other": (0.24, 0.24, 0.24)}


def _membrane_panel(frame, rd, pad, ctx, title):
    """膜の像(等倍 n×n)に、追跡した変位の矢印(×12)と読んだ接触円を描く(RGB float)。"""
    g = np.clip(frame["rgb"].mean(-1) / max(1e-9, float(frame["shading"].mean(-1).max())), 0, 1)
    img = np.repeat((0.08 + 0.6 * g)[..., None], 3, axis=2)
    tr = rd["track"]
    a_px = rd["a"] / pad["pitch"]
    c0 = ctx["c0"]
    for p0, u in zip(tr["p0"], tr["u"]):
        if math.hypot(p0[0] - c0, p0[1] - c0) > 2.6 * a_px or math.hypot(*u) * 12 < 1.0:
            continue
        img = AN.arrow(img, (float(p0[0]), float(p0[1])), (float(p0[0] + 12 * u[0]), float(p0[1] + 12 * u[1])), color="emphasis", width=1,
                       head_len=4.0, head_width=3.0)
    img = AN.ellipse(img, (c0, c0), (a_px, a_px), color="reference", width=1)
    img = AN.text_box(img, title, (4, 4), anchor="lt", font_size=13)
    img = AN.text_box(img, "read P %.3f N  q (%.3f, %.3f) N" % (rd["P"], rd["q"][0], rd["q"][1]), (4, pad["n"] - 4), anchor="lb", font_size=12)
    return np.clip(np.asarray(img, np.float64), 0, 1)


def figures(pad, ctx, out) -> None:
    print("== 図")
    t0 = time.time()
    # 1. 膜 2 枚の像と読み vs 真値(くさびの境目の二点: θ 3°、μ 0.8)
    th = 3.0 * DEG
    ww = PT.whitney_wrench(KP, "two_point", th, KP["chamfer"] + PS.two_point_depth(KP, th), 0.8, 0.6, 0.78)
    tw = through_membranes(ww["F"], ww["M_g"], ww["axis"], pad, ctx)
    panels = [_membrane_panel(tw["frames"][s], tw["reads"][s], pad, ctx, "finger %s (%s x)  arrows x12" % (s, "+" if s == "R" else "-")) for s in ("L", "R")]
    figs.save_grid("pegtactile_two_membranes_read", panels, captions=["finger L", "finger R"], ncols=2,
                   caption="Whitney の二点接触(θ 3°、μ 0.8 = くさびの境目の近く)を 2 本の指の膜で見た像(等倍 256 px = 16 mm)。矢印はマーカーの変位 ×12、円は読んだ接触円。"
                           "真値の荷重 L: P %.3f N・q (%.3f, %.3f) N、R: P %.3f N・q (%.3f, %.3f) N。左右でせん断の v 成分が逆向き = モーメントは偶力で運ばれる。"
                           % (tw["loads"]["L"]["P"], *tw["loads"]["L"]["q"], tw["loads"]["R"]["P"], *tw["loads"]["R"]["q"]))
    hdr = ["quantity", "truth (MuJoCo-free closed form)", "read from the two membranes"]
    rows = [["F_x [N]", "%.4f" % ww["F"][0], "%.4f" % tw["F"][0]], ["F_z [N]", "%.4f" % ww["F"][2], "%.4f" % tw["F"][2]],
            ["M_y about grasp [mN m]", "%.3f" % (1e3 * ww["M_g"][1]), "%.3f" % (1e3 * tw["M"][1])],
            ["state", "two_point", PT.contact_state_from_wrench(KP, tw["F"], tw["M"], ww["g"], ww["tip"], ww["axis"])["state"]],
            ["wall mu", "0.800", "%.4f" % PT.two_point_forces(KP, tw["F"], tw["M"], ww["g"], ww["tip"], ww["axis"])["mu"]]]
    figs.save_table("pegtactile_wrench_truth_vs_membranes", hdr, rows, title="Contact wrench: Whitney closed form vs read from two fingertip membranes",
                    caption="同じ二点接触の接触レンチ。真値は Whitney の平面の釣り合い(閉形式)、右列は膜の像 2 枚から読んだ値。壁の μ は二点の Whitney 分解。")
    # 2. 動く図: 閉形式の挿入(θ 3°、μ 0.3)を膜で読む —— 一点で深くなり、W + l₂(θ) で二点へ
    l2 = PS.two_point_depth(KP, th)
    seq = [("one_point", f, KP["chamfer"] + f * l2, 0.6 * min(1.0, 0.3 + f), 0.0) for f in np.linspace(0.15, 0.9, 7)]
    seq += [("two_point", 1.0, KP["chamfer"] + l2, 0.6, fm) for fm in np.linspace(0.08, 0.9, 7)]
    gif = []
    for st, f, depth, f1, f2 in seq:
        w2 = PT.whitney_wrench(KP, st, th, depth, 0.3, f1, f2)
        t2 = through_membranes(w2["F"], w2["M_g"], w2["axis"], pad, ctx)
        stt = PT.contact_state_from_wrench(KP, t2["F"], t2["M"], w2["g"], w2["tip"], w2["axis"])["state"]
        pl = [_membrane_panel(t2["frames"][s], t2["reads"][s], pad, ctx, "finger %s" % s) for s in ("L", "R")]
        frame = np.concatenate([pl[0], np.zeros((pad["n"], 8, 3)), pl[1]], axis=1)
        frame = np.concatenate([np.full((84, frame.shape[1], 3), 0.06), frame], axis=0)
        ok = stt == st
        frame = AN.text_box(frame, "depth %.2f mm   (two-point at W + l2 = %.2f mm)" % (1e3 * depth, 1e3 * (KP["chamfer"] + l2)), (6, 4), anchor="lt", font_size=13)
        frame = AN.text_box(frame, "truth: %s   membranes: %s" % (st, stt), (6, 30), anchor="lt", font_size=13, color="right" if ok else "wrong")
        frame = AN.text_box(frame, "F_x, F_z true (%.3f, %.3f) N  read (%.3f, %.3f) N" % (w2["F"][0], w2["F"][2], t2["F"][0], t2["F"][2]), (6, 56),
                            anchor="lt", font_size=11)
        gif.append(np.clip(np.asarray(frame, np.float64), 0, 1))
    assert len(gif) == 14
    figs.save_gif("pegtactile_whitney_insertion_through_membranes", gif, fps=2.0,
                  caption="Whitney の閉形式の挿入(θ 3°、μ 0.3)を膜 2 枚で読む動く図: 先端が壁に一点で触れたまま深くなり、深さ W + l₂(θ) = %.2f mm で胴が口の縁にも触れて二点へ。"
                          "上の文字の色 = 膜からの判定が真値と一致(全 %d コマ)。" % (1e3 * (KP["chamfer"] + l2), len(gif)))
    # 3. 接触半径のビンの罠
    sl = slope_trap(pad, ctx, np.linspace(3.6, 4.4, 17)) if FULL else out["slope"]
    figs.save_plot("pegtactile_contact_radius_binned_vs_pixelwise",
                   [("binned (tacsim.contact_radius_fit)", sl["P"], 1e3 * sl["err_binned"]), ("pixelwise (contact_radius_fit_pixelwise)", sl["P"], 1e3 * sl["err_pixel"]),
                    ("truth", sl["P"], np.zeros_like(sl["P"]))],
                   xlabel="true pad load P [N]", ylabel="P_hat - P [mN]", title="Where the binned contact radius breaks the slope", styles=[None, None, "dashed"],
                   kinds=["line", "line", "line"],
                   caption="半径ビンの接触半径は a が画素ピッチをまたぐたびに偏りの符号が変わる(%d 点、傾きの誤差 最大 %.1f %%)。画素ごとの当てはめは偏り %.2f mN で滑らか"
                           "(傾き %.3f %%)。2 本の指の差 F_x = P_L − P_R で効くのは値でなく傾き。" % (len(sl["P"]), 100 * sl["slope_binned"], 1e3 * sl["bias_pixel_N"], 100 * sl["slope_pixel"]))
    # 4. レンチだけの規則の死角(θ–μ 平面)
    c_ = (KP["R"] - KP["r"]) / KP["R"]
    thg = np.radians(np.linspace(1.9, 5.0, 100))                      # c/θ ≤ 1.2 の範囲だけ(縦軸の枠に収める)
    ok_pts, bad_pts = [], []
    for st, th_, depth, mu, f1, f2 in out["cases"]:
        if st != "two_point":
            continue
        ww_ = PT.whitney_wrench(KP, st, th_, depth, mu, f1, f2)
        s0 = PT.contact_state_from_wrench(KP, ww_["F"], ww_["M_g"], ww_["g"], ww_["tip"], ww_["axis"], geometry=False)["state"]
        (ok_pts if s0 == "two_point" else bad_pts).append((math.degrees(th_), mu))
    series = [("wedge boundary mu = c / theta", np.degrees(thg), c_ / thg)]
    kinds, styles = ["line"], ["dashed"]
    if ok_pts:
        series.append(("two-point read correctly (wrench only)", np.array([p[0] for p in ok_pts]), np.array([p[1] for p in ok_pts])))
        kinds.append("scatter")
        styles.append(None)
    if bad_pts:
        series.append(("two-point read as mouth one-point", np.array([p[0] for p in bad_pts]), np.array([p[1] for p in bad_pts])))
        kinds.append("scatter")
        styles.append(None)
    figs.save_plot("pegtactile_wrench_only_blind_band", series, xlabel="tilt theta [deg]", ylabel="wall friction mu", xlim=(1.2, 5.0), ylim=(0.0, 1.25),
                   title="The wrench alone is blind on Whitney's wedge boundary", kinds=kinds, styles=styles,
                   caption="二点接触(閉形式)をレンチだけの規則に通すと、口と先端を結ぶ線の傾き c/θ が μ に等しい線(破線、Whitney のくさびの境目そのもの)の近くでだけ"
                           "口の一点と読む(%d 組中 %d 組)。先端の摩擦円錐の縁が口の接触点を通るから。幾何の検査(深さ ≥ W + l₂(θ))で全部直る。" % (len(ok_pts) + len(bad_pts), len(bad_pts)))
    # 5. 形の向き: フーリエ位相(緑)vs 2 次モーメント(赤)
    tiles = []
    for name in PT.SHAPES:
        col = []
        for a in (0.0, 25.0, 50.0):
            img = PT.symmetric_peg_shape(name, 160, 50.0, 0.3 + a * DEG)
            so = PT.symmetry_order_contour(PT._level_contour(img))
            rr, cc, am = _moment_op(img)
            t_ = np.repeat((0.1 + 0.75 * img)[..., None], 3, axis=2)
            if np.isfinite(so["angle"]):
                for k_ in range(max(1, so["n"])):
                    a_ = so["angle"] + 2 * math.pi * k_ / max(1, so["n"])
                    t_ = AN.arrow(t_, (so["centroid"][1], so["centroid"][0]), (so["centroid"][1] + 60 * math.cos(a_), so["centroid"][0] + 60 * math.sin(a_)),
                                  color="right", width=2, head_len=8.0, head_width=6.0)
            t_ = AN.arrow(t_, (cc - 70 * math.cos(am), rr - 70 * math.sin(am)), (cc + 70 * math.cos(am), rr + 70 * math.sin(am)), color="wrong", width=1,
                          head_len=0.0)
            t_ = AN.text_box(t_, "%s n=%d  %+.0f deg" % (name, so["n"], a), (3, 3), anchor="lt", font_size=11)
            col.append(np.clip(np.asarray(t_, np.float64), 0, 1))
        tiles.append(np.concatenate(col, axis=0))
    figs.save("pegtactile_shape_orientation_fourier_vs_moment", np.concatenate(tiles, axis=1),
              "5 形状 × 3 角度(形を回して描き直し、等倍 160 px): 緑 = 輪郭の複素フーリエ位相の向き arg(c₁₋ₙ c₁ⁿ⁻¹)/n を n 本、赤 = 2 次モーメントの主軸(blob2d)。"
              "n ≥ 3 では慣性が等方になり赤は形と無関係に向く(罠)、フーリエ位相は形と一緒に回る。")
    if "res" in out:
        figures_full(pad, ctx, out)
    print("  図: %s(%.1f s)" % (figs.errors() or "ok", time.time() - t0))


def _band(states, width, height, cursor=None):
    img = np.full((height, width, 3), 0.1)
    n = len(states)
    for i, s in enumerate(states):
        x0, x1 = int(i * width / n), max(int(i * width / n) + 1, int((i + 1) * width / n))
        img[:, x0:x1] = _COL.get(s, _COL["other"])
    if cursor is not None:
        x = min(width - 1, int((cursor + 0.5) * width / n))
        img[:, max(0, x - 1):x + 1] = 1.0
    return img


def figures_full(pad, ctx, out) -> None:
    import camera
    eps, res = out["eps"], out["res"]
    # 6. 挿入の動く図(走行 A): 断面 + 手首カメラ + 膜 2 枚 + 状態の帯
    ep, r = eps["A"], res["A"]
    rows, frs = r["rows"], ep["frames"]
    first = next((i for i, row in enumerate(rows) if row["state_true"] != "none"), 0)
    idx = list(range(max(0, first - 6), len(rows), 2))[:48]                # 2 フレームに 1 枚(GIF の目安 8 MB、縮小・減色はしない)
    assert len(idx) >= 10
    st_t = [rows[i]["state_true"] for i in idx]
    st_e = [rows[i]["st_tactile"]["state"] for i in idx]
    gif = []
    for j, i in enumerate(idx):
        fr, row = frs[i], rows[i]
        sd = fr["side"]
        cut = np.asarray(sd["rgb"], np.float64) / 255.0

        def proj(p):
            uv, _ = camera.project_points(np.asarray(p, np.float64)[None, :], sd["K"], sd["R"], sd["t"])
            return float(uv[0, 0]), float(uv[0, 1])
        for c in fr["contacts"]:
            u, v = proj(c["pos"])
            rad = 3 + 5 * math.sqrt(max(c["fn"], 0) / 0.3)
            cut = AN.ellipse(cut, (u, v), (rad, rad), color="right", width=2)
        st = row["st_tactile"]
        pts = []
        if st["state"] in ("one_point", "chamfer") and st["c"] is not None:
            pts = [st["c"]]
        elif st["state"] == "two_point":
            try:
                tp = PT.two_point_forces(KP, row["tw"]["F"], row["tw"]["M"], row["g_hat"], row["tip_hat"], row["axis_hat"])
                pts = [tp["p_tip"], tp["p_mouth"]]
            except ValueError:
                pts = []
        for p in pts:
            u, v = proj(p)
            cut = AN.arrow(cut, (u - 7, v - 7), (u + 7, v + 7), color="emphasis", width=2, head_len=0.0)
            cut = AN.arrow(cut, (u - 7, v + 7), (u + 7, v - 7), color="emphasis", width=2, head_len=0.0)
        wr = np.asarray(fr["wrist"]["rgb"][0:400, 160:480], np.float64) / 255.0
        loads = row["tw"]["loads"]
        pl = []
        for s in ("L", "R"):
            f_ = PT.pad_tactile_frame(loads[s]["P"], loads[s]["q"], pad, ctx, torsion=loads[s]["torsion"])
            pl.append(_membrane_panel(f_, PT.pad_tactile_read(f_, pad, ctx), pad, ctx, "finger %s" % s)[28:228])    # 接触円を中央に 200 行
        right = np.concatenate(pl, axis=0)
        body = np.concatenate([cut, wr, right], axis=1)
        top = np.full((32, body.shape[1], 3), 0.05)
        bands = np.concatenate([np.full((72, 110, 3), 0.05), np.concatenate([_band(st_t, body.shape[1] - 110, 26, j), np.full((8, body.shape[1] - 110, 3), 0.05),
                                                                             _band(st_e, body.shape[1] - 110, 26, j), np.full((12, body.shape[1] - 110, 3), 0.05)], axis=0)], axis=1)
        canvas = np.concatenate([top, body, bands], axis=0)
        ok = st["state"] == row["state_true"]
        canvas = AN.text_box(canvas, "t %.2f s   depth %.2f mm   MuJoCo: %s   tactile: %s" % (fr["t"], 1e3 * fr["depth"], row["state_true"], st["state"]), (6, 4),
                             anchor="lt", font_size=15, color="right" if ok else "wrong")
        canvas = AN.text_box(canvas, "green = MuJoCo contacts (size ~ force), magenta x = read from the membranes", (6, 36), anchor="lt", font_size=11)
        canvas = AN.text_box(canvas, "wrist cam deflection (%.1f, %.1f) um / true (%.1f, %.1f) um" % (1e6 * row["cam"]["dx"], 1e6 * row["cam"]["dy"], 1e6 * row["p0_true"][0],
                                                                                                     1e6 * row["p0_true"][1]), (486, 36 + 370), anchor="lt", font_size=11)
        canvas = AN.text_box(canvas, "MuJoCo", (6, 32 + 400 + 2), anchor="lt", font_size=11)
        canvas = AN.text_box(canvas, "tactile", (6, 32 + 400 + 36), anchor="lt", font_size=11)
        gif.append(np.clip(np.asarray(canvas, np.float64), 0, 1))
    figs.save_gif("pegtactile_insertion_section_wrist_membranes", gif, fps=5.0,
                  caption="挿入の動く図(θ 3°、横ずれ 0.6 mm、%d コマ = 0.08 s ごと): 左 = 穴の断面(板を半透明、緑の円 = MuJoCo の接触点、大きさ ∝ 力、桃の × = 膜 2 枚から読んだ"
                          "接触点)、中 = 手首カメラ、右 = 2 本の指の膜(矢印 ×12)。下の帯 = 状態(灰 無接触・青 面取り・橙 一点・赤 二点)の MuJoCo と触覚。" % len(gif))
    # 7. 4 走行の時系列(深さ・|F|・M_y、真値 vs 触覚)
    for name in ("A", "B", "C", "D"):
        e_, r_ = eps[name], res[name]
        t = np.array([f["t"] for f in e_["frames"]])
        t = t - t[0]
        figs.save_plot("pegtactile_timeline_run_%s" % name,
                       [("|F| MuJoCo [N]", t, np.array([np.linalg.norm(f["Fc"]) for f in e_["frames"]])),
                        ("|F| membranes [N]", t, np.array([np.linalg.norm(row["tw"]["F"]) for row in r_["rows"]])),
                        ("M_y MuJoCo [N cm]", t, 100 * np.array([f["Mc"][1] for f in e_["frames"]])),
                        ("M_y membranes [N cm]", t, 100 * np.array([row["tw"]["M"][1] for row in r_["rows"]]))],
                       xlabel="t [s]", ylabel="force [N] / moment [N cm]", title="Run %s: tilt %.1f deg, offset %+.1f mm" % (name, e_["tilt_deg"], e_["eps_mm"][0]),
                       styles=["dashed", None, "dashed", None], size=(720, 360),
                       caption="走行 %s の接触力の大きさと把持点まわりの M_y(破線 = MuJoCo の露光平均、実線 = 膜 2 枚から)。状態の一致は %.1f %%。"
                               % (name, 100 * sum(1 for row in r_["rows"] if row["st_tactile"]["state"] == row["state_true"]) / len(r_["rows"])))
    # 8. 手首剛性
    series = []
    for name in ("A", "B", "C", "D"):
        r_ = res[name]
        sel = r_["k_sel"]
        series.append(("run %s: k = %.1f N/m" % (name, r_["k_fit"]["k"]), np.array([row["p0"] for row in r_["rows"]])[sel].ravel() * 1e6,
                       np.array([row["F_eff"] for row in r_["rows"]])[sel].ravel()))
    xs = np.linspace(-800, 800, 3)
    series.append(("MuJoCo setting %.0f N/m" % KP["k_trans"], xs, KP["k_trans"] * xs * 1e-6))
    figs.save_plot("pegtactile_wrist_stiffness_from_images", series, xlabel="wrist deflection from the wrist camera [um]", ylabel="contact force from the membranes [N]",
                   title="Wrist stiffness identified from images: F = k dx", kinds=["scatter"] * 4 + ["line"], styles=[None] * 4 + ["dashed"],
                   caption="手首カメラの軸の直線を z = 0 で切った点(たわみ)と、膜 2 枚から読んだ接触力(z 圧縮の分を軸の傾きで射影)。触覚が 3 フレーム続けて二点と言ったフレームだけ。"
                           "破線 = MuJoCo の設定値。k̂_t は ±%.1f %%。" % (100 * _NUM["k_t_err"]))
    # 9. 二点の始まり
    thg = np.radians(np.linspace(1.5, 5.0, 120))
    on = [v for v in out["onset"].values() if v]
    figs.save_plot("pegtactile_two_point_onset_depth",
                   [("Whitney closed form W + l2(theta)", np.degrees(thg), np.array([1e3 * (KP["chamfer"] + PS.two_point_depth(KP, t_)) for t_ in thg])),
                    ("membranes (depth from wrist cam + k)", np.array([v["theta_deg"] for v in on]), np.array([v["depth_tactile_mm"] for v in on])),
                    ("MuJoCo contacts", np.array([v["theta_mujoco_deg"] for v in on]), np.array([v["depth_mujoco_mm"] for v in on]))],
                   xlabel="peg tilt at onset [deg]", ylabel="tip depth below the mouth [mm]", title="Two-point contact onset: membranes vs Whitney vs MuJoCo",
                   kinds=["line", "scatter", "scatter"], styles=["dashed", None, None],
                   caption="二点接触の始まり(4 走行)。破線 = Whitney の閉形式、触覚の推定深さとの差は最大 %.3f mm。" % max(abs(v["err_mm"]) for v in on))
    # 10. 場面を 90° 回した時
    eq = out["equiv"]
    figs.save_table("pegtactile_rotated_scene_agreement", ["scene", "pad torsion", "state agreement with MuJoCo"],
                    [["0 deg", "read", "%.1f %%" % (100 * eq["accA"])], ["90 deg", "read", "%.1f %%" % (100 * eq["accG"])],
                     ["90 deg", "ignored", "%.1f %%" % (100 * eq["accG0"])]], title="Two-finger grip is not rotation symmetric",
                    caption="場面を 90° 回すと傾きのモーメントはせん断の偶力からパッドのねじりへ移る。ねじりを読めば一致率は変わらず、捨てると落ちる"
                            "(ねじりの全滑り比 最大 %.2f)。物理(MuJoCo)の状態列は %.1f %% 一致。" % (eq["torsion_ratio"], 100 * eq["state_same"]))


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    c_all = time.process_time()
    pad = PT.pad_params()
    ctx = PT.pad_context(pad)
    out = numpy_part(pad, ctx)
    if FULL:
        out = full_numpy_part(pad, ctx, out)
        out = full_part(pad, ctx, out)
    else:
        skip("門 11〜22(重い numpy と MuJoCo)", "--full のときだけ")
    if figs.enabled():
        figures(pad, ctx, out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s、この過程の CPU %.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all, time.process_time() - c_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
