#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の「触って見る」3 本のビューアを作る(1 つの入口で 3 本とも)。

    py -3.11 tools/build_view2026_viewers.py              # docs/view2026/viewers/*.html を書く
    py -3.11 tools/build_view2026_viewers.py --only poc_template_tracking
    py -3.11 tools/build_view2026_viewers.py --check      # 書かずに、命令が通ることと配列の健全さを検査

数字は **手で写さない**。各 PoC の関数を import して(または同じ計算をやり直して)得た値だけを使う:

* ``poc_cad_scan_deviation``  —— ``CadRef`` / ``section_align`` / ``make_scan`` / ``align``
* ``poc_lidar_terrain_change`` —— ``load_forest_park`` / ``_grid1m`` / ``section_real_usgs``(USGS 3DEP)
* ``poc_template_tracking``   —— ``make_world`` / ``make_sequence`` / ``run_tracker``

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
    os.environ.setdefault(DATA_ENV, "C:/dev/data")
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


BUILDERS = {
    "poc_cad_scan_deviation": build_cad,
    "poc_lidar_terrain_change": build_lidar,
    "poc_template_tracking": build_track,
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
            n = len(pv.build_html(spec, ALL_LANGS).encode("utf-8"))
            print("ok %s: %d tabs, %d bytes (not written)" % (pid, len(spec["tabs"]), n))
        else:
            path = pv.write_viewer(spec, OUT / (pid + ".html"), ALL_LANGS)
            print("wrote %s (%.2f MB, %d tabs)" % (Path(path).relative_to(ROOT).as_posix(),
                                                    Path(path).stat().st_size / 1e6, len(spec["tabs"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
