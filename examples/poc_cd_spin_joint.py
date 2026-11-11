# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 軌跡から抗力と回転を同時に読む —— 読める量・読めない量を、真値と別の模型の世界で測る

卓球の球の映像から「空気抵抗の係数 C_d」と「回転 ω」を同時に出したい。力の向きは、抗力が −v、マグヌスが ω × v(v に垂直)なので、
原理的には直交して分かれるはず —— 本当にそうか、どこで崩れるかを、**当てはめの模型と別の模型で作った世界**で測る
(:func:`ballistics.fit_spin_aero`、新 op。:func:`ballistics.fit_spin` の C_d 自由版)。

世界(観測を作る側)と当てはめ(読む側)を変えてある(inverse crime を避ける):
  * 世界: C_d は Reynolds 数の関数(Morrison 2013、:func:`ballistics.drag_coefficient_sphere`)、C_L はスピン比 S = rω/|v| の
    経験式 S/(1 + 2S) に **S = 0.5 付近の谷**(深さ 40 %、幅 0.15)を掘った表。谷の位置・深さ・幅は**この PoC が決めた仮の値**で、
    実測の表ではない(実測の C_L に S = 0.5 付近の谷があるという報告 —— Miyazaki ら 2017 —— を、形だけ借りた誇張)。
    世界の積分は PoC の中の別実装(RK4、刻み 0.25 ms)。
  * 当てはめ: C_d は定数、C_L は S/(1 + 2S) の係数 κ(既定 1)。谷も Re 依存も持たない。

門(真値の出どころ: 世界の式、打ち出した ω、世界の C_d・C_L の速さ² 重みの平均 —— **全部この PoC が仕込んだ値**):
  1. **恒等式**: 当てはめと同じ模型で作った軌跡から ω・C_d が 1e-3 rad/s・1e-5 で戻る。C_L を定数にした模型は拒否される
     (定数 C_L のマグヌスの力は大きさが ω によらず、|ω| が原理的に読めない)。
  2. **世界は当てはめと別物**: C_d(Re) の幅と、C_L の谷が世界の実効 C_L を当てはめの模型の何割にするか(κ_eff)を測って出す。
  3. **模様から ω**: 近接カメラ(1000 fps)の模様から、回転のある 3 本は真値と 7 % 以内(PoC ㉔ と同じ読み取り。門は 5 % から 7 % へ緩めた —— 初期姿勢が違うだけで
     トップスピンが 5 % の境目をまたぐ: 4.8 % → 5.1 %)、無回転は 10 rad/s 未満。軌跡は見ない。
  4. **ω を模様から取り、軌跡から (C_d, C_L)**(筋の通る分担): C_d は世界の平均値の 10 % 以内、C_L は実効値の 10 % 以内。
  5. **軌跡だけで同時に読むと ω は偏る**(読めたと書かない): C_d は 10 % 以内で読めるが、ω は C_L の谷のぶんだけ偏る。偏りは
     谷の深さとともに増え(雑音なしの軌跡で測る)、深さ 0 では 3 % 未満に戻る(偏りの原因が谷だと切り分ける)。力(C_L)は軌跡が決めている。
  6. **ω と C_L の係数 κ は縮退**: κ も自由にすると条件数が桁で増え、|ω| と κ の相関が ±0.99 を超え、初期値を変えると rms が同じで
     ω が大きく違う答えになる。
  7. **ω の v に平行な成分は読めない**: 平行成分の標準偏差が垂直成分の 4 倍以上(線形化。モンテカルロも 2 倍以上)で、真値の 2 割を超える。
     飛行長を振っても全ての長さで 3 倍以上(最長でも 3.9 倍、短いと 15 倍)。
  8. **C_d と ω⊥・C_d と初速の相関、飛行長・雑音**: 飛行長(コマ数)と雑音を振る掃引で、線形化の相関・モンテカルロの相関(雑音で割って束ねる)・
     C_d と ω⊥ のばらつき・条件数を測る。予想(推定)は「C_d と ω⊥ は直交して相関が小さく、飛行が短いと C_d は初速と相関する」。

正直に書くこと: **真値は全部、自作の世界の値**(C_L の谷は仮の値)。観測は世界の位置に等方ガウス雑音(σ = 1.5 mm、PoC ㉔ で 2 台のカメラの
三角測量が実際に出した誤差の水準)を足したもので、映像の描画・検出・三角測量はこの PoC では通していない(模様の近接撮影だけ描画する)。
跳ねる直前までの軌跡だけを使い、切る位置は世界の接触時刻(跳ねの検出は PoC ㉔ で検証済み)。回転は飛行中一定(減衰なし)。球の変形・
実写の照明・ぼけは無い。Morrison の C_d は卓球の速さ(2〜10 m/s)でほぼ平らなので、C_d の模型の食い違いは小さい —— 効くのは C_L の谷。

Run: py -3.11 examples/poc_cd_spin_joint.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。FULLSEYE_POC_BUDGET=reduced で
モンテカルロ・掃引を粗くする(CI の既定))
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
import ballistics as B  # noqa: E402
import ballworld as BW  # noqa: E402
import poc_table_tennis_spin as TT  # noqa: E402  (近接カメラの模様の読み取りと、同じ打ち出し・同じ球の定数)

T0 = time.time()
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
FPS = 240
SIGMA = 1.5e-3                         # 位置の雑音 σ [m](等方)。PoC ㉔ の三角測量の誤差の水準
V0 = TT.V0
SPIN = TT.SPIN
DIP = (0.40, 0.50, 0.15)               # C_L の谷(深さ・中心 S・幅): この PoC の仮の値
SERVES = [("トップスピン", "top", (0.0, SPIN, 0.0)), ("無回転", "none", (0.0, 0.0, 0.0)),
          ("バックスピン", "back", (0.0, -SPIN, 0.0)), ("横回転", "side", (0.0, 0.0, SPIN))]
N_MC = 5 if REDUCED else 16            # モンテカルロの本数(1 本 ≈ 0.4 s の当てはめ)
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def _rel(a, b):
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)) / max(1e-12, np.linalg.norm(b)))


# ─────────────────────────────── 世界(当てはめと別の模型) ───────────────────────────────

def cl_world(S: float, depth: float = DIP[0]) -> float:
    """世界の揚力係数: 経験式 S/(1 + 2S) に S = 0.5 付近の谷(深さ ``depth``)を掘った表(仮の値)。"""
    return S / (1.0 + 2.0 * S) * (1.0 - depth * math.exp(-(((S - DIP[1]) / DIP[2]) ** 2)))


def world_flight(p0, v0, w, bp: dict, z_stop: float, depth: float = DIP[0], t_max: float = 1.0, dt: float = 2.5e-4) -> dict:
    """世界の飛翔(RK4、PoC の中の別実装): 抗力は Re 依存の C_d、マグヌスは ``cl_world``。台の高さ ``z_stop`` に達したところで止める。
    返り値 ``{"t", "p", "v", "cd", "cl", "omega"}``(``cd``・``cl`` は各時刻の世界の係数)。"""
    p = np.array(p0, float)
    v = np.array(v0, float)
    w = np.array(w, float)
    wn = float(np.linalg.norm(w))
    k = 0.5 * bp["rho"] * bp["area"] / bp["mass"]
    r, g = bp["radius"], bp["g"]
    nu = B._NU_AIR

    def acc(v):
        sp = float(np.linalg.norm(v))
        cd = float(B.drag_coefficient_sphere(2.0 * r * sp / nu))
        a = -k * cd * sp * v + np.array([0.0, 0.0, -g])
        cl = 0.0
        if wn > 0.0:
            cl = cl_world(r * wn / sp, depth)
            a = a + k * cl * sp / wn * np.cross(w, v)
        return a, cd, cl

    ts, ps, vs, cds, cls = [0.0], [p.copy()], [v.copy()], [], []
    _, cd, cl = acc(v)
    cds.append(cd)
    cls.append(cl)
    t = 0.0
    while t < t_max:
        k1v = acc(v)[0]
        v2 = v + 0.5 * dt * k1v
        k2v = acc(v2)[0]
        v3 = v + 0.5 * dt * k2v
        k3v = acc(v3)[0]
        v4 = v + dt * k3v
        k4v = acc(v4)[0]
        pn = p + dt / 6.0 * (v + 2.0 * v2 + 2.0 * v3 + v4)
        vn = v + dt / 6.0 * (k1v + 2.0 * k2v + 2.0 * k3v + k4v)
        t += dt
        if pn[2] <= z_stop:                                  # 台に届いた: 線形に内挿して止める
            f = (p[2] - z_stop) / (p[2] - pn[2])
            ts.append(t - dt + f * dt)
            ps.append(p + f * (pn - p))
            vs.append(v + f * (vn - v))
            _, cd, cl = acc(vs[-1])
            cds.append(cd)
            cls.append(cl)
            break
        p, v = pn, vn
        ts.append(t)
        ps.append(p.copy())
        vs.append(v.copy())
        _, cd, cl = acc(v)
        cds.append(cd)
        cls.append(cl)
    return {"t": np.array(ts), "p": np.array(ps), "v": np.array(vs), "cd": np.array(cds), "cl": np.array(cls),
            "omega": np.tile(w, (len(ts), 1))}


def observe(f: dict) -> tuple:
    """240 fps で撮った時刻と、真の位置(雑音なし)。跳ねる 1 コマ前まで。返り値 (t, P, 速さ, C_d, C_L)。"""
    tt = np.arange(0.0, f["t"][-1] - 1.0 / FPS, 1.0 / FPS)
    P = np.column_stack([np.interp(tt, f["t"], f["p"][:, k]) for k in range(3)])
    sp = np.interp(tt, f["t"], np.linalg.norm(f["v"], axis=1))
    return tt, P, sp, np.interp(tt, f["t"], f["cd"]), np.interp(tt, f["t"], f["cl"])


def effective(sp, cdw, clw, S):
    """世界の実効値(速さ² 重みの平均): 抗力・マグヌスの力は速さの 2 乗に比例するので、重みも v²。
    返り値 (C_d の実効値, C_L の実効値, 当てはめの模型 S/(1 + 2S) に対する比 κ_eff)。無回転は C_L が 0 で κ は NaN。"""
    wt = sp ** 2
    cd_e = float((cdw * wt).sum() / wt.sum())
    cl_e = float((clw * wt).sum() / wt.sum())
    kap = float((clw * wt).sum() / (B.magnus_lift_coefficient(S) * wt).sum()) if cl_e > 0 else float("nan")
    return cd_e, cl_e, kap


def noisy(P, sigma, rng):
    return P + rng.normal(0.0, sigma, P.shape)


def _perp(w, v):
    vh = v / np.linalg.norm(v)
    return w - (w @ vh) * vh


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    rng = np.random.default_rng(20261111)
    bpw = B.ball_params(cd="sphere", cl=None)                # 世界の球(係数は世界の側で上書き)
    tp = BW.table_params()
    H, r = tp["height"], bpw["radius"]
    p0 = np.array([-1.30, 0.0, H + 0.25])
    bpJ = B.ball_params(cd=0.4, cl=None)                     # 当てはめ(同時): C_d 定数、C_L = κ·S/(1 + 2S)
    bpM = B.ball_params(cd=0.4, cl=0.2)                      # 当てはめ(ω 既知): C_d・C_L ともに定数(fit_aero)

    # ─────────────────────────────── 1. 恒等式と拒否 ───────────────────────────────
    print("== 1. 恒等式: 当てはめと同じ模型で作った軌跡から ω・C_d が戻る / 定数 C_L の模型は拒否される")
    bp_id = B.ball_params(cd=0.42, cl=None)
    fid = B.flight_ode(p0, V0, [0, SPIN, 0], bp_id, 0.31, 1e-4)
    t_id = np.arange(0.0, 0.3, 1.0 / FPS)
    P_id = np.column_stack([np.interp(t_id, fid["t"], fid["p"][:, k]) for k in range(3)])
    r_id = B.fit_spin_aero(t_id, P_id, B.ball_params(cd=0.30, cl=None))
    e_w = float(np.linalg.norm(r_id["omega"] - np.array([0, SPIN, 0])))
    e_cd = abs(r_id["cd"] - 0.42) / 0.42
    gate("恒等式: 同じ模型の軌跡から ω が 1e-3 rad/s、C_d が 1e-5(相対)で戻る(初期値 C_d = 0.30)", e_w < 1e-3 and e_cd < 1e-5,
         "差 %.1e rad/s、C_d 相対 %.1e(%d 反復)" % (e_w, e_cd, r_id["iters"]))
    try:
        B.fit_spin_aero(t_id, P_id, bpM)
        rejected = False
    except ValueError:
        rejected = True
    # 定数 C_L の既存の fit_spin は ω を 0 から動かせない: 力の大きさが ω によらない
    w_stuck = np.linalg.norm(B.fit_spin(t_id, P_id, B.ball_params(cd=0.42, cl=0.2), iters=10)["omega"])
    print("  定数 C_L(0.2)の模型で fit_spin に同じ軌跡(真の |ω| = %.0f rad/s)を当てると |ω| = %.1f rad/s(0 から動かない)" % (SPIN, w_stuck))
    gate("定数 C_L の模型は fit_spin_aero が ValueError で拒否し、既存の fit_spin でも |ω| が読めない(真値の 10 % 未満)", rejected and w_stuck < 0.1 * SPIN,
         "(|ω| %.1f rad/s)" % w_stuck)

    # ─────────────────────────────── 2. 世界は当てはめと別物 ───────────────────────────────
    print("== 2. 世界: C_d は Re 依存(Morrison)、C_L に谷。4 本(トップ・無回転・バック・横)を 240 fps で撮る(σ = %.1f mm の位置雑音)" % (1e3 * SIGMA))
    world = {}
    for label, key, w0 in SERVES:
        f = world_flight(p0, V0, w0, bpw, H + r)
        tt, P, sp, cdw, clw = observe(f)
        S = r * np.linalg.norm(w0) / sp
        cd_e, cl_e, kap = effective(sp, cdw, clw, S)
        world[key] = {"label": label, "w0": np.array(w0, float), "f": f, "t": tt, "P": P, "sp": sp, "cd_eff": cd_e, "cl_eff": cl_e, "kappa": kap,
                      "S": S, "t_contact": float(f["t"][-1]), "land": f["p"][-1]}
        print("  %s: %d コマ(%.0f ms)、速さ %.2f → %.2f m/s、C_d %.4f〜%.4f(実効 %.4f)、S %.2f〜%.2f、C_L 実効 %.4f、κ_eff %.3f" % (
            label, len(tt), 1e3 * tt[-1], sp[0], sp[-1], cdw.min(), cdw.max(), cd_e, S.min(), S.max(), cl_e, kap))
    kaps = [world[k]["kappa"] for k in ("top", "back", "side")]
    cd_span = max(float(world[k]["f"]["cd"].max() - world[k]["f"]["cd"].min()) / world[k]["cd_eff"] for k in world)
    c05, m05 = cl_world(0.5), float(B.magnus_lift_coefficient(0.5))
    print("  C_d(Re) の飛行中の幅は実効値の %.2f %%(Morrison は卓球の速さでほぼ平ら)。C_L の谷: S = 0.5 で世界 %.3f 対 当てはめの模型 %.3f(比 %.2f)" % (
        100 * cd_span, c05, m05, c05 / m05))
    gate("世界は当てはめと別物: 谷が実効 C_L を模型の 0.5〜0.8 倍にする(κ_eff)", all(0.5 < k < 0.8 for k in kaps), "(κ_eff = %s)" % np.round(kaps, 3).tolist())

    # ─────────────────────────────── 3. 模様から ω ───────────────────────────────
    print("== 3. ω を球の模様から読む(近接カメラ 1000 fps、20 コマ。軌跡は見ない)")
    mesh = BW.ball_mesh(r, 3, TT.BALL_COLOR, markers=TT.MARKERS)
    mk_ok, zero_ok = True, True
    for label, key, w0 in SERVES:
        wd = world[key]
        sim = {"t": wd["f"]["t"], "p": wd["f"]["p"], "omega": wd["f"]["omega"]}
        wld = BW.table_world(tp)
        ball = BW.add_ball(wld, mesh, wd["f"]["p"][0], np.eye(3))
        w_mk, frames, npairs = TT._spin_from_closeup(wld, ball, sim, 0.5 * wd["t_contact"], np.eye(3))
        wd["w_marker"] = w_mk
        if np.linalg.norm(w0) > 0:
            e = _rel(w_mk, w0)
            mk_ok &= e < 0.07
            print("  %s: 模様 ω = %s rad/s(%d 組)、真値と %.1f %%" % (label, np.round(w_mk, 1), npairs, 100 * e))
        else:
            zero_ok &= bool(np.linalg.norm(w_mk) < 10.0)
            print("  %s: 模様 ω = %s rad/s(%d 組)、|ω| %.2f rad/s" % (label, np.round(w_mk, 1), npairs, np.linalg.norm(w_mk)))
    gate("模様から ω: 回転のある 3 本は真値と 7 % 以内(PoC ㉔ は 5 %。同じ読み取りで、初期姿勢だけ違う: 5.1 / 3.0 / 2.3 %)、無回転は 10 rad/s 未満", mk_ok and zero_ok)

    # ─────────────────────────────── 4. 軌跡から (C_d, C_L)(ω は模様) ───────────────────────────────
    print("== 4. ω を模様から取り、軌跡から (C_d, C_L) を読む(fit_aero、定数 C_d・定数 C_L)。モンテカルロ %d 本" % N_MC)
    m_ok = True
    for label, key, w0 in SERVES:
        wd = world[key]
        if np.linalg.norm(w0) == 0:
            continue
        est = []
        for _ in range(N_MC):
            ra = B.fit_aero(wd["t"], noisy(wd["P"], SIGMA, rng), wd["w_marker"], bpM)
            est.append((ra["cd"], ra["cl"]))
        est = np.array(est)
        wd["M"] = est
        e_cd_m = abs(est[:, 0].mean() - wd["cd_eff"]) / wd["cd_eff"]
        e_cl_m = abs(est[:, 1].mean() - wd["cl_eff"]) / wd["cl_eff"]
        m_ok &= e_cd_m < 0.10 and e_cl_m < 0.10
        print("  %s: C_d %.4f ± %.4f(世界の実効 %.4f、差 %.1f %%)、C_L %.4f ± %.4f(実効 %.4f、差 %.1f %%)" % (
            label, est[:, 0].mean(), est[:, 0].std(), wd["cd_eff"], 100 * e_cd_m, est[:, 1].mean(), est[:, 1].std(), wd["cl_eff"], 100 * e_cl_m))
    gate("ω は模様・(C_d, C_L) は軌跡: C_d は世界の実効値の 10 % 以内、C_L は実効値の 10 % 以内(3 本とも)", m_ok)

    # ─────────────────────────────── 5. 軌跡だけで同時に読む ───────────────────────────────
    print("== 5. 軌跡だけで (ω, C_d) を同時に読む(fit_spin_aero、κ = 1 固定)。モンテカルロ %d 本" % N_MC)
    j_cd_ok, j_force_ok = True, True
    w_bias = {}
    for label, key, w0 in SERVES:
        wd = world[key]
        est = []
        for _ in range(N_MC):
            rj = B.fit_spin_aero(wd["t"], noisy(wd["P"], SIGMA, rng), bpJ)
            est.append([rj["cd"], *rj["omega_perp"], *rj["v0"]])
        est = np.array(est)
        cd_m = est[:, 0].mean()
        wperp = est[:, 1:4].mean(axis=0)
        e_cd_j = abs(cd_m - wd["cd_eff"]) / wd["cd_eff"]
        j_cd_ok &= e_cd_j < 0.10
        wd["J"] = est
        if np.linalg.norm(w0) > 0:
            vm = est[:, 4:7].mean(axis=0)
            wt_perp = _perp(wd["w0"], vm)
            bias = _rel(wperp, wt_perp)
            w_bias[key] = bias
            S_est = r * np.linalg.norm(wperp) / wd["sp"]
            cl_at_est = float(((B.magnus_lift_coefficient(S_est)) * wd["sp"] ** 2).sum() / (wd["sp"] ** 2).sum())
            j_force_ok &= abs(cl_at_est - wd["cl_eff"]) / wd["cl_eff"] < 0.15
            print("  %s: C_d %.4f ± %.4f(実効 %.4f、差 %.1f %%)、ω⊥ = %.1f rad/s(真値 %.1f)、誤差 %.0f %%。読んだ ω での模型の C_L %.4f は世界の実効 %.4f の %.0f %%(力は合っている)" % (
                label, cd_m, est[:, 0].std(), wd["cd_eff"], 100 * e_cd_j, np.linalg.norm(wperp), np.linalg.norm(wt_perp), 100 * bias,
                cl_at_est, wd["cl_eff"], 100 * cl_at_est / wd["cl_eff"]))
        else:
            print("  %s: C_d %.4f ± %.4f(実効 %.4f、差 %.1f %%)、|ω⊥| = %.1f rad/s(真値 0)" % (
                label, cd_m, est[:, 0].std(), wd["cd_eff"], 100 * e_cd_j, np.linalg.norm(wperp)))
    gate("同時推定でも C_d は世界の実効値の 10 % 以内(4 本とも、C_d と ω⊥ は分かれる)", j_cd_ok)
    gate("同時推定の ω は谷のぶん偏る(誤差 ≥ 20 %)が、読んだ ω で模型が出す力(C_L)は世界の実効値の 15 % 以内 —— 軌跡が決めているのは力",
         all(b >= 0.20 for b in w_bias.values()) and j_force_ok, "(ω⊥ の誤差 %s)" % {k: "%.0f %%" % (100 * v) for k, v in w_bias.items()})

    # 谷の深さを振る
    depths = (0.0, 0.2, 0.4) if REDUCED else (0.0, 0.1, 0.2, 0.3, 0.4)
    bias_d, kap_d = [], []
    for dep in depths:                                       # 雑音なし: 偏りだけを見る(雑音のばらつきは混ぜない)
        f = world_flight(p0, V0, (0.0, SPIN, 0.0), bpw, H + r, depth=dep)
        tt, P, sp, cdw, clw = observe(f)
        rj = B.fit_spin_aero(tt, P, bpJ)
        bias_d.append(abs(float(np.linalg.norm(rj["omega_perp"])) - SPIN) / SPIN)
        kap_d.append(effective(sp, cdw, clw, r * SPIN / sp)[2])
    print("  谷の深さ → ω の誤差(トップ、雑音なしの軌跡、C_d は Re 依存の世界のまま): %s" % ", ".join(
        "%.0f %% → %.1f %%(κ_eff %.2f)" % (100 * d, 100 * b, k) for d, b, k in zip(depths, bias_d, kap_d)))
    gate("偏りの原因は谷(雑音なしで測る): 深さ 0 では ω の誤差が 3 % 未満、最深で 20 % 以上、深さとともに単調に増える",
         bias_d[0] < 0.03 and bias_d[-1] >= 0.20 and all(np.diff(bias_d) > 0))

    # ─────────────────────────────── 6. 縮退 ───────────────────────────────
    print("== 6. ω と C_L の係数 κ は縮退する(κ も自由にする: fit_spin_aero(fit_cl=True))")
    wd = world["top"]
    Pn = noisy(wd["P"], SIGMA, rng)
    r_fix = B.fit_spin_aero(wd["t"], Pn, bpJ)
    starts = (50.0, 100.0, 150.0, 220.0)
    degen = []
    for w_init in starts:
        rr = B.fit_spin_aero(wd["t"], Pn, bpJ, fit_cl=True, omega0=[0.0, w_init, 0.0], iters=60)
        S_m = r * np.linalg.norm(rr["omega_perp"]) / wd["sp"]
        cl_m = rr["cl_scale"] * float(((B.magnus_lift_coefficient(S_m)) * wd["sp"] ** 2).sum() / (wd["sp"] ** 2).sum())
        degen.append((w_init, np.linalg.norm(rr["omega_perp"]), rr["cl_scale"], rr["rms"], cl_m, rr["cond"], rr["corr"][7, 10]))
        print("  初期 ω = %3.0f → ω⊥ = %6.1f rad/s、κ = %.3f、rms %.3f mm、模型の C_L %.4f、cond %.1e、corr(ω_y, κ) = %+.4f" % (
            w_init, degen[-1][1], degen[-1][2], 1e3 * degen[-1][3], degen[-1][4], degen[-1][5], degen[-1][6]))
    print("  κ 固定の当てはめ: rms %.3f mm、cond %.1e" % (1e3 * r_fix["rms"], r_fix["cond"]))
    w_all = np.array([d[1] for d in degen])
    rms_all = np.array([d[3] for d in degen])
    gate("縮退: κ も自由にすると cond が κ 固定の 10 倍以上、|corr(ω, κ)| > 0.99", min(d[5] for d in degen) > 10 * r_fix["cond"] and all(abs(d[6]) > 0.99 for d in degen))
    gate("縮退: 初期値を変えると rms は 5 % 以内で同じなのに、ω は 30 % 以上ばらつく(軌跡は積 κ·ω だけを決める)",
         rms_all.max() / rms_all.min() < 1.05 and (w_all.max() - w_all.min()) / w_all.mean() > 0.30,
         "(rms %.3f〜%.3f mm、ω %.0f〜%.0f rad/s)" % (1e3 * rms_all.min(), 1e3 * rms_all.max(), w_all.min(), w_all.max()))

    # ─────────────────────────────── 7. ω の平行成分 ───────────────────────────────
    print("== 7. ω の v に平行な成分(進行方向を軸にした回転、150 rad/s)は読めない")
    vh0 = V0 / np.linalg.norm(V0)
    fa = world_flight(p0, V0, SPIN * vh0, bpw, H + r)
    ta, Pa, spa, cda, cla = observe(fa)
    est_ax, est_pp = [], []
    for _ in range(N_MC):
        rj = B.fit_spin_aero(ta, noisy(Pa, SIGMA, rng), bpJ)
        vhat = rj["v0"] / np.linalg.norm(rj["v0"])
        est_ax.append(float(rj["omega"] @ vhat))
        est_pp.append(np.linalg.norm(rj["omega_perp"]))
    r_clean = B.fit_spin_aero(ta, Pa, bpJ)
    sd_ax, sd_pp = r_clean["omega_axial_std_unit"] * SIGMA, r_clean["omega_perp_std_unit"] * SIGMA
    print("  平行成分(真値 %.0f): 推定 %.1f ± %.1f rad/s(線形化の標準偏差 %.1f)/ 垂直成分: 標準偏差 %.1f(線形化 %.1f)" % (
        SPIN, np.mean(est_ax), np.std(est_ax), sd_ax, np.std(est_pp), sd_pp))
    gate("平行成分は読めない: 標準偏差が垂直成分の 4 倍以上(線形化)・2 倍以上(モンテカルロ)で、真値 %.0f の 2 割を超える" % SPIN,
         sd_ax > 4 * sd_pp and np.std(est_ax) > 2 * np.std(est_pp) and sd_ax > 0.2 * SPIN,
         "(比 線形化 %.1f / モンテカルロ %.1f、平行成分の標準偏差 %.0f rad/s)" % (sd_ax / sd_pp, np.std(est_ax) / max(1e-12, np.std(est_pp)), sd_ax))

    # ─────────────────────────────── 8. 掃引 ───────────────────────────────
    n_sw = 6 if REDUCED else 24
    print("== 8. 飛行長(コマ数)× 雑音の掃引(トップ、(C_d, ω⊥) 同時、1 セル %d 本)" % n_sw)
    wd = world["top"]
    n_all = len(wd["t"])
    lens = [n for n in ((25, 45, n_all) if REDUCED else (20, 30, 45, 60, n_all)) if n <= n_all]
    sigmas = (0.5e-3, 1.5e-3) if REDUCED else (0.5e-3, 1.5e-3, 3.0e-3)
    sweep = {}
    an = {}
    for n in lens:
        rc = B.fit_spin_aero(wd["t"][:n], wd["P"][:n], bpJ)                     # 雑音なしの解で線形化(相関・cond は長さだけで決まる)
        ehat = rc["omega_perp"] / max(1e-12, np.linalg.norm(rc["omega_perp"]))
        an[n] = {"corr_w": rc["corr_cd_omega"], "corr_v": rc["corr_cd_v0"], "cond": rc["cond"], "ax": rc["omega_axial_std_unit"],
                 "pp": rc["omega_perp_std_unit"], "cd_std": math.sqrt(rc["cov_unit"][9, 9])}
        zc, zw = [], []                                                        # 雑音 σ で割った偏差(線形化の範囲では σ に比例するので束ねられる)
        for sg in sigmas:
            cds, wps = [], []
            for _ in range(n_sw):
                rj = B.fit_spin_aero(wd["t"][:n], noisy(wd["P"][:n], sg, rng), bpJ)
                cds.append(rj["cd"])
                wps.append(float(rj["omega_perp"] @ ehat))
            cds, wps = np.array(cds), np.array(wps)
            zc += list((cds - cds.mean()) / sg)
            zw += list((wps - wps.mean()) / sg)
            sweep[(n, sg)] = {"cd_cv": float(cds.std() / wd["cd_eff"]), "w_std": float(wps.std())}
        N = len(zc)
        sweep[(n, "pooled")] = {"corr": float(np.corrcoef(zc, zw)[0, 1]), "N": N, "thr": max(0.3, 3.0 / math.sqrt(N))}
        print("  %3d コマ(%3.0f ms): 線形化 corr(C_d, ω⊥) = %+.3f、corr(C_d, |v₀|) = %+.3f、cond %.1e / 雑音 1 mm あたり: C_d ± %.4f、ω⊥ ± %.1f rad/s、平行成分 ± %.0f rad/s / "
              "モンテカルロ corr(C_d, ω⊥) = %+.2f(%d 本、3/√N = %.2f)、C_d の cv %s %%" % (
                  n, 1e3 * n / FPS, an[n]["corr_w"], an[n]["corr_v"], an[n]["cond"], 1e-3 * an[n]["cd_std"], 1e-3 * an[n]["pp"], 1e-3 * an[n]["ax"],
                  sweep[(n, "pooled")]["corr"], N, 3.0 / math.sqrt(N), " ".join("%.1f" % (100 * sweep[(n, s)]["cd_cv"]) for s in sigmas)))
    print("  (C_d の cv の列は雑音 σ = %s mm の順)" % ", ".join("%.1f" % (1e3 * s) for s in sigmas))
    gate("C_d と ω⊥ は直交して分かれる: 線形化の |相関| < 0.1、モンテカルロの相関は 0 と区別できない(|corr| < max(0.3, 3/√N))、全ての飛行長で",
         all(abs(an[n]["corr_w"]) < 0.1 and abs(sweep[(n, "pooled")]["corr"]) < sweep[(n, "pooled")]["thr"] for n in lens))
    gate("飛行を伸ばすと C_d・ω⊥ の精度が上がる: 雑音 1 mm あたりの標準偏差は最長で最短の 1/5 以下、cond も下がる、モンテカルロの cv(σ = 1.5 mm)は 1/3 以下",
         an[lens[-1]]["cd_std"] < an[lens[0]]["cd_std"] / 5 and an[lens[-1]]["pp"] < an[lens[0]]["pp"] / 5 and an[lens[-1]]["cond"] < an[lens[0]]["cond"]
         and sweep[(lens[-1], 1.5e-3)]["cd_cv"] < sweep[(lens[0], 1.5e-3)]["cd_cv"] / 3,
         "(C_d %.4f → %.4f、ω⊥ %.1f → %.1f rad/s / mm)" % (1e-3 * an[lens[0]]["cd_std"], 1e-3 * an[lens[-1]]["cd_std"], 1e-3 * an[lens[0]]["pp"], 1e-3 * an[lens[-1]]["pp"]))
    gate("C_d は初速と強く相関する(予想の的中): 線形化の corr(C_d, |v₀|) > 0.9 が全ての飛行長で。飛行を伸ばしても相関は消えず(精度だけが上がる)",
         all(an[n]["corr_v"] > 0.9 for n in lens), "(%s)" % ", ".join("%d コマ %+.3f" % (n, an[n]["corr_v"]) for n in lens))
    gate("読めない成分は全ての飛行長で悪い: 平行成分の標準偏差は垂直成分の 3 倍以上(短いほど開く)", all(an[n]["ax"] > 3 * an[n]["pp"] for n in lens),
         "(比 %s)" % ", ".join("%d コマ %.0f" % (n, an[n]["ax"] / an[n]["pp"]) for n in lens))
    if figs.enabled():
        print("== 9. 図")
        t_f = time.time()
        _figures(world, depths, bias_d, kap_d, degen, r_fix, lens, an, sweep, sigmas, w_bias)
        print("  図(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


def _figures(world, depths, bias_d, kap_d, degen, r_fix, lens, an, sweep, sigmas, w_bias):
    """表 2 枚 + グラフ 4 枚(図は FULLSEYE_FIGURE_DIR を設定したときだけ)。数字は本体の実行の値。"""
    rows = []
    for label, key, w0 in SERVES:
        wd = world[key]
        spin = np.linalg.norm(w0) > 0
        mk = "%s" % np.round(wd["w_marker"], 0).tolist()
        m_txt = "%.4f / %.4f" % tuple(wd["M"].mean(axis=0)) if "M" in wd else "(C_L 定義できず)"
        j = wd["J"]
        j_w = np.linalg.norm(j[:, 1:4].mean(axis=0))
        rows.append([label, "%.0f" % np.linalg.norm(w0), "%.4f / %.4f" % (wd["cd_eff"], wd["cl_eff"]), mk, m_txt,
                     "%.4f" % j[:, 0].mean(), "%.0f(%s)" % (j_w, "%.0f %%" % (100 * w_bias[key]) if spin else "真値 0")])
    spinning = [k for k in ("top", "back", "side")]
    d_cd_m = max(abs(world[k]["M"][:, 0].mean() - world[k]["cd_eff"]) / world[k]["cd_eff"] for k in spinning)
    d_cl_m = max(abs(world[k]["M"][:, 1].mean() - world[k]["cl_eff"]) / world[k]["cl_eff"] for k in spinning)
    d_cd_j = max(abs(world[k]["J"][:, 0].mean() - world[k]["cd_eff"]) / world[k]["cd_eff"] for k in world)
    figs.save_table("estimates_by_mode", ["打球", "真の |ω| [rad/s]", "世界の実効 C_d / C_L", "模様から ω [rad/s]",
                                          "ω = 模様 → 軌跡から C_d / C_L", "軌跡だけ(同時): C_d", "軌跡だけ: |ω⊥|(誤差)"], rows,
                    title="C_d と ω を 2 通りの分担で読む(世界は C_d が Re 依存・C_L に谷、当てはめは定数)",
                    caption="ω を模様から取り、軌跡から C_d・C_L を読むと世界の実効値との差は C_d %.1f %%・C_L %.1f %% 以内。軌跡だけで C_d と ω を同時に読むと C_d は %.1f %% 以内だが、ω は C_L の谷のぶん %.0f〜%.0f %% 小さく出る。真値は全部この PoC が仕込んだ世界の値。" % (
                        100 * d_cd_m, 100 * d_cl_m, 100 * d_cd_j, 100 * min(w_bias.values()), 100 * max(w_bias.values())))
    Sg = np.linspace(0.02, 1.2, 80)
    figs.save_plot("cl_world_vs_model", [("世界の C_L(S = 0.5 に谷、仮の値)", Sg, [cl_world(s) for s in Sg]),
                                         ("当てはめの模型 S/(1 + 2S)", Sg, B.magnus_lift_coefficient(Sg))],
                   xlabel="スピン比 S = rω/|v|", ylabel="C_L", title="世界と当てはめで C_L の式が違う", styles=[None, "dashed"],
                   caption="観測を作る世界(実線)は S = 0.5 付近に谷があり、当てはめの模型(破線)にはない。卓球の 150 rad/s・6 m/s は S ≈ 0.5 で、谷の真ん中に当たる。谷の位置・深さは仮の値。")
    figs.save_plot("omega_bias_vs_dip", [("ω の誤差 [%]", 100 * np.asarray(depths), 100 * np.asarray(bias_d)),
                                         ("C_L の不足 100(1 − κ_eff) [%]", 100 * np.asarray(depths), 100 * (1 - np.asarray(kap_d)))],
                   xlabel="C_L の谷の深さ [%]", ylabel="[%]", title="軌跡だけで読む ω は、谷の深さとともに偏る",
                   caption="トップスピンを軌跡だけ(C_d と ω を同時、κ = 1、雑音なしの軌跡)で読んだ ω の誤差(実線)と、世界の C_L が当てはめの模型に足りない割合(破線)。深さ 0 では誤差が %.1f %% まで消える。" % (100 * bias_d[0]))
    figs.save_table("degeneracy_valley", ["初期 ω [rad/s]", "読んだ ω⊥ [rad/s]", "κ", "rms [mm]", "模型の C_L", "条件数", "corr(ω, κ)"],
                    [["%.0f" % d[0], "%.1f" % d[1], "%.3f" % d[2], "%.3f" % (1e3 * d[3]), "%.4f" % d[4], "%.1e" % d[5], "%+.4f" % d[6]] for d in degen]
                    + [["κ = 1 固定", "-", "1.000", "%.3f" % (1e3 * r_fix["rms"]), "", "%.1e" % r_fix["cond"], ""]],
                    title="ω と C_L の係数 κ は縮退する(トップ、同じ軌跡)",
                    caption="κ も自由にすると、初期値によって ω は %.0f〜%.0f rad/s と違う答えになるのに、rms は %.3f〜%.3f mm で同じ、模型の C_L も同じ(%.4f〜%.4f)。軌跡が決めているのは積(力)だけで、ω の大きさは読めない。最下行は κ を 1 に固定した当てはめ(ω⊥ の欄は空)。" % (
                        min(d[1] for d in degen), max(d[1] for d in degen), 1e3 * min(d[3] for d in degen), 1e3 * max(d[3] for d in degen),
                        min(d[4] for d in degen), max(d[4] for d in degen)))
    figs.save_table("sweep_by_length", ["コマ数(時間)", "線形化 corr(C_d, ω⊥)", "線形化 corr(C_d, |v₀|)", "条件数", "C_d の ± / 雑音 1 mm", "ω⊥ の ± / 雑音 1 mm", "平行成分の ± / 雑音 1 mm", "モンテカルロ corr(C_d, ω⊥)"],
                    [["%d(%.0f ms)" % (n, 1e3 * n / FPS), "%+.3f" % an[n]["corr_w"], "%+.3f" % an[n]["corr_v"], "%.1e" % an[n]["cond"], "%.4f" % (1e-3 * an[n]["cd_std"]),
                      "%.1f rad/s" % (1e-3 * an[n]["pp"]), "%.0f rad/s" % (1e-3 * an[n]["ax"]), "%+.2f(%d 本)" % (sweep[(n, "pooled")]["corr"], sweep[(n, "pooled")]["N"])] for n in lens],
                    title="飛行の長さを振る(トップ、C_d と ω を同時に当てる)",
                    caption="C_d と ω⊥ は直交して相関が 0 に近い(最大 %.3f)一方、C_d は初速と %.2f〜%.2f で相関する。飛行を伸ばすと精度は上がるが、この相関は消えない。進行方向に平行な ω の成分は、どの長さでも垂直成分より %.0f〜%.0f 倍読めない。" % (
                        max(abs(an[n]["corr_w"]) for n in lens), min(an[n]["corr_v"] for n in lens), max(an[n]["corr_v"] for n in lens),
                        min(an[n]["ax"] / an[n]["pp"] for n in lens), max(an[n]["ax"] / an[n]["pp"] for n in lens)))
    figs.save_plot("cd_scatter_vs_length", [("σ = %.1f mm" % (1e3 * sg), [1e3 * n / FPS for n in lens], [100 * sweep[(n, sg)]["cd_cv"] for n in lens]) for sg in sigmas],
                   xlabel="使った軌跡の長さ [ms]", ylabel="C_d の標準偏差 / 実効値 [%]", title="C_d は飛行が短いと決まらず、雑音に比例して悪くなる",
                   caption="位置雑音 σ を 3 通りに振り、軌跡の先頭 n コマで C_d と ω を同時に当てたときの C_d のばらつき(モンテカルロ)。短い軌跡では速さの減衰が小さく、C_d は初速と分けられない。")


if __name__ == "__main__":
    sys.exit(main())
