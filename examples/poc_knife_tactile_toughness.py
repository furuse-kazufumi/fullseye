# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""包丁を指先の視触覚だけで持って切る —— 手首の力センサなしに食材の靱性 R と刃の当たり位置を読み、持てる柄の長さの限界を出す(2026-10-06)。

:mod:`cutting`(食材の切断を画像で測る)× :mod:`pegtactile`(2 本指の弾性膜で接触レンチを読む)の連鎖。新モジュール cuttouch(3 op)。
包丁の背を 2 枚のパッドで挟み、膜の像だけから押し V・引き H・モーメント M_x を復元して、当たり位置 Ly = (M_x + Lz·H)/V・
slice/push 比 ξ̂ = H/V・靱性 R を出す。途中で見つけたこと: :func:`pegtactile.pad_tactile_read` はねじりを無滑りの関係で読むので、
実際の接触(縁から必ず滑る)では M を過大に読む(全滑りまでの比 0.5 で +33 %)。部分滑りのねじりを数値で解いて直した。

何が外から来るか:
  * **閉形式**: Reissner–Sagoci の無滑りのねじれ角 β = 3M/(16Ga³) と、全滑りのトルク (3π/16)μPa —— 部分滑りの数値解の両端。
  * **MuJoCo**(:func:`cutting.cutting_mujoco_wrist`): 柔らかい手首で刃を押し下げた時の押し V の時系列・刃の高さ・靱性の設定値。
    ★V は MuJoCo の関節の摩擦損失に書いた R·w_eff·g(ξ) そのもので、切断の力の法則は外から来ていない。引き H は MuJoCo に無く
    H = ξV(Atkins)で作る。当たり位置の真値は場面の幾何(刃先が食材の上面より下にある区間の中点)。
  * **独立な読み手**: 膜の像を読むのは :mod:`pegtactile` の既存の読み手(このモジュールのコードではない)。

★合成と読みが同じ模型になる弱点: 膜の像の合成(部分滑りのねじり)と読みの補正は同じ数値解を使う。数値解そのものは両端の閉形式で、
読み手の偏りの大きさは既存の読み手の出力で確かめるが、「本物のゲルが Hertz の半空間の部分滑りどおりに振る舞うか」はここでは
確かめられない(有限厚のゲルの有限要素の比較が要る、:mod:`tacslip` の範囲)。せん断とねじりは重ね合わせ(連成は解いていない)。

門(既定 13 本、mujoco が無ければ MuJoCo の門は合成の切断 1 回分で代える): 部分滑りの両端、解像度、固着円の剛体回転、既存の読み手の偏りと
補正、静力学の往復、MuJoCo の連鎖(R・ξ・当たり位置・V)、無荷重と読めないコマ、持てる柄の長さの限界、数値が空でない、綴り壊し、入口、所要。
既定は CI の所要に合わせて絞る(CI は手元の約 9 倍遅い): MuJoCo の 4 コマ(入り始めの最初と最後 + 平坦 2、図を書く実行は 14 コマ)、解像度 64 vs 32 環、
既存の読み手の偏りを比 0.5 / 0.85、当たり位置を 3 点(図を書く実行は 9 点)。--full: MuJoCo の全コマ、解像度の比較を 64 vs 96 環で、偏りを比 5 通り、当たり位置を 17 点。切っている幅 w_eff は MuJoCo の刃の高さから
(画像の追跡は :mod:`cutting` の PoC の門 19 が担当、ここでは使わない)。
図(FULLSEYE_FIGURE_DIR): 持てる柄の長さの限界(把持力 3 通り)、当たり位置の読み(無滑りの読み vs 補正)、MuJoCo の切断の時系列、
パッドの像、固着円が縮むねじれの半径分布、切断の GIF(MuJoCo の描画 + 2 枚のパッドの像)。
Run: py -3.11 examples/poc_knife_tactile_toughness.py [--full]
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cutting as C  # noqa: E402
import cuttouch as CT  # noqa: E402
import examplefig as figs  # noqa: E402
import pegtactile as PT  # noqa: E402
import tacsim as T  # noqa: E402
import tacslip as S  # noqa: E402
import tactorque as TQ  # noqa: E402

FULL = "--full" in sys.argv
R_TRUE = 60.0                  # J/m²(柔らかい食材の桁。材料値ではない —— パッドの把持力 4 N で滑らない大きさに選んだ)
THETA = 4.0                    # 刃先の傾き [deg]
LZ0 = 18e-3                    # 把持点の真下の刃先までの高さ [m]
XG_OFFSET = -3.0               # 把持点の x = 食材の中央 + これ [mm]
KNIFE_MASS = 0.15              # kg(cutting_mujoco_wrist の既定)
COM_Y = 1.5e-3                 # 包丁の重心は把持点から柄の向きに 1.5 mm(釣り合いの点の近くを持つ。6 mm 離すと重さだけでねじりの比 0.75)
NOISE = 0.003                  # 膜の像の画素雑音
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    except Exception as exc:  # noqa: BLE001  別の例外は fail-closed ではない
        print("    (wrong exception %s: %s)" % (type(exc).__name__, exc))
        return False
    return False


def pad_frame(P, q, tau, pad, ctx, noise=NOISE, seed=0):
    """パッド 1 枚の像: Hertz の陰影 + Mindlin のせん断 + **部分滑りの**ねじり(cuttouch.torsion_partial_slip の場)。
    :func:`pegtactile.pad_tactile_frame` と同じ描き方で、ねじりの場だけ無滑りから部分滑りに替えたもの。"""
    disp = PT.pad_marker_displacement(P, q, pad, ctx, torsion=0.0)
    u = disp["u_m"]
    if tau != 0.0:
        u = u + CT.torsion_partial_slip(tau, P, pad, ctx=ctx, field=True)["u_markers"]
    ind = T.membrane_indent_sphere(disp["hz"], pad["n"], pad["fov"])
    sh = T.membrane_render_rgb(ind["normals"], ctx["lights"], ambient=PT._AMB)
    pts = ctx["pts_flat"] + u / pad["pitch"]
    rgb = S.membrane_render_markers(sh, pts, pad["marker_r_px"], pad["dark"])
    rng = np.random.default_rng(int(seed))
    return {"rgb": rgb + rng.normal(0.0, noise, rgb.shape), "shading": sh + rng.normal(0.0, noise, sh.shape)}


def food_wrench_world(V, H, Ly, Lz):
    """食材 → 刃のレンチ(グリッパ系、把持点まわり): F = (0, −H, V)、作用点 (0, Ly, −Lz)。"""
    F = np.array([0.0, -H, V])
    return F, np.cross(np.array([0.0, Ly, -Lz]), F)


def knife_on_pads(V, H, Ly, Lz, com_y, mass=KNIFE_MASS):
    """パッド → 包丁のレンチ(準静的): −(食材の分 + 重力の分)。重心は把持点から (0, com_y, −LZ0/2)。"""
    Ff, Mf = food_wrench_world(V, H, Ly, Lz)
    Fg = np.array([0.0, 0.0, -9.81 * mass])
    Mg = np.cross(np.array([0.0, com_y, -LZ0 / 2]), Fg)
    return -(Ff + Fg), -(Mf + Mg)


def read_pads(F_pad, M_pad, pad, ctx, seed):
    loads = PT.peg_wrench_to_pad_loads(F_pad, M_pad, pad)
    rd = {}
    for k, s in enumerate(("R", "L")):
        L = loads[s]
        fr = pad_frame(L["P"], L["q"], L["torsion"], pad, ctx, seed=seed * 2 + k)
        rd[s] = PT.pad_tactile_read(fr, pad, ctx)
        rd[s]["_frame"] = fr
    return rd, loads


# ======================================================================================================================
def solver_part(pad, ctx) -> dict:
    print("== 部分滑りのねじり(数値解の両端・解像度・固着円の剛体回転・既存の読み手の偏り)")
    out = {}
    t0 = time.time()
    tab = CT._torsion_table(64)
    bias0 = tab["beta"][0] / (3 * tab["M"][0] / 16)
    full_err = tab["M_full"] / (math.pi ** 2 / 8) - 1
    mono = bool(np.all(np.diff(tab["c"]) < 0) and np.all(np.diff(tab["ratio"]) > 0))
    _NUM["solver"] = {"bias0": bias0, "full_err": full_err}
    gate("門 1 部分滑りの数値解の両端 = 閉形式: c → a で β/β_無滑り %.4f(Reissner–Sagoci 3M/16Ga³)、c → 0 で全滑りのトルク %+.2f %%((3π/16)μPa)、c/a と比が単調"
         % (bias0, 100 * full_err), abs(bias0 - 1) < 0.005 and abs(full_err) < 0.003 and mono)
    nb = 96 if FULL else 32          # 既定 = CI の PoC の門の経路(CI は手元の約 9 倍遅い)。--full は 96 環
    tb = CT._torsion_table(nb)
    conv = []
    for m in (0.3, 0.5, 0.8):
        a, b = CT._interp_ratio(tab, m), CT._interp_ratio(tb, m)
        conv.append((abs(a[0] - b[0]), abs(a[1] / b[1] - 1)))
    dc, db = max(c[0] for c in conv), max(c[1] for c in conv)
    gate("門 2 解像度(環 64 本 vs %d 本、比 0.3 / 0.5 / 0.8): c/a の差 ≤ %.4f、読みの倍率の差 ≤ %.2f %%" % (nb, dc, 100 * db), dc < 0.01 and db < 0.01)
    hz = T.hertz_sphere(pad["grip"], pad["R"], pad["Es"])
    Mf = CT._FULL_SLIP_COEF * pad["mu"] * pad["grip"] * hz["a"]
    rig = []
    for m in (0.3, 0.6, 0.8):
        r = CT.torsion_partial_slip(m * Mf, pad["grip"], pad, ctx=ctx, field=True)
        X, Y = ctx["X"], ctx["Y"]
        msk = np.hypot(X, Y) < 0.9 * r["c_over_a"] * r["a"]
        fit = TQ.rigid_rotation_fit(np.column_stack([X[msk], Y[msk]]), np.column_stack([r["ux"][msk], r["uy"][msk]]))
        rig.append(fit["omega"] / r["beta"])
    gate("門 3 パッドの格子で畳んだ部分滑りの場は固着円の中で剛体回転、ω/β = %s(表の β と別の格子・別の単位で)"
         % ", ".join("%.4f" % v for v in rig), max(abs(v - 1) for v in rig) < 0.005)
    rows = []
    for k, m in enumerate((0.1, 0.3, 0.5, 0.7, 0.85) if FULL else (0.5, 0.85)):
        tau = m * Mf
        rd = PT.pad_tactile_read(pad_frame(pad["grip"], [0.3, 0.2], tau, pad, ctx, seed=100 + k), pad, ctx)
        tc, c_a, ok, _ = CT._true_torsion_from_stick_read(rd["torsion"], rd["P"], pad, 64)
        pr = CT.torsion_partial_slip(tau, pad["grip"], pad)
        rows.append((m, rd["torsion"] / tau, pr["read_bias"], tc / tau, c_a, ok))
    out["bias_rows"] = rows
    _NUM["bias_rows"] = rows
    good = [r for r in rows if r[5]]
    e_pred = max(abs(r[1] / r[2] - 1) for r in rows)
    e_corr = max(abs(r[3] - 1) for r in good)
    flagged = [r[0] for r in rows if not r[5]]
    gate("門 4 既存の読み手(pegtactile、無滑りの関係)は部分滑りの像で M を過大に読む: 比 %s で ×%s(予測との差 ≤ %.1f %%)。"
         "補正後 ≤ %.1f %%、読めない(c < 0.6a)= 比 %s"
         % (" / ".join("%g" % r[0] for r in rows), " / ".join("%.3f" % r[1] for r in rows), 100 * e_pred, 100 * e_corr, flagged),
         e_pred < 0.02 and e_corr < 0.02 and flagged == [0.85] and [r[1] for r in rows if r[0] == 0.5][0] > 1.25)
    print("    (%.1f s)" % (time.time() - t0))
    return out


def statics_part(pad) -> None:
    print("== 静力学の往復(像なし、閉形式の読み)")
    errs = []
    s = math.tan(math.radians(THETA))
    for V, H, Ly in ((1.0, 0.07, 3e-3), (2.0, 0.14, -6e-3), (0.5, 0.2, 10e-3)):
        Lz = LZ0 - Ly * s
        Fp, Mp = knife_on_pads(V, H, Ly, Lz, 6e-3)
        Ft, Mt = knife_on_pads(0.0, 0.0, 0.0, LZ0, 6e-3)
        L = PT.peg_wrench_to_pad_loads(Fp, Mp, pad)
        Lt = PT.peg_wrench_to_pad_loads(Ft, Mt, pad)
        mk = lambda LL, k: {"P": LL[k]["P"], "q": LL[k]["q"], "torsion": LL[k]["torsion"]}  # noqa: E731
        r = CT.knife_load_from_pads(mk(L, "R"), mk(L, "L"), pad, LZ0, edge_slope=s, torsion_model="no_slip", tare=(mk(Lt, "R"), mk(Lt, "L")))
        errs.append(max(abs(r["V"] - V), abs(r["H"] - H), abs(r["Ly"] - Ly), abs(r["xi"] - H / V)))
    gate("門 5 静力学の往復(食材 + 包丁の重さ → 2 パッド → 風袋を引いて V・H・Ly・ξ、刃の傾き込み): 最大の差 %.1e" % max(errs), max(errs) < 1e-12)


def _episode():
    """MuJoCo の切断 1 回分(mujoco が無ければ閉形式の切断 1 回分)と、各コマの幾何の真値。"""
    sc = C.cutting_scene("face")
    heel_x = 18.0
    try:
        run = C.cutting_mujoco_wrist(sc, theta_deg=THETA, R=R_TRUE, render=False, dt_frame=0.05,
                                     n_frames=100, heel_x=heel_x)
        src = "mujoco"
        t, ez, F = run["t"], run["edge_z_true"], run["F_constraint"]
    except ImportError:
        ep = C.cutting_episode_synth(R=R_TRUE, theta_deg=THETA, vx=0.0, vz=6.0, dt=0.05, n_frames=100)
        src = "synthetic"
        t, ez, F = ep["t"], ep["edge_z_c"], ep["F"]
    tt = math.tan(math.radians(THETA))
    w = np.array([C.food_cut_width(THETA, float(e), sc["food_w"], sc["food_h"]) for e in ez])
    x_mid = sc["food_xc"] - sc["food_w"] / 2 + w / 2              # 刃先が上面より下の区間の中点(θ > 0 は左から切れる)
    xg = sc["food_xc"] + XG_OFFSET
    Ly = (x_mid - xg) * 1e-3
    com_y = COM_Y
    return {"src": src, "t": np.asarray(t), "ez": np.asarray(ez), "V": np.asarray(F), "w": w, "Ly": Ly, "Lz": LZ0 - Ly * tt, "xi": tt,
            "com_y": com_y, "scene": sc, "heel_x": heel_x, "xg": xg}


def mujoco_part(pad, ctx) -> dict:
    print("== MuJoCo の切断 → 2 枚のパッドの像 → V・H・当たり位置・靱性(手首の力センサなし)")
    t0 = time.time()
    ep = _episode()
    s = ep["xi"]
    idx_cut = [i for i in range(len(ep["t"])) if ep["w"][i] > 0.5]
    entry = [i for i in idx_cut if ep["w"][i] < ep["scene"]["food_w"] - 1e-6]
    plateau = [i for i in idx_cut if i not in entry]
    # 既定(図なし = CI の経路)は入り始めの最初と最後 + 平坦 2 コマ。図を書く実行は入り始め全部 + 平坦 5 コマ(時系列と GIF のため、
    # 門は同じ閾値で通る)。--full は全コマ
    if FULL:
        pick = entry + plateau
    elif figs.enabled():
        pick = entry + plateau[:: max(1, len(plateau) // 5)]
    else:
        pick = [entry[0]] + entry[-1:] + plateau[-2:]
    air = [i for i in range(len(ep["t"])) if ep["w"][i] == 0.0][0]
    Ft, Mt = knife_on_pads(0.0, 0.0, 0.0, LZ0, ep["com_y"])
    rd_air, _ = read_pads(Ft, Mt, pad, ctx, seed=900)
    tare = (rd_air["R"], rd_air["L"])
    air_ok = _raises(CT.knife_load_from_pads, rd_air["R"], rd_air["L"], pad, LZ0, edge_slope=s, tare=tare)
    rows, loads, loads_ns, frames = [], [], [], []
    for i in pick:
        V, H, Ly, Lz = float(ep["V"][i]), float(ep["V"][i]) * s, float(ep["Ly"][i]), float(ep["Lz"][i])
        Fp, Mp = knife_on_pads(V, H, Ly, Lz, ep["com_y"])
        rd, ld = read_pads(Fp, Mp, pad, ctx, seed=i)
        r = CT.knife_load_from_pads(rd["R"], rd["L"], pad, LZ0, edge_slope=s, tare=tare)
        rn = CT.knife_load_from_pads(rd["R"], rd["L"], pad, LZ0, edge_slope=s, tare=tare, torsion_model="no_slip")
        loads.append(r)
        loads_ns.append(rn)
        frames.append((i, rd["R"]["_frame"]["rgb"], rd["L"]["_frame"]["rgb"]))
        rows.append((ep["t"][i], ep["w"][i], V, r["V"], Ly, r["Ly"], rn["Ly"], r["torsion_ratio"], r["readable"], ld["R"]["torsion_ratio"]))
    rows = np.array(rows, dtype=float)
    w_use = ep["w"][pick]
    tf = CT.toughness_from_pads(loads, w_use)
    tf_ns = CT.toughness_from_pads(loads_ns, w_use)
    rd_ok = rows[:, 8] > 0.5
    ly_err = np.abs(rows[rd_ok, 5] - rows[rd_ok, 4])
    ly_err_ns = np.abs(rows[rd_ok, 6] - rows[rd_ok, 4])
    v_rel = float(np.sqrt(np.mean(((rows[:, 3] - rows[:, 2]) / rows[:, 2]) ** 2)))
    out = {"ep": ep, "rows": rows, "loads": loads, "loads_ns": loads_ns, "frames": frames, "tf": tf, "pick": pick}
    _NUM["mujoco"] = {"src": ep["src"], "n": len(pick), "R": tf["R"], "R_ns": tf_ns["R"], "xi": tf["xi_tactile"], "ly_max_mm": 1e3 * ly_err.max(),
                      "ly_ns_max_mm": 1e3 * ly_err_ns.max(), "v_rel": v_rel, "max_ratio": float(rows[:, 7].max())}
    gate("門 6 %s の切断(%d コマ、入り始め %d)→ パッドの像だけで靱性 R̂ = %.2f J/m²(設定 %.0f、%+.2f %%)、ξ̂ = H/V = %.4f(tan θ = %.4f、%+.1f %%)、"
         "V の rms %.2f %%" % (ep["src"], len(pick), len(entry), tf["R"], R_TRUE, 100 * (tf["R"] / R_TRUE - 1), tf["xi_tactile"], s,
                              100 * (tf["xi_tactile"] / s - 1), 100 * v_rel),
         abs(tf["R"] / R_TRUE - 1) < 0.02 and abs(tf["xi_tactile"] / s - 1) < 0.05 and v_rel < 0.02)
    k_w = int(np.argmax(ly_err))
    gate("門 7 刃の当たり位置 Ly(真値 %.1f〜%.1f mm、入り始めで動く): 補正あり 中央値 %.2f mm・最大 %.2f mm(V = %.2f N のコマ、誤差 ∝ δM_x/V)"
         " / 無滑りの読みのまま 最大 %.2f mm(ねじりの比 最大 %.2f)"
         % (1e3 * rows[:, 4].min(), 1e3 * rows[:, 4].max(), 1e3 * np.median(ly_err), 1e3 * ly_err.max(), rows[rd_ok][k_w, 2],
            1e3 * ly_err_ns.max(), rows[:, 7].max()),
         np.median(ly_err) < 0.15e-3 and ly_err.max() < 0.75e-3 and ly_err_ns.max() > 5 * ly_err.max() and rd_ok.all())
    gate("門 8 空中のコマ(風袋を引くと V = 0)は Ly を出さず ValueError(fail-closed)", air_ok)
    print("    (%.1f s、R の無滑りの読み %.2f)" % (time.time() - t0, tf_ns["R"]))
    return out


def limit_part(pad, ctx) -> dict:
    print("== 持てる柄の長さの限界(いまの V・H のまま当たり位置を遠ざける)")
    t0 = time.time()
    V, s = 2.03, math.tan(math.radians(THETA))
    H = V * s
    grips = (4.0, 8.0, 16.0)
    curves = {}
    for g in grips:
        a0 = T.hertz_sphere(g, 20e-3, T.combined_modulus(3e6, 0.48))["a"]
        pd = PT.pad_params(grip=g, fov=max(16e-3, 6.0 * a0 * 1.5 ** (1 / 3)), n=256 if g < 10 else 320)
        Ly = np.linspace(-25e-3, 25e-3, 201)
        ratio = []
        for y in Ly:
            Lz = LZ0 - y * s
            Mx = y * V - Lz * H
            ratio.append(abs(Mx / 2) / (CT._FULL_SLIP_COEF * pd["mu"] * pd["grip"] * T.hertz_sphere(pd["grip"], pd["R"], pd["Es"])["a"]))
        curves[g] = (Ly, np.array(ratio), pd)
    # 把持力 4 N で像から: 当たり位置を動かし、無滑りの読みと補正の Ly
    meas = []
    if FULL:
        ly_list = np.arange(-6.0, 10.01, 1.0) * 1e-3
    elif figs.enabled():                  # 図を書く実行は 9 点(図 2 の読みの線のため)
        ly_list = np.array([-5.0, -3.0, -1.5, 0.0, 2.0, 4.0, 5.5, 7.0, 9.0]) * 1e-3
    else:                                  # 既定 = CI の経路: 読めない 1 点・読める 1 点・全滑り 1 点
        ly_list = np.array([-5.0, 5.5, 9.0]) * 1e-3
    for k, y in enumerate(ly_list):
        Lz = LZ0 - y * s
        Fp, Mp = knife_on_pads(V, H, y, Lz, 0.0, mass=0.0)
        loads = PT.peg_wrench_to_pad_loads(Fp, Mp, pad)
        if max(loads["R"]["torsion_ratio"], loads["L"]["torsion_ratio"]) >= 0.999:
            meas.append((y, math.nan, math.nan, 1.0, False))
            continue
        rd, _ = read_pads(Fp, Mp, pad, ctx, seed=500 + k)
        r = CT.knife_load_from_pads(rd["R"], rd["L"], pad, LZ0, edge_slope=s)
        rn = CT.knife_load_from_pads(rd["R"], rd["L"], pad, LZ0, edge_slope=s, torsion_model="no_slip")
        meas.append((y, r["Ly"], rn["Ly"], r["torsion_ratio"], r["readable"]))
    # 静力学で V・H だけを持たせた読み(ねじり 0)に、限界の式を当てる: 閉形式 Ly = (±2 m M_full + Lz₀ H)/(V + sH)
    Mf = CT._FULL_SLIP_COEF * pad["mu"] * pad["grip"] * T.hertz_sphere(pad["grip"], pad["R"], pad["Es"])["a"]
    lo_hi = ((-2 * Mf + LZ0 * H) / (V + s * H), (2 * Mf + LZ0 * H) / (V + s * H))
    Fp, Mp = knife_on_pads(V, H, 0.0, LZ0, 0.0, mass=0.0)
    L0 = PT.peg_wrench_to_pad_loads(Fp, Mp, pad)
    mk = lambda LL, k: {"P": LL[k]["P"], "q": LL[k]["q"], "torsion": LL[k]["torsion"]}  # noqa: E731
    r0 = CT.knife_load_from_pads(mk(L0, "R"), mk(L0, "L"), pad, LZ0, edge_slope=s)
    err_lim = max(abs(r0["Ly_range_full_slip"][0] - lo_hi[0]), abs(r0["Ly_range_full_slip"][1] - lo_hi[1]))
    rr = r0["Ly_range_readable"]
    good = [m for m in meas if m[4]]
    bad = [m for m in meas if not m[4]]
    inside_ok = all(rr[0] <= m[0] <= rr[1] for m in good) and all(not (rr[0] < m[0] < rr[1]) for m in bad)
    e_c = max(abs(m[1] - m[0]) for m in good)
    _NUM["limit"] = {"full": lo_hi, "readable": rr, "e_c_mm": 1e3 * e_c, "n_bad": len(bad), "ratio_read": r0["ratio_at_read_limit"],
                     "grips": {g: (1e3 * CT.knife_load_from_pads(mk(PT.peg_wrench_to_pad_loads(Fp, Mp, curves[g][2]), "R"),
                                                                 mk(PT.peg_wrench_to_pad_loads(Fp, Mp, curves[g][2]), "L"), curves[g][2], LZ0,
                                                                 edge_slope=s)["Ly_range_readable"][1]) for g in grips}}
    gate("門 9 持てる柄の長さの限界(V %.2f N、把持力 4 N): 全滑り Ly ∈ [%.2f, %.2f] mm(閉形式との差 %.1e)、読める範囲 [%.2f, %.2f] mm"
         "(比 %.3f で c = 0.6a)。像で: 読める %d 点は補正後 ≤ %.2f mm、範囲の外 %d 点は readable = False(黙って数を出さない)"
         % (V, 1e3 * lo_hi[0], 1e3 * lo_hi[1], err_lim, 1e3 * rr[0], 1e3 * rr[1], r0["ratio_at_read_limit"], len(good), 1e3 * e_c, len(bad)),
         err_lim < 1e-12 and inside_ok and e_c < 0.5e-3 and len(bad) >= 1)
    print("    把持力ごとの読める上限 Ly: %s mm  (%.1f s)" % (", ".join("%g N → %.1f" % (g, v) for g, v in _NUM["limit"]["grips"].items()),
                                                   time.time() - t0))
    return {"curves": curves, "meas": meas, "lim": lo_hi, "read": rr, "m_read": r0["ratio_at_read_limit"]}


def misc_part(pad, ctx, out) -> None:
    print("== 数値が空でない・綴り壊し・入口")
    rows = out["mj"]["rows"]
    fin = bool(np.all(np.isfinite(rows[:, :8])))
    gate("門 10 数値が空・定数・inf でない: 全コマ有限、V̂ の幅 %.3f N、Lŷ の幅 %.2f mm、ねじりの比の幅 %.3f"
         % (np.ptp(rows[:, 3]), 1e3 * np.ptp(rows[:, 5]), np.ptp(rows[:, 7])),
         fin and np.ptp(rows[:, 3]) > 0.5 and np.ptp(rows[:, 5]) > 3e-3 and np.ptp(rows[:, 7]) > 0.1)
    good = {"P": 4.0, "q": [0.1, 0.0], "torsion": 0.0}
    checks = [
        _raises(CT.torsion_partial_slip, 1e-3, 0.0, pad),
        _raises(CT.torsion_partial_slip, float("nan"), 4.0, pad),
        _raises(CT.torsion_partial_slip, 1e-3, 4.0, pad, na=8),
        _raises(CT.torsion_partial_slip, 1.0, 4.0, pad, ctx=ctx, field=True),           # 全滑りの場は作らない
        _raises(CT.knife_load_from_pads, good, {"P": 4.0}, pad, LZ0),
        _raises(CT.knife_load_from_pads, good, good, pad, LZ0, torsion_model="noslip"),
        _raises(CT.knife_load_from_pads, good, good, pad, float("inf")),
        _raises(CT.knife_load_from_pads, good, {"P": -1.0, "q": [0, 0], "torsion": 0.0}, pad, LZ0),
        _raises(CT.toughness_from_pads, [], []),
        _raises(CT.toughness_from_pads, out["mj"]["loads"][:2], [10.0, 10.0]),
        _raises(CT.toughness_from_pads, out["mj"]["loads"], [10.0]),
    ]
    sl = CT.torsion_partial_slip(1.0, 4.0, pad)
    gate("門 11 綴り壊し・測れない入力は ValueError(%d / %d)、全滑りは例外でなく印(slipping %s、readable %s)"
         % (sum(checks), len(checks), sl["slipping"], sl["readable"]), all(checks) and sl["slipping"] and not sl["readable"])
    docs_ok = all((getattr(CT, n).__doc__ or "").strip() and "](" not in getattr(CT, n).__doc__ for n in CT.__all__)
    gate("門 12 入口: __all__ の %d op が実在し docstring あり、Markdown のリンク記法なし" % len(CT.__all__), docs_ok and "](" not in CT.__doc__)


# ======================================================================================================================
def figures(out: dict) -> None:
    print("== 図")
    lim = out["lim"]
    ser, kinds, sty, cols = [], [], [], []
    for g, col in zip((4.0, 8.0, 16.0), ("wrong", "emphasis", "right")):
        Ly, ratio, _ = lim["curves"][g]
        ser.append(("grip %.0f N" % g, 1e3 * Ly, np.minimum(ratio, 1.6)))
        kinds.append("line")
        sty.append(None)
        cols.append(col)
    for yv, lab in ((1.0, "full slip"), (lim["m_read"], "stick zone = read core (c = 0.6a)")):
        ser.append((lab, [-25, 25], [yv, yv]))
        kinds.append("line")
        sty.append("dashed")
        cols.append("reference")
    mm = [m for m in lim["meas"] if np.isfinite(m[1])]
    ser.append(("measured from pad images (4 N)", [1e3 * m[0] for m in mm], [m[3] for m in mm]))
    kinds.append("scatter")
    sty.append(None)
    cols.append("neutral")
    figs.save_plot("handle_length_limit", ser, xlabel="blade contact from the grip, Ly [mm]", ylabel="torsion / full-slip torque, per pad",
                   title="How far from the fingers can the blade bite?", kinds=kinds, styles=sty, colors=cols, size=(760, 460), ylim=(0, 1.6),
                   caption="押し 2 N の切断で、刃の当たり位置が指から離れるほどパッドのねじりが増え、固着円が縮む。把持力 4 N では "
                           "%.1f〜%.1f mm の外で読めなくなり、%.1f〜%.1f mm の外で全滑り。把持力を 4 倍にすると範囲は約 %.1f 倍"
                           "(全滑りのトルク ∝ P a ∝ P^{4/3})。" % (1e3 * lim["read"][0], 1e3 * lim["read"][1], 1e3 * lim["lim"][0],
                                                              1e3 * lim["lim"][1], 4 ** (4 / 3)))
    good = [m for m in lim["meas"] if np.isfinite(m[1])]
    tl = np.array([m[0] for m in good])
    figs.save_plot("contact_position_read", [
        ("partial-slip corrected", 1e3 * tl, [1e3 * m[1] for m in good]),
        ("no-slip reading (pegtactile as is)", 1e3 * tl, [1e3 * m[2] for m in good]),
        ("truth", [-6, 10], [-6, 10]),
        ("readable limit", [1e3 * lim["read"][1]] * 2, [-6, 10]),
        ("", [1e3 * lim["read"][0]] * 2, [-6, 10])],
        xlabel="true contact position Ly [mm]", ylabel="read Ly [mm]", title="Where the blade bites, read through the pads",
        kinds=["scatter", "scatter", "line", "line", "line"], styles=[None, None, "dashed", "dotted", "dotted"],
        colors=["right", "wrong", "reference", "neutral", "neutral"], size=(720, 460),
        caption="無滑りの関係でねじりを読むと、指から離れるほど当たり位置を遠くに読む(部分滑りでねじれ角が大きい)。部分滑りの数値解で直すと真値の線に戻る。")
    mj = out["mj"]
    rows = mj["rows"]
    figs.save_plot("mujoco_cut_timeline", [
        ("V from MuJoCo [N]", rows[:, 0], rows[:, 2]), ("V read from pads [N]", rows[:, 0], rows[:, 3]),
        ("Ly truth [cm]", rows[:, 0], 100 * rows[:, 4]), ("Ly read, corrected [cm]", rows[:, 0], 100 * rows[:, 5]),
        ("Ly read, no-slip [cm]", rows[:, 0], 100 * rows[:, 6])],
        xlabel="time [s]", ylabel="N  /  cm", title="One cut in MuJoCo, read only through two fingertip pads",
        kinds=["line", "scatter", "line", "scatter", "scatter"], styles=["dashed", None, "dashed", None, None],
        colors=["reference", "right", "reference", "right", "wrong"], size=(760, 460),
        caption="刃が食材の左端から切れ始め、切っている幅の中点(当たり位置)が右へ動く。パッドの像だけで押し V と当たり位置を追う。R̂ = %.2f J/m²(設定 %.0f)。"
                % (mj["tf"]["R"], R_TRUE))
    fr = mj["frames"]
    k_hi = int(np.argmax(rows[:, 7]))
    k_lo = int(np.argmin(rows[:, 7]))
    figs.save_grid("pad_images", [fr[k_lo][1], fr[k_lo][2], fr[k_hi][1], fr[k_hi][2]],
                   captions=["pad R, torsion ratio %.2f" % rows[k_lo, 7], "pad L", "pad R, torsion ratio %.2f" % rows[k_hi, 7], "pad L"],
                   title="Fingertip membrane images", ncols=2)
    _stick_profile(out)
    _gif(out)


def _stick_profile(out: dict) -> None:
    """周方向の変位 u_θ / r(ねじれ)の半径分布: 固着円の中は平ら(剛体回転 β)、比が上がると平らな所が縮む。"""
    pad, ctx = out["pad"], out["ctx"]
    hz = T.hertz_sphere(pad["grip"], pad["R"], pad["Es"])
    Mf = CT._FULL_SLIP_COEF * pad["mu"] * pad["grip"] * hz["a"]
    X, Y = ctx["X"], ctx["Y"]
    R = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    edges = np.linspace(0.02, 1.4, 70) * hz["a"]
    ser, cols, kinds, sty = [], [], [], []
    for m, col in zip((0.2, 0.5, 0.8, 0.95), ("right", "neutral", "emphasis", "wrong")):
        r = CT.torsion_partial_slip(m * Mf, pad["grip"], pad, ctx=ctx, field=True)
        uth = -r["ux"] * np.sin(th) + r["uy"] * np.cos(th)
        prof = [np.mean(uth[(R >= e0) & (R < e1)] / R[(R >= e0) & (R < e1)]) for e0, e1 in zip(edges[:-1], edges[1:])]
        rc = 0.5 * (edges[:-1] + edges[1:]) / hz["a"]
        ser.append(("M / M_full = %.2f, c = %.2f a" % (m, r["c_over_a"]), rc, np.array(prof) / r["beta_no_slip"]))
        cols.append(col)
        kinds.append("line")
        sty.append(None)
    ser.append(("read core r < 0.6 a", [0.6, 0.6], [0, 3.5]))
    cols.append("reference")
    kinds.append("line")
    sty.append("dashed")
    figs.save_plot("stick_zone_shrinks", ser, xlabel="radius / contact radius a", ylabel="twist u_theta / r, relative to no-slip",
                   title="The stick zone shrinks as the blade bites further away", kinds=kinds, styles=sty, colors=cols, size=(760, 440),
                   caption="パッドのねじれ(周方向の変位 ÷ 半径)。固着円の中は平ら(剛体回転)で、その高さが無滑りの値より大きい = 無滑りの関係で読むと"
                           "トルクを過大に読む。平らな所が読みの核 0.6a より狭くなると読めない。")


def _gif(out: dict) -> None:
    """MuJoCo の描画 + 2 枚のパッドの像(等倍)を並べた GIF。描画は図のときだけ(MuJoCo が無ければ作らない)。"""
    ep = out["mj"]["ep"]
    if ep["src"] != "mujoco":
        print("  GIF は MuJoCo があるときだけ")
        return
    run = C.cutting_mujoco_wrist(ep["scene"], theta_deg=THETA, R=R_TRUE, render=True, dt_frame=0.05, n_frames=100, heel_x=ep["heel_x"])
    frames = []
    pick = out["mj"]["pick"]
    for k, i in enumerate(pick):
        top = run["frames"][i]
        H0, W0 = top.shape[:2]
        canvas = np.ones((H0 + 256, W0, 3))
        canvas[:H0] = top
        _, pr, pl = out["mj"]["frames"][k]
        canvas[H0:H0 + 256, 120:376] = np.clip(pr, 0, 1)
        canvas[H0:H0 + 256, 424:680] = np.clip(pl, 0, 1)
        frames.append(canvas)
    figs.save_gif("cut_with_fingertip_pads", frames, fps=4.0,
                  caption="MuJoCo の柔らかい手首で刃を押し下げる(上)。下は包丁の背を挟む 2 枚のパッドの膜の像 —— この像だけで力と当たり位置を読む。")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    pad = PT.pad_params()
    ctx = PT.pad_context(pad)
    out = solver_part(pad, ctx)
    out["pad"], out["ctx"] = pad, ctx
    statics_part(pad)
    out["mj"] = mujoco_part(pad, ctx)
    out["lim"] = limit_part(pad, ctx)
    misc_part(pad, ctx, out)
    el = time.time() - t_all
    budget = 120.0 if FULL else 30.0
    gate("門 13 所要 %.1f s ≤ %.0f s" % (el, budget), el <= budget)
    if figs.enabled():
        figures(out)
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
