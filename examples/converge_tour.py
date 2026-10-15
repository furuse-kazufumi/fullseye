# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""converge_tour — 収束するまで回し、収束した証拠と残りの誤差を返す。収束しなければ値を出さない。

    py -3.11 examples/converge_tour.py
    FULLSEYE_FIGURE_DIR=out/figures/converge_tour py -3.11 examples/converge_tour.py    # 図も出す

【この例が示すこと】
1. **溝の奥は、直接光だけで計算すると 10 倍暗い** —— 開き角 24°・反射率 0.95 の V 溝に真上から光を当てる。壁から壁への
   形態係数は 2-D の交差糸法(厳密)で作り、相互反射の放射度 B = ρE + ρFB を不動点反復で解く。素の反復(1 回 = 反射 1 回)
   は 1e-12 まで約 190 回、Anderson 加速は約 30 回。溝全体の見かけの反射率は直接光だけなら 0.198、収束解は 0.745。
   直接光だけのモデルを実写に合わせると、この差を係数(アルバド・照明の強さ)が吸い込んで「もっともらしく」合ってしまう。
   溝を分ける細かさを 3 段振ると、観測収束次数と GCI(Celik ら 2008)が「何本に分ければ足りるか」を数で言う。
2. **モンテカルロの区間は、標本を足すと公表値に縮んでいく** —— 濁ったスラブ(MCML マニュアル Table 6.1)の拡散反射を
   光子 1,000 個から 25 万個まで。1,000 個の区間は ±15 % もあり、25 万個で ±1 % になって van de Hulst の 0.09739 を含む。
   半無限・屈折率 1.5(Table 6.2)は鏡面 + 拡散 = 0.259 で Giovanelli の 0.2600 を含む。
3. **回しすぎた逆問題は雑音を増幅する** —— ぼけた光子計数の画像に Richardson-Lucy を回すと、真値との誤差はいったん
   下がってから上がる(半収束)。ポアソンの食い違い原理(τ = 1)はその谷の近くで止め、20 倍回すと誤差は 1.3 倍以上に
   増える。仮定の PSF が広すぎると食い違いは τ の上で頭打ちになり、値を返さずに「モデルの値域外」と言う。
4. **収束しないものは拒否する** —— 実数の不動点の無い写像(x^2 + 1)は発散、ロジスティック写像(r = 3.2)は周期 2 の振動。
   どちらも値ではなく NotConvergedError。振動する写像でも x = g(x) の解は在り、Anderson はそれを残差で裏づけて返す。

【グラウンドトゥルース】V 溝は連立一次方程式の直接解(np.linalg.solve)、MCML は公表表、RL は合成した真の像、
Celik の表は論文の値。どれもこの op 族の外の経路で作る。
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
import converge as cv          # noqa: E402  表と例外の型(NotConvergedError)
import deconvstop as ds        # noqa: E402  合成の PSF(_gauss_psf / _otf)を真値づくりに使う
import mcphoton as mp          # noqa: E402  公表表(MCML_TABLE_6_1 / 6_2)

REDUCED = bool(os.environ.get("CI"))


# --------------------------------------------------------------------------- #
# 1. V 溝の相互反射                                                            #
# --------------------------------------------------------------------------- #
def vgroove(n, half_angle_deg=12.0):
    """開き角 2a の V 溝(壁の長さ 1)を壁ごとに n 本の帯に分け、帯どうしの形態係数を交差糸法で作る(2-D で厳密)。

    戻り値: F(帯 i から帯 j へ。同じ壁の帯どうしは 0)、真上からの光の照度 E(= sin a)、開口へ抜ける割合 Fo、帯の長さ。
    """
    a = math.radians(half_angle_deg)
    ua = np.array([-math.sin(a), math.cos(a)])
    ub = np.array([math.sin(a), math.cos(a)])
    s = np.linspace(0.0, 1.0, n + 1)
    PA, PB = s[:, None] * ua, s[:, None] * ub
    L = 1.0 / n

    def d(p, q):
        return float(math.hypot(*(p - q)))

    F = np.zeros((2 * n, 2 * n))
    for i in range(n):
        for j in range(n):
            f = (d(PA[i], PB[j + 1]) + d(PA[i + 1], PB[j]) - d(PA[i], PB[j]) - d(PA[i + 1], PB[j + 1])) / (2.0 * L)
            F[i, n + j] = F[n + j, i] = f
    return F, np.full(2 * n, math.sin(a)), 1.0 - F.sum(axis=1), L, a


def groove_reflectance(n, rho):
    F, E, Fo, L, a = vgroove(n)
    B = np.linalg.solve(np.eye(2 * n) - rho * F, rho * E)
    return float((B * Fo * L).sum() / (2.0 * math.sin(a)))


def run():
    t0 = time.perf_counter()
    out = {}
    rho = 0.95
    n = 64
    F, E, Fo, L, a = vgroove(n)
    g = lambda B: rho * E + rho * F @ B                       # noqa: E731
    exact = np.linalg.solve(np.eye(2 * n) - rho * F, rho * E)
    runs = {m: fs.ledger.iterate_fixed_point(g, rho * E, method=m, m=8, tol=1e-12, max_iter=2000)
            for m in ("plain", "aitken", "anderson")}
    inc = 2.0 * math.sin(a)
    r_direct = float((rho * E * Fo * L).sum() / inc)
    r_conv = float((runs["anderson"]["x"] * Fo * L).sum() / inc)
    err = {m: float(np.abs(r["x"] - exact).max()) for m, r in runs.items()}
    print("1) V 溝(開き角 24°、反射率 0.95、壁ごとに %d 本): 1e-12 まで 素の反復 %d 回 / Aitken %d 回(評価 %d)/ Anderson %d 回"
          % (n, runs["plain"]["n_iter"], runs["aitken"]["n_iter"], runs["aitken"]["n_evals"], runs["anderson"]["n_iter"]))
    print("   直接解との差 %s、推定残り誤差(Anderson)%.2e" % ({k: "%.1e" % v for k, v in err.items()},
                                                           runs["anderson"]["error_estimate"] or float("nan")))
    print("   溝全体の見かけの反射率: 直接光だけ %.3f / 収束解 %.3f(%.1f 倍)、奥の帯は直接光の %.1f 倍明るい"
          % (r_direct, r_conv, r_conv / r_direct, exact[0] / (rho * E[0])))
    assert max(err.values()) < 1e-9
    assert runs["anderson"]["n_iter"] * 4 < runs["plain"]["n_iter"]
    assert np.abs(F * L - (F * L).T).max() < 1e-12                                       # 相反則 L_i F_ij = L_j F_ji
    assert Fo.min() > 0 and r_conv > 3.0 * r_direct
    sizes = (32, 64, 128) if not REDUCED else (16, 32, 64)
    phis = [groove_reflectance(k, rho) for k in sizes[::-1]]     # 細かい順
    gci = fs.ledger.conv_gci(phi=phis, n_cells=tuple(2 * k for k in sizes[::-1]), dim=1)
    print("   帯の数 %s で反射率 %s → 観測収束次数 p = %.2f、GCI = %.4f %%(%s)"
          % (sizes, ["%.6f" % v for v in phis[::-1]], gci["p"], gci["gci_fine21_pct"], gci["report"]))
    assert 0.5 < gci["p"] < 3.0 and gci["gci_fine21_pct"] < 0.1
    out["groove"] = {"plain": runs["plain"]["n_iter"], "anderson": runs["anderson"]["n_iter"],
                     "r_direct": r_direct, "r_conv": r_conv, "p": gci["p"], "gci_pct": gci["gci_fine21_pct"]}

    # Celik の表(論文の値の再現)
    rows = []
    for col, ex in cv.CELIK_TABLE1.items():
        c = fs.ledger.conv_gci(phi=ex["phi"], n_cells=ex["n_cells"], dim=2)
        rows.append([col, "%.4f" % c["p"], str(ex["p"]), "%.4f" % c["phi_ext21"], str(ex["phi_ext"]),
                     "%.2f" % c["gci_fine21_pct"], str(ex["gci_pct"])])
        assert round(c["p"], 2) == ex["p"] and abs(c["phi_ext21"] - ex["phi_ext"]) <= 5e-5
    print("   Celik ら 2008 Table 1: p = %s(表 1.53 / 0.75 / 1.51)" % ", ".join(r[1] for r in rows))

    # ---- 2. モンテカルロの区間 ------------------------------------------------- #
    t61 = mp.MCML_TABLE_6_1
    ns = [1000, 4000, 16000, 64000] + ([] if REDUCED else [256000])
    mc = [fs.ledger.mc_photon_slab(t61["layers"], n_photons=k, seed=100 + i) for i, k in enumerate(ns)]
    for k, r in zip(ns, mc):
        print("2) 光子 %7d 個: R_d = %.5f [%.5f, %.5f](半幅 %.1f %%)  T_t = %.5f [%.5f, %.5f]"
              % (k, r["Rd"], *r["Rd_ci"], 100.0 * (r["Rd_ci"][1] - r["Rd"]) / t61["Rd"], r["Tt"], *r["Tt_ci"]))
    last = mc[-1]
    assert last["Rd_ci"][0] <= t61["Rd"] <= last["Rd_ci"][1] and last["Tt_ci"][0] <= t61["Tt"] <= last["Tt_ci"][1]
    hw = [r["Rd_ci"][1] - r["Rd"] for r in mc]
    assert hw[0] > 4.0 * hw[-1 if REDUCED else -2]
    t62 = mp.MCML_TABLE_6_2
    r62 = fs.ledger.mc_photon_slab(t62["layers"], n_photons=30000 if REDUCED else 200000, seed=7)
    print("   Table 6.2(半無限、n = 1.5): 鏡面 %.3f + 拡散 %.4f = %.4f [%.4f, %.4f](Giovanelli 0.2600)"
          % (r62["Rsp"], r62["Rd"], r62["R_total"], *r62["R_total_ci"]))
    assert r62["R_total_ci"][0] <= t62["Rd"] <= r62["R_total_ci"][1]
    out["mc"] = {"n": ns, "Rd": [r["Rd"] for r in mc], "half_width": hw}

    # ---- 3. Richardson-Lucy の止め方 ------------------------------------------- #
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:96, 0:96]
    truth = np.full((96, 96), 5.0)
    for i, w in enumerate((1, 2, 3, 4)):
        truth[10:86, 8 + i * 10:8 + i * 10 + w] += 200.0
    truth[((yy - 30) ** 2 + (xx - 70) ** 2) <= 100] += 80.0
    truth[((yy - 70) ** 2 + (xx - 70) ** 2) <= 25] += 160.0
    otf = ds._otf(ds._gauss_psf(2.0, truth.shape), truth.shape)
    y = rng.poisson(np.fft.irfft2(np.fft.rfft2(truth) * otf, s=truth.shape)).astype(float)
    rmse = {}
    snaps = {}
    stop = fs.ledger.iv_richardson_lucy_until(y, psf_sigma=2.0)
    k = stop["k_stop"]
    keep = {k, 20 * k}

    def cb(it, x, d):
        rmse[it] = float(np.sqrt(((x - truth) ** 2).mean()))
        if it in keep:
            snaps[it] = x.copy()

    long = fs.ledger.iv_richardson_lucy_until(y, psf_sigma=2.0, tau=1e-12, max_iter=20 * k, plateau_rtol=1e-300,
                                              callback=cb)
    kbest = min(rmse, key=rmse.get)
    print("3) RL: 食い違い原理が %d 回目で止める(誤差 %.2f)。誤差最小は %d 回目(%.2f)、%d 回まで回すと %.2f(%.1f 倍)"
          % (k, rmse[k], kbest, rmse[kbest], 20 * k, rmse[20 * k], rmse[20 * k] / rmse[k]))
    print("   総和の保存(補題 3.2)の最大の相対誤差 %.1e" % stop["mass_rel_error_max"])
    assert rmse[k] <= 1.1 * rmse[kbest] and rmse[20 * k] > 1.3 * rmse[k] and stop["mass_rel_error_max"] < 1e-10
    wrong = fs.ledger.iv_richardson_lucy_until(y, psf_sigma=3.5)
    print("   仮定の PSF が広すぎる(σ 3.5 対 実際 2.0): %s、食い違いは %.2f で頭打ち(%d 回目)→ 値を返さない"
          % (wrong["status"], wrong["discrepancy"], wrong["n_iter"]))
    assert wrong["status"] == "outside_model_range" and wrong["image"] is None
    out["rl"] = {"k_stop": k, "k_best": kbest, "rmse_stop": rmse[k], "rmse_long": rmse[20 * k]}

    # ---- 4. 拒否 ---------------------------------------------------------------- #
    for label, gg, x0 in (("x^2 + 1", lambda x: x * x + 1.0, 0.0), ("3.2 x (1 - x)", lambda x: 3.2 * x * (1 - x), 0.3)):
        try:
            fs.ledger.iterate_fixed_point(gg, x0, method="plain")
            raise AssertionError("not refused: " + label)
        except cv.NotConvergedError as e:
            print("4) %s: 拒否 —— %s" % (label, str(e).split(": ", 1)[1][:96]))
    rep = fs.ledger.iterate_fixed_point(lambda x: 3.2 * x * (1 - x), 0.3, method="anderson")
    print("   同じ写像を Anderson で: x = %.10f(1 - 1/3.2 = 0.6875)、残差 %.1e、推定残り誤差 %s(縮小写像でないので出さない)"
          % (rep["x"], rep["residual"], rep["error_estimate"]))
    assert abs(rep["x"] - 0.6875) < 1e-9 and rep["error_estimate"] is None

    # ---- 図 ---------------------------------------------------------------------- #
    if figs.enabled():
        series = [(m, np.arange(len(runs[m]["residual_history"])), np.log10(np.maximum(runs[m]["residual_history"], 1e-300)))
                  for m in ("plain", "aitken", "anderson")]
        series.append(("tol 1e-12", [0, runs["plain"]["n_iter"]], [-12, -12]))
        figs.save_plot("groove_residuals", series, kinds=["line", "line", "line", "line"],
                       styles=[None, None, None, "dashed"], colors=["wrong", "neutral", "right", "reference"],
                       xlabel="反復の回数(素の反復では 1 回 = 反射 1 回)", ylabel="log10 ||g(B) - B||",
                       title="V 溝の相互反射: 素の反復 %d 回 / Anderson %d 回" % (runs["plain"]["n_iter"], runs["anderson"]["n_iter"]),
                       caption="放射度 B = ρE + ρFB(ρ = 0.95、開き角 24°、壁ごとに 64 本の帯、形態係数は交差糸法)。素の反復は"
                               "反射を 1 回ずつ足していく和そのもので、残差は 1 回に約 %.3f 倍しか減らない。Anderson(Walker & Ni の"
                               "式 3.1、記憶 8)は同じ精度に約 %d 回で着く。どれも直接解との差 1e-9 未満。"
                               % (runs["plain"]["residual_history"][-1] / runs["plain"]["residual_history"][-2],
                                  runs["anderson"]["n_iter"]))
        s = (np.arange(n) + 0.5) / n
        figs.save_plot("groove_profile",
                       [("収束解(相互反射込み)", s, exact[:n]), ("直接光だけ", s, (rho * E)[:n]),
                        ("2 回反射まで", s, (rho * E + rho * F @ (rho * E))[:n])],
                       kinds=["line", "line", "line"], styles=[None, "dashed", "dotted"],
                       colors=["right", "wrong", "neutral"],
                       xlabel="溝の奥(0)から縁(1)までの位置", ylabel="放射度 B",
                       title="溝の奥は、直接光だけなら %.0f 倍暗く見積もる" % (exact[0] / (rho * E[0])),
                       caption="同じ溝の片側の壁。直接光だけのモデルは壁を一様に塗る。2 回反射でも奥はまだ足りない。溝全体の"
                               "見かけの反射率は直接光だけ %.3f・収束解 %.3f。この差を実写の較正で係数が吸い込むと、"
                               "アルベドや照明の強さが「もっともらしく」間違う(設計書 §12)。" % (r_direct, r_conv))
        lx = [math.log10(k_) for k_ in ns]
        figs.save_plot("mc_interval_shrinks",
                       [("推定", lx, [r["Rd"] for r in mc]), ("区間の上端", lx, [r["Rd_ci"][1] for r in mc]),
                        ("区間の下端", lx, [r["Rd_ci"][0] for r in mc]),
                        ("van de Hulst 0.09739", [lx[0], lx[-1]], [t61["Rd"]] * 2)],
                       kinds=["scatter", "line", "line", "line"], styles=[None, None, None, "dashed"],
                       colors=["emphasis", "neutral", "neutral", "reference"],
                       xlabel="log10(光子の数)", ylabel="拡散反射 R_d",
                       title="モンテカルロの 95 % 区間は、光子を足すと公表値へ縮む",
                       caption="MCML マニュアル Table 6.1 のスラブ(n = 1、μa = 10・μs = 90 /cm、g = 0.75、d = 0.02 cm)。区間は"
                               "光子 1 個ずつの寄与の標準偏差から。光子 4 倍で半幅は 1/2(1/√N)。最後の区間は van de Hulst "
                               "の 0.09739 を含み、T_t も 0.66096 を含む(門は両側で判定)。")
        it = sorted(rmse)
        figs.save_plot("rl_semiconvergence",
                       [("真値との誤差", it, [rmse[i] for i in it]),
                        ("食い違い原理で止めた所", [k, k], [min(rmse.values()), max(rmse.values())]),
                        ("誤差最小", [kbest, kbest], [min(rmse.values()), max(rmse.values())])],
                       kinds=["line", "line", "line"], styles=[None, "dashed", "dotted"],
                       colors=["emphasis", "right", "neutral"],
                       xlabel="Richardson-Lucy の反復の回数", ylabel="真値との RMS 誤差(光子数)",
                       title="回しすぎると雑音を増幅する —— 止める所はデータが決める",
                       caption="96 x 96 の棒と円をガウス(σ = 2 px)でぼかし、ポアソン雑音を乗せた光子計数。誤差はいったん下がって"
                               "から上がる(半収束)。ポアソンの食い違い原理(Bertero ら 2010、τ = 1)は %d 回目で止め、そこは"
                               "誤差最小(%d 回目)の %.0f %% 以内。%d 回まで回すと誤差は %.1f 倍。"
                               % (k, kbest, 100.0 * (rmse[k] / rmse[kbest] - 1.0), 20 * k, rmse[20 * k] / rmse[k]))
        figs.save_grid("rl_images", [truth, y, snaps[k], snaps[20 * k], wrong["last_iterate"]],
                       captions=["真値", "観測(ぼけ + ポアソン)", "食い違い原理で停止(%d 回)" % k,
                                 "回しすぎ(%d 回)" % (20 * k), "PSF が広すぎる: 値は返さない(最後の反復)"],
                       gray=True, ncols=5, title="Richardson-Lucy: 止めた所と、回しすぎた所",
                       caption="回しすぎた像は棒の縁に輪がつき、平らな所に粒が立つ(雑音の増幅)。仮定の PSF が実際より広いと"
                               "食い違いが τ の上で頭打ちになり、op は「モデルの値域外」として像を返さない(右は参考に出した"
                               "最後の反復で、推定値ではない)。")
        figs.save_table("celik_table1", ["列", "p(計算)", "p(表)", "外挿値(計算)", "外挿値(表)", "GCI %(計算)", "GCI %(表)"],
                        rows, title="Celik ら 2008 Table 1 の再現(格子比はセル数から式 2 で)",
                        caption="単調収束・p < 1・振動収束の 3 列。表に印字された丸めた比(r32 = 1.333)をそのまま使うと"
                                "第 1 列の p は 1.537 になり、表の 1.53 はセル数からの比 sqrt(8000/4500) で出る。")
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  converge_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
