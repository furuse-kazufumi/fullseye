# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""食材の切断を画像で測る —— 刃の追跡・切片の厚み・切断面の粗さ・手首のたわみからの切断力、真値は閉形式と MuJoCo(2026-10-05)。

物理シミュ × Fullseye 系列。題材はロボットの食材スライスの研究(arXiv:2404.02569、ICRA 2024)。学習はせず規則だけで、
「画像 → 刃の高さ → 柔らかい手首のたわみ → 力 → 靱性 R」の鎖を閉じる。外から来るもの:
  * **閉形式の切断力学**: Atkins 2016(Interface Focus 6:20160019、式 1.1〜1.4、摩擦なしの slice/push)と Williams & Patel 2016
    (同 6:20150108、式 2.6、くさび + Coulomb 摩擦)。本文の数(H/Rw の最大 0.5 は ξ = 1、ξ = tan i、μ = 0.2 で θo = 79°・最小 1.24)を門に。
  * **物理エンジン(--full)**: MuJoCo の正射影カメラで描いた刃を同じ追跡器で追い、手首の拘束力と比べる。柔体(flexcomp)は剛性の桁が
    合うが破断しない(刃は潜り込む)ことも門で固定する。
  * **有限要素の力曲線(--full、任意、非商用)**: arXiv:2105.12244 が公開した FEM の刃の力(CC BY-NC 4.0)。置き場所は環境変数
    ``FULLSEYE_CUT_FORCE_DATA``(``forces/*.csv`` を含むディレクトリ)。無ければ skip。数値の比較だけで図には載せない。

門(既定 14 本、numpy + scipy、解像度を落とした 4 px/mm と 10 px/mm): 閉形式と本文の数、描画器の面積、刃の角度・刃先・先端、
切り込み深さ、切片の厚み 0.1〜5 mm、刃が端面を突き抜ける形は測らない、切断面の粗さ(床と sinc)、画像 → 力 → R、両辺に同じ模型
(自己申告)、綴り壊し、測るものが無い、壊れる場所(普通の条件)、被験者と一致、入口と MJCF。
--full(7 本): 元の解像度(8 px/mm・20 px/mm)の精度と壊れる場所の全掃引(ぼけ 4 px は窓を広げて偏らず、8 px は拒否)、MuJoCo の柔体の
圧縮と刃の潜り込み、MuJoCo の描画 → 刃の追跡、手首の力 vs 拘束力(誤差 ≤ 減衰 c·v)、FEM の力曲線(任意)。
図(``FULLSEYE_FIGURE_DIR`` があるとき、元の解像度・等倍): 合成の切断の GIF(推定の刃先線・隠れた所は破線・真値・先端・力の曲線)、
刃先方向の像と両縁、40 枚の厚みの分布と散布、切断面の断面、壊れる場所、slice/push の閉形式、--full では MuJoCo の GIF と柔体の力。
正直に: 力の真値は外から来ていない(合成も当てはめも同じ Atkins の模型 = 配管の検査、門 9 で固定)。食材は変形しない、刃先は直線、
片刃を仮定。靱性の実測値は引用しない。
Run: py -3.11 examples/poc_food_cutting_measure.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import math
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cutting as C  # noqa: E402
import examplefig as figs  # noqa: E402

FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}

#: CI の既定は解像度を落とす(正面像 4 px/mm・400×240、刃先方向 10 px/mm・260×280)。--full と図は元の解像度。
SF = C.cutting_scene("face", 4.0)
SE = C.cutting_scene("edge", 10.0)
SF_FULL = C.cutting_scene("face")
SE_FULL = C.cutting_scene("edge")


_T = [time.process_time()]


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    t = time.process_time()
    print("  [%s] %s %s  (cpu %.2f s)" % ("ok" if ok else "NG", name, detail, t - _T[0]), flush=True)
    _T[0] = t


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def edge_z_at(track, x_mm, sc):
    """追跡した刃先の直線の、x_mm での高さ(mm)。"""
    f = track["line"]
    r = f["cy"] + (x_mm * sc["px_per_mm"] - f["cx"]) * f["dy"] / f["dx"]
    return (sc["board_row"] - r) / sc["px_per_mm"]


def _zband(se):
    return (6.0 + se["blade_hb"] + 0.3, se["food_top"] - 0.3)


# ======================================================================================================================
def blade_accuracy(sf, noise=0.01):
    errs, zerr, tip = [], [], []
    for th in (-9.0, -1.0, 0.37, 4.5, 10.0):
        img = C.cutting_face_render(sf, 18.0, 12.0, th, noise=noise, seed=int(th * 10) + 100)
        tr = C.knife_edge_track(img, sf["board_row"])
        errs.append(abs(tr["angle_deg"] - th))
        zerr.append(abs(edge_z_at(tr, sf["food_xc"], sf) - (12.0 + (sf["food_xc"] - 18.0) * math.tan(math.radians(th)))))
        if tr["tip_rc"] is not None:
            v = C._blade_polygon_xz(sf, 18.0, 12.0, th)
            r, c = C._face_xz_to_rc(sf, v[1, 0], v[1, 1])
            tip.append(math.hypot(tr["tip_rc"][0] - r, tr["tip_rc"][1] - c) / sf["px_per_mm"])
    assert len(errs) == 5
    return max(errs), 1000 * max(zerr), tip


def depth_accuracy(sf):
    errs = []
    for th, hz in ((0.0, 20.0), (3.0, 14.0), (-5.0, 8.0), (1.0, 3.0)):
        img = C.cutting_face_render(sf, 18.0, hz, th, noise=0.01, seed=7)
        tr = C.knife_edge_track(img, sf["board_row"])
        d = C.cut_depth_from_side(img, tr, sf["px_per_mm"], sf["board_row"])
        errs.append(abs(d["depth_mm"] - (sf["food_h"] - (hz + (sf["food_xc"] - 18.0) * math.tan(math.radians(th))))))
    assert len(errs) == 4
    return 1000 * max(errs)


def thickness_accuracy(se, cases):
    wm, wr, wl = 0.0, 0.0, 0.0
    assert len(cases) >= 3
    for h, lean in cases:
        img = C.cutting_edge_render(se, 6.0, 6.0 + h, lean, 6.0, noise=0.01, seed=3)
        r = C.slice_thickness_profile(img, se["px_per_mm"], se["board_row"], _zband(se))
        e = r["thickness_mm"] - (h + (se["food_top"] - r["z_mm"]) * math.tan(math.radians(lean)))
        wm = max(wm, abs(float(e.mean())))
        wr = max(wr, float(np.sqrt(np.mean(e ** 2))))
        wl = max(wl, abs(r["lean_deg"] - lean))
    return 1000 * wm, 1000 * wr, wl


def breakage(sf, se, conds, th=2.5, hz=12.0):
    """照明(gain・左右勾配)・ぼけ・雑音で角度・深さ・厚みの誤差を掃く。拒否(ValueError)は inf。"""
    ez = hz + (sf["food_xc"] - 18.0) * math.tan(math.radians(th))

    def face(**cam):
        try:
            img = C.cutting_face_render(sf, 18.0, hz, th, seed=11, **cam)
            tr = C.knife_edge_track(img, sf["board_row"])
            d = C.cut_depth_from_side(img, tr, sf["px_per_mm"], sf["board_row"])
            return abs(tr["angle_deg"] - th), abs(d["depth_mm"] - (sf["food_h"] - ez))
        except ValueError:
            return math.inf, math.inf

    def thick(**cam):
        try:
            img = C.cutting_edge_render(se, 6.0, 7.0, 0.0, 6.0, seed=5, **cam)
            return abs(C.slice_thickness_profile(img, se["px_per_mm"], se["board_row"], _zband(se))["mean_mm"] - 1.0)
        except ValueError:
            return math.inf
    out = {}
    for key, vals in conds:
        out[key] = [(v,) + face(**{key: v}) + (thick(**{key: v}),) for v in vals]
    for key, rows in out.items():
        print("      %-8s " % key + "  ".join("%g: ang %.3f dep %s thk %s" % (v, a, "%.0fum" % (1000 * d) if math.isfinite(d) else "refused",
                                                                         "%.0fum" % (1000 * t) if math.isfinite(t) else "refused")
                                              for v, a, d, t in rows))
    return out


def _rough_profile(A, lam, rr, seed=3):
    """端面 y(z) = 6 + 0.02 z + A sin(2πz/λ) + rr·(滑らかな乱数)の密な標本と、その真値の関数。"""
    from scipy.ndimage import gaussian_filter1d
    rng = np.random.default_rng(seed)
    zg = np.linspace(-1, 30, 31001)
    rnd = gaussian_filter1d(rng.standard_normal(zg.size), 300)
    rnd /= rnd.std()
    y = 6.0 + 0.02 * zg + A * np.sin(2 * np.pi * zg / lam) + rr * rnd
    return {"z_mm": zg, "y_mm": y}


def rough_case(se, A, lam, rr):
    import roughness
    prof = _rough_profile(A, lam, rr)
    img = C.cutting_edge_render(se, prof, 0.0, 0.0, 0.0, blade=False)
    r = C.cut_surface_roughness(img, se["px_per_mm"], se["board_row"], (2.0, 22.0))
    zs = r["z_mm"]
    tru = np.interp(zs, prof["z_mm"], prof["y_mm"])
    c = np.polyfit(zs, tru, 1)
    return r, roughness.profile_params((tru - np.polyval(c, zs)) * 1000, dx=r["dz_um"]), prof


def force_chain(sf, R=400.0, every=4, noise=0.01):
    theta = 4.0
    ep = C.cutting_episode_synth(R=R, theta_deg=theta, vx=4.0, vz=6.0, k_wrist=4.0, dt=0.12, n_frames=36, heel_x0=4.0, scene=sf)
    idx = np.arange(0, len(ep["t"]), every)
    assert idx.size >= 4
    zs, th_est, xt, zt, dep = [], [], [], [], None
    for i in idx:
        img = C.cutting_face_render(sf, ep["heel_x"][i], ep["heel_z"][i], theta, noise=noise, seed=int(i))
        tr = C.knife_edge_track(img, sf["board_row"])
        zs.append(edge_z_at(tr, sf["food_xc"], sf))
        th_est.append(tr["angle_deg"])
        tip = tr["tip_rc"]
        xt.append(np.nan if tip is None else tip[1] / sf["px_per_mm"])
        zt.append(np.nan if tip is None else (sf["board_row"] - tip[0]) / sf["px_per_mm"])
        if dep is None:
            dep = C.cut_depth_from_side(img, tr, sf["px_per_mm"], sf["board_row"])
    zs, xt, zt = np.array(zs), np.array(xt), np.array(zt)
    tt = math.tan(math.radians(theta))
    z_cmd_c = ep["heel_z_cmd"][idx] + (sf["food_xc"] - ep["heel_x"][idx]) * tt
    F_est = C.force_from_wrist_displacement(zs, z_cmd_c, 4.0)
    th_m = float(np.median(th_est))
    food_w = (dep["food_cols"][1] - dep["food_cols"][0] + 1) / sf["px_per_mm"]
    w_eff = np.array([C.food_cut_width(th_m, z, food_w, dep["top_z_mm"]) for z in zs])
    # ξ は刃が食材の全幅を切っている定常区間の先端の動きで(入り始めを混ぜると 0.63 vs 0.57 で R が 5 % ずれた、試作)
    full = (w_eff >= 0.98 * food_w) & np.isfinite(xt)
    xi_est = C.slice_push_from_track(th_m, xt[full], zt[full])
    fit = C.cut_force_fit(F_est, w_eff, xi_est)
    return {"ep": ep, "idx": idx, "R": fit["R"], "xi": xi_est, "xi_true": ep["xi"], "Ferr": float(np.abs(F_est - ep["F"][idx]).max()),
            "food_w": food_w, "n": int(idx.size), "n_full": int(full.sum())}


# ======================================================================================================================
def numpy_part() -> dict:
    print("== 1. numpy の門(解像度を落とした 4 px/mm・10 px/mm)")
    out = {}
    # ── 1. 閉形式と本文の数
    worst = 0.0
    for R in (50.0, 400.0, 1500.0):
        for w in (10.0, 34.0):
            for xi in (0.0, 0.3, 1.0, 3.0):
                f = C.cut_force_atkins(R, w, xi=xi)
                s = R * w * 1e-3
                worst = max(worst, abs(f["H"] - xi * f["V"]) / s, abs(math.hypot(f["V"], f["H"]) - f["F_res"]) / s)
    a = C.cut_force_atkins(400, 34, xi=0.7)["V"]
    lin = max(abs(C.cut_force_atkins(800, 34, xi=0.7)["V"] - 2 * a), abs(C.cut_force_atkins(400, 68, xi=0.7)["V"] - 2 * a)) / a
    xs = np.linspace(0.0, 4.0, 4001)
    hh = np.array([C.cut_force_atkins(1.0, 1000.0, xi=x)["H"] for x in xs])
    xi_pk, h_pk = float(xs[int(np.argmax(hh))]), float(hh.max())
    tan_err = max(abs(C.slice_push_ratio(i, 0.0, 5.0) - math.tan(math.radians(abs(i)))) for i in (5, 20, 45, 60))
    ths = np.linspace(20, 89.9, 6991)
    v = np.array([C.cut_force_atkins(1.0, 1000.0, wedge_deg=t, mu=0.2)["Fc_over_bGc"] for t in ths])
    th_o, vmin = float(ths[int(np.argmin(v))]), float(v.min())
    closed = 1.0 / (1.0 - math.sin(math.atan(0.2)))
    _NUM["closed_forms"] = {"identity": worst, "H_peak": h_pk, "xi_peak": xi_pk, "theta_o_deg": th_o, "wp_min": vmin}
    gate("門 1 閉形式: Atkins 2016 の H = ξV と合力(%.0e)、R・w の 1 次(%.0e)、本文の「H/Rw は ξ = 1 で最大 0.5」= %.4f @ ξ %.3f、"
         "「傾けた刃を縦に動かすと ξ = tan i」(%.0e)、Williams & Patel 2016 の μ = 0.2 で θo = %.2f°(本文 79°)・最小 %.4f(閉形式 1/(1 − sin β) = %.4f、"
         "本文 1.24)" % (worst, lin, h_pk, xi_pk, tan_err, th_o, vmin, closed),
         worst < 1e-12 and lin < 1e-12 and abs(xi_pk - 1) < 1e-3 and abs(h_pk - 0.5) < 1e-6 and tan_err < 1e-12
         and abs(th_o - 78.69) < 0.05 and abs(vmin - closed) < 1e-6 and abs(round(vmin, 2) - 1.24) < 1e-9)
    # ── 2. 描画器の面積
    worst = 0.0
    for th in (-7.3, 0.0, 2.2, 11.0):
        vv = C._blade_polygon_xz(SF, 15.0, 12.0, th)
        rr, cc = C._face_xz_to_rc(SF, vv[:, 0], vv[:, 1])
        cov = C._cov_polygon(SF["H"], SF["W"], np.stack([rr, cc], 1))
        area = 0.5 * abs(np.dot(cc, np.roll(rr, -1)) - np.dot(rr, np.roll(cc, -1)))
        worst = max(worst, abs(cov.sum() - area) / area)
    gate("門 2 描画器: 被覆率の和 = 刃の多角形の面積(4 角度、相対 %.1e)" % worst, worst < 2e-4)
    # ── 3. 刃の角度・刃先・先端
    ang, zum, tip = blade_accuracy(SF)
    _NUM["blade"] = {"angle_deg": ang, "edge_um": zum, "tip_mm": max(tip) if tip else None, "px_per_mm": SF["px_per_mm"]}
    gate("門 3 刃の追跡(4 px/mm、雑音 0.01、5 角度 −9〜10°): 角度 %.4f°、食材に隠れた中央の刃先の高さ(両側からの内挿)%.1f µm、先端 %d/5 で %.3f mm"
         % (ang, zum, len(tip), max(tip) if tip else -1), ang < 0.04 and zum < 20.0 and len(tip) >= 4 and max(tip) < 0.4)
    # ── 4. 切り込み深さ
    dum = depth_accuracy(SF)
    _NUM["depth_um"] = dum
    gate("門 4 切り込み深さ(食材の上面 = 彩度の縁、4 姿勢・深さ 4〜21 mm、0.25 mm/px): 最大 %.1f µm(0.12 px)" % dum, dum < 45.0)
    # ── 5. 切片の厚み
    cases = ((0.1, 0.0), (0.3, 0.0), (0.4, -1.0), (1.0, 1.5), (5.0, 0.0))
    wm, wr, wl = thickness_accuracy(SE, cases)
    _NUM["thickness"] = {"bias_um": wm, "rms_um": wr, "lean_deg": wl, "cases": len(cases)}
    gate("門 5 切片の厚み 0.1〜5 mm(10 px/mm = 1 px が 0.1 mm、%d 例、傾き ±1.5°): 平均の偏り %.1f µm、行ごとの RMS %.1f µm、傾き %.4f°"
         % (len(cases), wm, wr, wl), wm < 15.0 and wr < 40.0 and wl < 0.05)
    # ── 6. 刃が端面を突き抜ける形
    img = C.cutting_edge_render(SE, 6.0, 6.2, -3.0, 6.0)
    try:
        r = C.slice_thickness_profile(img, SE["px_per_mm"], SE["board_row"], _zband(SE))
        n_band = int(round((_zband(SE)[1] - _zband(SE)[0]) * SE["px_per_mm"]))
        ok6 = r["n_rows"] < 0.5 * n_band and r["thickness_mm"].min() > 0
        d6 = "受け付けたのは %d / %d 行、最小 %.3f mm > 0" % (r["n_rows"], n_band, r["thickness_mm"].min())
    except ValueError as exc:
        ok6, d6 = True, "ValueError: %s" % str(exc)[:70]
    gate("門 6 刃が端面を突き抜ける形(厚み ≤ 0)は 0 や負の厚みを返さない", ok6, d6)
    # ── 7. 切断面の粗さ
    r0, _, _ = rough_case(SE, 0.0, 1.0, 0.0)
    floor = r0["params"]["Rq"]
    rows7 = []
    for A, lam, rr in ((0.03, 1.0, 0.01), (0.05, 2.0, 0.02), (0.03, 0.5, 0.0)):
        r, pt, _ = rough_case(SE, A, lam, rr)
        rq_c = math.sqrt(max(r["params"]["Rq"] ** 2 - floor ** 2, 0.0))
        x = math.pi * (1.0 / SE["px_per_mm"]) / lam
        rows7.append((lam, r["params"]["Ra"] / pt["Ra"] - 1, rq_c / pt["Rq"], math.sin(x) / x))
    assert len(rows7) == 3
    ra = max(abs(o[1]) for o in rows7 if o[0] >= 1.0)
    rq = max(abs(o[2] - 1) for o in rows7 if o[0] >= 1.0)
    sinc_err = max(abs(o[2] - o[3]) for o in rows7 if o[0] < 1.0)
    _NUM["roughness"] = {"floor_um": floor, "ra": ra, "rq": rq, "sinc_err": sinc_err}
    gate("門 7 切断面の粗さ(シルエットの行ごと副画素 → roughness.profile_params、100 µm/px): 平らな面の床 Rq %.2f µm、λ ≥ 10 px で Ra %.1f %%・"
         "Rq(床を二乗で引く)%.1f %%、λ = 5 px では Rq の比が箱型の閉形式 sinc(πΔ/λ) と %.4f 差" % (floor, 100 * ra, 100 * rq, sinc_err),
         floor < 15.0 and ra < 0.10 and rq < 0.03 and sinc_err < 0.02)
    # ── 8. 画像 → 力 → R
    ch = force_chain(SF)
    out["chain"] = ch
    _NUM["chain"] = {k: ch[k] for k in ("R", "xi", "xi_true", "Ferr", "food_w", "n", "n_full")}
    gate("門 8 画像 → 刃の高さ → 手首のたわみ → 力 → 靱性: R %.1f J/m²(真値 400、%+.2f %%)、ξ %.4f(真値 %.4f、定常区間 %d コマ)、力の誤差 %.3f N"
         "(k 4 N/mm、定常 %.2f N)、食材の幅 %.2f mm、%d コマ" % (ch["R"], 100 * (ch["R"] / 400 - 1), ch["xi"], ch["xi_true"], ch["n_full"], ch["Ferr"],
                                                         ch["ep"]["F"].max(), ch["food_w"], ch["n"]),
         abs(ch["R"] / 400 - 1) < 0.03 and abs(ch["xi"] - ch["xi_true"]) < 0.02 and ch["Ferr"] < 0.15)
    # ── 9. 両辺に同じ模型(自己申告)
    ep = C.cutting_episode_synth(R=400.0 * 1.25, theta_deg=4.0, vx=4.0, vz=6.0, k_wrist=4.0, dt=0.12, n_frames=36, heel_x0=4.0, scene=SF)
    z_cmd_c = ep["heel_z_cmd"] + (SF["food_xc"] - ep["heel_x"]) * math.tan(math.radians(4.0))
    fit = C.cut_force_fit(C.force_from_wrist_displacement(ep["edge_z_c"], z_cmd_c, 4.0), ep["w_eff"], ep["xi"])
    gate("門 9 両辺に同じ模型が入る(自己申告): 力が 1.25 倍の世界(摩擦は模型に無い)でも当てはめは R = %.1f と出て、差を靱性に吸い込む"
         " —— この鎖は靱性と摩擦を分けられない(力の真値は外から来ていない)" % fit["R"], abs(fit["R"] / 400.0 - 1.25) < 1e-6)
    # ── 10. 綴り壊し・fail-closed
    img = C.cutting_face_render(SF, 18.0, 12.0, 0.0)
    bad = [lambda: C.knife_edge_track(img, method="Coverage"), lambda: C.knife_edge_track(img, method="subpixel"),
           lambda: C.cut_force_atkins(400, 34, model="atkins"), lambda: C.cut_force_atkins(400, 34, model="slice-push"),
           lambda: C.cut_force_atkins(400, 34, xi=0.5, mu=0.3), lambda: C.cut_force_atkins(400, 34, xi=0.5, wedge_deg=20),
           lambda: C.cut_force_atkins(-1, 34), lambda: C.force_from_wrist_displacement([1, 2], [1, 2], 0.0),
           lambda: C.slice_push_ratio(30, 5 * math.cos(math.radians(30)), 5 * math.sin(math.radians(30)) * -1),
           lambda: C.cut_force_fit([1, 2, 3], [5, 5, 5], 0.0, min_w_mm=10), lambda: C.cutting_scene("side"),
           lambda: C.cutting_scene("face", food_wdth=30), lambda: C.cut_force_csv_load("x.csv", ""),
           lambda: C.cutting_edge_render(SE, {"z": [0, 1]}, 6.0, 0.0, 6.0)]
    n_bad = sum(_raises(f) for f in bad)
    gate("門 10 綴り壊し・fail-closed(method の大文字、model の綴り、未読の式の組合せ、k = 0、刃先方向への運動、kind・キーの綴り、"
         "ライセンス未記入、端面の dict の鍵): %d / %d が ValueError" % (n_bad, len(bad)), n_bad == len(bad))
    # ── 11. 測るものが無い
    flat = np.full((200, 300, 3), 0.5)
    nan = img.copy()
    nan[5, 5, 0] = np.nan
    checks = [_raises(lambda: C.knife_edge_track(C.cutting_face_render(SF, -200.0, 12.0, 0.0), SF["board_row"])),
              _raises(lambda: C.knife_edge_track(flat)), _raises(lambda: C.knife_edge_track(np.full((10, 10), 0.5))),
              _raises(lambda: C.slice_thickness_profile(flat, 20, 190)), _raises(lambda: C.cut_surface_roughness(flat, 20, 190, (1, 5))),
              _raises(lambda: C.knife_edge_track(nan)), _raises(lambda: C.cut_depth_from_side(flat, {"line": {}}, 4, 190))]
    gate("門 11 測るものが無い(刃が画面の外 / 一様 / 小さすぎ / 厚みも粗さも一様 / NaN / 追跡結果でない入力): %d / %d が ValueError"
         % (sum(checks), len(checks)), all(checks))
    # ── 12. 壊れる場所(普通の条件)
    sw = breakage(SF, SE, (("noise", (0.0, 0.02)), ("blur_px", (1.0,)), ("gain", (0.4, 0.7, 1.3)), ("gradient", (0.4, 0.8))))
    w_ang = max(r[1] for rows in sw.values() for r in rows)
    w_dep = max(r[2] for rows in sw.values() for r in rows)
    w_thk = max(r[3] for rows in sw.values() for r in rows)
    ok12 = all(r[1] < 0.05 and r[2] < 0.03 and r[3] < 0.03 for rows in sw.values() for r in rows)
    _NUM["breakage_ci"] = sw
    gate("門 12 壊れる場所(普通の条件、低い解像度): 雑音 ≤ 0.02・ぼけ 1 px・gain 0.4〜1.3・照明勾配 ≤ 0.8 で角度 < 0.05°・深さ < 30 µm・厚み < 30 µm"
         "(試作では gain 0.4 が刃の灰の絶対の閾値で拒否されていた)", ok12, "最悪 角度 %.3f° 深さ %.0f µm 厚み %.0f µm" % (w_ang, 1000 * w_dep, 1000 * w_thk))
    # ── 13. 被験者と一致
    import measure
    rng = np.random.default_rng(1)
    x = np.linspace(0, 300, 200)
    pts = np.column_stack([120 + 0.07 * x + rng.normal(0, 0.3, x.size), x])
    fa, fb = C._tls(pts), measure.fit_line(pts)
    d_ang = abs(math.degrees(math.atan2(fa["dy"], fa["dx"])) - fb["angle_deg"])
    gate("門 13 被験者と一致: 内部の全最小二乗と measure.fit_line の差 角度 %.1e° rms %.1e(粗さは roughness.profile_params を直接呼ぶ)"
         % (d_ang, abs(fa["rms"] - fb["rms"])), d_ang < 1e-9 and abs(fa["rms"] - fb["rms"]) < 1e-12)
    # ── 14. 入口と MJCF
    names = [n for n in C.__all__]
    missing = [n for n in names if not callable(getattr(C, n, None))]
    bad_doc = [n for n in names if "](" in (getattr(C, n).__doc__ or "")]
    root = ET.fromstring(C.cutting_wrist_mjcf(SF_FULL))
    cam = root.find(".//camera")
    ok14 = (not missing and not bad_doc and len(names) == 17 and root.find(".//joint").get("type") == "slide"
            and cam is not None and cam.get("projection") == "orthographic" and "](" not in (C.__doc__ or ""))
    gate("門 14 入口: __all__ %d 本(台帳 16 + facade 1)が呼べる、docstring に '](' が無い、MJCF(スライド関節 1 本・正射影カメラ)が読める"
         % len(names), ok14, "missing %s, '](' %s" % (missing, bad_doc))
    return out


# ======================================================================================================================
def full_part(out: dict) -> dict:
    print("== 2. --full(元の解像度・MuJoCo・任意のデータ)")
    # ── 15. 元の解像度の精度
    ang, zum, tip = blade_accuracy(SF_FULL)
    dum = depth_accuracy(SF_FULL)
    wm, wr, wl = thickness_accuracy(SE_FULL, ((0.1, 0.0), (0.15, 1.5), (0.3, 0.0), (0.4, -1.0), (1.0, 1.5), (2.0, -1.0), (5.0, 0.0)))
    _NUM["full_res"] = {"angle": ang, "edge_um": zum, "tip_mm": max(tip), "depth_um": dum, "thk_bias_um": wm, "thk_rms_um": wr, "lean": wl}
    gate("門 15 元の解像度(8 px/mm・20 px/mm): 角度 %.4f°・刃先 %.1f µm・先端 %d/5 で %.3f mm・深さ %.1f µm、厚み 7 例で偏り %.1f µm・RMS %.1f µm・傾き %.4f°"
         % (ang, zum, len(tip), max(tip), dum, wm, wr, wl),
         ang < 0.01 and zum < 10 and len(tip) >= 4 and max(tip) < 0.06 and dum < 12 and wm < 6 and wr < 25 and wl < 0.03)
    # ── 16. 壊れる場所の全掃引(元の解像度)
    sw = breakage(SF_FULL, SE_FULL, (("noise", (0.0, 0.02, 0.05, 0.1, 0.2)), ("blur_px", (0.0, 1.0, 2.0, 4.0, 8.0)),
                                     ("gain", (0.4, 0.7, 1.0, 1.3)), ("gradient", (0.0, 0.4, 0.8, 1.2))))
    out["breakage_full"] = sw
    _NUM["breakage_full"] = sw
    thk = {k: {v: t for v, _, _, t in rows} for k, rows in sw.items()}
    ok16 = (thk["blur_px"][4.0] < 0.015 and not math.isfinite(thk["blur_px"][8.0]) and thk["gain"][0.4] < 0.01
            and all(t < 0.012 for t in thk["gradient"].values()) and not math.isfinite(thk["noise"][0.1])
            and all(math.isfinite(t) is False or t < 0.05 for rows in thk.values() for t in rows.values()))
    gate("門 16 壊れる場所の全掃引(元の解像度): ぼけ 4 px は窓を広げて %.1f µm(試作 −18 µm)、8 px は刃の帯が細すぎて拒否(試作は −37 µm で黙って通った)、"
         "gain 0.4 は %.1f µm(試作は拒否)、照明勾配 ≤ 1.2 で ≤ %.1f µm、雑音 0.1 は拒否 —— 通った値はどれも 50 µm 未満(黙って大きく間違えない)"
         % (1000 * thk["blur_px"][4.0], 1000 * thk["gain"][0.4], 1000 * max(thk["gradient"].values())), ok16)
    try:
        import mujoco  # noqa: F401
    except ImportError:
        skip("門 17〜20(MuJoCo)", "mujoco が無い")
        mj = False
    else:
        mj = True
    if mj:
        flex_compression()
        flex_knife(out)
        mujoco_wrist(out)
    cut_force_data()
    return out


def _flex_xml(E, knife=False):
    body = ('<body name="knife" pos="0 0 0.0425"><joint name="kz" type="slide" axis="0 0 1" damping="5"/>'
            '<geom type="box" size="0.03 0.0005 0.002" mass="0.05"/></body>') if knife else \
        ('<body name="platen" pos="0 0 0.0415"><joint name="kz" type="slide" axis="0 0 1" damping="5"/>'
         '<geom type="box" size="0.03 0.03 0.0005" mass="0.1"/></body>')
    count, spacing, pin = ("9 9 6", "0.005 0.005 0.008", "0 0 0 8 8 0") if knife else ("6 6 6", "0.008 0.008 0.008", "0 0 0 5 5 0")
    return f"""<mujoco>
 <option timestep="0.0002" gravity="0 0 0" solver="Newton" integrator="implicitfast" iterations="50"/>
 <worldbody>
  {body}
  <flexcomp name="food" type="grid" count="{count}" spacing="{spacing}" pos="0 0 0.020" dim="3" radius="0.0005" mass="0.07">
   <elasticity young="{E}" poisson="0.3" damping="0.0005"/>
   <contact condim="1" solref="0.003 1" selfcollide="none"/>
   <edge equality="false"/>
   <pin gridrange="{pin}"/>
  </flexcomp>
 </worldbody>
 <actuator><position joint="kz" kp="2e4" kv="0"/></actuator>
</mujoco>"""


def _contact_fz(mujoco, m, d):
    fz = 0.0
    f6 = np.zeros(6)
    for c in range(d.ncon):
        mujoco.mj_contactForce(m, d, c, f6)
        fz += f6[0]
    return fz


def flex_compression():
    """柔体の柱(40 mm 角、E 20 kPa、底を固定)を平板で 2 / 3 / 4 mm 押す。保持中も揺れ続けるので保持の後半 6,000 歩の平均で比べる。"""
    import mujoco
    E = 2e4
    m = mujoco.MjModel.from_xml_string(_flex_xml(E))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    v0 = d.flexvert_xpos.copy()
    top = v0[:, 2] > v0[:, 2].max() - 1e-6
    ratios, spreads, prev, t0 = [], [], 0.0, time.time()
    for target in (0.002, 0.003, 0.004):
        samp = []
        for i in range(12000):
            d.ctrl[0] = -(prev + (target - prev) * min(1.0, (i + 1) / 3000))
            mujoco.mj_step(m, d)
            if i >= 6000 and i % 500 == 499:
                comp = -(d.flexvert_xpos[top, 2] - v0[top, 2]).mean()
                samp.append(_contact_fz(mujoco, m, d) / (E * 0.04 ** 2 * comp / 0.04))
        assert len(samp) >= 10
        prev = target
        ratios.append(float(np.mean(samp)))
        spreads.append(float(np.ptp(samp)))
    _NUM["flex_ratio"] = ratios
    gate("門 17 MuJoCo の柔体の圧縮: F/(E·A·δ/H) = %s(底を固定 = 横に広がれないので 1(自由)〜 1.35(完全拘束、ν 0.3)の間)、保持中の揺れ ptp %s、%.1f s"
         % (" / ".join("%.3f" % r for r in ratios), " / ".join("%.2f" % x for x in spreads), time.time() - t0),
         all(0.9 <= r <= 1.35 for r in ratios))


def flex_knife(out):
    """刃(厚さ 1 mm の板)を柔体に 10 mm 押し込む: 力は頭打ちの後に下がる = 破断ではなく潜り込み。切断は摩擦損失で入れる理由。"""
    import mujoco
    m = mujoco.MjModel.from_xml_string(_flex_xml(2e4, knife=True))
    d = mujoco.MjData(m)
    F, Z, n, t0 = [], [], 12000, time.time()
    for i in range(n):
        d.ctrl[0] = -0.010 * (i + 1) / n
        mujoco.mj_step(m, d)
        if i % 500 == 499:
            F.append(_contact_fz(mujoco, m, d))
            Z.append(-d.qpos[0])
    F, Z = np.array(F), np.array(Z)
    assert F.size >= 10
    ipk = int(np.argmax(F))
    drop = 1.0 - F[ipk:].min() / F[ipk]
    out["flex_knife"] = (Z, F)
    _NUM["flex_knife"] = {"peak_N": float(F[ipk]), "peak_mm": float(1000 * Z[ipk]), "drop": float(drop)}
    gate("門 18 MuJoCo の柔体に刃を押す: %.2f N(%.1f mm)で頭打ちの後 −%.0f %% —— 切れずに要素へ潜り込む(破断のエネルギーも定常値も出ない)、%.1f s"
         % (F[ipk], 1000 * Z[ipk], 100 * drop, time.time() - t0), bool(np.isfinite(F).all() and drop > 0.3 and ipk < len(F) - 3))


def mujoco_wrist(out):
    t0 = time.time()
    sc = SF_FULL
    run = C.cutting_mujoco_wrist(sc, theta_deg=4.0, R=400.0, k_n_per_mm=4.0, damping=25.0, mass=0.15, vz=6.0, n_frames=30)
    ez_img, ang = [], []
    for img in run["frames"]:
        try:
            tr = C.knife_edge_track(img, sc["board_row"])
            ez_img.append(edge_z_at(tr, sc["food_xc"], sc))
            ang.append(tr["angle_deg"])
        except ValueError:
            ez_img.append(np.nan)
            ang.append(np.nan)
    ez_img, ang = np.array(ez_img), np.array(ang)
    ok_track = bool(np.isfinite(ez_img).all())
    F_img = C.force_from_wrist_displacement(ez_img, run["z_cmd_c"], 4.0) if ok_track else np.full(len(ez_img), np.nan)
    F_img = F_img - F_img[0]                                  # 空中の 1 コマ目で重さを差し引く(風袋)
    z_err = float(np.nanmax(np.abs(ez_img - run["edge_z_true"]))) if ok_track else math.inf
    a_err = float(np.nanmax(np.abs(ang - 4.0))) if ok_track else math.inf
    F_err = float(np.nanmax(np.abs(F_img - run["F_constraint"]))) if ok_track else math.inf
    cv = 25.0 * 6.0 / 1000
    out["mujoco"] = {"run": run, "ez_img": ez_img, "F_img": F_img}
    _NUM["mujoco"] = {"z_err_um": 1000 * z_err, "angle_err": a_err, "F_err": F_err, "cv": cv, "plateau": run["params"]["plateau_N"]}
    gate("門 19 MuJoCo の描画 → 刃の追跡(正射影カメラ、8 px/mm、%d コマ): 刃先の高さ %.1f µm、角度 %.4f°" % (len(ez_img), 1000 * z_err, a_err),
         ok_track and z_err < 0.03 and a_err < 0.03)
    gate("門 20 手首の力(画像のたわみ、空中で風袋)vs MuJoCo の拘束力: 最大 %.3f N ≤ 減衰 c·v = %.3f N(定常 %.2f N の %.1f %%)、%.1f s"
         % (F_err, cv, run["params"]["plateau_N"], 100 * F_err / run["params"]["plateau_N"], time.time() - t0), ok_track and F_err <= cv)


def _ramp_plateau_fit(dep, F):
    """F = min(k·d, Fp) の 2 定数を格子で。"""
    best = None
    for Fp in np.linspace(0.3 * F.max(), F.max(), 120):
        for kk in np.linspace(Fp / dep.max(), 50 * Fp / dep.max(), 120):
            r = float(np.sqrt(np.mean((F - np.minimum(kk * dep, Fp)) ** 2)))
            if best is None or r < best[0]:
                best = (r, kk, Fp)
    return best


def cut_force_data():
    root = os.environ.get("FULLSEYE_CUT_FORCE_DATA", "").strip()
    p = os.path.join(root, "forces") if root else ""
    if not root or not os.path.isdir(p):
        skip("門 21 FEM の力曲線(任意、非商用)", "環境変数 FULLSEYE_CUT_FORCE_DATA が無い(arXiv:2105.12244 のデータセット、CC BY-NC 4.0)")
        return
    rows = []
    for name, vel in (("prism_fine", 50), ("cylinder_fine", 50), ("sphere_fine", 50), ("prism_fine_sphereprops", 50),
                      ("cylinder_fine_vel35", 35), ("cylinder_fine_vel65", 65)):
        f = os.path.join(p, name + "_resultant_force_xyz.csv")
        if not os.path.isfile(f):
            continue
        dd = C.cut_force_csv_load(f, license="CC-BY-NC-4.0")
        t, Fy = dd["t_s"], dd["F_xyz"][:, 1]
        i0 = int(np.argmax(np.abs(Fy) > 1e-6))
        dep = (t - t[i0]) * vel                               # mm(刃は等速で下がる)
        sel = (dep >= 0) & (dep <= 30.0)
        best = _ramp_plateau_fit(dep[sel], Fy[sel])
        rows.append((name, best[0] / best[2]))
    if not rows:
        skip("門 21 FEM の力曲線(任意、非商用)", "forces/ に想定の CSV が無い")
        return
    worst = max(r[1] for r in rows)
    _NUM["fem_force"] = {"n": len(rows), "worst_rms_over_plateau": worst}
    gate("門 21 FEM の刃の力(任意、CC BY-NC 4.0、数値だけ): %d 本を「立ち上がり + 定常」の 2 定数で当てた残差 / 定常値 最大 %.3f"
         "(食材の幅が分からないので R は出さない、形の比較だけ)" % (len(rows), worst), worst < 0.15)


# ======================================================================================================================
C_EST = np.array([0.90, 0.10, 0.75])      # 推定(マゼンタ)
C_TRUE = np.array([0.00, 0.62, 0.45])     # 真値(緑)
C_TIP = np.array([0.95, 0.55, 0.00])


def _seg(img, p0, p1, color, width=1.5, dash=0.0):
    """(row, col) の線分を太さ width で塗る(距離 + 0.5 px の縁のぼかし)。dash > 0 で破線(px)。"""
    H, W = img.shape[:2]
    (r0, c0), (r1, c1) = p0, p1
    rmin, rmax = int(max(0, math.floor(min(r0, r1) - width - 2))), int(min(H, math.ceil(max(r0, r1) + width + 2)))
    cmin, cmax = int(max(0, math.floor(min(c0, c1) - width - 2))), int(min(W, math.ceil(max(c0, c1) + width + 2)))
    if rmin >= rmax or cmin >= cmax:
        return img
    rr, cc = np.mgrid[rmin:rmax, cmin:cmax].astype(float)
    dv = np.array([r1 - r0, c1 - c0])
    L2 = float(dv @ dv) or 1e-12
    t = np.clip(((rr - r0) * dv[0] + (cc - c0) * dv[1]) / L2, 0, 1)
    a = np.clip(width / 2 + 0.5 - np.hypot(rr - (r0 + t * dv[0]), cc - (c0 + t * dv[1])), 0, 1)
    if dash > 0:
        a *= ((t * math.sqrt(L2)) // dash) % 2 == 0
    img[rmin:rmax, cmin:cmax] = img[rmin:rmax, cmin:cmax] * (1 - a[..., None]) + a[..., None] * color
    return img


def _text(img, s, xy, fs=14):
    import annotate as AN
    try:
        return np.asarray(AN.text_box(img, s, xy, anchor="lt", font_size=fs), dtype=np.float64)
    except Exception as exc:  # noqa: BLE001  文字が収まらない等は図を落とさず素のコマ
        figs._errors.append("text_box: %r" % (exc,))
        return img


def _line_across(img, f, c0, c1, color, width, dash=0.0):
    r = lambda c: f["cy"] + (c - f["cx"]) * f["dy"] / f["dx"]  # noqa: E731
    return _seg(img, (r(c0), c0), (r(c1), c1), color, width, dash)


def fig_cutting_gif():
    sc = SF_FULL
    theta = 4.0
    ep = C.cutting_episode_synth(R=400.0, theta_deg=theta, vx=4.0, vz=6.0, k_wrist=4.0, dt=0.06, n_frames=80, heel_x0=4.0, scene=sc)
    tt = math.tan(math.radians(theta))
    frames, Fs, ts = [], [], []
    for i in range(0, len(ep["t"]), 4):                  # 4 コマおき(3 コマおきは GIF が 9.2 MB で上限 8 MB を超えた。縮小・減色はしない)
        img = C.cutting_face_render(sc, ep["heel_x"][i], ep["heel_z"][i], theta, noise=0.01, seed=int(i))
        tr = C.knife_edge_track(img, sc["board_row"])
        ez = edge_z_at(tr, sc["food_xc"], sc)
        zc = ep["heel_z_cmd"][i] + (sc["food_xc"] - ep["heel_x"][i]) * tt
        F = float(C.force_from_wrist_displacement(np.array([ez]), np.array([zc]), 4.0)[0])
        Fs.append(F)
        ts.append(ep["t"][i])
        o = np.clip(img, 0, 1).copy()
        v = C._blade_polygon_xz(sc, ep["heel_x"][i], ep["heel_z"][i], theta)
        r0, c0 = C._face_xz_to_rc(sc, v[0, 0], v[0, 1])
        r1, c1 = C._face_xz_to_rc(sc, v[1, 0], v[1, 1])
        o = _seg(o, (r0, c0), (r1, c1), C_TRUE, 1.0)
        f = tr["line"]
        oc, (cl, cr) = tr["occluded_cols"], tr["cols_used"]
        if oc is not None:
            o = _line_across(o, f, max(0.0, float(c0)), oc[0] - 3, C_EST, 2.0)
            o = _line_across(o, f, oc[0] - 3, oc[1] + 3, C_EST, 2.0, dash=8)
            o = _line_across(o, f, oc[1] + 3, min(sc["W"] - 1, cr), C_EST, 2.0)
        else:
            o = _line_across(o, f, cl, cr, C_EST, 2.0)
        if tr["tip_rc"] is not None:
            a, b = tr["tip_rc"]
            o = _seg(o, (a - 7, b), (a + 7, b), C_TIP, 2.0)
            o = _seg(o, (a, b - 7), (a, b + 7), C_TIP, 2.0)
        try:
            import annotate as AN
            cz = 210.0
            rz = r0 + (cz - c0) * (r1 - r0) / (c1 - c0)
            o = np.asarray(AN.zoom_inset(o, (int(cz) - 12, int(round(rz)) - 8, 24, 16), (sc["W"] - 24 * 8 - 10, 80), factor=8), dtype=np.float64)
        except Exception as exc:  # noqa: BLE001
            figs._errors.append("zoom_inset: %r" % (exc,))
        o = _text(o, "t %.2f s   depth %.2f mm (true %.2f)   angle %.3f deg (true %.1f)\nforce from wrist %.2f N (true %.2f)   xi %.3f"
                  % (ep["t"][i], sc["food_h"] - ez, sc["food_h"] - ep["edge_z_c"][i], tr["angle_deg"], theta, F, ep["F"][i], ep["xi"]), (8, 8))
        tsa, Fsa = (np.array(ts), np.array(Fs)) if len(ts) >= 2 else (np.array(ts * 2), np.array(Fs * 2))
        plot = figs.render_plot([("true (Atkins slice/push)", ep["t"], ep["F"]), ("from image (k dz)", tsa, Fsa)], xlabel="time [s]",
                                ylabel="push force [N]", title="", size=(sc["W"], 200), xlim=(0, ep["t"][-1]), ylim=(-0.5, ep["F"].max() * 1.15),
                                styles=["dashed", None], colors=["reference", "emphasis"])
        frames.append(np.concatenate([o, plot], axis=0))
    figs.save_gif("cutting_track_force", frames, fps=10,
                  caption="合成の切断(8 px/mm、等倍): 刃先線の推定(マゼンタ、食材に隠れた所は破線 = 両側からの内挿)、真値(緑)、先端(橙)、"
                          "差し込みは最近傍 8 倍。下は手首のたわみからの力(実線)と Atkins の閉形式(破線)。")


def fig_thickness():
    se = SE_FULL
    rng = np.random.default_rng(21)
    tru, est = [], []
    for k in range(40):
        h, lean = 1.5 + rng.normal(0, 0.08), rng.normal(0, 0.5)
        img = C.cutting_edge_render(se, 6.0, 6.0 + h, lean, 6.0, noise=0.01, seed=k)
        r = C.slice_thickness_profile(img, se["px_per_mm"], se["board_row"], _zband(se))
        tz = h + (se["food_top"] - r["z_mm"]) * math.tan(math.radians(lean))
        tru.append(tz.mean())
        est.append(r["mean_mm"])
        if k == 0:
            o = np.clip(img.copy(), 0, 1)
            rr0, rr1 = se["board_row"] - _zband(se)[1] * se["px_per_mm"], se["board_row"] - _zband(se)[0] * se["px_per_mm"]
            for fit in (r["face_line"], r["end_line"]):
                c = lambda rr: fit["cx"] + (rr - fit["cy"]) * fit["dx"] / fit["dy"]  # noqa: E731
                o = _seg(o, (rr0, c(rr0)), (rr1, c(rr1)), C_EST, 1.5, dash=6)
            o = _text(o, "slice %.3f mm (true %.3f)\nlean %.3f deg (true %.3f)" % (r["mean_mm"], tz.mean(), r["lean_deg"], lean), (8, 8))
            figs.save("edge_view_thickness", o, caption="刃先方向の像(20 px/mm、等倍): 片刃の平らな面と食材の端面の距離 = 切片の厚み。破線 = 推定の両縁。")
    tru, est = np.array(tru), np.array(est)
    err = est - tru
    bins = np.linspace(1.25, 1.75, 26)
    xc = 0.5 * (bins[1:] + bins[:-1])
    figs.save_plot("thickness_distribution", [("true", xc, np.histogram(tru, bins)[0]), ("from image", xc, np.histogram(est, bins)[0])],
                   xlabel="slice thickness [mm]", ylabel="count (40 slices)",
                   title="40 slices: target 1.5 mm, robot spread 0.08 mm  |  error %+.1f +- %.1f um" % (1000 * err.mean(), 1000 * err.std()),
                   styles=["dashed", None], colors=["reference", "emphasis"], size=(640, 360),
                   caption="狙い 1.5 mm・ばらつき σ 0.08 mm・傾き σ 0.5° の 40 枚: 真値(破線)と画像(実線)の分布。")
    figs.save_plot("thickness_scatter", [("", tru, est), ("y = x", np.array([1.25, 1.75]), np.array([1.25, 1.75]))],
                   xlabel="true mean thickness [mm]", ylabel="measured [mm]", title="measured vs true (40 slices)",
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"], size=(480, 480), aspect="equal",
                   caption="40 枚の測った厚み vs 真値(破線 = y = x)。誤差 %+.1f ± %.1f µm。" % (1000 * err.mean(), 1000 * err.std()))


def fig_roughness():
    r, pt, prof = rough_case(SE_FULL, 0.03, 1.0, 0.010)
    zs = r["z_mm"]
    tru = np.interp(zs, prof["z_mm"], prof["y_mm"])
    dev = (tru - np.polyval(np.polyfit(zs, tru, 1), zs)) * 1000
    figs.save_plot("cut_surface_profile", [("true", zs, dev), ("from silhouette", zs, r["profile_um"])], xlabel="height z [mm]",
                   ylabel="deviation [um]", title="cut face: Ra %.1f um (true %.1f) at 50 um/px" % (r["params"]["Ra"], pt["Ra"]),
                   styles=["dashed", None], colors=["reference", "emphasis"], size=(720, 320),
                   caption="切断面の断面(振幅 30 µm・波長 1 mm + 乱れ 10 µm): 真値(破線)とシルエットからの断面(実線)。")


def fig_breakage(out):
    sw = out.get("breakage_full")
    if sw is None:
        sw = breakage(SF_FULL, SE_FULL, (("noise", (0.0, 0.02, 0.05, 0.1, 0.2)), ("blur_px", (0.0, 1.0, 2.0, 4.0, 8.0))))
    series = []
    for key, lab in (("noise", "noise sigma x100"), ("blur_px", "blur px")):
        sc = 100 if key == "noise" else 1
        rows = [r for r in sw[key] if math.isfinite(r[2])]
        series.append(("depth err [um] vs " + lab, np.array([r[0] * sc for r in rows]), np.array([1000 * r[2] for r in rows])))
        rows = [r for r in sw[key] if math.isfinite(r[3])]
        series.append(("thickness err [um] vs " + lab, np.array([r[0] * sc for r in rows]), np.array([1000 * r[3] for r in rows])))
    figs.save_plot("where_it_breaks", series, xlabel="noise sigma x100  /  blur sigma [px]", ylabel="error [um]",
                   title="where it breaks (missing points = refused, ValueError)", size=(720, 400), ylim=(0, 60),
                   caption="雑音とぼけを強めたときの深さ・厚みの誤差(元の解像度)。点が無い所は拒否(ValueError)= 黙って間違えない。")


def fig_closed_form(out):
    xs = np.linspace(0, 4, 400)
    f = [C.cut_force_atkins(1, 1000, xi=x) for x in xs]
    xi0 = out["chain"]["xi"]
    figs.save_plot("slice_push_closed_form", [("V/Rw push", xs, np.array([g["V"] for g in f])), ("H/Rw slice", xs, np.array([g["H"] for g in f])),
                                              ("F_res/Rw", xs, np.array([g["F_res"] for g in f])), ("this cut", np.array([xi0, xi0]), np.array([0, 1]))],
                   xlabel="slice/push ratio xi", ylabel="force / (R w)", title="Atkins 2016 eqs 1.2-1.4 (frictionless)  |  xi from the image %.3f" % xi0,
                   styles=[None, None, None, "dashed"], colors=["emphasis", "right", "neutral", "reference"], size=(640, 380),
                   caption="摩擦なしの slice/push の閉形式。引く分が増える(ξ が大きい)ほど押す力が下がる。破線 = 画像から出したこの切断の ξ。")


def fig_mujoco(out):
    mj = out.get("mujoco")
    if mj:
        run = mj["run"]
        frames = []
        for i, img in enumerate(run["frames"]):
            o = np.clip(img.copy(), 0, 1)
            try:
                o = _line_across(o, C.knife_edge_track(img, SF_FULL["board_row"])["line"], 0, SF_FULL["W"] - 1, C_EST, 1.5, dash=10)
            except ValueError:
                pass
            o = _text(o, "MuJoCo render  t %.2f s\nedge z %.3f mm (MuJoCo %.3f)   force: image %.2f N / constraint %.2f N"
                      % (run["t"][i], mj["ez_img"][i], run["edge_z_true"][i], mj["F_img"][i], run["F_constraint"][i]), (8, 8))
            frames.append(o)
        figs.save_gif("mujoco_wrist_track", frames, fps=6, caption="MuJoCo の正射影カメラで描いた刃(柔らかい手首 4 N/mm、抵抗 = 摩擦損失 = "
                      "Atkins の切断力)を同じ追跡器で追う。破線 = 推定の刃先線。")
    if "flex_knife" in out:
        Z, F = out["flex_knife"]
        figs.save_plot("mujoco_flex_knife", [("knife into flex block", 1000 * Z, F)], xlabel="knife travel [mm]", ylabel="contact force [N]",
                       title="MuJoCo flex: force peaks then drops (blade sinks through, no fracture)", size=(560, 320),
                       caption="MuJoCo の柔体に刃を押し込むと、力は頭打ちの後に下がる(潜り込み)。切断は関節の摩擦損失で入れる理由。")


def figures(out):
    print("== 3. 図(元の解像度、等倍)")
    for fn in (fig_cutting_gif, fig_thickness, fig_roughness, lambda: fig_breakage(out), lambda: fig_closed_form(out), lambda: fig_mujoco(out)):
        fn()
    print("  figures:", figs.errors() or "ok")


# ======================================================================================================================
def main() -> int:
    t_all, c_all = time.time(), time.process_time()
    out = numpy_part()
    print("  (numpy の門: CPU %.2f s / 壁時計 %.2f s。壁時計は機械の負荷で伸びる)" % (time.process_time() - c_all, time.time() - t_all))
    if FULL:
        out = full_part(out)
    else:
        skip("門 15〜21(元の解像度・MuJoCo・任意のデータ)", "--full のときだけ")
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
