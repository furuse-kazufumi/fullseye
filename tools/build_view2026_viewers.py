#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の「触って見る」7 本のビューアを作る(1 つの入口で 7 本とも。第 1 弾 3 本 + 第 2 弾 4 本)。

    py -3.11 tools/build_view2026_viewers.py              # docs/view2026/viewers/*.html を書く
    py -3.11 tools/build_view2026_viewers.py --only poc_template_tracking
    py -3.11 tools/build_view2026_viewers.py --check      # 書かずに、命令が通ることと配列の健全さを検査

数字は **手で写さない**。各 PoC の関数を import して(または同じ計算をやり直して)得た値だけを使う:

* ``poc_cad_scan_deviation``  —— ``CadRef`` / ``section_align`` / ``make_scan`` / ``align``
* ``poc_lidar_terrain_change`` —— ``load_forest_park`` / ``_grid1m`` / ``section_real_usgs``(USGS 3DEP)
* ``poc_template_tracking``   —— ``make_world`` / ``make_sequence`` / ``run_tracker``
* ``poc_thermography_ndt``    —— ``build_scene`` / ``synth_cube`` / ``tsr_depth``(合成。数秒)
* ``poc_grating_interferometry`` —— ``chapter_carpet`` / ``chapter_source`` / ``chapter_coupon``(常に full 予算で作る)
* ``poc_phase_measuring_deflectometry`` —— ``surface`` / ``decode`` / ``integrate`` / ``depth``(合成)
* ``poc_asteroid_curvature``  —— ``curvature3d``(``studio_assets/sample_3d/itokawa_points.npy`` は公有の形状モデルの頂点)

実際の HTML は公開 API :mod:`pocviewer`(``fullseye.write_viewer``)が書く。ここは「PoC の結果を仕様に
詰める」薄い呼び出し側。文字列(8 言語)は ``tools/view2026_viewer_texts.py``。出力は
``docs/view2026/viewers/<poc_id>.html``(GitHub Pages が ``https://furuse.work/view2026/viewers/`` として配る)。

**regen_all には入れない**: LiDAR の実データ(``FULLSEYE_DATA_DIR`` 配下、リポジトリには無い)が要り、
無い環境では作れないため。全体で 10 秒前後で決定的だが、データの有無で結果が変わる生成物を
``regen_all --check`` に入れると、データの無い CI で赤になる。出力を変えたらこのコマンドを手で回して commit する。
LiDAR のデータが無ければ、それが無いと言って止まる(合成で代用しない)。
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pocviewer as pv  # noqa: E402
import view2026_viewer_texts as TX  # noqa: E402

OUT = ROOT / "docs" / "view2026" / "viewers"
ALL_LANGS = list(pv.LANGS)             # ja が先頭 = 既定
DATA_ENV = "FULLSEYE_DATA_DIR"


def _load(name: str):
    """``examples/<name>.py`` を import する(リポジトリ直下を sys.path の先頭に置いて)。"""
    spec = importlib.util.spec_from_file_location(name, ROOT / "examples" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _quiet(fn, *a, **k):
    """PoC の節は大量に印字する。ここでは値だけ要るので捨てる。"""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def _n(key: str, value) -> dict:
    return pv.viewer_number(TX.N[key], value)


# --------------------------------------------------------------------------- #
# 1. CAD と実測点群                                                             #
# --------------------------------------------------------------------------- #
def build_cad() -> dict:
    P = _load("poc_cad_scan_deviation")
    ref = P.CadRef()
    al = _quiet(P.section_align, ref)
    sc, keep, rows = al["scan"], al["keep"], al["rows"]
    row = {"none": 0, "centroid": 1, "fpfh": 2, "p2plane": 4, "oracle": 6}
    cb = {"lo": -200.0, "hi": 200.0, "unit": "µm", "cmap": "div", "label": TX.CAD["cbar"]}
    tol_mm = P.TOL

    def deg(r):
        return "%.3f°" % float(r[1])

    def mm(r):
        return "%.3f mm" % float(r[2])

    def um(x):
        return "%.1f µm" % float(x)

    def area(r):
        return "%.0f mm² (%s)" % (float(r[5]), r[6])

    ghost = ref.pts[::4]
    tabs = []

    def pose_tab(tid, meth, label, text, badge, nums):
        k = keep[meth]
        return pv.viewer_points_tab(
            tid, TX.CAD[label], badge, text, k["q"], val=1000.0 * k["sig"], cbar=cb, numbers=nums,
            ghost=ghost if meth in ("none", "centroid") else None)

    d0, d1 = float(keep["none"]["unsig"].mean()), float(keep["centroid"]["unsig"].mean())
    r0, r1, r2, r4, r6 = (rows[row[k]] for k in ("none", "centroid", "fpfh", "p2plane", "oracle"))
    tabs.append(pose_tab("none", "none", "t_none", TX.fmt(TX.CAD["x_none"], d=d0, x=d0 / tol_mm), "null",
                         [_n("nn", "%.2f mm" % d0), _n("rot", deg(r0))]))
    tabs.append(pose_tab("centroid", "centroid", "t_cent", TX.fmt(TX.CAD["x_cent"], d=d1, x=d1 / tol_mm), "null",
                         [_n("nn", "%.2f mm" % d1), _n("rot", deg(r1))]))
    tabs.append(pose_tab("fpfh", "fpfh", "t_fpfh", TX.fmt(TX.CAD["x_fpfh"], rot="%.3f" % float(r2[1]), rms=r2[3]),
                         "limit", [_n("rot", deg(r2)), _n("shift", mm(r2)), _n("rms", um(r2[3])),
                                   _n("max", um(r2[4])), _n("area", area(r2))]))
    tabs.append(pose_tab("icp", "p2plane", "t_icp",
                         TX.fmt(TX.CAD["x_icp"], rot="%.3f" % float(r4[1]), rms=r4[3], floor=r6[3]), "passed",
                         [_n("rot", deg(r4)), _n("shift", mm(r4)), _n("rms", um(r4[3])),
                          _n("max", um(r4[4])), _n("area", area(r4))]))
    tabs.append(pose_tab("truepose", "oracle", "t_true", TX.fmt(TX.CAD["x_true"], rms=r6[3]), "passed",
                         [_n("rms", um(r6[3])), _n("max", um(r6[4])), _n("area", area(r6))]))

    # 反りだけ(第 6 章): 無雑音・真の姿勢を初期値に点-面 ICP
    sw = P.make_scan(n=14000, noise=0.0, dent_h=0.0, warp_a=P.WARP_A, wear_w=0.0)
    q_true = sw["pts"] @ sw["R_true"].T + sw["t_true"]
    _, s_true, _, ed_t = ref.deviate(q_true)
    R, t = P.align(sw["pts"], ref, method="p2plane", init=(sw["R_true"], sw["t_true"]), iters=25)
    q_icp = sw["pts"] @ R.T + t
    _, s_icp, _, ed = ref.deviate(q_icp)
    Pn = sw["nom"]
    sel = (np.abs(Pn[:, 0]) < 3.0) & (Pn[:, 2] > P.H - 1e-6) & (sw["nrm"][:, 2] > 0.9) & ~ed
    true_um = 1000.0 * float(np.mean(sw["dev_true"][sel]))
    meas_um = 1000.0 * float(np.mean(s_icp[sel]))
    meas_true_um = 1000.0 * float(np.mean(s_true[sel & ~ed_t]))
    tz_um = 1000.0 * float((t - sw["t_true"])[2])
    assert meas_um < -1000.0 * tol_mm, "反りの偽のへこみが公差を超えなかった: %r" % meas_um
    tabs.append(pv.viewer_points_tab(
        "warp_true", TX.CAD["t_warpT"], "passed", TX.fmt(TX.CAD["x_warpT"], t=meas_true_um), q_true,
        val=1000.0 * s_true, cbar=cb, numbers=[_n("truec", "%.1f µm" % true_um), _n("measc", "%.1f µm" % meas_true_um)]))
    tabs.append(pv.viewer_points_tab(
        "warp_icp", TX.CAD["t_warpI"], "limit", TX.fmt(TX.CAD["x_warpI"], t=true_um, m=meas_um, tz=tz_um), q_icp,
        val=1000.0 * s_icp, cbar=cb,
        numbers=[_n("truec", "%.1f µm" % true_um), _n("measc", "%.1f µm" % meas_um), _n("tz", "%.1f µm" % tz_um)]))

    # 稜線の罠: 欠陥も雑音もゼロ・姿勢は真値でも、素朴な最近傍は偽の公差外領域を出す
    scn = P.make_scan(noise=0.0, defects=False)
    q1 = scn["pts"] @ scn["R_true"].T + scn["t_true"]
    _, s1, _, ed1 = ref.deviate(q1)
    a_false = P.out_of_tol_area(s1, scn["w"])
    a_ok = P.out_of_tol_area(s1[~ed1], scn["w"])
    frac = 100.0 * float(ed1.mean())
    tabs.append(pv.viewer_points_tab(
        "edge", TX.CAD["t_edge"], "limit", TX.fmt(TX.CAD["x_edge"], a=a_false, f=frac, b=a_ok), q1,
        val=1000.0 * s1, cbar=cb,
        numbers=[_n("falsearea", "%.1f mm²" % a_false), _n("fixed", "%.1f mm²" % a_ok)]))

    return pv.viewer_spec(
        "poc_cad_scan_deviation", TX.CAD["title"], TX.CAD["subtitle"],
        TX.fmt(TX.CAD["hint"], t=true_um, m=meas_um), tabs)


# --------------------------------------------------------------------------- #
# 2. LiDAR の地形変化                                                            #
# --------------------------------------------------------------------------- #
def build_lidar() -> dict:
    # 実データの置き場は環境変数 FULLSEYE_DATA_DIR で受ける(手元の絶対パスを既定にしない)。
    L = _load("poc_lidar_terrain_change")
    root, why = L.real_data_dir(L.USGS_SUBDIR)
    if root is None:
        raise SystemExit("LiDAR の実データが無い(%s)。合成で代用しない: ビューアを作らない" % why)
    D, why = L.load_forest_park(root)
    if D is None:
        raise SystemExit("LiDAR の実データが読めない(%s)" % why)
    R = _quiet(L.section_real_usgs)
    if R is None:
        raise SystemExit("section_real_usgs が実データを読めなかった")
    box = D["box"]
    G = {}
    for name, _ in L.USGS_EPOCHS:
        P = D["ep"][name]
        g = P["cls"] == 2
        G[name] = L._grid1m(P["E"][g], P["N"][g], P["Z"][g], box)[0]
    dod_raw = G["2017"] - G["2012"]
    valid = np.isfinite(dod_raw)
    ny, nx = dod_raw.shape
    rr, cc = np.nonzero(valid)
    zscale = 3.0
    z17 = G["2017"][valid]
    pos = np.column_stack([cc + 0.5, ny - rr - 0.5, zscale * (z17 - float(z17.mean()))])
    v_raw = dod_raw[valid]
    off_flat, off_full = R["off_flat"], float(v_raw.mean())
    assert abs(R["off_flat"] + 0.183) < 0.002, "平坦部の系統差が −0.183 m でなくなった: %r" % R["off_flat"]
    assert R["n_valid"] == int(valid.sum())
    cb = {"lo": -0.5, "hi": 0.5, "unit": "m", "cmap": "div", "label": TX.LIDAR["cbar"]}
    chc = int(round(R["frac_ch"] * R["n_valid"]))
    base = dict(pos=pos, cbar=cb, point_size=1.8, view={"az": -0.9, "el": 0.75})
    tabs = [
        pv.viewer_points_tab(
            "plain", TX.LIDAR["t_plain"], "null",
            TX.fmt(TX.LIDAR["x_plain"], off=abs(off_flat), n=R["n_valid"], net=R["net_raw"]),
            val=v_raw, numbers=[_n("off", "%+.3f m" % off_flat), _n("cells", "{:,}".format(R["n_valid"])),
                                _n("net", "{:+,.0f} m³".format(R["net_raw"]))], **base),
        pv.viewer_points_tab(
            "flat", TX.LIDAR["t_flat"], "passed",
            TX.fmt(TX.LIDAR["x_flat"], off=off_flat, net=R["net_flat"], nmad=R["nmad"], chc=chc),
            val=v_raw - off_flat, numbers=[_n("net", "{:+,.0f} m³".format(R["net_flat"])),
                                           _n("nmad", "%.3f m" % R["nmad"]), _n("chcells", "{:,}".format(chc))], **base),
        pv.viewer_points_tab(
            "full", TX.LIDAR["t_full"], "limit",
            TX.fmt(TX.LIDAR["x_full"], net=R["net_full"], ch=R["ch_full"]),
            val=v_raw - off_full, numbers=[_n("net", "%+.1f m³" % R["net_full"]),
                                           _n("chnet", "{:+,.0f} m³".format(R["ch_full"]))], **base),
    ]
    credit = {l: L.USGS_CREDIT + " " + TX.LIDAR["credit_mod"][l] for l in ALL_LANGS}
    return pv.viewer_spec(
        "poc_lidar_terrain_change", TX.LIDAR["title"], TX.LIDAR["subtitle"],
        TX.fmt(TX.LIDAR["hint"], off=abs(off_flat)), tabs, credit=credit)


# --------------------------------------------------------------------------- #
# 3. テンプレート追跡                                                            #
# --------------------------------------------------------------------------- #
def build_track() -> dict:
    K = _load("poc_template_tracking")
    rng = np.random.default_rng(20260906)             # main() と同じ種(世界画像の最初の消費)
    world = K.make_world(rng)
    tg = K.TARGETS["一意"]
    lost_px = K.LOST_PX

    def run(mode="static", **kw):
        fr, tr, _, _ = K.make_sequence(world, tg, **kw)
        t0 = K.crop_template(fr[0], tr[0])
        est, pk, pr = K.run_tracker(fr, t0, tr[0], mode)
        return fr, tr, est, pk, pr, K.err_of(est, tr)

    # しきい値は遮蔽なしの実行で校正する(PoC の第 5 章と同じ)
    fr0, tr0, est0, pk0, pr0, e0 = run(n=30, step=2.0)
    thr_pk, thr_pr = float(np.nanmin(pk0[1:])), float(np.nanmin(pr0[1:]))

    def tab(tid, badge, label, text_key, frames, truth, est, peak, prom, e, nums, **fmt_kw):
        lost = e > lost_px
        boxes = [
            {"label": TX.TRACK["b_true"], "color": "#4fc3f7", "xy": truth, "size": [K.TPL, K.TPL]},
            {"label": TX.TRACK["b_est"], "color": "#ffb74d", "xy": est, "size": [K.TPL + 6, K.TPL + 6],
             "flag": lost, "flag_color": "#ff5252", "flag_text": TX.TRACK["b_lost"]},
        ]
        hi_e = float(max(10.0, math.ceil(float(e.max()) / 10.0) * 10.0))
        series = [
            {"label": TX.TRACK["s_pk"], "color": "#ffb74d", "values": peak, "lo": 0.0, "hi": 1.0, "threshold": thr_pk},
            {"label": TX.TRACK["s_pr"], "color": "#ba68c8", "values": prom, "lo": 0.0, "hi": 1.0, "threshold": thr_pr},
            {"label": TX.TRACK["s_err"], "color": "#ef5350", "values": e, "lo": 0.0, "hi": hi_e, "unit": "px", "decimals": 1},
        ]
        return pv.viewer_frames_tab(tid, TX.TRACK[label], badge, TX.fmt(TX.TRACK[text_key], **fmt_kw),
                                    np.asarray(frames), dt=0.2, boxes=boxes, series=series, numbers=nums)

    def counts(pk, e, n):
        m = np.arange(n) >= 3                          # 遮蔽が入るフレームだけ
        nl = int(((e > lost_px) & m).sum())
        ff = int(((e > lost_px) & m & (pk >= thr_pk)).sum())
        return m, nl, ff

    tabs = []
    # (1) 遮蔽なし
    tabs.append(tab("clean", "passed", "t_clean", "x_clean", fr0, tr0, est0, pk0, pr0, e0,
                    [_n("err", "%.2f px" % e0.mean()), _n("pk", "%.3f" % np.nanmean(pk0[1:])),
                     _n("thr", "%.3f" % thr_pk)], err=float(e0.mean())))
    # (2) 平坦な遮蔽物 70 %
    fr, tr, est, pk, pr, e = run(n=30, step=2.0, occl=0.7)
    m, nl, ff = counts(pk, e, 30)
    assert float(np.nanmean(pk[m])) < thr_pk, "平坦な遮蔽物でピークがしきい値を割らなかった"
    tabs.append(tab("flat", "passed", "t_flat", "x_flat", fr, tr, est, pk, pr, e,
                    [_n("err", "%.2f px" % e.mean()), _n("lost", "%d / 27" % nl), _n("pk", "%.3f" % np.nanmean(pk[m])),
                     _n("thr", "%.3f" % thr_pk)], pk=float(np.nanmean(pk[m])), thr=thr_pk, err=float(e.mean()), nl=nl))
    # (3) そっくりな別物体 + 遮蔽 70 %
    fr, tr, est, pk, pr, e = run(n=30, step=2.0, occl=0.7, twin=True)
    m, nl, ff = counts(pk, e, 30)
    assert nl > 0 and ff > 0, "そっくりな別物体で「ずれているのに見つけた」が出なかった"
    tabs.append(tab("twin", "limit", "t_twin", "x_twin", fr, tr, est, pk, pr, e,
                    [_n("err", "%.2f px" % e.mean()), _n("lost", "%d / 27" % nl),
                     _n("falsefound", "%d / %d" % (ff, nl)), _n("pk", "%.3f" % np.nanmean(pk[m])), _n("thr", "%.3f" % thr_pk)],
                    pk=float(np.nanmean(pk[m])), thr=thr_pk, err=float(e.mean()), nl=nl, ff=ff))
    # (4) 毎フレーム更新(ドリフト)と (5) 更新なし —— 同じ映像(第 8 章の条件、種 0)
    kw = dict(n=64, step=1.5, amp=26.0, seed=0)
    fr, tr, est, pk, pr, e = run("update1", **kw)
    m, nl, ff = counts(pk, e, 64)
    nl = int((e > lost_px).sum())
    ff = int(((e > lost_px) & (pk >= thr_pk)).sum())
    assert nl > 0 and ff == nl, "毎フレーム更新が、ずれながらピークを保つ形にならなかった: %r" % ((nl, ff),)
    tabs.append(tab("drift", "limit", "t_drift", "x_drift", fr, tr, est, pk, pr, e,
                    [_n("err", "%.2f px" % e.mean()), _n("lasterr", "%.1f px" % e[-1]),
                     _n("falsefound", "%d / %d" % (ff, nl)), _n("pk", "%.3f" % np.nanmean(pk[1:]))],
                    last=float(e[-1]), mx=float(e.max()), nl=nl, ff=ff, pk=float(np.nanmean(pk[1:])), thr=thr_pk))
    fr, tr, est, pk, pr, e = run("static", **kw)
    tabs.append(tab("static", "null", "t_static", "x_static", fr, tr, est, pk, pr, e,
                    [_n("err", "%.2f px" % e.mean()), _n("lasterr", "%.2f px" % e[-1]), _n("pk", "%.3f" % np.nanmean(pk[1:]))],
                    err=float(e.mean()), last=float(e[-1])))
    return pv.viewer_spec("poc_template_tracking", TX.TRACK["title"], TX.TRACK["subtitle"],
                          TX.fmt(TX.TRACK["hint"], pk=thr_pk, pr=thr_pr), tabs)


# --------------------------------------------------------------------------- #
# 第 2 弾 —— 4 本。数は各 PoC の関数を呼び直して得る(手で写さない)。                #
# --------------------------------------------------------------------------- #
_STOPS = {
    "viridis": [(0.0, (68, 1, 84)), (0.25, (59, 82, 139)), (0.5, (33, 145, 140)), (0.75, (94, 201, 98)),
                (1.0, (253, 231, 37))],
    "div": [(0.0, (33, 102, 172)), (0.5, (247, 247, 247)), (1.0, (178, 24, 43))],
}


def _rgb(a, lo: float, hi: float, name: str = "viridis") -> np.ndarray:
    """値の配列を (…,3) uint8 に塗る(依存を増やさないための小さな色表。NaN は最小の色)。"""
    if not hi > lo:
        raise ValueError("色の範囲が逆: %r %r" % (lo, hi))
    x = np.nan_to_num((np.asarray(a, float) - lo) / (hi - lo), nan=0.0)
    x = np.clip(x, 0.0, 1.0)
    xs = [s[0] for s in _STOPS[name]]
    out = np.stack([np.interp(x, xs, [s[1][c] for s in _STOPS[name]]) for c in range(3)], axis=-1)
    return np.rint(out).astype(np.uint8)


def _gray(a, lo: float, hi: float) -> np.ndarray:
    """値の配列を 0..255 の uint8 の濃淡に(lo 以下が 0、hi 以上が 255)。"""
    if not hi > lo:
        raise ValueError("濃淡の範囲が逆: %r %r" % (lo, hi))
    return np.rint(255.0 * np.clip(np.nan_to_num((np.asarray(a, float) - lo) / (hi - lo)), 0.0, 1.0)).astype(np.uint8)


# --------------------------------------------------------------------------- #
# 4. パルスサーモグラフィ(CFRP 板の内部欠陥の深さ)                                 #
# --------------------------------------------------------------------------- #
def build_thermo() -> dict:
    K = _load("poc_thermography_ndt")
    dm = K.build_scene()
    masks, sound = K.defect_masks(dm)
    ts, cube = K.synth_cube(dm, netd=K.NETD, seed=1)                      # main() と同じ
    d25, _ = K.tsr_depth(ts, cube)
    k4 = int(np.searchsorted(ts, 4.0))
    d4, _ = K.tsr_depth(ts[:k4], cube[:k4])
    _, cube_nb = K.synth_cube(dm, blur=False, netd=K.NETD, seed=1)         # 4 節の対照群(横拡散を切る)
    d_nb, _ = K.tsr_depth(ts, cube_nb)

    def err(d, key):
        return 100.0 * (1e3 * float(np.median(d[masks[key]])) / key[0] - 1.0)

    small = [(d, dia) for d in K.DEPTHS_MM for dia in (2.0, 4.0)]
    e25, e4 = [err(d25, k) for k in small], [err(d4, k) for k in small]
    e_nb = [err(d_nb, k) for k in masks]
    assert max(abs(v) for v in e4) <= 20.0, "窓 4 秒で小さい欠陥が ±20 %% に入らない: %r" % e4
    assert max(e25) > 400.0, "窓 25 秒で +400 %% 超が出ない: %r" % e25
    assert max(abs(v) for v in e_nb) <= 8.0, "横拡散を切っても ±8 %% に入らない: %r" % e_nb
    truth = np.array([k[0] * 1e-3 for k in masks])
    est = np.array([float(np.median(d25[m])) for m in masks.values()])
    z0 = 1e3 * float(np.mean(np.abs(K.L_PLATE / 2 - truth)))
    z1 = 1e3 * float(np.mean(np.abs(est - truth)))
    big = np.array([k[1] >= 8.0 for k in masks])
    b1 = 1e3 * float(np.mean(np.abs(est - truth)[big]))
    s25, s4 = (1e3 * float(np.median(d[sound])) for d in (d25, d4))
    w25, w4 = max(e25), max(e4, key=abs)

    # 映像: 時刻を対数に等間隔に 60 枚(0.05 秒〜25 秒)。毎コマ、健全部の平均を引いて濃淡を伸ばす
    sel = np.unique(np.rint(np.geomspace(1, len(ts) - 1, 60)).astype(int))
    frames = []
    for k in sel:
        c = cube[k] - float(cube[k][sound].mean())
        lo, hi = (float(np.percentile(c, q)) for q in (0.5, 99.5))
        frames.append(_gray(c, lo, hi))
    frames = np.stack(frames)
    ref = cube[sel][:, sound].mean(axis=1)
    c_shallow = cube[sel][:, masks[(0.5, 16.0)]].mean(axis=1) - ref
    c_deep = cube[sel][:, masks[(2.0, 16.0)]].mean(axis=1) - ref
    hi_c = float(math.ceil(max(c_shallow.max(), c_deep.max())))
    tr = TX.THERMO
    series = [
        {"label": tr["s_time"], "color": "#90a4ae", "values": ts[sel], "lo": 0.0, "hi": float(K.T_END),
         "unit": "s", "decimals": 2},
        {"label": tr["s_shallow"], "color": "#ffb74d", "values": c_shallow, "lo": 0.0, "hi": hi_c, "unit": "K",
         "decimals": 2},
        {"label": tr["s_deep"], "color": "#4fc3f7", "values": c_deep, "lo": 0.0, "hi": hi_c, "unit": "K",
         "decimals": 2},
    ]

    def mm(a):
        return _rgb(a * 1e3, 0.0, 3.0)                                      # 深さ [m] → 0〜3 mm の色

    tabs = [
        pv.viewer_frames_tab(
            "video", tr["t_video"], "null", TX.fmt(tr["x_video"], n=len(sel)), frames, dt=0.15, series=series,
            numbers=[_n("th_frames", "%d" % len(sel)), _n("th_netd", "%.0f mK" % (1e3 * K.NETD))]),
        pv.viewer_split_tab(
            "tsr", tr["t_tsr"], "limit", TX.fmt(tr["x_tsr"], z0=z0, z1=z1, b1=b1), mm(dm), mm(d25),
            tr["l_truth"], tr["l_tsr25"],
            numbers=[_n("th_zero", "%.3f mm" % z0), _n("th_all", "%.3f mm" % z1), _n("th_big", "%.3f mm" % b1),
                     _n("th_worst25", "%+.0f %%" % w25)]),
        pv.viewer_split_tab(
            "window", tr["t_window"], "passed", TX.fmt(tr["x_window"], w25=w25, w4=abs(w4), s4=s4, s25=s25),
            mm(d25), mm(d4), tr["l_tsr25"], tr["l_tsr4"],
            numbers=[_n("th_worst25", "%+.0f %%" % w25), _n("th_worst4", "%+.0f %%" % w4),
                     _n("th_sound4", "%.2f mm" % s4)]),
        pv.viewer_split_tab(
            "nodiff", tr["t_nodiff"], "passed", TX.fmt(tr["x_nodiff"], w=max(abs(v) for v in e_nb)), mm(d25), mm(d_nb),
            tr["l_tsr25"], tr["l_nodiff"], numbers=[_n("th_worstnb", "%.1f %%" % max(abs(v) for v in e_nb))]),
    ]
    return pv.viewer_spec("poc_thermography_ndt", tr["title"], tr["subtitle"], tr["hint"], tabs)


# --------------------------------------------------------------------------- #
# 5. 格子干渉計(タルボ絨毯と、吸収では見えない繊維・割れ)                          #
# --------------------------------------------------------------------------- #
def build_talbot() -> dict:
    prev = os.environ.get("FULLSEYE_POC_BUDGET")
    os.environ["FULLSEYE_POC_BUDGET"] = "full"          # CI は reduced(絨毯の z 点が半分)。ビューアは常に full で作る
    try:
        G = _load("poc_grating_interferometry")
    finally:
        if prev is None:
            os.environ.pop("FULLSEYE_POC_BUDGET", None)
        else:
            os.environ["FULLSEYE_POC_BUDGET"] = prev
    _quiet(G.chapter_carpet)
    g = _quiet(G.chapter_source)
    _quiet(G.chapter_coupon, g)
    assert not G.FAILS, "PoC の門が落ちた: %r" % (G.FAILS,)
    c = G.R["carpet"]
    img = c["intensity"].T[::-1]                                            # 縦 = x(2 周期)、横 = z
    z, vis = c["z_mm"], c["visibility"]
    idx = np.unique(np.rint(np.linspace(23, z.size - 1, 20)).astype(int))
    hi_i = float(img.max())
    col = np.arange(img.shape[1])
    car = np.stack([_gray(img * (col <= j), 0.0, hi_i) for j in idx])
    tx = TX.TALBOT
    ser_c = [
        {"label": tx["s_z"], "color": "#90a4ae", "values": z[idx], "lo": 0.0, "hi": float(math.ceil(z[-1])),
         "unit": "mm", "decimals": 0},
        {"label": tx["s_vis"], "color": "#ffb74d", "values": vis[idx], "lo": 0.0, "hi": 1.5,
         "threshold": 4.0 / math.pi, "decimals": 3},
    ]
    k = G.R["coupon"]
    cp, rec, om = k["c"], k["rec"], k["omegas"]
    mat = ~cp["hole"]
    tr0 = rec[0]["transmission"]
    t_lo, t_hi = (float(np.percentile(tr0[mat], q)) for q in (0.5, 99.5))
    best = k["best"]
    cnr_t, cnr_d = k["cnr"]
    df_frames = np.stack([_gray(o["darkfield"], 0.3, 1.05) for o in rec])
    y = np.stack([-np.log(np.clip(o["darkfield"], 1e-3, None)) for o in rec])
    sel = mat & ~cp["crack"] & (cp["iso"] < 0.05)
    cc2 = np.tensordot(np.exp(-2j * om[[0, 2]]), y[[0, 2]], axes=(0, 0))
    th2 = np.mod(-np.angle(-cc2) / 2.0, np.pi)
    dth4 = np.angle(np.exp(2j * (k["theta_hat"] - cp["theta"]))) / 2.0
    dth2 = np.angle(np.exp(2j * (th2 - cp["theta"]))) / 2.0
    diag = sel & (np.abs(np.mod(cp["theta"], np.pi / 2) - np.pi / 4) < np.pi / 8)
    med4 = float(np.rad2deg(np.median(np.abs(dth4[sel]))))
    med4d, med2d = (float(np.rad2deg(np.median(np.abs(x[diag])))) for x in (dth4, dth2))
    assert med2d > 3 * med4d, "2 方位が斜めの繊維を決められないはずが決めた: %r" % ((med2d, med4d),)

    def hsv(theta):
        h = np.mod(theta, np.pi) / np.pi
        return np.rint(255.0 * G._hsv(h, 1.0, mat.astype(float))).astype(np.uint8)

    tabs = [
        pv.viewer_frames_tab(
            "carpet", tx["t_carpet"], "passed",
            TX.fmt(tx["x_carpet"], e=float(G.E_KEV), p=float(G.P1_UM), v=float(vis.max()), n=len(c["self_image_mm"])),
            car, dt=0.25, series=ser_c,
            numbers=[_n("tb_vmax", "%.4f" % vis.max()), _n("tb_fourpi", "%.4f" % (4.0 / math.pi)),
                     _n("tb_zt", "%.0f mm" % c["self_image_mm"][0])]),
        pv.viewer_split_tab(
            "absorb", tx["t_absorb"], "passed", TX.fmt(tx["x_absorb"], ct=cnr_t, cd=cnr_d, deg=float(np.rad2deg(om[best]))),
            _gray(tr0, t_lo, t_hi), _gray(rec[best]["darkfield"], 0.3, 1.05), tx["l_trans"], tx["l_dark"],
            numbers=[_n("tb_cnr_t", "%.2f" % cnr_t), _n("tb_cnr_d", "%.1f" % cnr_d)]),
        pv.viewer_frames_tab(
            "angles", tx["t_angles"], "passed", tx["x_angles"], df_frames, dt=1.2,
            series=[{"label": tx["s_deg"], "color": "#ffb74d", "values": np.rad2deg(om), "lo": 0.0, "hi": 180.0,
                     "unit": "°", "decimals": 0}]),
        pv.viewer_split_tab(
            "fibre4", tx["t_fibre4"], "passed", TX.fmt(tx["x_fibre4"], m=med4), hsv(cp["theta"]), hsv(k["theta_hat"]),
            tx["l_truth"], tx["l_est4"], numbers=[_n("tb_med4", "%.1f°" % med4)]),
        pv.viewer_split_tab(
            "fibre2", tx["t_fibre2"], "limit", TX.fmt(tx["x_fibre2"], m2=med2d, m4=med4d), hsv(cp["theta"]), hsv(th2),
            tx["l_truth"], tx["l_est2"], numbers=[_n("tb_med2", "%.1f°" % med2d), _n("tb_med4d", "%.1f°" % med4d)]),
    ]
    return pv.viewer_spec("poc_grating_interferometry", tx["title"], tx["subtitle"], tx["hint"], tabs)


# --------------------------------------------------------------------------- #
# 6. 位相計測デフレクトメトリ(写真では見えない µm の凹み)                           #
# --------------------------------------------------------------------------- #
def build_deflect() -> dict:
    P = _load("poc_phase_measuring_deflectometry")
    fs, photometric = P.fs, P.photometric
    rig = fs.ledger.deflectometry_rig()
    N = P.N
    X = (np.arange(N) - (N - 1) / 2.0) * rig["field_mm"] / (N - 1)
    XX, YY = np.meshgrid(X, X)
    sp = float(X[1] - X[0])
    h, p, q = P.surface(XX, YY)
    photo = fs.ledger.deflectometry_render(h, rig, kind="softbox", slope_x=p, slope_y=q, noise_sigma=P.NOISE,
                                           bits=P.BITS, seed=7)[0]
    photo_clean = fs.ledger.deflectometry_render(h, rig, kind="softbox", slope_x=p, slope_y=q)[0]
    photo_flat = fs.ledger.deflectometry_render(np.zeros_like(h), rig, kind="softbox")[0]
    sig_photo = float(np.abs(photo_clean - photo_flat).max())
    lsb = 1.0 / (2 ** P.BITS - 1)
    assert sig_photo < lsb, "写真に凹みが 8 bit の 1 段以上で写った: %r" % sig_photo
    n_meas, ph = P.decode(h, p, q, rig, noise_sigma=P.NOISE, bits=P.BITS, seed=1)
    k_map = fs.ledger.slope_to_curvature(n_meas, sp, "mean", P.SIGMA_PX)
    n_kd, _ = P.decode(h, p, q, rig, diffuse_fraction=0.98, noise_sigma=P.NOISE, bits=P.BITS, seed=3)
    k_kd = fs.ledger.slope_to_curvature(n_kd, sp, "mean", P.SIGMA_PX)

    def core(dm):
        return (XX - dm[0]) ** 2 + (YY - dm[1]) ** 2 < (0.25 * dm[3]) ** 2

    far = np.ones_like(h, bool)
    for dm in (P.DIMPLE_A, P.DIMPLE_B):
        far &= (XX - dm[0]) ** 2 + (YY - dm[1]) ** 2 > (4 * dm[3]) ** 2
    far &= ((XX - P.POLISH[0]) / 9.0) ** 2 + ((YY - P.POLISH[1]) / 5.0) ** 2 > 1.0
    far[:8] = far[-8:] = False
    far[:, :8] = far[:, -8:] = False
    k_true = fs.ledger.slope_to_curvature(
        np.dstack([-p, -q, np.ones_like(p)]) / np.sqrt(1 + p * p + q * q)[..., None], sp, "mean", P.SIGMA_PX)
    sd = float(np.nanstd((k_map - k_true)[far]))
    snr_a = float(np.nanmean(k_map[core(P.DIMPLE_A)]) / sd)
    snr_b = float(np.nanmean(k_map[core(P.DIMPLE_B)]) / sd)
    sd_kd = float(np.nanstd((k_kd - k_true)[far]))
    snr_b_kd = float(np.nanmean(k_kd[core(P.DIMPLE_B)]) / sd_kd)
    snr_photo = sig_photo / P.NOISE
    assert snr_a > 30 and snr_b > 8 and snr_photo < 0.25, (snr_a, snr_b, snr_photo)
    assert snr_b_kd < 3.0, "拡散 98 %% でも浅い凹みが雑音の上に立った: %r" % snr_b_kd
    z = P.integrate(n_meas, sp)
    dep_a, dep_a_true = P.depth(z, XX, YY, P.DIMPLE_A), P.depth(h, XX, YY, P.DIMPLE_A)
    dep_b, dep_b_true = P.depth(z, XX, YY, P.DIMPLE_B), P.depth(h, XX, YY, P.DIMPLE_B)
    assert abs(dep_a / dep_a_true - 1) < 0.02 and abs(dep_b / dep_b_true - 1) < 0.03
    rig_wrong = fs.ledger.deflectometry_rig(screen_distance_mm=rig["screen_distance_mm"] * 1.02)
    n_w, _ = P.decode(h, p, q, rig, decode_rig=rig_wrong)
    z_w = P.integrate(n_w, sp)
    dep_w = P.depth(z_w, XX, YY, P.DIMPLE_A)
    assert -0.03 < dep_w / dep_a_true - 1 < -0.01

    fr = [_gray(np.asarray(a), 0.0, 1.0) for a in list(ph["imgx"]) + list(ph["imgy"])]
    fr += [_gray(ph["wx"], -math.pi, math.pi), _gray(ph["wy"], -math.pi, math.pi)]
    kc = 2.0e-3                                                            # 曲率の色の範囲 [1/mm](凹み A の中心 ≈ 2.1e-3)
    hc = 3.0e-3                                                            # 高さの色の範囲 [mm]
    ph8 = _gray(photo, 0.0, 1.0)
    lo, hi = (float(np.percentile(photo, q)) for q in (1, 99))
    tx = TX.DEFLECT
    tabs = [
        pv.viewer_split_tab(
            "photo", tx["t_photo"], "null",
            TX.fmt(tx["x_photo"], s=sig_photo, l=lsb, r=sig_photo / lsb, sn=P.NOISE), ph8, _gray(photo, lo, hi),
            tx["l_photo"], tx["l_stretch"],
            numbers=[_n("df_sig", "%.5f" % sig_photo), _n("df_lsb", "%.5f" % lsb), _n("df_snrp", "%.2f" % snr_photo)]),
        pv.viewer_frames_tab(
            "fringes", tx["t_fringes"], "passed", tx["x_fringes"], np.stack(fr), dt=0.8,
            series=[{"label": tx["s_shot"], "color": "#ffb74d", "values": np.arange(1, len(fr) + 1, dtype=float),
                     "lo": 0.0, "hi": float(len(fr)), "decimals": 0}]),
        pv.viewer_split_tab(
            "curv", tx["t_curv"], "passed", TX.fmt(tx["x_curv"], a=snr_a, b=snr_b, p=snr_photo),
            np.repeat(ph8[..., None], 3, axis=-1),
            _rgb(k_map, -kc, kc, "div"), tx["l_photo"], tx["l_curv"],
            numbers=[_n("df_snra", "%.0f" % snr_a), _n("df_snrb", "%.0f" % snr_b), _n("df_snrp", "%.2f" % snr_photo)]),
        pv.viewer_split_tab(
            "height", tx["t_height"], "passed",
            TX.fmt(tx["x_height"], da=1000 * dep_a, ta=1000 * dep_a_true, db=1000 * dep_b, tb=1000 * dep_b_true),
            _rgb(h - h.mean(), -hc, hc, "div"), _rgb(z - z.mean(), -hc, hc, "div"), tx["l_truth_h"], tx["l_meas_h"],
            numbers=[_n("df_depa", "%.3f µm" % (1000 * dep_a)), _n("df_deptrue", "%.3f µm" % (1000 * dep_a_true)),
                     _n("df_depb", "%.3f µm" % (1000 * dep_b)), _n("df_deptrueb", "%.3f µm" % (1000 * dep_b_true))]),
        pv.viewer_split_tab(
            "diffuse", tx["t_diffuse"], "limit", TX.fmt(tx["x_diffuse"], sb=snr_b, sk=abs(snr_b_kd)),
            _rgb(k_map, -kc, kc, "div"), _rgb(k_kd, -kc, kc, "div"), tx["l_curv"], tx["l_curv_kd"],
            numbers=[_n("df_snrb", "%.0f" % snr_b), _n("df_snrb_kd", "%.1f" % abs(snr_b_kd))]),
        pv.viewer_split_tab(
            "wrongd", tx["t_wrongd"], "limit", TX.fmt(tx["x_wrongd"], d=100 * (dep_w / dep_a_true - 1)),
            _rgb(h - h.mean(), -hc, hc, "div"), _rgb(z_w - z_w.mean(), -hc, hc, "div"), tx["l_truth_h"], tx["l_meas_w"],
            numbers=[_n("df_depw", "%.3f µm" % (1000 * dep_w)),
                     _n("df_depwpct", "%+.1f %%" % (100 * (dep_w / dep_a_true - 1)))]),
    ]
    return pv.viewer_spec("poc_phase_measuring_deflectometry", tx["title"], tx["subtitle"], tx["hint"], tabs)


# --------------------------------------------------------------------------- #
# 7. 小惑星の表面曲率(点群 3000 点。公有の形状モデルから)                          #
# --------------------------------------------------------------------------- #
def build_asteroid() -> dict:
    import curvature3d
    src = ROOT / "studio_assets" / "sample_3d" / "itokawa_points.npy"
    pts = np.load(src).astype(np.float64)
    pts = pts - pts.mean(axis=0)
    rng = np.random.default_rng(0)                                         # itokawa_curvature.py と同じ球
    u = rng.normal(size=(3000, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    R = 100.0
    sphere = u * R
    cv_s = curvature3d.curvedness(sphere, k=25)
    med_s = float(np.median(cv_s))
    assert abs(med_s - 1.0 / R) / (1.0 / R) < 0.15, med_s
    cv = curvature3d.curvedness(pts, k=20)
    si = curvature3d.shape_index(pts, k=20)
    cv6 = curvature3d.curvedness(pts, k=6)
    med = float(np.median(cv))
    high = float(np.mean(cv > 1.5 * med))
    low = float(np.mean(cv < 0.5 * med))
    convex, concave = float(np.mean(si > 0.3)), float(np.mean(si < -0.1))
    from scipy.spatial import cKDTree
    _, nb = cKDTree(pts).query(pts, k=6)
    coh = float(np.corrcoef(cv, cv[nb[:, 1:]].mean(axis=1))[0, 1])
    coh6 = float(np.corrcoef(cv6, cv6[nb[:, 1:]].mean(axis=1))[0, 1])
    assert coh > 0.3 and high > 0 and low > 0
    tx = TX.ASTER
    cb_cv = {"lo": 0.0, "hi": float(np.percentile(cv, 98)), "unit": "1/m", "cmap": "seq", "label": tx["cbar_cv"]}
    cb_si = {"lo": -1.0, "hi": 1.0, "unit": "", "cmap": "div", "label": tx["cbar_si"]}
    cb_s = {"lo": 0.0, "hi": 2.0 / R, "unit": "1/m", "cmap": "seq", "label": tx["cbar_cv"]}
    cb_6 = {"lo": 0.0, "hi": float(np.percentile(cv6, 98)), "unit": "1/m", "cmap": "seq", "label": tx["cbar_cv"]}
    view = {"az": -0.7, "el": 0.45}
    tabs = [
        pv.viewer_points_tab("sphere", tx["t_sphere"], "passed",
                             TX.fmt(tx["x_sphere"], r=R, g=1.0 / R, m=med_s, e=100 * abs(med_s - 1 / R) * R),
                             sphere, val=cv_s, cbar=cb_s,
                             numbers=[_n("as_truth", "%.5f 1/m" % (1.0 / R)), _n("as_meas", "%.5f 1/m" % med_s)]),
        pv.viewer_points_tab("curvedness", tx["t_cv"], "passed",
                             TX.fmt(tx["x_cv"], h=100 * high, l=100 * low, c=coh),
                             pts, val=cv, cbar=cb_cv, view=view,
                             numbers=[_n("as_high", "%.1f %%" % (100 * high)), _n("as_low", "%.1f %%" % (100 * low)),
                                      _n("as_coh", "%.3f" % coh)]),
        pv.viewer_points_tab("shape", tx["t_si"], "passed",
                             TX.fmt(tx["x_si"], cx=100 * convex, cc=100 * concave),
                             pts, val=si, cbar=cb_si, view=view,
                             numbers=[_n("as_convex", "%.1f %%" % (100 * convex)),
                                      _n("as_concave", "%.1f %%" % (100 * concave))]),
        pv.viewer_points_tab("k6", tx["t_k6"], "limit", TX.fmt(tx["x_k6"], c20=coh, c6=coh6),
                             pts, val=cv6, cbar=cb_6, view=view,
                             numbers=[_n("as_coh", "%.3f" % coh), _n("as_coh6", "%.3f" % coh6)]),
    ]
    return pv.viewer_spec("poc_asteroid_curvature", tx["title"], tx["subtitle"], tx["hint"], tabs,
                          credit=tx["credit"])


# --------------------------------------------------------------------------- #
# 第 3 弾 — PoC の公開関数を引数掃引する軽量ビューア 8 本。                       #
# --------------------------------------------------------------------------- #
_SWEEP_TITLE = TX.T("引数を動かして結果を見る", "Sweep a real PoC parameter", "移动参数查看结果",
                    "移動參數查看結果", "매개변수를 움직여 결과 보기", "Einen PoC-Parameter variieren",
                    "PoC पैरामीटर बदलकर परिणाम देखें", "Faire varier un paramètre du PoC")
_SWEEP_SUB = TX.T("各コマは PoC の関数を再実行した結果。", "Every frame is recomputed by the PoC function.",
                  "每帧都由 PoC 函数重新计算。", "每格都由 PoC 函數重新計算。", "각 프레임은 PoC 함수가 다시 계산한다.",
                  "Jedes Bild wird von der PoC-Funktion neu berechnet.", "हर फ़्रेम PoC फ़ंक्शन से फिर गणित होता है।",
                  "Chaque image est recalculée par la fonction du PoC.")
_SWEEP_HINT = TX.T("再生または下のスライダーで引数を動かす。", "Play or drag the slider to change the argument.",
                   "播放或拖动滑块来改变参数。", "播放或拖曳滑桿來改變參數。", "재생하거나 슬라이더로 인수를 바꾼다.",
                   "Abspielen oder den Regler ziehen, um das Argument zu ändern.", "चलाएँ या तर्क बदलने के लिए स्लाइडर खींचें।",
                   "Lancer ou déplacer le curseur pour changer l'argument.")


def _sweep(pid, parameter, unit, values, frames, metric=None):
    vals = np.asarray(values, float)
    fr = np.asarray(frames)
    series = [] if metric is None else [{"label": parameter, "color": "#ffb74d", "values": metric,
                                         "lo": float(np.min(metric)), "hi": float(np.max(metric) + 1e-12), "decimals": 3}]
    tab = pv.viewer_frames_tab("sweep", TX.T("引数の掃引", "Parameter sweep", "参数扫描", "參數掃描", "매개변수 스윕",
                                                    "Parametersuche", "पैरामीटर स्वीप", "Balayage du paramètre"),
                               "passed", _SWEEP_SUB, fr, dt=0.18, series=series, png=True,
                               axis={"values": vals, "segments": [{"k": 0, "label": parameter,
                                                                      "unit": unit, "decimals": 3}]})
    return pv.viewer_spec(pid, _SWEEP_TITLE, _SWEEP_SUB, _SWEEP_HINT, [tab])


def build_focus_sweep():
    P = _load("poc_focus_stacking"); depth, tex = P.ground_truth(size=128, seed=7)
    focus = np.linspace(float(depth.min()), float(depth.max()), 12); vals = np.linspace(2.0, 16.0, 24)
    frames=[]; err=[]
    for v in vals:
        st=P.focal_stack(tex, depth, focus, f_number=float(v), layers=16); fm=P.fm_laplacian(st); fused=P.fuse(st,fm,focus)[0]
        frames.append(_gray(fused,0,1)); err.append(P.rms(fused-tex))
    return _sweep("poc_focus_stacking", TX.T("F値", "f-number", "光圈值", "光圈值", "조리개값", "Blendenzahl", "एफ़-नंबर", "nombre d’ouverture"), "", vals, frames, err)


def build_interferometry_sweep():
    P=_load("poc_interferometry_step"); vals=np.linspace(0.0,0.12,24); frames=[]; err=[]
    for i,v in enumerate(vals):
        _,st=P.make_stack(0.55,float(v),i,dz=P.DZ,n_planes=P.NP)
        measured_step_um, rejected_fraction = P.measure_step(0.55,float(v),i,dz=P.DZ,n_planes=P.NP)
        frames.append(_gray(st[len(st)//2],float(st.min()),float(st.max()))); err.append(abs(float(measured_step_um)-0.55))
    return _sweep("poc_interferometry_step", TX.T("雑音 σ", "noise σ", "噪声 σ", "雜訊 σ", "잡음 σ", "Rauschen σ", "शोर σ", "bruit σ"), "", vals, frames, err)


def build_polarization_sweep():
    P=_load("poc_polarization_specular"); d,l=P.scene(128,160); vals=np.linspace(0,80,25); frames=[]; err=[]
    for v in vals:
        ss,sp=P.specular_components(l,float(v)); raw=P.render_sweep(d,ss,sp); sep=P.separate(raw)
        diffuse=np.asarray(sep[0] if isinstance(sep,tuple) else sep); frames.append(_gray(diffuse,0,0.7)); err.append(P.rmse(diffuse,d))
    return _sweep("poc_polarization_specular", TX.T("入射角", "incidence angle", "入射角", "入射角", "입사각", "Einfallswinkel", "आपतन कोण", "angle d’incidence"), "°", vals, frames, err)


def build_photoelastic_sweep():
    P=_load("poc_photoelasticity"); _,theta,delta=P.build_fields()
    vals=np.linspace(0,135,25); images=[P.polariscope_image(delta,theta,float(v)) for v in vals]
    frames=[_gray(im,0,1) for im in images]; mean_intensity=[float(np.mean(im)) for im in images]
    return _sweep("poc_photoelasticity", TX.T("検光子角", "analyser angle", "检偏器角度", "檢偏器角度", "검광자 각도", "Analysatorwinkel", "विश्लेषक कोण", "angle de l’analyseur"), "°", vals, frames, mean_intensity)


def build_motion_sweep():
    P=_load("poc_motion_magnification"); vals=np.linspace(0.02,0.8,24); base=P.surface(h=128,w=160); frames=[]; amp=[]
    for v in vals:
        clip,disp=P.make_clip([(float(v),P.FREQ,0.0)],t=16,base=base); frames.append(_gray(clip[-1],0,1)); amp.append(P.amp_rms(P.read_dx_oracle(clip)))
    return _sweep("poc_motion_magnification", TX.T("運動振幅", "motion amplitude", "运动振幅", "運動振幅", "운동 진폭", "Bewegungsamplitude", "गति आयाम", "amplitude du mouvement"), "px", vals, frames, amp)


def build_compound_sweep():
    P=_load("poc_compound_eye"); lf,_=P.ommatidial_scene((1.0,),occlusion=False,seed=1); vals=np.geomspace(0.5,16,24); frames=[]; rms=[]
    clean=np.asarray(lf[P.V_C,P.U_C])
    for i,v in enumerate(vals):
        noisy,_,_=P.add_photoreceptor_noise(lf,float(v),seed=i); im=np.asarray(noisy[P.V_C,P.U_C]); frames.append(_gray(im,float(im.min()),float(im.max()))); rms.append(float(np.sqrt(np.mean((im-clean)**2))))
    return _sweep("poc_compound_eye", TX.T("視点ごとのSNR", "per-view SNR", "每视点信噪比", "每視點訊噪比", "시점별 SNR", "SNR je Ansicht", "प्रति-दृश्य SNR", "SNR par vue"), "", vals, frames, rms)


def build_ct_threshold_sweep():
    P=_load("poc_ct_void_morphology"); voids=P.make_voids("sphere","spread","interface"); sc=P.build_scene(voids,voxel=0.06); obs=P.observe(sc["mu"],0.06); vals=np.linspace(0.2,0.8,24); frames=[]; frac=[]
    z=obs.shape[0]//2
    for v in vals:
        m=P.segment(obs,sc["layer"],float(v)); frames.append(np.where(m[z],255,_gray(obs[z],float(obs.min()),float(obs.max())))); frac.append(P.void_fraction(m,sc["layer"]))
    return _sweep("poc_ct_void_morphology", TX.T("しきい値", "threshold", "阈值", "閾值", "임계값", "Schwellenwert", "सीमा", "seuil"), "", vals, frames, frac)


def build_active_sweep():
    P=_load("poc_active_contours"); r=_quiet(P.u_shape); im=np.asarray(r["img"]); history=r["gvf"]["history"]
    picks=np.unique(np.rint(np.linspace(0,len(history)-1,min(24,len(history)))).astype(int)); vals=20*picks; frames=[]; score=[]
    final=np.asarray(history[-1],float)
    for k in picks:
        points=np.asarray(history[k],float); frame=_gray(im,float(im.min()),float(im.max()))
        for row,col in np.rint(points).astype(int):
            frame[max(0,row-1):row+2,max(0,col-1):col+2]=255
        frames.append(frame); score.append(float(np.sqrt(np.mean((points-final)**2))))
    return _sweep("poc_active_contours", TX.T("反復回数", "iterations", "迭代次数", "迭代次數", "반복 횟수", "Iterationen", "पुनरावृत्तियाँ", "itérations"), "", vals, frames, score)


BUILDERS = {
    "poc_cad_scan_deviation": build_cad,
    "poc_lidar_terrain_change": build_lidar,
    "poc_template_tracking": build_track,
    "poc_thermography_ndt": build_thermo,
    "poc_grating_interferometry": build_talbot,
    "poc_phase_measuring_deflectometry": build_deflect,
    "poc_asteroid_curvature": build_asteroid,
    "poc_focus_stacking": build_focus_sweep,
    "poc_interferometry_step": build_interferometry_sweep,
    "poc_polarization_specular": build_polarization_sweep,
    "poc_photoelasticity": build_photoelastic_sweep,
    "poc_motion_magnification": build_motion_sweep,
    "poc_compound_eye": build_compound_sweep,
    "poc_ct_void_morphology": build_ct_threshold_sweep,
    "poc_active_contours": build_active_sweep,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=sorted(BUILDERS), help="1 本だけ作る")
    ap.add_argument("--check", action="store_true", help="書かずに、仕様の検査と HTML の生成だけ行う")
    a = ap.parse_args(argv)
    for pid, fn in BUILDERS.items():
        if a.only and a.only != pid:
            continue
        spec = fn()
        if a.check:
            n = len(pv._build_html(spec, ALL_LANGS).encode("utf-8"))
            print("ok %s: %d tabs, %d bytes (not written)" % (pid, len(spec["tabs"]), n))
        else:
            path = pv.write_viewer(spec, OUT / (pid + ".html"), ALL_LANGS)
            print("wrote %s (%.2f MB, %d tabs)" % (Path(path).relative_to(ROOT).as_posix(),
                                                    Path(path).stat().st_size / 1e6, len(spec["tabs"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
