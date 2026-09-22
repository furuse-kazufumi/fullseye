# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 高さは 2 つある・実データ編 —— 公開されている測量成果 523 点で、高さの取り違えを検出器にかける

合成(``poc_geodetic_height_frames``)では「楕円体高と標高を混ぜると 30〜40 m ずれる」を**自分で作った数字**で示した。
ここは同じ主張を**公開された測量成果**で確かめる回である。使うのは NOAA/NGS(米国測地測量局)の datasheet で、
1 つの基準点について

* 楕円体高 ``h``(NAD 83(2011)、epoch 2010.00)—— GNSS が返す高さ
* 正標高 ``H``(NAVD 88)—— 地図と設計図が使う高さ
* ジオイド高 ``N``(GEOID18)
* 地心直交座標 ``(x, y, z)``

の 4 つが**全部公開されている**。この 4 つが揃うと、こちらの op の答えを合成値と比べるのではなく、
**他人が測って公開した値**と比べられる。コロラド州フロントレンジ(ロッキーの縁。ジオイドの勾配が大きいので、
補間の誤差が「出るなら出る」場所)から 523 点。

分かったこと(どれもこの PoC が数える):

1. **既存 op は公開値と 1 mm 以内で合う。** ``dem_geodetic_to_ecef`` が返す ``(x, y, z)`` は NGS の公開値と
   rms 0.5 mm・最大 0.8 mm。これまでこの op は「自分との往復」しか測っていなかった —— 往復は実装が
   一貫していることしか言わないので、**外の値と比べるまで正しさの証拠にはならない**。
2. **粗い格子を引く誤りは、モデルを 1 世代取り違える誤りより大きい。** 0.25 度の GEOID18 格子を
   ``dem_geoid_height`` で双一次補間した値と、同じ点の公開値の差は rms 11.1 cm。いっぽう GEOID18 と
   一世代前の GEOID12B のモデル差は同じ格子上で平均 −1.0 cm(幅 −9.8〜+6.3 cm)。**格子を細かくするほうが、
   モデルを新しくするより先に効く。**
3. **格子の外は拒否する。** 523 点のうち 15 点は格子の外に落ちた。端の値で埋めれば例外は出ないが、
   外挿した undulation は測量値ではない。``dem_geoid_height`` はここで止まる。
4. **取り違えは −N に張り付く。** 楕円体高をそのまま標高の列に入れると、残差の中央値は 16.75 m
   (この地域の −N)。桁で間違うのではなく、**全部が同じだけ**ずれるので、数字を見ただけでは気づけない。
5. ★**残差は測量の等級を、言われないまま並べ替える。** ``dem_height_frame_residual`` は成果の由来
   (どう測ったか)を 1 文字も読まない。それでも ``|h - H - N|`` の中央値は
   水準測量 < 網調整 < GPS 観測 < VERTCON3(モデルによる基準換算)の順に並ぶ。
   **基準が噛み合っているかを数えるだけで、由来の弱い点が浮く。**

図:
1. ``residual_sorted``: 523 点の ``|h - H - N|`` を小さい順に。許容 0.1 m の線と、どこから超えるか。
2. ``by_provenance``: 由来ごとの中央値と最大値(op は由来を読んでいない)。
3. ``misuse``: 正しい組と取り違えた組を、``N`` に対して並べる —— 取り違えは ``-N`` の直線に乗る。
4. ``geoid_grid``: GEOID18 の格子(疑似カラー)と、補間に使った基準点の位置。
5. ``interp_error``: 補間誤差と、その点での格子の勾配。誤差が大きいのは勾配が大きいところ。
6. ``model_shift``: GEOID18 − GEOID12B(格子上のモデル差)。
7. ``ecef_mm``: 公開 ``(x, y, z)`` とこちらの ``dem_geodetic_to_ecef`` の差[mm]。
8. ``enu_map``: 523 点を局所 ENU に載せた地図(色 = 標高)と、地球の丸みで沈む量。
9. ``numbers``: 数表。

データ: ``examples/data/ngs_geodetic_benchmarks_2026_09_22.json`` = 公開 datasheet から作った**集計だけ**
(点ごとに 10 列 + ジオイド格子 2 枚)。生データ(タイル 54 枚)は commit しない。
出典: NOAA / National Geodetic Survey(米国政府の公開成果)。
走らせ方: ``py -3.11 examples/poc_geodetic_benchmarks_real.py``(図は ``out/figures/poc_geodetic_benchmarks_real/``)。
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

L = fs.ledger
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "ngs_geodetic_benchmarks_2026_09_22.json")


def load():
    d = json.load(io.open(DATA, encoding="utf-8"))
    m = d["marks"]
    cols = {k: np.asarray(v) for k, v in m.items() if k != "pid"}
    cols["pid"] = list(m["pid"])
    for k in ("lat_deg", "lon_deg", "h_ellipsoidal_m", "h_orthometric_m",
              "geoid_height_m", "x_m", "y_m", "z_m"):
        cols[k] = cols[k].astype(np.float64)
    cols["source_code"] = cols["source_code"].astype(int)
    return d, cols


def grid_of(d, key="geoid_grid"):
    g = d[key]
    ref = d["geoid_grid"]
    return (np.asarray(g["undulation_m"], dtype=np.float64),
            float(ref["lat0_deg"]), float(ref["lon0_deg"]),
            float(ref["dlat_deg"]), float(ref["dlon_deg"]))


def inside(lat, lon, grid, lat0, lon0, dla, dlo):
    la1 = lat0 + dla * (grid.shape[0] - 1)
    lo1 = lon0 + dlo * (grid.shape[1] - 1)
    return (lat >= lat0) & (lat <= la1) & (lon >= lon0) & (lon <= lo1)


def main():
    figs.reset()
    d, c = load()
    lat, lon = c["lat_deg"], c["lon_deg"]
    h, H, N = c["h_ellipsoidal_m"], c["h_orthometric_m"], c["geoid_height_m"]
    xyz = np.stack([c["x_m"], c["y_m"], c["z_m"]], axis=1)
    n_all = len(lat)
    checks = []

    def ck(name, ok):
        checks.append((name, bool(ok)))

    print("== 公開されている測量成果 ==")
    print("   出所 %s / %s, %s" % (d["source"], d["geoid_model"], d["region"]))
    print("   点の数 %d(楕円体高 %s・正標高 %s・ジオイド高・地心直交座標が全部公開されている点だけ)"
          % (n_all, d["pos_datum"], d["vert_datum"]))
    print("   標高 %.1f〜%.1f m / ジオイド高 %.2f〜%.2f m" % (H.min(), H.max(), N.min(), N.max()))
    ck("523 点そろっている", n_all == 523)

    # ------------------------------------------------------------------ #
    # 1 章 公開値どうしがどれだけ噛み合っているか(h - H - N)               #
    # ------------------------------------------------------------------ #
    print()
    print("== 1 章 公開値の残差 h - H - N ==")
    res = L.dem_height_frame_residual(h, H, N)
    r = np.asarray(res["residual_m"], dtype=np.float64)
    print("   rms %.4f m / 中央値 %+.4f m / 最大 %.4f m / 許容 %.2f m を超えた点 %d/%d"
          % (res["rms_m"], res["median_m"], res["max_abs_m"], res["tol_m"],
             res["n_over_tol"], res["n"]))
    print("   —— 公開値どうしでも**ぴったり 0 ではない**。NAVD 88(水準の基準)と GEOID18(重力の基準)は")
    print("      別に作られていて、その食い違いがこの残差として出る。桁は cm。")
    ck("公開値の残差は cm 台(0 ではないが 0.2 m 未満)", 0.0 < res["rms_m"] < 0.2)
    ck("残差の中央値はほぼ 0(1 cm 未満)", abs(res["median_m"]) < 0.01)

    # 基準どおりに変換したら定義そのものに戻ること
    conv = np.asarray(L.dem_height_frame_convert(h, N, "ellipsoidal", "orthometric"))
    ck("h -> H の変換は定義 h-N そのもの", np.abs(conv - (h - N)).max() == 0.0)
    back = np.asarray(L.dem_height_frame_convert(conv, N, "orthometric", "ellipsoidal"))
    ck("H -> h で戻る(丸めの分だけ)", np.abs(back - h).max() < 1e-9)

    order = np.argsort(np.abs(r))
    figs.save_plot("residual_sorted",
                   [("|h - H - N| [m]", np.arange(n_all, dtype=float), np.abs(r)[order]),
                    ("tolerance 0.1 m", np.arange(n_all, dtype=float), np.full(n_all, res["tol_m"]))],
                   xlabel="benchmark, sorted by residual", ylabel="metres",
                   title="published survey marks: how well h, H and N agree",
                   caption=("%d NGS marks, each publishing ellipsoidal height h (NAD 83), orthometric height H "
                            "(NAVD 88) and geoid height N (GEOID18). The residual h - H - N is not exactly zero: "
                            "NAVD 88 and GEOID18 were built from different measurements, and the mismatch shows up "
                            "here at the centimetre level (rms %.3f m, median %+.3f m). %d of %d marks exceed 0.1 m"
                            % (n_all, res["rms_m"], res["median_m"], res["n_over_tol"], res["n"])))

    # ------------------------------------------------------------------ #
    # 2 章 残差は測量の等級を、言われないまま並べ替える                       #
    # ------------------------------------------------------------------ #
    print()
    print("== 2 章 op は由来を読んでいないのに、由来の順に並ぶ ==")
    labels = d["source_labels"]
    rows2, bar_x, bar_med, bar_max = [], [], [], []
    stat = []
    for code, name in enumerate(labels):
        sel = c["source_code"] == code
        if sel.sum() < 4:                       # 数点しかない等級は順位の主張に使わない
            continue
        med = float(np.median(np.abs(r[sel])))
        mx = float(np.abs(r[sel]).max())
        stat.append((name, int(sel.sum()), med, mx))
    stat.sort(key=lambda t: t[2])
    for k, (name, n, med, mx) in enumerate(stat):
        print("   %-22s n=%3d  中央 |残差| %.4f m  最大 %.4f m" % (name, n, med, mx))
        rows2.append([name, "%d" % n, "%.4f" % med, "%.4f" % mx])
        bar_x.append(float(k)); bar_med.append(med); bar_max.append(mx)
    names = [s[0] for s in stat]
    lev = [i for i, s in enumerate(stat) if "LEVELING" in s[0]]
    vc = [i for i, s in enumerate(stat) if "VERTCON3" in s[0]]
    gps = [i for i, s in enumerate(stat) if "GPS OBS" in s[0]]
    ck("水準測量が最良の側にある", bool(lev) and lev[0] <= 1)
    ck("VERTCON3(モデル換算)が最悪", bool(vc) and vc[0] == len(stat) - 1)
    ck("水準・網調整が GPS 観測より良い", bool(gps) and bool(lev) and lev[0] < gps[0])
    print("   —— 検出器は 'ADJUSTED' や 'VERTCON3' という文字を 1 度も見ていない。")
    print("      それでも順番は測量の等級どおりになる(水準 < 網調整 < GPS < モデル換算)。")

    figs.save_plot("by_provenance",
                   [("median |residual| [m]", np.array(bar_x), np.array(bar_med)),
                    ("max |residual| [m]", np.array(bar_x), np.array(bar_max))],
                   kinds=["bar", "scatter"],
                   xlabel="provenance class, sorted by median", ylabel="metres",
                   title="the residual sorts the marks by how they were surveyed",
                   caption=("dem_height_frame_residual reads only the three height columns — never the metadata "
                            "saying how each mark was measured. Sorting the classes by median |h - H - N| "
                            "reproduces the survey hierarchy anyway: %s. VERTCON3 is a modelled datum conversion, "
                            "not an observation, and it lands last (max %.2f m)"
                            % (" < ".join(names), stat[-1][3])))

    # ------------------------------------------------------------------ #
    # 3 章 取り違えたらどう見えるか                                        #
    # ------------------------------------------------------------------ #
    print()
    print("== 3 章 楕円体高をそのまま標高として使う ==")
    bad = L.dem_height_frame_residual(h, h, N)
    rb = np.asarray(bad["residual_m"], dtype=np.float64)
    print("   残差の中央値 %+.3f m(= -N の中央値 %+.3f m)/ 許容超え %d/%d"
          % (bad["median_m"], -float(np.median(N)), bad["n_over_tol"], bad["n"]))
    print("   —— GNSS の高さを地図の高さとして使うと、この地域では全部が同じだけ持ち上がる。")
    ck("取り違えの残差は -N に一致する", np.abs(rb + N).max() < 1e-9)
    ck("取り違えは全点が許容を超える", bad["fraction_over_tol"] == 1.0)
    ck("そのずれは 15〜20 m(この地域の -N)", 15.0 < abs(bad["median_m"]) < 20.0)

    figs.save_plot("misuse",
                   [("published h, H, N [m]", N, r), ("h used as H [m]", N, rb),
                    ("the line -N", N, -N)],
                   kinds=["scatter", "scatter", "line"],
                   xlabel="geoid height N at the mark [m]", ylabel="residual h - H - N [m]",
                   title="a height-frame mix-up does not look like an outlier",
                   caption=("left cloud near zero: the published triples. The other cloud is the same marks with "
                            "the ellipsoidal height put into the orthometric column — every point lands exactly on "
                            "the line -N (median %+.2f m here). Nothing is out of range, nothing raises an "
                            "exception; the whole table is simply %.1f m too high"
                            % (bad["median_m"], abs(bad["median_m"]))))

    # ------------------------------------------------------------------ #
    # 4 章 公開ジオイド格子を引く —— 格子の外は拒否する                      #
    # ------------------------------------------------------------------ #
    print()
    print("== 4 章 ジオイド格子を引く ==")
    grid, lat0, lon0, dla, dlo = grid_of(d)
    print("   格子 %dx%d、%.2f 度刻み、undulation %.3f〜%.3f m"
          % (grid.shape[0], grid.shape[1], dla, grid.min(), grid.max()))
    refused = None
    try:
        L.dem_geoid_height(grid, lat, lon, lat0, lon0, dla, dlo)
    except ValueError as exc:
        refused = str(exc)
    print("   全 523 点をそのまま渡すと: %s" % (refused.split(" — ")[0] if refused else "(通ってしまった)"))
    ck("格子の外を渡すと拒否される", refused is not None and "outside the grid" in refused)

    ins = inside(lat, lon, grid, lat0, lon0, dla, dlo)
    print("   格子の内側 %d 点 / 外側 %d 点(端の値で埋めれば例外は出ないが、外挿した undulation は測量値ではない)"
          % (int(ins.sum()), int((~ins).sum())))
    ck("外に落ちる点が実際にある", 0 < int((~ins).sum()) < n_all)

    got = np.asarray(L.dem_geoid_height(grid, lat[ins], lon[ins], lat0, lon0, dla, dlo))
    err = got - N[ins]
    rms = float(np.sqrt((err ** 2).mean()))
    print("   補間 vs 公開の GEOID18: rms %.4f m / 最大 %.4f m" % (rms, np.abs(err).max()))
    ck("補間誤差は 0.2 m 未満", rms < 0.2)
    ck("だが機械精度ではない(公開点は格子点ではない)", rms > 1e-3)

    figs.save("geoid_grid", grid, gray=False, signed=False,
              caption=("the published GEOID18 undulation on a %.2f-degree grid over the Colorado Front Range "
                       "(%.2f to %.2f m, %dx%d nodes). dem_geoid_height interpolates it bilinearly at each "
                       "benchmark; %d of %d marks fall outside and are refused rather than clamped to the edge"
                       % (dla, grid.min(), grid.max(), grid.shape[0], grid.shape[1],
                          int((~ins).sum()), n_all)))

    # 誤差はどこで大きいか —— その点での格子の勾配で説明する
    gy, gx = np.gradient(grid, dla, dlo)
    slope = np.hypot(gy, gx)
    ri = np.clip(((lat[ins] - lat0) / dla).astype(int), 0, grid.shape[0] - 1)
    ci = np.clip(((lon[ins] - lon0) / dlo).astype(int), 0, grid.shape[1] - 1)
    loc = slope[ri, ci]
    figs.save_plot("interp_error",
                   [("|interpolation error| [m]", loc, np.abs(err))], kinds=["scatter"],
                   xlabel="local geoid slope of the grid [m per degree]", ylabel="metres",
                   title="where interpolating a coarse grid costs you",
                   caption=("each point is one benchmark inside the grid: the error of bilinear interpolation "
                            "against the value published at that same point, against how steep the geoid is "
                            "there. rms %.3f m, worst %.3f m — the cost is not random, it grows with curvature, "
                            "which is why the closed-form bound |d2N| d^2 / 8 is the right way to state it"
                            % (rms, np.abs(err).max())))

    # ------------------------------------------------------------------ #
    # 5 章 モデルを 1 世代取り違えるのと、粗い格子を引くのはどちらが重いか       #
    # ------------------------------------------------------------------ #
    print()
    print("== 5 章 モデル世代の差 ==")
    g12, _, _, _, _ = grid_of(d, "geoid_grid_previous_model")
    dm = grid - g12
    print("   GEOID18 - GEOID12B(同じ格子): 平均 %+.4f m / 幅 %+.4f〜%+.4f m"
          % (dm.mean(), dm.min(), dm.max()))
    print("   粗い格子の補間誤差 rms %.4f m のほうが大きい —— **格子を細かくするほうが先に効く。**" % rms)
    ck("モデル差は 0.1 m 未満", np.abs(dm).max() < 0.1)
    ck("補間誤差がモデル差の中央より大きい", rms > float(np.median(np.abs(dm))))

    figs.save("model_shift", dm, signed=True,
              caption=("GEOID18 minus GEOID12B on the same nodes: mean %+.3f m, range %+.3f to %+.3f m. "
                       "Revising the geoid model by a generation moves the answer less than interpolating a "
                       "0.25-degree grid does (rms %.3f m), so grid spacing is the first thing to fix"
                       % (dm.mean(), dm.min(), dm.max(), rms)))

    # ------------------------------------------------------------------ #
    # 6 章 既存 op を外の値と突き合わせる(往復ではなく)                     #
    # ------------------------------------------------------------------ #
    print()
    print("== 6 章 地心直交座標を公開値と比べる ==")
    mine = np.asarray(L.dem_geodetic_to_ecef(lat, lon, h))
    de = np.linalg.norm(mine - xyz, axis=1)
    print("   dem_geodetic_to_ecef vs NGS の公開 (x,y,z): rms %.4f mm / 最大 %.4f mm"
          % (1e3 * float(np.sqrt((de ** 2).mean())), 1e3 * de.max()))
    print("   —— この op はこれまで『自分との往復』しか測っていなかった。往復は実装が一貫していることしか")
    print("      言わない。**外の値と比べるまで、正しさの証拠にはならない。**")
    ck("公開 ECEF と 1 mm 以内で一致", de.max() < 1e-3)
    # 公開座標は mm 刻みで丸められている。緯度 1e-8 度 = 1.1 mm なので、
    # 逆変換の一致はこの**データの床**より良くはならない(丸めが先に効く)。
    floor_deg = 0.001 / (6378137.0 * np.pi / 180.0)
    dlat = float(np.abs(np.asarray(L.dem_ecef_to_geodetic(xyz))[:, 0] - lat).max())
    print("   公開 (x,y,z) から緯度に戻すと最大 %.2e 度ずれる —— 公開座標の mm 丸めが作る床 %.2e 度の内側"
          % (dlat, floor_deg))
    ck("逆変換は公開座標の mm 丸めの床の内側", dlat < floor_deg)

    figs.save_plot("ecef_mm",
                   [("|ours - published| [mm]", np.sort(1e3 * de),
                     np.arange(n_all, dtype=float) / n_all)],
                   kinds=["line"],
                   xlabel="distance to the published ECEF coordinate [mm]",
                   ylabel="fraction of marks at or below",
                   title="the existing op, checked against someone else's numbers",
                   caption=("dem_geodetic_to_ecef run on the published latitude, longitude and ellipsoidal "
                            "height of %d NGS marks, compared with the Cartesian coordinates NGS publishes for "
                            "the same marks: rms %.2f mm, worst %.2f mm. Until now this op was only checked "
                            "against its own inverse, which tests consistency, not correctness"
                            % (n_all, 1e3 * float(np.sqrt((de ** 2).mean())), 1e3 * de.max())))

    # ------------------------------------------------------------------ #
    # 7 章 局所 ENU に載せる —— 地図になり、地球の丸みが見える                #
    # ------------------------------------------------------------------ #
    print()
    print("== 7 章 局所 ENU ==")
    i0 = int(np.argmin((lat - np.median(lat)) ** 2 + (lon - np.median(lon)) ** 2))
    la0, lo0, h0 = float(lat[i0]), float(lon[i0]), float(h[i0])
    enu = np.asarray(L.dem_enu_from_geodetic(lat, lon, h, la0, lo0, h0))
    rt = np.asarray(L.dem_geodetic_from_enu(enu, la0, lo0, h0))
    print("   基準点 %s(%.5f, %.5f, %.2f m)。東西 %.1f km / 南北 %.1f km に広がる"
          % (c["pid"][i0], la0, lo0, h0,
             (enu[:, 0].max() - enu[:, 0].min()) / 1e3,
             (enu[:, 1].max() - enu[:, 1].min()) / 1e3))
    print("   往復の床: 緯度 %.2e 度 / 経度 %.2e 度 / 高さ %.2e m"
          % (np.abs(rt[:, 0] - lat).max(), np.abs(rt[:, 1] - lon).max(), np.abs(rt[:, 2] - h).max()))
    ck("基準点そのものは厳密に原点", np.abs(enu[i0]).max() == 0.0)
    ck("ENU の往復は 1e-9 度 / 1e-5 m 以内", np.abs(rt[:, 0] - lat).max() < 1e-9
       and np.abs(rt[:, 2] - h).max() < 1e-5)

    # 別経路(既存の ECEF op を手で回す)と一致すること
    x0 = np.asarray(L.dem_geodetic_to_ecef(la0, lo0, h0))[0]
    p, q = np.radians(la0), np.radians(lo0)
    sp, cp, sl, cl = np.sin(p), np.cos(p), np.sin(q), np.cos(q)
    R = np.array([[-sl, cl, 0.0], [-sp * cl, -sp * sl, cp], [cp * cl, cp * sl, sp]])
    alt = (mine - x0) @ R.T
    print("   別経路(dem_geodetic_to_ecef を経由)との差 最大 %.2e m" % np.abs(alt - enu).max())
    ck("ENU は別経路と一致する", np.abs(alt - enu).max() < 1e-6)

    # 地球の丸み —— 水平に離れた点は up が負に沈む
    hor = np.hypot(enu[:, 0], enu[:, 1])
    flat = enu[:, 2] - (h - h0)                  # 高さの差を引くと、残るのは丸みの落差
    far = hor > 20e3
    print("   20 km より遠い %d 点では、高さの差を引いても up が平均 %.1f m 沈む(地球の丸み)"
          % (int(far.sum()), float(flat[far].mean())))
    ck("遠い点は丸みで沈む(負)", float(flat[far].mean()) < -10.0)
    for km, want in ((10.0, -7.8), (100.0, -783.0)):
        dlat = np.degrees(km * 1000.0 / 6371000.0)
        up = float(np.asarray(L.dem_enu_from_geodetic([la0 + dlat], [lo0], [h0], la0, lo0, h0))[0, 2])
        ck("%d km で丸みの落差 %.0f m" % (km, want), abs(up - want) < 0.06 * abs(want))

    figs.save_plot("enu_map",
                   [("benchmarks, east-north [km]", enu[:, 0] / 1e3, enu[:, 1] / 1e3)],
                   kinds=["scatter"],
                   xlabel="east of %s [km]" % c["pid"][i0], ylabel="north [km]",
                   title="the same marks on a local ENU frame",
                   caption=("%d marks placed in the east-north-up frame of one of them (%s). The reference mark "
                            "is exactly the origin, the round trip back to latitude and longitude closes to "
                            "%.0e degrees, and the frame agrees with the independent route through "
                            "dem_geodetic_to_ecef to %.0e m. Points more than 20 km out sink an average of "
                            "%.0f m below the tangent plane — that is the curvature of the Earth, not an error"
                            % (n_all, c["pid"][i0], np.abs(rt[:, 0] - lat).max(),
                               np.abs(alt - enu).max(), abs(float(flat[far].mean())))))

    # ------------------------------------------------------------------ #
    # 8 章 測地成果を乗り換える                                           #
    # ------------------------------------------------------------------ #
    print()
    print("== 8 章 datum の乗り換え(既定値を置かない) ==")
    same = np.asarray(L.dem_datum_shift_3param(lat, lon, h, 0.0, 0.0, 0.0,
                                               6378137.0, 1.0 / 298.257223563,
                                               6378137.0, 1.0 / 298.257223563))
    ck("0 の平行移動は恒等写像", np.abs(same[:, 0] - lat).max() < 1e-12
       and np.abs(same[:, 2] - h).max() < 1e-6)
    moved = np.asarray(L.dem_datum_shift_3param(lat, lon, h,
                                                -146.414, 507.337, 680.507,
                                                6377397.155, 1.0 / 299.152813,
                                                6378137.0, 1.0 / 298.257223563))
    me = np.asarray(L.dem_enu_from_geodetic(moved[:, 0], moved[:, 1], moved[:, 2], la0, lo0, h0))
    shift = np.hypot(me[:, 0] - enu[:, 0], me[:, 1] - enu[:, 1])
    print("   ベッセル楕円体 + 3 パラメータで乗り換えると、同じ緯度経度が地上で %.0f〜%.0f m 動く"
          % (shift.min(), shift.max()))
    ck("実在の 3 パラメータでは数百 m 動く", 100.0 < float(shift.mean()) < 2000.0)
    print("   —— だからこの op はパラメータに既定値を置かない。黙って仮定すると")
    print("      『例外は出ないが数百 m ずれた座標』が出る。")

    # ------------------------------------------------------------------ #
    # 数表                                                              #
    # ------------------------------------------------------------------ #
    rows = [
        ["marks with the full chain", "%d" % n_all, "NGS datasheet, GEOID18"],
        ["published residual h-H-N, rms", "%.4f m" % res["rms_m"], "not zero: NAVD 88 vs GEOID18"],
        ["published residual, median", "%+.4f m" % res["median_m"], "centred"],
        ["over 0.1 m", "%d / %d" % (res["n_over_tol"], res["n"]), "mostly modelled conversions"],
        ["h used as H, median", "%+.3f m" % bad["median_m"], "= -N, every point"],
        ["marks outside the geoid grid", "%d" % int((~ins).sum()), "refused, not clamped"],
        ["bilinear vs published N, rms", "%.4f m" % rms, "0.25-degree grid"],
        ["bilinear vs published N, max", "%.4f m" % float(np.abs(err).max()), "steep geoid"],
        ["GEOID18 - GEOID12B", "%+.4f m" % dm.mean(), "range %+.3f..%+.3f" % (dm.min(), dm.max())],
        ["ECEF vs published, rms", "%.3f mm" % (1e3 * float(np.sqrt((de ** 2).mean()))), "external check"],
        ["ECEF vs published, max", "%.3f mm" % (1e3 * de.max()), "external check"],
        ["ENU round trip, latitude", "%.1e deg" % float(np.abs(rt[:, 0] - lat).max()), "floor"],
        ["ENU vs ECEF route", "%.1e m" % float(np.abs(alt - enu).max()), "independent route"],
        ["3-parameter datum shift", "%.0f m" % float(shift.mean()), "mean ground movement"],
    ]
    for name, n, med, mx in stat:
        rows.append(["  |residual| by %s" % name, "%.4f m" % med, "n=%d, max %.3f m" % (n, mx)])
    figs.save_table("numbers", ["quantity", "value", "note"], rows,
                    title="height frames, checked against published survey results",
                    caption=("every number here comes from NGS's own published values for %d marks in the "
                             "Colorado Front Range; nothing is synthetic" % n_all))

    print()
    for name, ok in checks:
        print("  [%s] %s" % ("ok" if ok else "NG", name))
    nbad = [n for n, ok in checks if not ok]
    if nbad:
        print("FAIL: %d check(s) did not hold: %s" % (len(nbad), nbad))
        raise SystemExit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
