# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 三枚玉の製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする。

新 op 8 本(`lenstol`, `opsoptics` の `tolerancing`)を使う実行例。公開処方の三枚玉に、
曲率・厚み・屈折率・アッベ数・偏心・傾き・面の非点不整・くさび・群偏心を割り当てる。
行ごとの独立な乱数、分布ごとの解析分散、Wilson 95 % 区間、失敗光線の明示、補償後の
移動量を報告する。図の数値はこの実行で得た値だけを使う。

呼び出し例::

    table = tolerance_table(system, defaults={"radius_pct": 0.1})
    criteria = tolerance_criteria(mtf={"frequency_cpmm": 50, "min": 0.2})
    run = tolerance_monte_carlo(system, table, criteria, trials=2000, seed=7)

【外部真値】薄いプリズム f(n-1)alpha、非点 Zernike の RMS 1/sqrt(6)、分布の閉形式分散、
二項比率の Wilson 区間。【学習】0。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lenstol as LT  # noqa: E402
import raytrace as RT  # noqa: E402

CI = bool(os.environ.get("CI"))
FAILS = []
NUMBERS = {}


def gate(name, ok, detail=""):
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, " — " + detail if detail else ""))
    if not ok:
        FAILS.append(name)


def triplet():
    radii = [22.01359, -435.76044, -22.21328, 20.29192, 79.68360, -18.39533]
    thick = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, 42.20778]
    media = [(1.62041, 60.32), 1.0, (1.62004, 36.37), 1.0, (1.62041, 60.32), 1.0]
    aps = [4.0, 4.8, 5.2, 5.6, 7.2, 7.4]
    return RT.lens_system([{"R": r, "t": t, "n": n, "ap": a}
                           for r, t, n, a in zip(radii, thick, media, aps)],
                          stop=0, field=8.0, image_mm=thick[-1])


def budget(system, distribution="uniform", scale=1.0):
    rows = LT.tolerance_table(system, defaults={
        "radius_pct": {"tolerance": 0.08 * scale, "distribution": distribution},
        "thickness_mm": {"tolerance": 0.015 * scale, "distribution": distribution},
        "decenter_mm": {"tolerance": 0.008 * scale, "distribution": distribution},
        "tilt_deg": {"tolerance": 0.015 * scale, "distribution": distribution},
    })
    rows += LT.tolerance_table(system, defaults={}, overrides=[
        {"kind": "wedge_arcmin", "surface": 1, "tolerance": 0.5 * scale, "distribution": distribution},
        {"kind": "irregularity_fringes", "surface": 2, "tolerance": 0.2 * scale,
         "distribution": distribution},
        {"kind": "group_decenter_mm", "surfaces": [2, 3], "tolerance": 0.006 * scale,
         "distribution": distribution},
    ])
    return rows


def criteria(system):
    return LT.tolerance_criteria(rms_spot={"max": 0.055}, mtf={"frequency_cpmm": 50.0, "min": 0.08},
                                 fields=[0.0], wavelengths=[system["wavelength_um"]], rings=3, psf_size=32)


def closed_form_gates(system):
    print("\n1. 閉形式")
    prism = RT.lens_system([{"R": math.inf, "t": 2.0, "n": 1.5, "ap": 5.0},
                            {"R": math.inf, "t": 10.0, "n": 1.0, "ap": 5.0},
                            {"f": 50.0, "t": 50.0, "n": 1.0, "ap": 5.0}], image_mm=50.0)
    row = LT._normalise_row(prism, {"kind": "wedge_arcmin", "surface": 1, "tolerance": 1.0}, 0)
    got = abs(RT.chief_ray(LT._apply_row(prism, row, 1.0), 0.0)["image_y"])
    want = 50.0 * 0.5 * math.radians(1 / 60)
    gate("薄いくさびの像移動 = f(n-1)alpha (0.5 %)", abs(got / want - 1) < 0.005,
         "%.9f / %.9f mm" % (got, want))
    NUMBERS.update(wedge_actual=got, wedge_closed=want)

    row = LT._normalise_row(system, {"kind": "irregularity_fringes", "surface": 0,
                                     "tolerance": 1.0}, 0)
    pert = LT._apply_row(system, row, 1.0)
    a, b = RT.opd_samples(system, size=65), RT.opd_samples(pert, size=65)
    valid = a[3] & b[3]
    got = float(np.std(b[2][valid] - a[2][valid]))
    want = (system["surfaces"][0]["n_value"] - system["index_object"]) / (2 * math.sqrt(6))
    gate("1 fringe の非点不整の実光線 OPD RMS = (n'-n)/(2 sqrt(6)) (2 %)",
         abs(got / want - 1) < 0.02, "%.6f / %.6f waves" % (got, want))
    NUMBERS.update(irregularity_actual=got, irregularity_closed=want)


def run_analysis(system):
    print("\n2. 感度・Monte Carlo・補償")
    tab = budget(system)
    note_lines = LT.tolerance_table_zmx(tab)
    roundtrip = LT.tolerance_table_from_zmx(system, note_lines)
    gate("公差表の NOTE 行は書く・読むで不動点", roundtrip == tab)
    crit = criteria(system)
    sens = LT.tolerance_sensitivity(system, tab, crit, allowed_degradation={"mtf": 0.02})
    n = 16 if CI else 160
    base = LT.tolerance_monte_carlo(system, tab, crit, trials=n, seed=271)
    comp = LT.compensators(["t5", "t3"], criterion="rms_spot", iterations=3)
    after = LT.tolerance_monte_carlo(system, tab, crit, compensators=comp, trials=8 if CI else 60, seed=271)
    print(LT.tolerance_report(base, sens))
    print("   内部間隔と像面の補償: yield %.3f -> %.3f" % (base["yield"], after["yield"]))
    gate("ヒストグラムの度数は成功試行数", all(sum(v["histogram"]["counts"]) == n - base["failed_trials"]
                                                   for v in base["criteria"].values()))
    gate("Wilson 区間が観測歩留まりを含む", base["yield_wilson95"][0] <= base["yield"] <= base["yield_wilson95"][1])
    NUMBERS.update(yield_before=base["yield"], yield_after=after["yield"], trials=n)
    return tab, crit, sens, base, after


def distribution_and_rebudget(system, tab, crit, sens):
    print("\n3. 分布と再配分")
    n = 12 if CI else 100
    runs = {}
    for d in ("uniform", "normal", "truncated_normal"):
        runs[d] = LT.tolerance_monte_carlo(system, budget(system, d), crit, trials=n, seed=91)
        print("   %-16s yield %.3f" % (d, runs[d]["yield"]))
    tight_id = sens["drivers"][0]["id"]
    cheap = {q["id"] for q in sens["drivers"][-max(1, len(sens["drivers"]) // 4):]}
    new = []
    for r in tab:
        q = dict(r)
        q["tolerance"] *= 0.55 if q["id"] == tight_id else (1.35 if q["id"] in cheap else 1.0)
        new.append(q)
    rebudget = LT.tolerance_monte_carlo(system, new, crit, trials=n, seed=92)
    print("   再配分(%s を締め、安い行を緩める): yield %.3f" % (tight_id, rebudget["yield"]))
    NUMBERS.update(yield_uniform=runs["uniform"]["yield"], yield_normal=runs["normal"]["yield"],
                   yield_truncated=runs["truncated_normal"]["yield"], yield_rebudget=rebudget["yield"])
    return runs, rebudget, tight_id


def _hist(stat, title, units, limit=None):
    h = stat["histogram"]
    x = 0.5 * (np.asarray(h["edges"][:-1]) + np.asarray(h["edges"][1:]))
    series = [("試行", x, h["counts"])]
    if limit is not None:
        ymax = max(h["counts"] or [1])
        series.append(("限界", [limit, limit], [0, ymax]))
    return figs.render_plot(series, title=title, size=(640, 430), kinds=["bar"] + (["line"] if limit is not None else []),
                            colors=["reference", "wrong"], xlabel=units, ylabel="count")


def figures(system, tab, crit, sens, base, after, distributions, rebudget, tight_id):
    drivers = sens["drivers"][:10]
    y = [q["std_contribution"]["mtf"] for q in drivers]
    bars = [(q["id"], [0.0, v], [i, i]) for i, (q, v) in enumerate(zip(drivers, y))]
    figs.save("sensitivity", figs.render_plot(bars, title="Sorted sensitivity | top %.3g MTF" % y[0],
              size=(1280, 680), kinds=["line"] * len(bars), colors=["wrong"] + ["reference"] * (len(bars)-1),
              xlabel="standard-deviation contribution [MTF at 50 cycles/mm]", ylabel="sorted tolerance row"),
              caption="感度上位 10 行。首位は %s。" % drivers[0]["id"])
    figs.save("histograms", np.concatenate([_hist(base["criteria"]["mtf"], "MTF | yield %.1f %%" % (100 * base["yield"]), "MTF at 50 cycles/mm", 0.08),
                                                _hist(base["criteria"]["rms_spot"], "RMS spot | limit 0.055 mm", "RMS spot [mm]", 0.055)], axis=1),
              caption="同じ試行から得た MTF と RMS spot。赤線は合否限界。")
    cy = figs.render_plot([("none", [0], [base["yield"]]), ("two", [1], [after["yield"]])],
              title="Yield | %.1f%% -> %.1f%%" % (100*base["yield"], 100*after["yield"]), size=(640, 430), kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5), ylim=(0, 1), ylabel="yield")
    cs = figs.render_plot([("none", [0], [base["criteria"]["rms_spot"]["std"]]), ("two", [1], [after["criteria"]["rms_spot"]["std"]])],
              title="RMS-spot std | %.3g -> %.3g mm" % (base["criteria"]["rms_spot"]["std"], after["criteria"]["rms_spot"]["std"]), size=(640, 430), kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5), ylabel="RMS spot std [mm]")
    figs.save("compensation", np.concatenate([cy, cs], axis=1), caption="像面だけの場合と内部間隔を加えた場合を比較。")
    names = ["uniform", "normal", "truncated_normal"]
    dy = figs.render_plot([(n, [i], [distributions[n]["yield"]]) for i, n in enumerate(names)],
              title="Yield | %.2f / %.2f / %.2f" % tuple(distributions[n]["yield"] for n in names), size=(640, 430), kinds=["bar"] * 3, colors=["reference", "wrong", "right"], xlim=(-0.5, 2.5), ylim=(0, 1), ylabel="yield")
    ds = figs.render_plot([(n, [i], [distributions[n]["criteria"]["rms_spot"]["std"]]) for i, n in enumerate(names)],
              title="RMS-spot distribution width [mm]", size=(640, 430), kinds=["bar"] * 3, colors=["reference", "wrong", "right"], xlim=(-0.5, 2.5), ylabel="standard deviation [mm]")
    figs.save("distributions", np.concatenate([dy, ds], axis=1),
              caption="一様・正規・±公差で切った正規分布の歩留まり。")
    pred, actual = sens["rss_std"]["rms_spot"], base["criteria"]["rms_spot"]["std"]
    rp = figs.render_plot([("linear prediction", [0], [pred]), ("Monte-Carlo actual", [1], [actual])], title="Linear prediction %.3g vs Monte-Carlo actual %.3g mm" % (pred, actual), size=(640, 430), kinds=["bar", "bar"], colors=["reference", "wrong"], xlim=(-0.5, 1.5), ylabel="RMS spot std [mm]")
    ra = figs.render_plot([("before", [0], [base["yield"]]), ("rebudget", [1], [rebudget["yield"]])], title="Rebudget actual | %.1f%% -> %.1f%%" % (100*base["yield"], 100*rebudget["yield"]), size=(640, 430), kinds=["bar", "bar"], colors=["wrong", "right"], xlim=(-0.5, 1.5), ylim=(0, 1), ylabel="yield")
    figs.save("rebudget", np.concatenate([rp, ra], axis=1), caption="線形予測と Monte-Carlo 実測を明示。締めた行: %s。" % tight_id)
    row = LT._normalise_row(system, {"kind": "wedge_arcmin", "surface": 1, "tolerance": 1.0}, 0)
    pert = LT._apply_row(system, row, 1.0)
    panels = []
    for s, name in ((system, "基準"), (pert, "くさび 1 arcmin")):
        b = RT.ray_bundle(s, field=0, rings=5)
        xy = b["image_xy"][b["valid"]] * 1e3
        panels.append(figs.render_plot([(name, xy[:, 0], xy[:, 1])], title=name, size=(640, 480), kinds=["scatter"],
                                       colors=["reference"], xlabel="x [um]", ylabel="y [um]", aspect="equal"))
    figs.save("wedge_probe", np.concatenate(panels, axis=1), caption="同じ処方の基準像と、1 arcmin のくさびを入れた像。")
    frames = []
    for v in np.linspace(-tab[0]["tolerance"], tab[0]["tolerance"], 24):
        p = LT._apply_row(system, tab[0], float(v))
        b = RT.ray_bundle(p, field=0, rings=4)
        xy = b["image_xy"][b["valid"]] * 1e3
        frames.append(figs.render_plot([("spot", xy[:, 0], xy[:, 1])], title="%s = %+.4g" % (tab[0]["id"], v),
                                       size=(1200, 600), kinds=["scatter"], colors=["emphasis"],
                                       xlabel="x [um]", ylabel="y [um]", aspect="equal"))
    figs.save_video("tolerance_sweep", frames, caption="感度首行を -tol から +tol へ掃引した点像。", fps=12, gif_every=2,
                    gif_width=1200)


def main():
    wall, cpu = time.time(), time.process_time()
    system = triplet()
    print("PoC 製造公差を歩留まりまでつなぐ(収蔵番号 2026.271)")
    closed_form_gates(system)
    tab, crit, sens, base, after = run_analysis(system)
    distributions, rebudget, tight_id = distribution_and_rebudget(system, tab, crit, sens)
    if not CI and figs.target_dir() is not None:
        figures(system, tab, crit, sens, base, after, distributions, rebudget, tight_id)
    print("\nCPU %.2f s、壁時計 %.2f s、NG %d" % (time.process_time() - cpu, time.time() - wall, len(FAILS)))
    assert not figs.errors(), figs.errors()
    if FAILS:
        raise SystemExit("FAIL: " + ", ".join(FAILS))
    print("PASS")


if __name__ == "__main__":
    main()
