# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす —— 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g と COD(2026-10-05)。

混合物の粉末に X 線を当てると、検出器には相ごとの同心の環(デバイ環)が重なって写る。新モジュール pxrd(14 op)で、
学習なしに次の連鎖を組む: 標準 Si の環で検出器の中心・距離・傾きを較正 → 方位積分で 2θ のプロファイル → 山の幅から
Scherrer で結晶子径 → 結晶構造から作った参照の辞書で相を 1 つずつ剥がす(貪欲な前進選択の NNLS)→ 残差に残った山を
立方晶として指数付けし、候補の中から未知相を名指しして辞書に足す。背景: 多相の回折パターンの 1 回観測での分解を生成モデルで
解く研究(npj Comput. Mater. 2026、doi:10.1038/s41524-026-02087-w)。ここは同じ問いを物理模型だけで解く。

何が外から来るか:
  * **NIST SRM 640g の証明書**(2024-02-27): Si の格子定数 a = 0.543 110 9 nm(k = 2 の拡張不確かさ 0.000 008 0 nm)と、
    Cu Kα1 λ = 0.154 059 29 nm で計算した線の位置の表 A1(11 本)。Bragg と消滅則でその 11 本を再現するのが最初の門。
  * **COD の CIF**(CC0): NaCl・コランダム・CaF₂・MgO・Al・CeO₂・Si の結晶構造(データがあるとき。無ければ教科書の
    原型の座標で同じ連鎖を回す)。
  * **散乱因子**: Waasmaier & Kirfel 1995 の 5 ガウス近似の係数(DABAX から機械的に写した)。

合成像の真値(既知): 検出器の幾何、重量分率、結晶子径。合成と解析は同じ物理模型を共有するので、ここで閉じているのは
「幾何・画素・雑音・背景・重なりを通り抜けても模型の量が戻るか」まで。散乱強度の模型そのものの正しさは閉形式の門
(消滅則、|F|² の式、f(0) = 電子数、教科書の X 線密度)と NIST の線位置が別の経路で支える。

門(既定、データが無ければ COD を使う門は原型で代える): NIST の 11 本、較正(中心・距離・傾き)、山の位置と格子定数、
Scherrer の径、剥がす順と重量分率、未知相の山・指数・名指し、4 相の分率、罠(傾きの無視、格子のずれ)、図の中身。
--full: 雑音の種を 5 通りに増やして分率の誤差の散らばりを出す。
図(既定の出力先は out/figures/<PoC 名>/、FULLSEYE_FIGURE_DIR で変更): 相が 1 つずつ剥がれる 2-D 検出器の GIF、
最後の色分けの検出器像(等倍)、1-D の当てはめと相ごとの寄与、傾きを無視したときに割れる山、格子のずれの罠の表、
較正と NIST の表。
データの置き場は環境変数 FULLSEYE_PXRD_DATA(PROVENANCE.md のあるディレクトリ。repo にデータは入れない)。
Run: py -3.11 examples/poc_pxrd_phase_peel.py [--full]
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
import pxrd as X  # noqa: E402

FULL = "--full" in sys.argv
LAM = 0.5                                   # Å(約 24.8 keV の単色 X 線)
PIX = 0.2                                   # mm
GEOM = {"cx": 261.3, "cy": 247.8, "distance": 100.0, "pixel": PIX, "wavelength": LAM, "tilt": 3.0, "tilt_dir": -40.0}
SHAPE = (512, 512)
SIZE_TRUE = 350.0                           # Å(35 nm、全相共通)
W_TRUE = {"NaCl": 0.35, "Al2O3": 0.30, "CaF2": 0.20, "MgO": 0.15}
#: NIST SRM 640g の証明書の値(本文から機械的に抜いた。データの門で本文と照合する)
SRM640G_A_NM, SRM640G_U_NM, SRM640G_LAMBDA_NM = 0.5431109, 0.0000080, 0.15405929
SRM640G_TABLE_A1 = [((1, 1, 1), 28.441), ((2, 2, 0), 47.301), ((3, 1, 1), 56.120), ((4, 0, 0), 69.127),
                    ((3, 3, 1), 76.373), ((4, 2, 2), 88.026), ((5, 1, 1), 94.948), ((4, 4, 0), 106.703),
                    ((5, 3, 1), 114.086), ((6, 2, 0), 127.537), ((5, 3, 3), 136.883)]
COD = {"Si": "9008565", "NaCl": "9008678", "Al2O3": "1000032", "CaF2": "2300449", "MgO": "1000053",
       "Al": "9008460", "CeO2": "4343161"}
#: 相の色(Okabe–Ito の色覚に配慮した配色)
COLOURS = {"NaCl": (0.00, 0.45, 0.70), "Al2O3": (0.90, 0.62, 0.00), "CaF2": (0.00, 0.62, 0.45),
           "MgO": (0.80, 0.47, 0.65), "Al": (0.34, 0.71, 0.91), "Si": (0.94, 0.89, 0.26), "CeO2": (0.84, 0.37, 0.00)}
_GATES: list[tuple[str, bool]] = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _data_dir():
    d = os.environ.get("FULLSEYE_PXRD_DATA", "").strip()
    return Path(d) if d and (Path(d) / "cod").is_dir() else None


def load_phases(data):
    """相の辞書: データがあれば COD の CIF、無ければ教科書の原型(コランダムは立方晶でないので Al で代える)。"""
    if data is not None:
        return {nm: X.cif_read(str(data / "cod" / ("%s.cif" % code)), name=nm) for nm, code in COD.items()}, "COD"
    P = {"Si": X.cubic_prototype("diamond", SRM640G_A_NM * 10, ["Si"], name="Si"),
         "NaCl": X.cubic_prototype("rocksalt", 5.6402, ["Na", "Cl"], name="NaCl"),
         "CaF2": X.cubic_prototype("fluorite", 5.4632, ["Ca", "F"], name="CaF2"),
         "MgO": X.cubic_prototype("rocksalt", 4.2117, ["Mg", "O"], name="MgO"),
         "Al": X.cubic_prototype("fcc", 4.0495, ["Al"], name="Al"),
         "CeO2": X.cubic_prototype("fluorite", 5.4110, ["Ce", "O"], name="CeO2")}
    return P, "prototypes"


def decoys():
    """未知相の名指しの候補(辞書に無い立方晶。値は教科書の概数で、真値としては使わない)。"""
    return {"NiO": X.cubic_prototype("rocksalt", 4.1771, ["Ni", "O"], name="NiO"),
            "CaO": X.cubic_prototype("rocksalt", 4.8105, ["Ca", "O"], name="CaO"),
            "KCl": X.cubic_prototype("rocksalt", 6.2917, ["K", "Cl"], name="KCl")}


def profile(image, geom):
    p = X.azimuthal_integrate(image, geom, polarization=0.0)
    ok = np.isfinite(p["intensity"]) & (p["count"] > 0.1 * np.nanmax(p["count"]))
    return p["two_theta"][ok], p["intensity"][ok], p["sigma"][ok]


def geom_of(c):
    return {k: c[k] for k in ("cx", "cy", "distance", "pixel", "wavelength", "tilt", "tilt_dir")}


# ----------------------------------------------------------------------------------------------
# 図の部品
# ----------------------------------------------------------------------------------------------
def plot_panel(series, size, xlim, ylim, title, xlabel="2θ [deg]", ylabel="intensity"):
    """色を相ごとに指定できる折れ線(examplefig の render_plot と同じ部品で、色だけ RGB を許す)。"""
    import fullseye as fs
    w, h = size
    img = np.ones((h, w, 3))
    rect = (72, 44, w - 96, h - 108)
    ax = fs.axes_transform(rect, xlim, ylim)
    xt, yt = fs.nice_ticks(xlim[0], xlim[1], 8), fs.nice_ticks(ylim[0], ylim[1], 4)
    img = np.asarray(fs.grid_lines(img, ax, xticks=xt, yticks=yt, alpha=0.25))
    img = np.asarray(fs.axes_frame(img, ax, width=1))
    img = np.asarray(fs.ticks(img, ax, xticks=xt, yticks=yt, tick_len=5, font_size=10))
    legend = []
    for label, x, y, col in series:
        y = np.clip(np.asarray(y, float), ylim[0], ylim[1])
        img = np.asarray(fs.plot_series(img, ax, np.asarray(x, float), y, kind="line", color=col, width=2))
        if label:
            legend.append((col, label))
    if legend:
        img = np.asarray(fs.legend_box(img, legend, (rect[0] + rect[2] - 6, rect[1] + 6), anchor="rt",
                                       markers=True, font_size=11, swatch=11, pad=6))
    img = np.asarray(fs.text_box(img, title, (10, 8), anchor="lt", font_size=13))
    img = np.asarray(fs.text_box(img, xlabel + "   |   " + ylabel, (10, h - 10), anchor="lb", font_size=11))
    return img


def composite(residual, models, vmax, gamma=0.45):
    """2-D 検出器: 残り(灰)+ 剥がした相(色)。値は全コマ共通の vmax で割る(コマごとに伸ばさない)。"""
    g = np.clip(residual / vmax, 0, 1) ** gamma
    rgb = np.repeat(g[..., None], 3, axis=2) * 0.92
    for name, m, alpha in models:
        c = np.clip(m / vmax, 0, 1) ** gamma * alpha
        col = np.asarray(COLOURS.get(name, (1, 1, 1)), dtype=np.float64)
        rgb = rgb + c[..., None] * (col / col.max())[None, None, :]
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


# ----------------------------------------------------------------------------------------------
def main() -> int:
    t_start = time.time()
    data = _data_dir()
    P, source = load_phases(data)
    mix = ["NaCl", "Al2O3", "CaF2", "MgO"] if source == "COD" else ["NaCl", "Al", "CaF2", "MgO"]
    w_true = np.array([W_TRUE[k] for k in ("NaCl", "Al2O3", "CaF2", "MgO")])
    print("pxrd PoC —— phases from %s%s" % (source, "" if data else " (set FULLSEYE_PXRD_DATA for the COD CIFs)"))

    # 1. NIST SRM 640g
    print("\n[1] NIST SRM 640g: Bragg + extinction rules reproduce the certificate's line table")
    si_cert = X.cubic_prototype("diamond", SRM640G_A_NM * 10, ["Si"])
    r = X.powder_reflections(si_cert, SRM640G_LAMBDA_NM * 10, two_theta_max=140.0)
    got = {tuple(int(v) for v in h): t for h, t in zip(r["hkl"], r["two_theta"])}
    want = dict(SRM640G_TABLE_A1)
    err = max(abs(got.get(h, 1e9) - want[h]) for h in want)
    gate("NIST 640g: the 11 certified lines and no others up to 140 deg", set(got) == set(want) and err <= 6e-4,
         "(max |d2theta| %.5f deg; table is rounded to 0.001)" % err)
    nist_rows = [["%d%d%d" % h, "%.3f" % t, "%.4f" % got[h], "%+.4f" % (got[h] - t)] for h, t in SRM640G_TABLE_A1]

    # 2. 標準 Si で較正
    print("\n[2] calibrate the detector on the Si standard (tilt %.1f deg)" % GEOM["tilt"])
    # 標準は SRM 640g そのもの(証明書の a)。辞書の Si(COD なら 1963 年の a = 5.4307 Å)とは別に持つ
    srm = X.cubic_prototype("diamond", SRM640G_A_NM * 10, ["Si"], name="Si (SRM 640g)")
    std = X.debye_ring_image([srm], [1.0], GEOM, shape=SHAPE, counts=3e4, seed=21)
    d_si = X.powder_reflections(srm, LAM, 40.0)["d"]
    t0 = time.time()
    cal = X.detector_calibrate(std["image"], d_si, {"pixel": PIX, "wavelength": LAM})
    dc = math.hypot(cal["cx"] - GEOM["cx"], cal["cy"] - GEOM["cy"])
    gate("calibration: centre / distance / tilt", cal["ok"] and dc < 0.05 and abs(cal["distance"] / GEOM["distance"] - 1) < 2e-4
         and abs(cal["tilt"] - GEOM["tilt"]) < 0.05 and abs(cal["tilt_dir"] - GEOM["tilt_dir"]) < 2.0,
         "(centre %.3f px, distance %+.4f %%, tilt %.3f deg, dir %.2f deg, rms %.4f deg, %d rings, %.2f s)"
         % (dc, 100 * (cal["distance"] / GEOM["distance"] - 1), cal["tilt"], cal["tilt_dir"], cal["rms_two_theta_deg"],
            cal["n_rings"], time.time() - t0))
    g = geom_of(cal)
    xs, ys, ss = profile(std["image"], g)
    pks = X.diffraction_peaks(xs, ys, noise=ss)
    ix = X.cubic_index(pks["two_theta"], LAM, max_unindexed=1)
    a_si = srm["cell"][0]
    tt_true = X._two_theta_deg(a_si / np.sqrt(ix["N"]), LAM) if ix["lattice"] else np.zeros(1)
    perr = float(np.max(np.abs(ix["two_theta"] - tt_true))) if ix["lattice"] else 1e9
    # ★a の門 5e-5 の余裕(組み込み時 2026-10-06 に雑音の種を 12 通りずつ振って実測): 誤差は雑音でなく較正の系統で決まり、
    # この像(傾き 3°・向き −40°)では +3.0〜+4.1e-5(種 21 は +3.8e-5)。種による散らばりは ±0.5e-5 程度で、24 通りの最大は |4.2e-5|。
    # 種は固定なので結果は決定的。門を締めると系統の偏りに当たり、緩める理由も無いので 5e-5 のまま。
    gate("Si standard: diamond lattice, a and the peak positions",
         ix["lattice"] == "diamond" and abs(ix["a"] / a_si - 1) < 5e-5 and perr < 0.01,
         "(a = %.5f vs %.5f A, %d lines, max |d2theta| %.4f deg = %.2f px)"
         % (ix["a"], a_si, len(ix["N"]), perr, perr / math.degrees(PIX / GEOM["distance"])))
    inst = (pks["two_theta"], pks["fwhm"])
    cal_rows = [["centre x [px]", "%.2f" % GEOM["cx"], "%.3f" % cal["cx"]],
                ["centre y [px]", "%.2f" % GEOM["cy"], "%.3f" % cal["cy"]],
                ["distance [mm]", "%.3f" % GEOM["distance"], "%.4f" % cal["distance"]],
                ["tilt [deg]", "%.2f" % GEOM["tilt"], "%.4f" % cal["tilt"]],
                ["tilt direction [deg]", "%.1f" % GEOM["tilt_dir"], "%.2f" % cal["tilt_dir"]],
                ["Si lattice a [A]", "%.5f" % a_si, "%.5f" % ix["a"]]]

    # 3. 混合物
    print("\n[3] the mixture: %s (wt %%: %s), crystallites %.0f A" % (", ".join(mix), ", ".join("%.0f" % (100 * w) for w in w_true), SIZE_TRUE))
    seeds = (31, 32, 33, 34, 35) if FULL else (31,)
    results = []
    for sd in seeds:
        results.append(run_mixture(P, mix, w_true, g, inst, sd, figures=(sd == seeds[0])))
    res = results[0]
    gate("Scherrer: crystallite size from the mixture's own peaks", abs(res["size_est"] / SIZE_TRUE - 1) < 0.10,
         "(%.0f A from %d peaks, truth %.0f A)" % (res["size_est"], res["n_size"], SIZE_TRUE))
    gate("peel: the three dictionary phases in the mixture, and nothing else", sorted(res["order"]) == sorted(mix[:3]),
         "(order %s, rwp %s)" % (" > ".join(res["order"]), " > ".join("%.3f" % v for v in res["rwp"])))
    e3 = np.abs(res["w3"] - w_true[:3] / w_true[:3].sum())
    gate("3-phase weight fractions (normalised to the known phases)", float(e3.max()) < 0.015,
         "(max error %.2f wt%%: %s)" % (100 * e3.max(), ", ".join("%s %.1f" % (k, 100 * v) for k, v in zip(mix[:3], res["w3"]))))
    gate("unknown phase: residual peaks indexed as cubic F", res["unk_lattice"] == "F" and res["n_unk"] >= 5
         and abs(res["unk_a"] / P["MgO"]["cell"][0] - 1) < 5e-4,
         "(%d peaks, a = %.4f A vs %.4f A)" % (res["n_unk"], res["unk_a"], P["MgO"]["cell"][0]))
    gate("unknown phase named among candidates (MgO, NiO, CaO, KCl)", res["named"] == "MgO",
         "(lattice filter kept %s; rwp %s)" % (res["kept"], ", ".join("%s %.4f" % kv for kv in res["cand_rwp"].items())))
    e4 = np.abs(res["w4"] - w_true)
    gate("4-phase weight fractions after adding the named phase", float(e4.max()) < 0.015,
         "(max error %.2f wt%%: %s)" % (100 * e4.max(), ", ".join("%s %.1f" % (k, 100 * v) for k, v in zip(mix, res["w4"]))))
    if FULL:
        all_e = np.array([np.abs(r_["w4"] - w_true) for r_ in results])
        print("    --full: %d noise seeds, 4-phase error mean %.2f / max %.2f wt%%" % (len(seeds), 100 * all_e.mean(), 100 * all_e.max()))

    # 4. 罠 1: 傾きの無視
    print("\n[4] trap: integrate the tilted detector as if it were flat")
    xb, yb, sb = profile(std["image"], dict(g, tilt=0.0))
    bad = X.diffraction_peaks(xb, yb, noise=sb)
    gate("trap (tilt ignored): rings become ellipses, the peaks split", len(bad["two_theta"]) > 1.5 * len(pks["two_theta"])
         and bad["fwhm"][0] > 1.5 * pks["fwhm"][0],
         "(%d peaks instead of %d, 111 FWHM %.3f vs %.3f deg)" % (len(bad["two_theta"]), len(pks["two_theta"]), bad["fwhm"][0], pks["fwhm"][0]))

    # 5. 罠 2: 格子のずれ
    print("\n[5] trap: the sample's lattice is a little larger than the reference's")
    lat_rows, lat_ok = lattice_trap(P, mix, g, inst)
    gate("trap (lattice +0.4 %): fractions collapse without refinement, return with it", lat_ok,
         "(see the table)")

    # 6. 模型の取り違えの効き(正直に: 合成と辞書が同じ模型だと分率は出来すぎる)
    print("\n[6] how much a wrong model costs (synthesis and dictionary share the physics, so first measure the leaks)")
    sens_rows, sens = model_sensitivity(P, mix, g, inst)
    if source != "COD":
        print("    (the ions case is vacuous here: the textbook prototypes are neutral atoms; set FULLSEYE_PXRD_DATA)")
    gate("model mismatch: a wrong width costs more than a wrong peak shape or ionic vs neutral atoms",
         sens["width"] > 2 * max(sens["same"], 1e-3) and sens["shape"] < 1.0 and sens["ions"] < 1.0,
         "(max error wt%%: same %.2f, shape %.2f, ions %.2f, width -29 %% %.2f)" % (sens["same"], sens["shape"], sens["ions"], sens["width"]))

    # 7. 図
    if figs.enabled():
        make_figures(res, std, g, xs, ys, xb, yb, pks, bad, nist_rows, cal_rows, lat_rows, sens_rows)
        n_fig = len(figs.manifest())
        gate("figures written and not empty", n_fig >= 6 and not figs.errors(), "(%d files, errors %r)" % (n_fig, figs.errors()))

    # 7. 中身と所要
    gate("outputs are finite and non-constant", all(np.all(np.isfinite(a)) and np.ptp(a) > 0 for a in
                                                  (std["image"], res["image"], res["y"], res["fit4"])), "")
    el = time.time() - t_start
    # ★40 s は手元(19-22 s)の 2 倍で決めていたが、CI の py3.10 の走者で 41.6 s に
    #   なり落ちた(2026-10-11、ほかの 13 門は全部 ok)。走者は手元の約 2 倍遅いので 3 倍の 60 s に。
    gate("run time", el < (120 if FULL else 60), "(%.1f s)" % el)
    n_ok = sum(ok for _, ok in _GATES)
    print("\n%d / %d gates passed" % (n_ok, len(_GATES)))
    # test_poc_scripts_run は stdout の「PASS」の行を合格の印として見る(exit 0 だけでは通さない)
    print("PASS" if n_ok == len(_GATES) else "FAIL")
    return 0 if n_ok == len(_GATES) else 1


def run_mixture(P, mix, w_true, g, inst, seed, figures=False):
    im = X.debye_ring_image([P[k] for k in mix], w_true, GEOM, shape=SHAPE, size=SIZE_TRUE, counts=3e4, seed=seed)
    x, y, s = profile(im["image"], g)
    # 結晶子径: 混合物の強い山の FWHM から(装置の幅は標準 Si の表で引く)
    pk = X.diffraction_peaks(x, y, noise=s)
    m = (pk["two_theta"] > inst[0][0]) & (pk["two_theta"] < inst[0][-1]) & (pk["snr"] > 40) & pk["fit_ok"]
    w_inst = np.interp(pk["two_theta"][m], *inst)
    m2 = pk["fwhm"][m] > 1.05 * w_inst
    Ls = X.scherrer_size(pk["fwhm"][m][m2], pk["two_theta"][m][m2], LAM, instrumental_fwhm=w_inst[m2])
    size_est = float(np.median(Ls))
    names = ["Si", "NaCl", "Al2O3" if "Al2O3" in mix else "Al", "CaF2", "CeO2"] + (["Al"] if "Al2O3" in mix else [])
    dic = X.phase_dictionary([P[k] for k in names], x, LAM, size=size_est, instrumental_fwhm=inst)
    pe = X.phase_peel(x, y, dic, sigma=s)
    f3 = pe["final"]
    w3 = np.array([dict(zip(f3["names"], f3["weight_fraction"]))[k] for k in mix[:3]])
    u = X.unexplained_peaks(f3, noise=s)
    idx = u["index"] or {"lattice": None, "a": float("nan")}
    # 名指し: 同じ格子で a が 0.3 % 以内の候補を残し、辞書に足して当て直し、rwp が最小のもの
    cands = dict(decoys())
    cands["MgO"] = P["MgO"]
    kept, cand_rwp = [], {}
    for nm, ph in cands.items():
        a_c = ph["cell"][0]
        lat = {"rocksalt": "F"}.get(ph["source"].get("prototype", ""), "F")
        if idx["lattice"] == lat and abs(a_c / idx["a"] - 1) < 3e-3:
            kept.append(nm)
        dic4 = X.phase_dictionary([P[k] for k in mix[:3]] + [ph], x, LAM, size=size_est, instrumental_fwhm=inst)
        cand_rwp[nm] = X.phase_fractions(x, y, dic4, sigma=s)["rwp"]
    pool = kept or list(cands)
    named = min(pool, key=lambda k: cand_rwp[k])
    dic4 = X.phase_dictionary([P[k] for k in mix[:3]] + [cands[named]], x, LAM, size=size_est, instrumental_fwhm=inst)
    f4 = X.phase_fractions(x, y, dic4, sigma=s)
    out = {"image": im["image"], "x": x, "y": y, "s": s, "size_est": size_est, "n_size": int(m2.sum()),
           "order": pe["order"], "rwp": [st["rwp"] for st in pe["stages"]], "w3": w3, "unk_lattice": idx["lattice"],
           "unk_a": idx["a"], "n_unk": int((~u["near_known"]).sum()), "kept": kept, "cand_rwp": cand_rwp, "named": named,
           "w4": f4["weight_fraction"], "fit4": f4["fit"], "f4": f4, "pe": pe, "u": u, "mix": mix,
           "dic4_rows": dict(zip(dic4["names"], dic4["matrix"]))}
    if figures:
        out["models2d"] = models_2d(P, mix[:3] + [named] if named in P else mix[:3], cands, f4, g, size_est)
    return out


def models_2d(P, names, cands, f4, g, size_est):
    """当てはめた倍率で相ごとの 2-D の像と背景を描く(図の素材)。"""
    out = {}
    for nm, sc in zip(f4["names"], f4["scale"]):
        ph = P.get(nm) or cands[nm]
        im = X.debye_ring_image([ph], [1.0], g, shape=SHAPE, size=size_est, instrumental_fwhm=0.02, counts=None,
                                background=0.0)
        out[nm] = sc * im["per_phase"][0]
    tt = X.detector_two_theta(SHAPE, g)
    bg = np.interp(tt["two_theta"], f4["two_theta"], f4["background"]) * tt["solid_angle"]
    out["_background"] = bg
    return out


def lattice_trap(P, mix, g, inst):
    rows, ok = [], True
    names = mix[:3]
    w = np.array([0.5, 0.3, 0.2])
    for strain in (0.0, 0.002, 0.004):
        im = X.debye_ring_image([P[k] for k in names], w, GEOM, shape=SHAPE, size=SIZE_TRUE, counts=3e4, seed=41,
                                lattice_scales=[1 + strain, 1, 1])
        x, y, s = profile(im["image"], g)
        dic = X.phase_dictionary([P[k] for k in names], x, LAM, size=SIZE_TRUE, instrumental_fwhm=inst)
        f0 = X.phase_fractions(x, y, dic, sigma=s)
        f1 = X.phase_fractions(x, y, dic, sigma=s, lattice_tolerance=0.01)
        rows.append(["%+.1f %%" % (100 * strain), "%.1f" % (100 * f0["weight_fraction"][0]), "%.3f" % f0["rwp"],
                     "%.1f" % (100 * f1["weight_fraction"][0]), "%.4f" % f1["lattice_scale"][0], "%.3f" % f1["rwp"]])
        if strain == 0.004:
            ok = f0["weight_fraction"][0] < 0.35 and abs(f1["weight_fraction"][0] - 0.5) < 0.01
    return rows, ok


def model_sensitivity(P, mix, g, inst):
    """合成と辞書の模型をわざと食い違わせて、分率の誤差がどれだけ増えるかを測る(3 相、既知の相だけ)。"""
    import copy
    names = mix[:3]
    w = np.array([0.4, 0.35, 0.25])
    rows, out = [], {}
    cases = [("same", "same model", {}, None, {}),
             ("shape", "synthesis 30 % Lorentzian tails, dictionary Gaussian", {"eta": 0.3}, None, {}),
             ("ions", "dictionary neutral atoms (synthesis uses the CIF ions)", {}, "neutral", {}),
             ("width", "dictionary crystallites 250 A (truth 350 A)", {}, None, {"size": 250.0})]
    for key, label, skw, dmode, dkw in cases:
        im = X.debye_ring_image([P[k] for k in names], w, GEOM, shape=SHAPE, size=SIZE_TRUE, counts=3e4, seed=51, **skw)
        x, y, s = profile(im["image"], g)
        dp = [P[k] for k in names]
        if dmode == "neutral":
            dp = copy.deepcopy(dp)
            for ph in dp:
                for at in ph["atoms"]:
                    at["type"] = X._element(at["type"])
        kw = {"size": SIZE_TRUE, "instrumental_fwhm": inst}
        kw.update(dkw)
        f = X.phase_fractions(x, y, X.phase_dictionary(dp, x, LAM, **kw), sigma=s)
        e = float(100 * np.max(np.abs(f["weight_fraction"] - w)))
        out[key] = e
        rows.append([label, " / ".join("%.1f" % (100 * v) for v in f["weight_fraction"]), "%.2f" % e, "%.3f" % f["rwp"]])
    return rows, out


def make_figures(res, std, g, xs, ys, xb, yb, pks, bad, nist_rows, cal_rows, lat_rows, sens_rows):
    mod = res["models2d"]
    img = res["image"]
    bg = mod["_background"]
    order = res["pe"]["order"] + [n for n in res["f4"]["names"] if n not in res["pe"]["order"]]
    vmax = 0.6 * float(np.quantile(np.clip(img - bg, 0, None), 0.998))
    x, y = res["x"], res["y"]
    f4 = res["f4"]
    frames = []
    ylim = (0.0, float(np.quantile(y - f4["background"], 0.999)) * 1.05)
    xlim = (float(x[0]), float(x[-1]))
    stages = [[]] + [order[:k] for k in range(1, len(order) + 1)]
    labels = ["observed (background removed)"] + ["+ %s%s" % (order[k - 1], "  (named from the residual)" if order[k - 1] not in res["pe"]["order"] else "")
                                                  for k in range(1, len(order) + 1)]
    prof_by = {nm: sc * res["dic4_rows"][nm] for nm, sc in zip(f4["names"], f4["scale"])}   # 倍率 × 辞書の行
    for si_, (sel, lab) in enumerate(zip(stages, labels)):
        prev = stages[si_ - 1] if si_ > 0 else []
        new = [n for n in sel if n not in prev]
        steps = (0.0,) if si_ == 0 else (0.25, 0.5, 0.75, 1.0)
        for a in steps:
            removed = sum((mod[n] for n in prev), np.zeros(SHAPE)) + sum((a * mod[n] for n in new), np.zeros(SHAPE))
            resid = img - bg - removed
            models = [(n, mod[n], 1.0) for n in prev] + [(n, mod[n], a) for n in new]
            det = composite(resid, models, vmax)
            series = [("residual", x, y - f4["background"] - sum((prof_by[n] for n in prev), np.zeros_like(x))
                       - sum((a * prof_by[n] for n in new), np.zeros_like(x)), (0.35, 0.35, 0.35))]
            series += [(n, x, prof_by[n] * (1.0 if n in prev else a), COLOURS.get(n, (1, 0, 1))) for n in prev + new]
            pan = plot_panel(series, (SHAPE[1], 300), xlim, ylim, "stage %d: %s" % (si_, lab))
            frame = np.concatenate([det, (np.clip(pan, 0, 1) * 255).astype(np.uint8)], axis=0)
            frames.append(frame)
        for _ in range(4 if si_ < len(stages) - 1 else 10):          # 段ごとに止める
            frames.append(frames[-1])
    figs.save_gif("phase_peel", frames, caption="2-D detector: the phases are peeled off one at a time "
                  "(grey = what is still unexplained; colours = identified phases). Bottom: the azimuthally "
                  "integrated profile and each phase's contribution. The last ring set is named from the residual.", fps=6)
    final = composite(img - bg - sum((mod[n] for n in order), np.zeros(SHAPE)), [(n, mod[n], 1.0) for n in order], vmax)
    figs.save("detector_by_phase", final, caption="the detector image coloured by phase (1:1 pixels, lossless PNG)")
    raw = composite(img - bg, [], vmax)
    figs.save("detector_observed", raw, caption="the observed detector image (background removed, gamma 0.5)")
    series = [("observed", x, y, (0.2, 0.2, 0.2)), ("fit", x, f4["fit"], (0.85, 0.1, 0.1))]
    series += [(n, x, prof_by[n] + f4["background"], COLOURS.get(n, (1, 0, 1))) for n in f4["names"]]
    series += [("residual", x, f4["residual"] + 0.0, (0.5, 0.5, 0.5))]
    yl = (float(np.min(f4["residual"])), float(np.quantile(y, 0.999)) * 1.05)
    figs.save("profile_fit", (np.clip(plot_panel(series, (1100, 460), xlim, yl, "4-phase NNLS fit (rwp %.3f)" % f4["rwp"]), 0, 1) * 255).astype(np.uint8),
              caption="integrated profile, NNLS fit and each phase's contribution")
    lo, hi = 13.5, 18.5
    m1, m2 = (xs > lo) & (xs < hi), (xb > lo) & (xb < hi)
    trap = plot_panel([("tilt solved", xs[m1], ys[m1], (0.0, 0.45, 0.70)), ("tilt ignored", xb[m2], yb[m2], (0.84, 0.37, 0.0))],
                      (900, 380), (lo, hi), (0.0, float(max(ys[m1].max(), yb[m2].max())) * 1.05),
                      "Si standard, detector tilted %.1f deg: two rings integrated" % GEOM["tilt"])
    figs.save("trap_tilt_ignored", (np.clip(trap, 0, 1) * 255).astype(np.uint8),
              caption="integrating a tilted detector as if flat turns each ring into an ellipse and splits the peak")
    figs.save_table("trap_lattice_mismatch", ["NaCl strain", "NaCl wt% (no refine)", "rwp", "NaCl wt% (refined)", "lattice scale", "rwp"],
                    lat_rows, title="reference lattice vs sample lattice (truth: NaCl 50 wt%)")
    figs.save_table("model_mismatch", ["case", "wt% (truth 40 / 35 / 25)", "max error wt%", "rwp"], sens_rows,
                    title="what a wrong model costs")
    figs.save_table("calibration", ["quantity", "truth", "calibrated"], cal_rows, title="detector calibration on the Si standard")
    figs.save_table("nist_srm640g", ["hkl", "certificate 2theta", "computed", "difference"], nist_rows,
                    title="NIST SRM 640g table A1 vs Bragg")


if __name__ == "__main__":
    raise SystemExit(main())
