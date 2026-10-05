# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ディアボロの解析模型を原文から写して確かめ、合成映像から軸・回転・張力を読む —— 閉形式・厳密な糸・MuJoCo を真値に(2026-10-05)。

物理シミュ × Fullseye 系列。一次情報はロボット学習用のディアボロ解析模型(von Drigalski ほか、ICRA 2021、arXiv:2011.09068)の
LaTeX 原文。模型は「ディアボロ = 質点 + 糸が作る補助の回転楕円体 + 重力」で、1 ステップ = 前進 Euler → 楕円体の外に出たら戻す。
原文どおりでは成り立たない所が 3 つあった: 式 (1b) は次元が合わず論文の実機寸法で NaN、状態遷移の LOOSE → ON は帯が重なって
毎ステップ行き来する、回転の式 (2) と公開実装(BSD-3、読んで比べただけ)の回転則は別物で後者は刻みに依存する。直した形を、
外から来る真値 3 系統と突き合わせる:
  * **閉形式・恒等式**: 焦点の恒等式、前進 Euler のずれ g t dt/2、式 (2) の望遠鏡和と転がりの極限 μ = 1/r、振り子の周期(縦は
    楕円の最下点の曲率半径 a²/b)、静止張力 m g a/(2b)、放物線の頂点と受け。
  * **厳密な糸の模型**(こちらで足した物): 伸びない糸の片側拘束を RATTLE で。エネルギー・角運動量・仕事率の収支が閉じる。
  * **MuJoCo の空間テンドン(--full)**: 別の解法の第 2 実装。
視覚は学習なし: 光線追跡の合成映像から、手前のカップの縁と底の板の 2 つの円の透視モーメントで軸と中心を、内面のマーカーの位相と
回転ぶれの弧で回転数を、棒の先と軸の V 字で糸の張力を読む。

門(既定 18 本、--full でさらに 7 本): 1 焦点の恒等式と原文の NaN / 2 法線 = 勾配(公開実装の法線のずれ)/ 3 前進 Euler のずれ /
4 回転の式 (2) と公開実装の刻み依存 / 5 エネルギー / 6 仕事率の収支 / 7 角運動量 / 8 振り子の周期 / 9 張力の乗数 /
10 画像から張力 / 11 受けの時刻 / 12 頂点のずれ / 13 状態遷移の再分類 / 14 画像から軸(3 姿勢)/ 15 回転数の枝選び(位相列)/
16 綴り壊し / 17 推定が寸法を使う・鏡 / 18 MJCF 文字列; --full: 19 画像から軸(42 姿勢)/ 20 壊れる場所と 45° の警報 /
21 回転数(描画、120 fps)/ 22 投げの映像の追跡 / 23 状態の一致 / 24 MuJoCo vs 厳密 ≤ 5 mm / 25 論文の模型 vs 厳密 ≤ 5 mm。
図(FULLSEYE_FIGURE_DIR があるとき): 投げの映像に画像から推定した軸と真値の軸を重ねた GIF、垂れと張力(閉形式・原文の式・
画像から読んだ点)、3 つの模型の軌跡と差、回転則の刻み依存; --full で回転の錯視の GIF、軸の誤差の表、壊れる場所の表を足す。
正直に: 外の真値は論文の式・閉形式・MuJoCo だけで実写とは合わせていない。姿勢(傾き・首振り)は力学で解かず、画像から読む軸は
描いた時に与えた姿勢。描画は理想化した色と照明。受けの瞬間は厳密模型が完全非弾性、MuJoCo は跳ねる(比べない窓 0.3 s)。
Run: py -3.11 examples/poc_diabolo_model_and_vision.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import math
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import diabolo as D  # noqa: E402
import examplefig as figs  # noqa: E402
import imagedraw as IDR  # noqa: E402
from drawstyle import DrawStyle  # noqa: E402

P = D.diabolo_params()
G = P["g"]
FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}
RNG = np.random.default_rng(20261005)
# 軸の推定の門のカメラ: 前 1.2 m、240 × 320、画角 16°(縁の半径 ≈ 48 px)
RATIO_PAPER_TOL, RATIO_CODE_TOL = 0.01, 0.05     # 実測(2026-10-05)から固定
CAM_AX = D.diabolo_camera(position=(1.2, 0, 0.6), look_at=(0, 0, 0.6), shape=(240, 320), fovy_deg=16)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _hang(sticks):
    """棒の組の真下、楕円体の最下点(静止の位置)。"""
    s = np.asarray(sticks)
    sph = D.diabolo_spheroid(s[0], s[1], P["string_length"])
    return sph["center"] - np.array([0.0, 0.0, sph["b"]])


def _periods(t, y):
    y = y - np.mean(y)
    i = np.nonzero((y[:-1] < 0) & (y[1:] >= 0))[0]
    tc = t[i] - y[i] * (t[i + 1] - t[i]) / (y[i + 1] - y[i])
    return np.diff(tc)


def _axis_dir(th_deg, ph_deg):
    th, ph = math.radians(th_deg), math.radians(ph_deg)
    return np.array([math.cos(th), math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph)])


def _axis_case(cam, th_d, ph_d, c, **kw):
    a = _axis_dir(th_d, ph_d)
    img = D.diabolo_render(cam, P, center=c, axis=a, phase=float(RNG.uniform(0, 2 * np.pi)), **kw)
    r = D.diabolo_axis_from_image(img, cam, P)
    return D._angle_deg(r["axis"], a), 1000 * float(np.linalg.norm(r["center"] - c)), r


# ======================================================================================================================
def numpy_part() -> dict:
    print("== 1. 既定の門(閉形式・厳密な糸・合成映像の 3 姿勢)")
    out = {}
    # ── 1. 焦点の恒等式と原文の (1b)
    errs = []
    for _ in range(60):
        pl = RNG.normal(0, 0.5, 3)
        pr = pl + RNG.normal(0, 0.5, 3)
        ln = float(np.linalg.norm(pl - pr)) * RNG.uniform(1.05, 3.0)
        sph = D.diabolo_spheroid(pl, pr, ln)
        e1, e2, _ = D._body_frame(sph["axis"])
        for th, ph in RNG.uniform([0, 0], [np.pi, 2 * np.pi], (10, 2)):
            x = sph["center"] + sph["a"] * math.cos(th) * sph["axis"] + sph["b"] * math.sin(th) * (math.cos(ph) * e1 + math.sin(ph) * e2)
            errs.append(abs(np.linalg.norm(x - pl) + np.linalg.norm(x - pr) - ln) / ln)
    assert len(errs) >= 600
    s11 = D.diabolo_spheroid(*D._mo_fixed(0), 1.45)
    s03 = D.diabolo_spheroid([0, 0.15, 1], [0, -0.15, 1], 1.45)
    gate("門 1 焦点の恒等式 d_L + d_R = l(直した式 1b、楕円体の面の 600 点): max %.1e。原文どおりの (1b) は棒の間隔 1.1 m で根の中が負 = %s、"
         "0.3 m で b = %.3f m(正しくは %.3f m)" % (max(errs), s11["b_paper_literal"], s03["b_paper_literal"], s03["b"]),
         max(errs) < 1e-12 and math.isnan(s11["b_paper_literal"]) and abs(s03["b"] - math.sqrt(0.725 ** 2 - 0.15 ** 2)) < 1e-15 and abs(s03["b_paper_literal"] - math.sqrt(0.725 ** 2 - 0.15)) < 1e-15)
    _NUM["focal_identity_max"] = max(errs)
    # ── 2. 法線 = 勾配、公開実装の法線、放射の戻し方
    sph = s11
    pl, pr = D._mo_fixed(0)
    e1, e2, _ = D._body_frame(sph["axis"])
    worst_true = worst_code = radial_gap = 0.0
    n_pts = 0
    for th in np.linspace(0.05, np.pi - 0.05, 30):
        for ph in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            x = sph["center"] + sph["a"] * math.cos(th) * sph["axis"] + sph["b"] * math.sin(th) * (math.cos(ph) * e1 + math.sin(ph) * e2)
            g = (x - pl) / np.linalg.norm(x - pl) + (x - pr) / np.linalg.norm(x - pr)
            worst_true = max(worst_true, D._angle_deg(g, D.spheroid_closest(x + 1e-9 * g / np.linalg.norm(g), sph)["normal"]))
            worst_code = max(worst_code, D._angle_deg(g, D._normal_code_variant(x, sph)))
            xo = x + 0.005 * g / np.linalg.norm(g)
            r = xo - sph["center"]
            z = float(r @ sph["axis"])
            rho = float(np.linalg.norm(r - z * sph["axis"]))
            k = 1 / math.sqrt((z / sph["a"]) ** 2 + (rho / sph["b"]) ** 2)
            radial_gap = max(radial_gap, float(np.linalg.norm(sph["center"] + k * r - D.spheroid_closest(xo, sph)["point"])))
            n_pts += 1
    assert n_pts >= 360
    gate("門 2 法線 = 楕円体の勾配 û_L + û_R(最近点から、%d 点): max %.1e°。公開実装の法線 (x/b, y/a, z/b) は最大 %.1f° ずれ、中心から"
         "放射方向に戻すと最近点と外 5 mm の点で最大 %.1f mm 違う" % (n_pts, worst_true, worst_code, 1000 * radial_gap),
         worst_true < 1e-9 and 10 < worst_code < 15 and 1.5e-3 < radial_gap < 3e-3)
    _NUM["normal"] = {"true_deg": worst_true, "code_variant_deg": worst_code, "radial_mm": 1000 * radial_gap}
    # ── 3. 前進 Euler のずれ(飛んでいる間)
    dt, n = 1e-3, 600
    st = {"x": np.array([0.1, 0.0, 2.0]), "v": np.array([0.3, 0.2, 2.5]), "omega": 0.0, "mode": "flying"}
    sticks = np.array([[0, 0.15, 1.0], [0, -0.15, 1.0]])
    x0, v0 = st["x"].copy(), st["v"].copy()
    worst, modes = 0.0, set()
    for i in range(1, n + 1):
        st = D.diabolo_dynamics_step(st, sticks, sticks, dt, P)
        modes.add(st["mode"])
        t = i * dt
        pred = x0 + v0 * t + 0.5 * np.array([0, 0, -G]) * t * t + np.array([0, 0, G * t * dt / 2])
        worst = max(worst, float(np.max(np.abs(st["x"] - pred))))
    gate("門 3 飛んでいる間の前進 Euler は真の放物線より g t dt/2 だけ上(0.6 s で %.2f mm): 閉形式との差 max %.1e m"
         % (1000 * G * n * dt * dt / 2, worst), worst < 1e-12 and modes == {"flying"})
    # ── 4. 回転の式 (2): 望遠鏡和、転がりの極限、公開実装の回転則の刻み依存
    om = {}
    worst = 0.0
    x_hang = _hang(D._mo_linear_accel(0))
    for dt in (2e-3, 1e-3):
        r = D.diabolo_simulate(x_hang, [0, 0, 0], "linear_accel", 2.0, dt, P, model="paper")
        dr = np.diff(np.linalg.norm(r["x"] - r["sticks"][:, 1], axis=1))
        pred = r["omega"][0] + P["mu_acc"] * dr[dr > 0].sum() + P["mu_dec"] * dr[dr <= 0].sum()
        worst = max(worst, abs(pred - r["omega"][-1]) / abs(r["omega"][-1]))
        rc = D.diabolo_simulate(x_hang, [0, 0, 0], "linear_accel", 2.0, dt, P, model="paper", rotation="code")
        om[dt] = (float(r["omega"][-1]), float(rc["omega"][-1]), bool(np.all(r["mode"] == "on_string")))
    Pr = D.diabolo_params(mu_acc=1 / P["axle_radius"], mu_dec=1 / P["axle_radius"])
    r = D.diabolo_simulate(x_hang, [0, 0, 0], "linear_accel", 2.0, 2e-3, Pr, model="paper")
    dr = np.linalg.norm(r["x"] - r["sticks"][:, 1], axis=1)
    roll = float(np.max(np.abs(r["omega"] * P["axle_radius"] - (dr - dr[0]))))
    ratio_paper = om[1e-3][0] / om[2e-3][0]
    ratio_code = om[1e-3][1] / om[2e-3][1]
    gate("門 4 回転の式 (2) ω_t = ω_{t−1} + μ Δ_string は望遠鏡和(相対 %.1e)、μ = 1/r で滑らない転がり ω r = Δd_R(%.1e m)。直線加速 2 s、刻み 2 → 1 ms で"
         "式 (2) の ω は %.2f → %.2f rad/s(比 %.3f)、公開実装の回転則 Δω = k(Δd/dt − ω r) は %.3f → %.3f(比 %.2f ≈ 刻みに反比例)"
         % (worst, roll, om[2e-3][0], om[1e-3][0], ratio_paper, om[2e-3][1], om[1e-3][1], ratio_code),
         worst < 1e-9 and roll < 1e-9 and abs(ratio_paper - 1) < RATIO_PAPER_TOL and abs(ratio_code - 2) < RATIO_CODE_TOL and om[1e-3][2] and om[2e-3][2])
    _NUM["rotation"] = {"paper_2ms": om[2e-3][0], "paper_1ms": om[1e-3][0], "code_2ms": om[2e-3][1], "code_1ms": om[1e-3][1]}
    # ── 5. エネルギー(厳密、棒は固定、振れ 20°)
    th = math.radians(20)
    x20 = s11["center"] + s11["b"] * np.array([math.sin(th), 0, -math.cos(th)])
    re = D.diabolo_simulate(x20, [0, 0, 0], "fixed", 2.0, 1e-3, P, model="exact")
    rp = D.diabolo_simulate(x20, [0, 0, 0], "fixed", 2.0, 1e-3, P, model="paper")
    Esw = P["mass"] * G * s11["b"] * (1 - math.cos(th))
    drift = float((re["energy"].max() - re["energy"].min()) / Esw)
    p_end = float((rp["energy"][-1] - rp["energy"][0]) / Esw)
    gate("門 5 エネルギー(厳密な糸、棒は固定、振れ 20°、2 s): 振れのエネルギー %.3f J に対し幅 %.1e。論文の模型は 2 s で %+.2f %%"
         % (Esw, drift, 100 * p_end), drift < 1.5e-5, "")
    _NUM["energy"] = {"exact_rel_range": drift, "paper_rel_change": p_end}
    out["energy_series"] = (re, rp)
    # ── 6. 仕事率の収支 ΔE = ∫ −T(û·v_棒) dt(棒を振る、厳密)
    errs6 = {}
    xs = _hang(D._mo_swing(0))
    for h in (4e-4, 2e-4):
        r = D.diabolo_simulate(xs, [0, 0, 0], "swing", 1.0, h, P, model="exact")
        T = np.nan_to_num(r["tension"])
        eps = 1e-6
        Pw = np.zeros(len(r["t"]))
        for i, t in enumerate(r["t"]):
            vs = (D._mo_swing(t + eps) - D._mo_swing(t - eps)) / (2 * eps)
            x = r["x"][i]
            ul = (x - r["sticks"][i, 0]) / np.linalg.norm(x - r["sticks"][i, 0])
            ur = (x - r["sticks"][i, 1]) / np.linalg.norm(x - r["sticks"][i, 1])
            Pw[i] = -T[i] * (ul @ vs[0] + ur @ vs[1])
        Wk = np.concatenate([[0], np.cumsum(0.5 * (Pw[1:] + Pw[:-1]) * h)])
        dE = r["energy"] - r["energy"][0]
        errs6[h] = float(np.max(np.abs(dE - Wk)) / np.max(np.abs(dE)))
    order = math.log(errs6[4e-4] / errs6[2e-4], 2)
    gate("門 6 仕事率の収支(棒を左右に振る、厳密な糸、1 s): エネルギーの変化 = 張力 × 棒の速度の積分、相対差 %.1e(刻み 0.4 ms)→ %.1e(0.2 ms)、"
         "収束の次数 %.2f" % (errs6[4e-4], errs6[2e-4], order), errs6[2e-4] < 3e-4 and 0.8 < order < 1.3)
    # ── 7. 角運動量(焦点軸が鉛直、重力 ∥ 軸)
    pl, pr = D._mo_vertical_axis(0)
    sv = D.diabolo_spheroid(pl, pr, 1.45)
    zax = -0.3
    rho = sv["b"] * math.sqrt(1 - (zax / sv["a"]) ** 2)
    xv = sv["center"] + zax * sv["axis"] + rho * np.array([1.0, 0, 0])
    lz = {}
    for model in ("exact", "paper"):
        r = D.diabolo_simulate(xv, [0.0, 1.8, 0.2], "vertical_axis", 2.0, 1e-3, P, model=model, topology=False)
        Lz = P["mass"] * (r["x"][:, 0] * r["v"][:, 1] - r["x"][:, 1] * r["v"][:, 0])
        lz[model] = float(np.max(np.abs(Lz - Lz[0])) / abs(Lz[0]))
    gate("門 7 焦点軸まわりの角運動量(軸が鉛直・重力 ∥ 軸、2 s): 厳密な糸 %.1e、論文の模型 %.2f %%(最近点への戻しと速度の頭打ちが回転対称を崩す)"
         % (lz["exact"], 100 * lz["paper"]), lz["exact"] < 1e-12 and lz["paper"] > 1e-4)
    # ── 8. 振り子の周期(厳密な糸、横・縦 2 周期ずつ)
    a_, b_ = s11["a"], s11["b"]
    T_tr, T_lo = 2 * math.pi * math.sqrt(b_ / G), 2 * math.pi * math.sqrt(a_ * a_ / (b_ * G))
    x_tr = s11["center"] + b_ * np.array([math.sin(math.radians(1)), 0, -math.cos(math.radians(1))])
    x_lo = s11["center"] + np.array([0, a_ * math.sin(math.radians(1)), -b_ * math.cos(math.radians(1))])
    r1 = D.diabolo_simulate(x_tr, [0, 0, 0], "fixed", 2.2 * T_tr, 1e-3, P, model="exact")
    r2 = D.diabolo_simulate(x_lo, [0, 0, 0], "fixed", 2.2 * T_lo, 1e-3, P, model="exact")
    p1, p2 = _periods(r1["t"], r1["x"][:, 0]), _periods(r2["t"], r2["x"][:, 1])
    assert len(p1) >= 1 and len(p2) >= 1
    e_tr, e_lo = float(np.mean(p1)) / T_tr - 1, float(np.mean(p2)) / T_lo - 1
    gate("門 8 振り子の周期(厳密な糸、振れ 1°): 横 2π√(b/g) = %.3f s に %+.1e、縦は楕円の最下点の曲率半径 a²/b で 2π√(a²/(bg)) = %.3f s に %+.1e"
         % (T_tr, e_tr, T_lo, e_lo), max(abs(e_tr), abs(e_lo)) < 1e-4)
    _NUM["periods"] = {"T_transverse": T_tr, "T_longitudinal": T_lo, "rel": (e_tr, e_lo)}
    # ── 9, 10. 張力: 閉形式 vs 厳密の乗数 vs 画像
    cam9 = D.diabolo_camera(position=(2.2, 0, 0.75), look_at=(0, 0, 0.75), shape=(240, 320), fovy_deg=34)
    worst_mult, worst_img, rows9 = 0.0, 0.0, []
    for gap in (0.6, 0.9, 1.1, 1.3):
        sk = {"kind": "fixed", "gap": gap}
        cf = D.string_tension_static(gap, P)
        xh = _hang(D._mo_fixed(0, gap))
        r = D.diabolo_simulate(xh, [0, 0, 0], sk, 0.2, 1e-3, P, model="exact")
        worst_mult = max(worst_mult, abs(r["tension"][-1] / cf["tension"] - 1))
        img = D.diabolo_render(cam9, P, center=xh, axis=[1, 0, 0], sticks=D._mo_fixed(0, gap))
        est = D.diabolo_axis_from_image(img, cam9, P)
        Pt = D._backproject_to_plane(cam9, D._stick_tips_px(img), est["center"], cam9["R"][2])
        a1, a2 = (Pt[0], Pt[1]) if Pt[0, 1] > Pt[1, 1] else (Pt[1], Pt[0])
        te = D.string_tension_from_sag(a1, a2, est["center"], P["mass"])
        worst_img = max(worst_img, abs(te["tension"] / cf["tension"] - 1))
        rows9.append((gap, cf["sag"], cf["tension"], float(r["tension"][-1]), te["tension"], 1000 * float(np.linalg.norm(est["center"] - xh))))
    assert len(rows9) == 4
    gate("門 9 静止張力: 厳密な糸の乗数(RATTLE)= 閉形式 m g a/(2b)、棒の間隔 0.6 / 0.9 / 1.1 / 1.3 m で %.1e" % worst_mult, worst_mult < 1e-9)
    gate("門 10 画像から張力: 合成映像の棒の先(青い印)と軸の推定の V 字 → T = m g/(sin α_L + sin α_R)、閉形式との差 max %.2f %%(%s N、320 × 240・2.2 m 先)"
         % (100 * worst_img, " / ".join("%.2f" % rr[4] for rr in rows9)), worst_img < 0.006)
    out["tension_rows"] = rows9
    _NUM["tension_image_max_rel"] = worst_img
    # ── 11, 12, 13. 投げと受け(閉形式 vs 論文の模型)、状態遷移の再分類
    dt = 1e-3
    xt = _hang(D._mo_throw(0))
    r = D.diabolo_simulate(xt, [0, 0, 0], "throw", 2.0, dt, P, model="paper")
    md = r["mode"]
    fly = np.nonzero(md == "flying")[0]
    assert len(fly) >= 1
    k0 = int(fly[0])
    k1 = k0 + int(np.nonzero(md[k0:] != "flying")[0][0])
    tr = D.diabolo_throw_catch_truth(r["x"][k0], r["v"][k0], D._mo_throw(1.0), P, t_max=2.0)
    t_sim = float(r["t"][k1] - r["t"][k0])
    zmax = float(r["x"][k0:k1, 2].max())
    euler = G * tr["t_apex"] * dt / 2
    gate("門 11 受けの時刻: 放物線 × 楕円体 × 棒を結ぶ面(閉形式 + 二分法)%.4f s、論文の模型 %.4f s(差 %.1f ms ≤ 2 刻み)、頂点 %.3f m"
         % (tr["t_catch"], t_sim, 1000 * abs(t_sim - tr["t_catch"]), tr["apex_z"]), abs(t_sim - tr["t_catch"]) <= 2 * dt)
    gate("門 12 頂点のずれ = 前進 Euler の g t_apex dt/2(%.4f mm): 模型 − 閉形式 = %.4f mm(差 %.5f mm)"
         % (1000 * euler, 1000 * (zmax - tr["apex_z"]), 1000 * abs((zmax - tr["apex_z"]) - euler)),
         abs((zmax - tr["apex_z"]) - euler) < 1e-5)
    seq = D.diabolo_state_sequence(r["x"], r["sticks"], P)
    agree = float(np.mean(seq == md))
    n_states = {s: int(np.sum(md == s)) for s in D.DIABOLO_STATES}
    gate("門 13 状態遷移だけを位置の列に回す(diabolo_state_sequence)と、模型の内部の状態と %.1f %% 一致(投げ 2 s: %s 刻)"
         % (100 * agree, " / ".join("%s %d" % kv for kv in n_states.items())), agree >= 0.995 and n_states["flying"] > 100)
    out["throw_sim"] = r
    _NUM["throw"] = {"t_release": float(r["t"][k0]), "t_catch_closed": tr["t_catch"], "t_catch_sim": t_sim, "apex_z": tr["apex_z"],
                     "state_agree": agree}
    # ── 14. 画像から軸(3 姿勢)
    e14 = []
    for th_d, ph_d in ((0, 0), (20, 120), (38, 300)):
        c = np.array([0.0, *RNG.uniform(-0.03, 0.03, 2)]) + [0, 0, 0.6]
        e, ce, rr = _axis_case(CAM_AX, th_d, ph_d, c)
        e14.append((th_d, e, ce, rr["residual_px"], rr["ok"]))
    assert len(e14) == 3
    gate("門 14 画像から軸(縁の円 + 底の板の円の透視モーメント、縁の半径 %.0f px、視線から 0 / 20 / 38°): 3-D の角 %s°、中心 %s mm、警報なし"
         % (rr["a_px"], " / ".join("%.3f" % e[1] for e in e14), " / ".join("%.1f" % e[2] for e in e14)),
         max(e[1] for e in e14) < 0.3 and all(e[4] for e in e14))
    # ── 15. 回転数の枝選び(合成の位相列、描画なし)
    fps, expo = 120.0, 1 / 500
    dtf = 1 / fps
    rows15, err15, wrapped_wrong, tol15 = [], 0.0, [], []
    for rps in (10, 30, 50, 70, 90, 110):
        w = 2 * math.pi * rps
        phs = np.mod(0.4 + w * dtf * np.arange(5), 2 * np.pi)
        sms = abs(w) * expo * (1 + 0.05 * np.array([1, -1, 1, -1, 1]))       # 弧の幅を ±5 % 外す(中央値は +5 %)
        base = math.remainder(w * dtf, 2 * math.pi)
        wrong = [abs((base + 2 * math.pi * k) / dtf) for k in range(-12, 13) if abs((base + 2 * math.pi * k) / dtf - w) > 1e-6]
        tol15.append(min(abs(x - abs(w)) for x in wrong) / 2 / abs(w))     # 枝を取り違えない弧の幅の相対誤差の上限
        r1 = D.diabolo_spin_from_markers(phs, sms, dtf, expo)
        r0 = D.diabolo_spin_from_markers(phs, sms, dtf, expo, use_smear=False)
        err15 = max(err15, abs(r1["omega"] / w - 1))
        if abs(r0["omega"] / w - 1) > 0.05:
            wrapped_wrong.append(rps)
        rows15.append((rps, r0["omega"] / 2 / math.pi))
    gate("門 15 回転数の枝選び(120 fps、露光 2 ms、位相列は閉形式): 弧の幅で枝を選ぶと 10〜110 rev/s で誤差 %.1e、位相だけでは"
         "ナイキスト 60 rev/s を超えた %s rev/s が %s rev/s に折り返す。弧の幅の誤差の許容(枝を取り違えない上限)は %s %%"
         "(110 rev/s では回転の向きの違う枝 −817 rad/s が近い)" % (err15, wrapped_wrong, " / ".join("%.0f" % x for rp, x in rows15 if rp in wrapped_wrong),
                                     " / ".join("%.0f" % (100 * t) for t in tol15)),
         err15 < 1e-9 and wrapped_wrong == [70, 90, 110] and min(tol15) > 0.05)
    # ── 16. 綴り壊し(fail-closed)
    st0 = {"x": [0, 0, .5], "v": [0, 0, 0], "omega": 0, "mode": "on_string"}
    fx = D._mo_fixed(0)
    probes = [("kind", lambda: D.diabolo_params("rde")), ("key", lambda: D.diabolo_params(mu_acel=1.0)),
              ("model", lambda: D.diabolo_simulate([0, 0, 0.5], [0, 0, 0], "fixed", 0.01, 1e-3, P, model="papr")),
              ("motion", lambda: D.diabolo_simulate([0, 0, 0.5], [0, 0, 0], "fixd", 0.01, 1e-3, P)),
              ("motion key", lambda: D.diabolo_simulate([0, 0, 0.5], [0, 0, 0], {"kind": "swing", "ampl": 0.1}, 0.01, 1e-3, P)),
              ("plane_rule", lambda: D.diabolo_dynamics_step(st0, fx, fx, 1e-3, P, plane_rule="papr")),
              ("rotation", lambda: D.diabolo_dynamics_step(st0, fx, fx, 1e-3, P, rotation="cod")),
              ("flying_rule", lambda: D.diabolo_dynamics_step(st0, fx, fx, 1e-3, P, flying_rule="pape")),
              ("mode", lambda: D.diabolo_dynamics_step(dict(st0, mode="on-string"), fx, fx, 1e-3, P)),
              ("gap >= string", lambda: D.diabolo_spheroid([0, 1, 1], [0, -1, 1], 1.45)),
              ("NaN stick", lambda: D.diabolo_spheroid([0, np.nan, 1], [0, -0.5, 1], 1.45)),
              ("negative mass", lambda: D.diabolo_params(mass=-0.1)),
              ("one phase", lambda: D.diabolo_spin_from_markers([0.1], [0.1], 1e-2, 2e-3)),
              ("empty frames", lambda: D.diabolo_track([], CAM_AX, P)),
              ("gray image", lambda: D.diabolo_axis_from_image(np.zeros((240, 320)), CAM_AX, P))]
    missed = [nm for nm, fn in probes if not _raises(fn)]
    gate("門 16 綴り壊し %d 本(kind・鍵・model・棒の動きの名と引数・plane_rule・rotation・flying_rule・mode・間隔 ≥ 糸・NaN・負の質量・位相 1 コマ・"
         "空のコマ列・灰色の画像)は全部 ValueError" % len(probes), not missed, "取りこぼし %s" % missed)
    # ── 17. 推定が寸法を使っているか(探針)と鏡
    c = np.array([0.0, 0.0, 0.6])
    img = D.diabolo_render(CAM_AX, P, center=c, axis=[math.cos(0.2), math.sin(0.2), 0], phase=0.1)
    r0 = D.diabolo_axis_from_image(img, CAM_AX, P)
    r1 = D.diabolo_axis_from_image(img, CAM_AX, D.diabolo_params(diameter=P["diameter"] * 1.05))
    depth_ratio = float(np.linalg.norm(r1["center_rim"] - CAM_AX["C"]) / np.linalg.norm(r0["center_rim"] - CAM_AX["C"]))
    rm = D.diabolo_axis_from_image(img[:, ::-1].copy(), CAM_AX, P)
    mirror = abs(rm["axis"][1] + r0["axis"][1]) + abs(rm["axis"][2] - r0["axis"][2])
    gate("門 17 推定は寸法を本当に使う: 直径を 5 %% 大きく偽ると深度 × %.4f(期待 1.05)、左右を反転した画像では軸が鏡に映る(%.1e)"
         % (depth_ratio, mirror), abs(depth_ratio - 1.05) < 0.002 and mirror < 1e-6)
    _NUM["probe_depth_ratio"] = depth_ratio
    # ── 18(既定). MJCF 文字列
    root = ET.fromstring(D.diabolo_scene_mjcf(P))
    sp = root.find("tendon/spatial")
    ok = (sp is not None and sp.get("range") == "0 1.45" and [s.get("site") for s in sp if s.tag == "site"] == ["sL", "sD", "sR"]
          and sum(1 for b in root.iter("body") if b.get("mocap") == "true") == 2
          and abs(float(next(root.iter("inertial")).get("mass")) - P["mass"]) < 1e-12
          and _raises(lambda: D.diabolo_scene_mjcf(P, solref=(0.0005,))))
    gate("門 18 第 2 実装の MJCF(mujoco 不要): 空間テンドン 棒の先 → ディアボロ → 棒の先、長さの上限 = 糸 1.45 m、mocap の棒 2 本、質量 = 表 I", ok)
    return out


# ======================================================================================================================
def full_part(out: dict) -> dict:
    print("== 2. --full の門(軸 42 姿勢・壊れる場所・描画した回転・投げの追跡・MuJoCo)")
    # ── 19. 画像から軸(42 姿勢)
    errs, cerr, table = [], [], {}
    for th_d in (0, 2, 5, 10, 20, 30, 38):
        for ph_d in (0, 60, 120, 180, 240, 300):
            c = np.array([0.0, *RNG.uniform(-0.03, 0.03, 2)]) + [0, 0, 0.6]
            e, ce, r = _axis_case(CAM_AX, th_d, ph_d, c)
            errs.append(e)
            cerr.append(ce)
            table[(th_d, ph_d)] = e
    assert len(errs) == 42
    gate("門 19 画像から軸(視線から 0〜38° × 方位 6 = 42 姿勢、縁の半径 %.0f px): 3-D の角 max %.3f°・中央値 %.3f°、中心 max %.1f mm"
         % (r["a_px"], max(errs), float(np.median(errs)), max(cerr)), max(errs) < 0.5)
    out["axis_table"] = table
    # ── 20. 壊れる場所と警報
    c = np.array([0.0, 0.01, 0.6])
    sweep = {}
    for s in (0.5, 1.0, 2.0, 3.0):
        sweep["blur σ %.1f px" % s] = max(_axis_case(CAM_AX, th, 60, c, blur_sigma=s)[0] for th in (5, 20))
    for nz in (0.01, 0.02, 0.05, 0.1):
        vals = []
        for th in (5, 20):
            try:
                vals.append(_axis_case(CAM_AX, th, 60, c, noise=nz, seed=3)[0])
            except ValueError:
                vals.append(float("inf"))
        sweep["noise σ %.2f" % nz] = max(vals)
    for fov in (32, 64, 128):
        cam = D.diabolo_camera(position=(1.2, 0, 0.6), look_at=(0, 0, 0.6), shape=(240, 320), fovy_deg=fov)
        try:
            e, _, r = _axis_case(cam, 20, 60, c)
            sweep["rim %.0f px" % r["a_px"]] = e
        except ValueError:
            sweep["fov %d (rim ~6 px)" % fov] = float("inf")
    _, _, r45 = _axis_case(CAM_AX, 45, 135, c)
    _, _, r38 = _axis_case(CAM_AX, 38, 135, c)
    breaks = [k for k, v in sweep.items() if v > 0.5]
    gate("門 20 壊れる場所: %s が 0.5° を超える / 視線から 45° は底の板が壁に隠れ残差 %.2f px で警報(38° は %.3f px で警報なし)"
         % (breaks, r45["residual_px"], r38["residual_px"]), len(breaks) > 0 and not r45["ok"] and r38["ok"])
    out["sweep"] = sweep
    # ── 21. 回転数(描画、120 fps、露光 2 ms)
    fps, expo, nfr = 120.0, 1 / 500, 5
    dtf = 1 / fps
    a = _axis_dir(8, 50)
    c = np.array([0.0, 0.0, 0.6])
    rows, err_s, wrapped = [], 0.0, []
    for rps in (10, 30, 50, 70, 90, 110):
        w = 2 * math.pi * rps
        phs, sms = [], []
        for k in range(nfr):
            img = D.diabolo_render(CAM_AX, P, center=c, axis=a, phase=0.4 + w * k * dtf, omega=w, exposure=expo, n_sub=16)
            mp = D.diabolo_marker_phase(img, CAM_AX, P, D.diabolo_axis_from_image(img, CAM_AX, P))
            phs.append(mp["phase"])
            sms.append(mp["smear"])
        r1 = D.diabolo_spin_from_markers(phs, sms, dtf, expo)
        r0 = D.diabolo_spin_from_markers(phs, sms, dtf, expo, use_smear=False)
        err_s = max(err_s, abs(r1["omega"] / w - 1))
        if abs(r0["omega"] / w - 1) > 0.05:
            wrapped.append(rps)
        rows.append((rps, r1["omega"] / 2 / math.pi, r0["omega"] / 2 / math.pi, r1["omega_smear"] / 2 / math.pi))
    gate("門 21 回転数を描いた映像から(120 fps・露光 2 ms・5 コマ、10〜110 rev/s): 誤差 max %.2f %%、位相だけでは %s rev/s が折り返す"
         % (100 * err_s, wrapped), err_s < 0.01 and wrapped == [70, 90, 110],
         "読み(枝あり / 位相だけ / 弧の幅だけ)= " + "; ".join("%d: %.1f / %.1f / %.0f" % rr for rr in rows))
    # ── 22, 23. 投げの映像の追跡と状態の一致
    cam = D.diabolo_camera(position=(3.0, 0, 1.05), look_at=(0, 0, 1.05), shape=(360, 480), fovy_deg=34)
    sim = out["throw_sim"]
    idx = np.arange(0, 1601, 40)
    frames, axes = [], []
    for i in idx:
        t = sim["t"][i]
        ax_t = np.array([math.cos(math.radians(8)), math.sin(math.radians(8)) * math.cos(3 * t), math.sin(math.radians(8)) * math.sin(3 * t)])
        axes.append(ax_t)
        frames.append(D.diabolo_render(cam, P, center=sim["x"][i], axis=ax_t, sticks=sim["sticks"][i]))
    trk = D.diabolo_track(frames, cam, P)
    err = 1000 * np.linalg.norm(trk["center"] - sim["x"][idx], axis=1)
    ax_err = np.array([D._angle_deg(u, v) for u, v in zip(trk["axis"], axes)])
    st_true = D.diabolo_state_sequence(sim["x"][idx], sim["sticks"][idx], P)
    st_est = D.diabolo_state_sequence(trk["center"], sim["sticks"][idx], P)
    agree = float(np.mean(st_true == st_est))
    rms = float(np.sqrt(np.nanmean(err ** 2)))
    gate("門 22 投げの映像の追跡(3 m 先、縁の半径 ≈ 13 px、%d コマ): 中心 RMS %.1f mm・max %.1f mm(主に深度)、軸 中央値 %.2f°・max %.2f°、警報 %d コマ"
         % (len(idx), rms, float(np.nanmax(err)), float(np.nanmedian(ax_err)), float(np.nanmax(ax_err)), int((~trk["ok"]).sum())), rms < 12.0)
    gate("門 23 追跡した位置に状態遷移を回すと真の軌跡の状態と %.1f %% 一致" % (100 * agree), agree >= 0.95)
    # ── 24, 25. MuJoCo vs 厳密、論文の模型 vs 厳密
    try:
        D._mujoco()
    except ImportError:
        skip("門 24〜25(MuJoCo)", "mujoco が無い")
        return out
    worst_mj, worst_paper, det = 0.0, 0.0, {}
    for name, T in (("linear_accel", 2.0), ("swing", 3.0), ("throw", 1.6)):
        motion = D._MOTIONS[name]
        x0 = _hang(motion(0))
        re = D.diabolo_simulate(x0, [0, 0, 0], name, T, 1e-4, P, model="exact")
        rp = D.diabolo_simulate(x0, [0, 0, 0], name, T, 1e-3, P, model="paper")
        rm = D.diabolo_mujoco_simulate(P, x0, [0, 0, 0], name, T)
        xe = re["x"][::10]
        dm = np.linalg.norm(rm["x"] - xe, axis=1)
        dp = np.linalg.norm(rp["x"] - xe, axis=1)
        win = np.ones(len(dm), bool)
        if name == "throw":       # 受けの直後 0.3 s は比べない(厳密と論文は完全非弾性、MuJoCo の柔らかい拘束は跳ねる)
            te = np.nan_to_num(re["tension"][::10])
            flying = np.nonzero((rm["t"] > 0.5) & (te[: len(dm)] <= 0))[0]
            assert len(flying) >= 1
            t_c = rm["t"][flying[-1] + 1]
            win = ~((rm["t"] >= t_c) & (rm["t"] < t_c + 0.3))
            det["bounce_mm"] = 1000 * float(dm[~win].max())
            out["models"] = (re, rp, rm, float(t_c))
        det[name] = (1000 * float(dm[win].max()), 1000 * float(dp.max()))
        worst_mj = max(worst_mj, float(dm[win].max()))
        worst_paper = max(worst_paper, float(dp.max()))
    rest = D.diabolo_mujoco_simulate(P, _hang(D._mo_fixed(0)), [0, 0, 0], "fixed", 1.0)
    trest = abs(rest["tension"][-1] / D.string_tension_static(1.1, P)["tension"] - 1)
    gate("門 24 MuJoCo の空間テンドン vs 厳密な糸(直線加速 / 振り / 投げ、受けの直後 0.3 s を除く): max %s mm、静止張力 %.1e。受けの瞬間だけ"
         " MuJoCo は %.0f mm 跳ねる" % (" / ".join("%.2f" % v[0] for k, v in det.items() if k != "bounce_mm"), trest, det["bounce_mm"]),
         worst_mj < 5e-3 and trest < 1e-5)
    gate("門 25 論文の模型 vs 厳密な糸(同じ 3 つの動き): max %s mm(違いは前進 Euler のずれと楕円体の内 5 cm で FLYING に入る規則)"
         % " / ".join("%.2f" % v[1] for k, v in det.items() if k != "bounce_mm"), worst_paper < 5e-3)
    _NUM["mujoco"] = det
    return out


# ======================================================================================================================
def _overlay_frame(img, cam, c_true, a_true, est, lines, inset=True):
    """1 コマに真の軸(紫の破線)と推定の軸(緑の矢印)と文字を重ねる。拡大の差し込みは最近傍の整数倍(値を作らない)。"""
    L = 0.22
    u0, ut = D._project(cam, np.stack([c_true, c_true + L * a_true]))
    im = IDR.draw_line(np.asarray(img, np.float64), tuple(u0), tuple(ut), style=DrawStyle(color=(0.78, 0.16, 0.86), width=3, line_style="dashed"))
    if est is not None and np.all(np.isfinite(est["center"])):
        e0, e1 = D._project(cam, np.stack([est["center"], est["center"] + L * est["axis"]]))
        im = AN.arrow(im, tuple(e0), tuple(e1), color=(0.16, 0.82, 0.24), width=2, head_len=8, head_width=6)
    H, W = im.shape[:2]
    if inset:
        cx, cy = int(round(u0[0])), int(round(u0[1]))
        x0, y0 = min(max(cx - 25, 0), W - 50), min(max(cy - 25, 0), H - 50)
        im = AN.zoom_inset(im, (x0, y0, 50, 50), (W - 156, 4), factor=3)
    return _with_caption_band(im, lines)


def _with_caption_band(im, lines, font_size=12):
    """文字は画の下に足した帯に書く(画の上に重ねるとディアボロが隠れる)。画そのものは等倍のまま。"""
    txt = "\n".join(lines)
    wmax = im.shape[1] - 22
    h = int(AN.measure_text(txt, font_size=font_size, max_width=wmax)["height"]) + 2 * 5 + 10      # 板の pad 5 + 余白
    band = np.full((h, im.shape[1], 3), 0.12)
    try:
        band = np.asarray(AN.text_box(band, txt, (6, 4), anchor="lt", font_size=font_size, box_alpha=0.0, max_width=wmax), np.float64)
    except ValueError as exc:            # 文字が収まらない等は図を落とさず素の帯(理由は図の失敗として残す)
        figs._errors.append("caption band: %r" % (exc,))
    return np.vstack([np.asarray(im, np.float64), band])


def figures(out: dict) -> None:
    print("== 図")
    # 01 投げの映像 + 推定の軸 vs 真の軸
    cam = D.diabolo_camera(position=(2.2, 0, 1.12), look_at=(0, 0, 1.12), shape=(360, 480), fovy_deg=40)
    r = D.diabolo_simulate(_hang(D._mo_throw(0)), [0, 0, 0], "throw", 1.9, 1e-3, P, model="paper")
    idx = np.arange(0, len(r["t"]), 60)
    st_true = D.diabolo_state_sequence(r["x"][idx], r["sticks"][idx], P)
    frames, est_c, errs = [], [], []
    for n, i in enumerate(idx):
        t = float(r["t"][i])
        tilt = math.radians(6 + 4 * math.sin(2.1 * t))
        a = np.array([math.cos(tilt), math.sin(tilt) * math.cos(2.6 * t), math.sin(tilt) * math.sin(2.6 * t)])
        img = D.diabolo_render(cam, P, center=r["x"][i], axis=a, sticks=r["sticks"][i])
        est = D.diabolo_axis_from_image(img, cam, P)
        est_c.append(est["center"])
        st_e = D.diabolo_state_sequence(np.array(est_c), r["sticks"][idx[:n + 1]], P)[-1]
        e = D._angle_deg(est["axis"], a)
        ce = 1000 * float(np.linalg.norm(est["center"] - r["x"][i]))
        errs.append((e, ce))
        frames.append(_overlay_frame(img, cam, r["x"][i], a, est,
                                     ["t = %.2f s (x0.6 slow)" % t, "state  true: %s  image: %s" % (st_true[n], st_e),
                                      "axis error %.2f deg   centre error %.1f mm" % (e, ce),
                                      "violet dashed = true axis, green arrow = from image"]))
    figs.save_gif("diabolo_throw_axis_from_image", frames, fps=10.0,
                  caption="投げ → 飛行 → 受けの合成映像(論文の模型の軌跡、480 × 360・2.2 m 先、0.06 s ごと)。各コマで画像だけから読んだ軸(緑の矢印)と描いた時の真の軸"
                          "(紫の破線)、状態遷移を真の位置と推定の位置で回した結果。軸の誤差 中央値 %.2f°・中心 中央値 %.1f mm(右上は 3 倍の最近傍拡大)。"
                          % (float(np.median([e[0] for e in errs])), float(np.median([e[1] for e in errs]))))
    # 02 垂れ: 直した式 vs 原文の式
    gaps = np.linspace(0.05, 1.44, 140)
    sag = np.array([D.string_tension_static(g, P)["sag"] for g in gaps])
    a_ = P["string_length"] / 2
    ok = a_ * a_ - gaps / 2 >= 0
    lit = np.sqrt(a_ * a_ - gaps[ok] / 2)
    figs.save_plot("diabolo_sag_corrected_vs_printed",
                   [("b = sqrt(a^2 - c^2) (eq. 1b corrected)", gaps, sag), ("eq. 1b as printed: sqrt(a^2 - d/2)", gaps[ok], lit),
                    ("printed form gives NaN beyond d = 2a^2", np.array([2 * a_ * a_, 2 * a_ * a_]), np.array([0.0, 0.75]))],
                   xlabel="stick gap d [m]", ylabel="sag below the sticks [m]", title="Spheroid half-axis b: corrected vs printed",
                   styles=[None, "dashed", "dotted"], colors=["reference", "wrong", "neutral"],
                   caption="式 (1b) の原文 √(a² − d/2) は長さと長さの 2 乗の差で次元が合わず、d > 2a² = %.3f m で NaN(論文の実機の間隔 1.10 m は NaN の側)。"
                           "直した √(a² − c²)(楕円の恒等式)が実線。" % (2 * a_ * a_))
    # 03 張力: 閉形式 vs 厳密の乗数 vs 画像(vs MuJoCo)
    rows = out["tension_rows"]
    T = np.array([D.string_tension_static(g, P)["tension"] for g in gaps])
    series = [("T = m g a / (2b) closed form", gaps, T),
              ("exact string (RATTLE multiplier)", np.array([rr[0] for rr in rows]), np.array([rr[3] for rr in rows])),
              ("read from the rendered image", np.array([rr[0] for rr in rows]), np.array([rr[4] for rr in rows]))]
    kinds, cols = ["line", "scatter", "scatter"], ["reference", "neutral", "emphasis"]
    if "rest_mj" in out:
        series.append(("MuJoCo tendon limit force", np.array([rr[0] for rr in out["rest_mj"]]), np.array([rr[1] for rr in out["rest_mj"]])))
        kinds.append("scatter")
        cols.append("right")
    figs.save_plot("diabolo_tension_closed_form_vs_image", series, xlabel="stick gap d [m]", ylabel="string tension [N]",
                   title="Static string tension (red diabolo 284.5 g)", kinds=kinds, colors=cols, styles=["dashed"] + [None] * (len(series) - 1),
                   ylim=(0, 12), caption="閉形式 T = m g a/(2b)(破線)に、厳密な糸の模型の乗数と、合成映像の棒の先と軸の V 字から読んだ張力(最大 %.2f %% 差)を重ねる。"
                                         % (100 * _NUM["tension_image_max_rel"]))
    # 04 軌跡: 論文の模型 vs 厳密(vs MuJoCo)
    if "models" in out:
        re, rp, rm, t_c = out["models"]
    else:
        re = D.diabolo_simulate(_hang(D._mo_throw(0)), [0, 0, 0], "throw", 1.6, 2e-4, P, model="exact")
        rp, rm, t_c = out["throw_sim"], None, None
    def _upto(rr, t_end=1.6):
        k = rr["t"] <= t_end + 1e-9
        return rr["t"][k], rr["x"][k]
    (te_, xe_), (tp_, xp_) = _upto(re), _upto(rp)
    series = [("exact string (RATTLE)", te_, xe_[:, 2]), ("paper model (eqs. 1-4, dt 1 ms)", tp_, xp_[:, 2])]
    styles, cols = ["dashed", None], ["reference", "emphasis"]
    if rm is not None:
        tm_, xm_ = _upto(rm)
        series.append(("MuJoCo spatial tendon", tm_, xm_[:, 2]))
        styles.append("dotted")
        cols.append("right")
    figs.save_plot("diabolo_throw_height_three_models", series, xlabel="time [s]", ylabel="diabolo height z [m]",
                   title="Throw: paper model vs exact string" + (" vs MuJoCo" if rm is not None else ""), styles=styles, colors=cols,
                   caption="同じ棒の動き(0.30〜0.50 s で開いて持ち上げ、張りつめたまま受ける)での高さ。頂点 %.3f m、受け %.3f s(閉形式)。"
                           % (_NUM["throw"]["apex_z"], _NUM["throw"]["t_release"] + _NUM["throw"]["t_catch_closed"]))
    step = int(round((tp_[1] - tp_[0]) / (te_[1] - te_[0])))
    xe = xe_[::step]
    nn = min(len(xe), len(tp_))
    assert nn >= 100
    diff = [("paper - exact", tp_[:nn], 1000 * np.linalg.norm(xp_[:nn] - xe[:nn], axis=1))]
    if rm is not None:
        diff.append(("MuJoCo - exact", tm_[:nn], 1000 * np.linalg.norm(xm_[:nn] - xe[:nn], axis=1)))
    figs.save_plot("diabolo_throw_position_difference", diff, xlabel="time [s]", ylabel="position difference [mm]",
                   title="Distance from the exact string model", colors=["emphasis", "right"][:len(diff)],
                   caption="論文の模型は厳密な糸と最大 %.1f mm で一致する(前進 Euler のずれ g t dt/2 と、楕円体の内 5 cm で FLYING に入る規則)。"
                           % float(diff[0][2].max()) + ("MuJoCo は受けの瞬間だけ跳ねる(%.3f s 付近)。" % t_c if t_c else ""))
    # 05 回転則の刻み依存
    series = []
    x_h = _hang(D._mo_linear_accel(0))
    for dt in (1e-3, 5e-4):
        r1 = D.diabolo_simulate(x_h, [0, 0, 0], "linear_accel", 2.0, dt, P, model="paper")
        r2 = D.diabolo_simulate(x_h, [0, 0, 0], "linear_accel", 2.0, dt, P, model="paper", rotation="code")
        series += [("eq. (2), dt %.1f ms" % (dt * 1e3), r1["t"], r1["omega"]), ("released code law x50, dt %.1f ms" % (dt * 1e3), r2["t"], 50 * r2["omega"])]
    figs.save_plot("diabolo_spin_law_step_dependence", series, xlabel="time [s] (sticks up/down in antiphase)", ylabel="spin ω [rad/s]",
                   title="Spin law: paper eq. (2) vs released code", styles=[None, None, "dashed", "dashed"],
                   colors=["reference", "emphasis", "reference", "emphasis"],
                   caption="式 (2) は望遠鏡和なので刻み 1 ms と 0.5 ms の線が重なる。公開実装の回転則(50 倍して表示)は刻みを半分にすると 2 倍になる。")
    if FULL:
        _figures_full(out)
    print("  figures:", figs.errors() or "ok")


def _figures_full(out: dict) -> None:
    # 06 回転の錯視(位相だけ vs ぶれの弧で枝を選ぶ)
    fps, expo = 120.0, 1 / 500
    dtf = 1 / fps
    a = np.array([math.cos(0.14), math.sin(0.14) * 0.6, math.sin(0.14) * 0.8])
    c = np.array([0.0, 0.0, 0.6])
    rps_list = np.repeat([10, 25, 45, 60, 75, 95, 115], 6)
    psi = 0.4
    phs, sms, frames = [], [], []
    for k, rps in enumerate(rps_list):
        w = 2 * math.pi * rps
        if k:
            psi += w * dtf
        img = D.diabolo_render(CAM_AX, P, center=c, axis=a, phase=psi, omega=w, exposure=expo, n_sub=16)
        mp = D.diabolo_marker_phase(img, CAM_AX, P, D.diabolo_axis_from_image(img, CAM_AX, P))
        phs.append(mp["phase"])
        sms.append(mp["smear"])
        same = [j for j in range(max(0, k - 4), k + 1) if rps_list[j] == rps]
        if len(same) >= 3:
            r1 = D.diabolo_spin_from_markers([phs[j] for j in same], [sms[j] for j in same], dtf, expo)
            r0 = D.diabolo_spin_from_markers([phs[j] for j in same], [sms[j] for j in same], dtf, expo, use_smear=False)
            txt = ["true        %5.1f rev/s" % rps, "phase only  %5.1f rev/s" % (r0["omega"] / 2 / math.pi),
                   "with smear  %5.1f rev/s" % (r1["omega"] / 2 / math.pi), "120 fps, exposure 2 ms, Nyquist 60 rev/s"]
        else:
            txt = ["true        %5.1f rev/s" % rps, "(collecting frames)", "", "120 fps, exposure 2 ms, Nyquist 60 rev/s"]
        frames.append(_with_caption_band(img, txt, font_size=11))
    figs.save_gif("diabolo_spin_aliasing_and_smear", frames, fps=5.0,
                  caption="回転を上げると 120 fps の像ではマーカーが止まり、逆に回って見える(車輪の錯視)。位相だけの読みはナイキスト 60 rev/s で折り返し、"
                          "回転ぶれの弧の幅で枝を選んだ読みは真値に付いていく(320 × 240、等倍)。")
    # 07 軸の誤差の表、08 壊れる場所の表
    tab = out["axis_table"]
    phs_ = sorted({k[1] for k in tab})
    ths_ = sorted({k[0] for k in tab})
    figs.save_table("diabolo_axis_error_table", ["tilt / azimuth [deg]"] + [str(p) for p in phs_],
                    [[str(t)] + ["%.3f" % tab[(t, p)] for p in phs_] for t in ths_], title="3-D axis error from one image [deg]",
                    caption="視線からの傾き × 像の上の方位で、画像だけから読んだ軸と描いた時の軸の角(縁の半径 ≈ 48 px)。")
    figs.save_table("diabolo_where_axis_breaks", ["condition", "worst axis error [deg]", "> 0.5 deg"],
                    [[k, "%.2f" % v if math.isfinite(v) else "no estimate", str(v > 0.5)] for k, v in out["sweep"].items()],
                    title="Where the axis estimate breaks (tilt 5 and 20 deg)",
                    caption="ぼけ・雑音・縁の大きさを悪くしていくと壊れる所。縁の半径が 6 px では分割できず推定しない(fail-closed)。")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    t0, c0 = time.time(), time.process_time()
    out = numpy_part()
    print("  (既定の門 %.1f s、CPU %.1f s)" % (time.time() - t0, time.process_time() - c0))
    if FULL:
        t1, c1 = time.time(), time.process_time()
        out = full_part(out)
        if "models" in out:
            try:
                out["rest_mj"] = [(g, float(D.diabolo_mujoco_simulate(P, _hang(D._mo_fixed(0, g)), [0, 0, 0], {"kind": "fixed", "gap": g}, 0.5)["tension"][-1]))
                                  for g in (0.6, 0.9, 1.1, 1.3)]
            except ImportError:
                pass
        print("  (--full の門 %.1f s、CPU %.1f s)" % (time.time() - t1, time.process_time() - c1))
    else:
        skip("門 19〜25(軸 42 姿勢・壊れる場所・描画した回転・追跡・MuJoCo)", "--full のときだけ")
    if figs.enabled():
        t2, c2 = time.time(), time.process_time()
        figures(out)
        print("  (図 %.1f s、CPU %.1f s)" % (time.time() - t2, time.process_time() - c2))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
