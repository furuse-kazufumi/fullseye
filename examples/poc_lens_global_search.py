# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 硝材の置き換えと多始点の大域探索 ―― 色消し 2 枚の閉形式と、単レンズの曲げの 3 次収差の解で採点する。

【問い】(1) モデル硝材 (n_d, V_d) をカタログ硝材に置き換えたとき、色消しの残りはどれだけ動くか。それは手で計算した
閉形式と合うか。(2) 局所最適化を何度も違う始点から回すと、本当の最適解(と、はまりやすい浅い解)が見つかるか。
新 op 3 本(`lensglobal`、`opsoptics` の `lensglobal`): `glass_nearest` / `lens_substitute_glasses` / `lens_global_search`。
局所最適化は `lensopt.optimize_lens` をそのまま使い、merit は再実装していない。4 章:

  1. **硝材の置き換え**: カタログ硝材 8 種が自分自身の最近傍で距離 0、モデル硝材を作ってから置き換えるとその硝材に戻る。
     距離の測り方(nd_vd / partial_dispersion)で最近傍が変わる。許容距離の外のモデル硝材は拒否。
  2. **色消しの残り**: 薄肉 2 枚の色消し φ1 = φ V1/(V1−V2)、φ2 = −φ V2/(V1−V2) の硝材を置き換えると、F−C の屈折力差が
     φ1'/V1' + φ2'/V2' になる。光線追跡で測った値と手計算が 1e-6 で合う。
  3. **大域探索**: (a) 単レンズの曲げ: 開口を小さくすると最適な形状係数が 3 次の解 q* = 2(n²−1)/(n+2) = 0.7397 に近づく
     (開口 5・3 mm の 2 点から ap² で外挿)。(b) 色消し 2 枚の屈折力: 8 始点がすべて閉形式の屈折力に 1e-6 以内で着き、重複と判定される。
     (c) 3 枚の曲率の色消し 2 枚: 浅い解(merit 1.18e-5)に 20 始点中 19 本がはまり、深い解(5.04e-6)には 1 本だけ届く。
  4. **壊して確かめる**: 近傍の無い硝材は ValueError、未知の merit の欄・不正な始点数も ValueError、同じ seed は同じ結果。

【外部真値】薄肉色消しの閉形式(Smith / Kingslake)、薄肉単レンズの 3 次球面収差の最小(Coddington の形状係数、
Welford の薄肉 Seidel 係数)。【学習】0。【較正】0。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lensglobal as LG  # noqa: E402
import materials as MAT  # noqa: E402
import raytrace as RT  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
FCD = [RT.WL_F, RT.WL_D, RT.WL_C]
N1, V1, N2, V2 = 1.5168, 64.17, 1.6200, 36.37
NAMED = ["N-BK7", "N-SF11", "N-FK51A", "N-F2", "N-SK16", "N-SF6", "N-LAK9", "N-BAK4"]


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _row(name):
    return next(r for r in MAT.glass_map("glass") if r["name"] == name)


def chapter_glass():
    print("\n1. 硝材の置き換え")
    worst, back = 0.0, 0
    for nm in NAMED:
        r = _row(nm)
        nb = LG.glass_nearest(r["nd"], r["vd"])["neighbours"][0]
        worst = max(worst, nb["distance"])
        s = RT.lens_system([{"R": 60.0, "t": 4.0, "n": (r["nd"], r["vd"]), "ap": 8.0}, {"R": -60.0, "t": None, "n": 1.0}], stop=0)
        back += LG.lens_substitute_glasses(s)["table"][0]["glass"] == nm == nb["name"]
    gate("カタログ硝材 8 種は自分自身が最近傍で距離 0、モデル硝材にしてから置き換えても元の名前に戻る",
         worst == 0.0 and back == len(NAMED), "最大距離 %.1e、戻った %d/%d" % (worst, back, len(NAMED)))
    q = (1.62, 36.4)
    a = LG.glass_nearest(*q)["neighbours"][0]
    b = LG.glass_nearest(*q, metric="partial_dispersion", p_gf=0.535)["neighbours"][0]
    c = LG.glass_nearest(*q, metric="partial_dispersion", p_gf=0.62)["neighbours"][0]
    print("   (n_d, V_d) = %s の最近傍: nd_vd → %s、P_gF 0.535 → %s、P_gF 0.62 → %s" % (q, a["name"], b["name"], c["name"]))
    gate("距離の測り方(P_g,F の項)で最近傍が変わる", b["name"] != c["name"], "%s / %s" % (b["name"], c["name"]))
    far = RT.lens_system([{"R": 50.0, "t": 3.0, "n": (2.6, 12.0), "ap": 5.0}, {"R": -50.0, "t": None, "n": 1.0}], stop=0)
    try:
        LG.lens_substitute_glasses(far)
        refused = False
    except ValueError as e:
        refused = "tolerance" in str(e)
    gate("カタログの許容距離の外のモデル硝材(2.6 / 12.0)は拒否", refused)


def _doublet_powers(phi=0.01, c0=0.012):
    p1 = phi * V1 / (V1 - V2)
    p2 = -phi * V2 / (V1 - V2)
    c1 = c0 - p1 / (N1 - 1.0)
    c2 = c1 - p2 / (N2 - 1.0)
    return phi, p1, p2, c0, c1, c2


def chapter_achromat():
    print("\n2. 色消しの残り(薄肉 2 枚、置き換え前後)")
    phi, p1, p2, c0, c1, c2 = _doublet_powers()
    s = RT.lens_system([{"R": 1 / c0, "t": 0.0, "n": (N1, V1), "ap": 0.004}, {"R": 1 / c1, "t": 0.0, "n": (N2, V2)},
                        {"R": 1 / c2, "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)

    def dpow(sys_):
        pf = 1.0 / RT.paraxial_trace(RT.with_wavelength(sys_, RT.WL_F))["efl"]
        pc = 1.0 / RT.paraxial_trace(RT.with_wavelength(sys_, RT.WL_C))["efl"]
        return pf - pc

    gate("閉形式の屈折力の 2 枚はモデル硝材で F−C の屈折力差が 0(1e-12)", abs(dpow(s)) < 1e-12, "%.1e" % dpow(s))
    errs, rows = [], []
    for k in (1, 2, 3):
        out = LG.lens_substitute_glasses(s, k=k, tolerance=0.3)
        g1, g2 = (_row(r["glass"]) for r in out["table"])
        expect = (g1["nd"] - 1) * (c0 - c1) / g1["vd"] + (g2["nd"] - 1) * (c1 - c2) / g2["vd"]
        got = dpow(out["system"])
        errs.append(abs(got - expect) / abs(expect))
        rows.append((k, g1["name"], g2["name"], got / phi))
        print("   k=%d: %s + %s   残り (Φ_F−Φ_C)/Φ = %+.3e   手計算との相対差 %.1e" % (k, g1["name"], g2["name"], got / phi, errs[-1]))
    gate("置き換え後の F−C の屈折力差は φ1'/V1' + φ2'/V2' と相対 1e-6 以内(k = 1, 2, 3)", max(errs) < 1e-6, "最大 %.1e" % max(errs))
    NUMBERS["achromat_residual_err"] = max(errs)
    return s, rows


def _singlet(q, ap, n=1.5168, f=100.0):
    R1 = 2 * f * (n - 1) / (q + 1)
    R2 = -2 * f * (n - 1) / (1 - q)
    return RT.lens_system([{"R": R1, "t": 0.012 * ap * ap, "n": n, "ap": ap}, {"R": R2, "t": None, "n": 1.0}],
                          stop=0, object_mm=RT.INF)


def _doublet(c0, c1, c2):
    return RT.lens_system([{"R": 1 / c0, "t": 3.0, "n": (N1, V1), "ap": 8.0}, {"R": 1 / c1, "t": 1.5, "n": (N2, V2)},
                           {"R": 1 / c2, "t": None, "n": 1.0}], stop=0, object_mm=RT.INF)


def chapter_search():
    print("\n3. 多始点の大域探索")
    n = 1.5168
    q_star = 2 * (n * n - 1) / (n + 2)
    qs = {}
    for ap in (5.0, 3.0):
        r = LG.lens_global_search(_singlet(0.0, ap), ["c0", "c1"], {"tolerance": 1e-12}, n_starts=6, seed=2,
                                  spread=0.3, iterations=200)
        v = r["best"]["values"]
        qs[ap] = (1 / v[1] + 1 / v[0]) / (1 / v[1] - 1 / v[0])
        print("   (a) 開口 %.0f mm: 最良の形状係数 q = %.4f(6 始点、別の解 %d 個)" % (ap, qs[ap], r["n_distinct"] - 1))
    q0 = qs[3.0] - (qs[5.0] - qs[3.0]) * 9.0 / 16.0
    gate("(a) 単レンズの曲げ: 開口を小さくすると q は 3 次の解 0.7397 に下から近づき、ap² で外挿した値が 2e-3 以内",
         qs[5.0] < qs[3.0] < q_star and abs(q0 - q_star) < 2e-3, "q* = %.4f、外挿 %.4f" % (q_star, q0))
    NUMBERS.update({"q_star": q_star, "q_extrapolated": q0})

    phi, p1, p2, c0, c1, c2 = _doublet_powers(0.01)
    thin = RT.lens_system([{"R": 1 / c0, "t": 1e-5, "n": (N1, V1), "ap": 0.004},
                           {"R": 1 / (1.3 * c1), "t": 1e-5, "n": (N2, V2)}, {"R": 1 / (0.8 * c2), "t": None, "n": 1.0}],
                          stop=0, object_mm=RT.INF)
    r = LG.lens_global_search(thin, ["c1", "c2"], {"wavelengths": FCD, "efl_target": 100.0, "efl_weight": 1.0, "tolerance": 1e-14},
                              n_starts=8, seed=5, spread=0.4, iterations=300)
    err = max(max(abs((N1 - 1) * (c0 - o["values"][0]) / p1 - 1), abs((N2 - 1) * (o["values"][0] - o["values"][1]) / p2 - 1))
              for o in r["optima"])
    print("   (b) 色消し 2 枚の屈折力: 8 始点の閉形式との相対差の最大 %.1e、別々の解 %d 個" % (err, r["n_distinct"]))
    gate("(b) 色消し 2 枚: 8 始点すべてが閉形式の屈折力 φ1, φ2 に 1e-6 以内で着き、1 つの解にまとまる",
         err < 1e-6 and r["n_distinct"] == 1, "%.1e" % err)
    NUMBERS["doublet_power_err"] = err

    merit = {"wavelengths": FCD, "tolerance": 1e-12}
    bad = _doublet(1 / 187.04, 1 / -54.72, 1 / -139.15)
    single = LG.lens_global_search(bad, ["c0", "c1", "c2"], merit, n_starts=1, iterations=150)
    multi = LG.lens_global_search(bad, ["c0", "c1", "c2"], merit, n_starts=20, seed=1, spread=0.7, iterations=150)
    good, worse = multi["basins"][0], multi["basins"][1]
    print("   (c) 3 曲率の色消し: 1 始点 → merit %.3e。20 始点 → 深い解 %.3e(%d 本)、浅い解 %.3e(%d 本)" % (
        single["best"]["merit"], good["merit"], good["n_starts"], worse["merit"], worse["n_starts"]))
    gate("(c) 1 始点は浅い解にはまり、20 始点は深い解(merit が半分以下)を見つける。両方の解に始点が届く",
         multi["n_distinct"] == 2 and good["merit"] < 0.5 * single["best"]["merit"]
         and (good["n_starts"], worse["n_starts"]) == (1, 19))
    NUMBERS.update({"merit_single": single["best"]["merit"], "merit_multi": good["merit"]})
    again = LG.lens_global_search(bad, ["c0", "c1", "c2"], merit, n_starts=20, seed=1, spread=0.7, iterations=150)
    gate("同じ seed は同じ結果(全 20 本の merit が一致)", [o["merit"] for o in again["optima"]] == [o["merit"] for o in multi["optima"]])
    return multi


def chapter_probes():
    print("\n4. 壊して確かめる")
    s = RT.lens_system()
    bad = [{"merit": {"nonsense": 1}}, {"n_starts": 0}, {"seed": -1}, {"variables": ["c9"]}]
    ok = 0
    for kw in bad:
        try:
            LG.lens_global_search(s, **kw)
        except ValueError:
            ok += 1
    gate("未知の merit の欄・不正な始点数・seed・面番号は ValueError", ok == len(bad))


def make_figure(multi, rows, s):
    cat = MAT.glass_map("glass")
    # panel 1: merit against start index, basins coloured
    order = sorted(multi["optima"], key=lambda o: o["start"])
    basin_of = {}
    for i, b in enumerate(multi["basins"]):
        basin_of[b["start"]] = i
    for o in multi["optima"]:
        o["_b"] = basin_of.get(o["start"], basin_of.get(o["duplicate_of"]))
    ser, kinds, colors = [], [], []
    for i, (lab, col) in enumerate((("深い解", "right"), ("浅い解", "wrong"))):
        pts = [(o["start"], np.log10(o["merit"])) for o in order if o["_b"] == i]
        if pts:
            ser.append((lab, [p[0] for p in pts], [p[1] for p in pts]))
            kinds.append("scatter")
            colors.append(col)
    left = figs.render_plot(ser, xlabel="始点の番号(0 は与えた処方)", ylabel="log10 merit", kinds=kinds, colors=colors,
                            title="20 始点の局所解: 19 本が浅い解、1 本が深い解")
    # panel 2: glass map with substitution arrows
    series = [("カタログ 46 種", [r["vd"] for r in cat], [r["nd"] for r in cat])]
    kinds, colors = ["scatter"], ["neutral"]
    series.append(("モデル硝材", [V1, V2], [N1, N2]))
    kinds.append("scatter")
    colors.append("emphasis")
    for k, col, lab in ((1, "right", "k = 1(最近傍)"), (2, "reference", "k = 2"), (3, "wrong", "k = 3")):
        for j, r in enumerate(LG.lens_substitute_glasses(s, k=k, tolerance=0.3)["table"]):
            series.append((lab if j == 0 else "", [r["model_vd"], r["vd"]], [r["model_nd"], r["nd"]]))
            kinds.append("line")
            colors.append(col)
    right = figs.render_plot(series, xlabel="Abbe 数 V_d", ylabel="屈折率 n_d", kinds=kinds, colors=colors,
                             title="硝材図: モデル硝材 → 最近傍のカタログ硝材")
    h = min(left.shape[0], right.shape[0])
    img = np.concatenate([left[:h], right[:h]], axis=1)
    figs.save("lens_global_search", img, caption="左: 始点ごとの局所解の merit(基が違う 2 つの解)。右: 硝材図の上で、"
              "モデル硝材(クラウン・フリント)から最近傍のカタログ硝材への置き換え。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 硝材の置き換えと大域探索(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_glass()
    s, rows = chapter_achromat()
    multi = chapter_search()
    chapter_probes()
    if not REDUCED and figs.target_dir() is not None:
        make_figure(multi, rows, s)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
