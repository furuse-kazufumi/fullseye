# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""simcal_tour — 実画像から物理モデルの係数を合わせる。ただし、画像が決めない係数には数を出さない。

    py -3.11 examples/simcal_tour.py
    FULLSEYE_FIGURE_DIR=out/figures/simcal_tour py -3.11 examples/simcal_tour.py    # 図も出す

【この例が示すこと】
1. **利得と照明は掛け算でしか効かない** —— 画像を明るくする 2 つのつまみ(照明の強さとカメラの利得)を同時に合わせようとすると、
   simcal_fit は**数を出さずに拒否する**。理由は「積しか決まらない」で、その積(照明 x 利得)は 0.1 % で決まっている。
   χ² の地形を描くと、谷は 1 点ではなく**まっすぐな溝**(積が一定の線)になっている。照明を固定すれば利得は 1 つに決まる。
2. **単波長の膜は n x d しか決まらない** —— 550 nm 1 波長で一様な膜を撮ると、屈折率 n と膜厚 d の組で決まるのは
   n^1 x d^0.94(位相 4π n d / λ が効くので、ほぼ光路長 n d。指数が 1 でないのは境界の反射率も n で変わるから)。谷は干渉の次数ごとに何本も並ぶ平行な溝(どれも n^1 d^0.94 が一定の線)。31 波長で撮ると溝は 1 点に締まって n と d が
   別々に決まる —— ただし島が干渉の次数ごとにいくつもあり、小さな計画から始めた LM は**違う次数**(d = 357 nm、χ²/自由度 = 60)
   に落ちる。その時 simcal_fit は数と一緒に「χ² が雑音の 60 倍、multistart を」と警告する。multistart は真の次数(d = 521 nm)へ。
3. **効かないつまみ** —— 一様な白い板を撮った画像では、ボケ(PSF の σ)は何も変えない。合わせる前のふるい(simcal_screen)が
   「効かない」と言い、当てはめも拒否する。チャートを撮れば同じ σ は 1.198 px(真値 1.2)に決まる。
4. **位置合わせ** —— 2 px 下・3 px 左にずれて写った画像を、位相相関(既存の phase_correlation_fft)で戻し、
   巻き込んだ縁の 114 画素だけを外して合わせる。

【グラウンドトゥルース】合成の観測は物理の経路(電子のポアソン + 読み出し雑音 + 丸め、EMVA 1288 の線形カメラ)で作り、
当てはめは分散の式(同じ規格の SNR の式)を使う —— 同じ式を往復させない。真値は作った値。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
from metriccontract import MetricContractError  # noqa: E402

K, SIGMA_D, DARK = 0.5, 6.0, 64.0          # 線形カメラ: 0.5 DN/電子、暗雑音 6 電子、黒レベル 64 DN
NOISE = {"kind": "emva", "K": K, "sigma_d": SIGMA_D, "dark": DARK}


def chart(n=32):
    """縞・円・灰の段のテストチャート(0.25..1)。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = np.full((n, n), 0.55)
    img[:, : n // 3] = 0.25 + 0.75 * ((xx[:, : n // 3] // 2) % 2)
    img[np.hypot(xx - 0.68 * n, yy - 0.5 * n) < n / 5.0] = 1.0
    img[: n // 4, n // 3:] = 0.35
    return img


def capture(model, theta, seed):
    """物理の経路で撮る: 電子はポアソン、読み出し雑音、K 倍して黒レベルを足し、整数に丸める。"""
    rng = np.random.default_rng(seed)
    out = []
    for mu in fs.ledger.simcal_simulate(model, theta):
        e = rng.poisson(np.maximum(mu - DARK, 0.0) / K)
        out.append(np.round(K * (e + SIGMA_D * rng.standard_normal(mu.shape)) + DARK))
    return out


def chi2_map(model, images, xname, xs, yname, ys, base):
    """2 つのつまみを格子で振った χ²(雑音の分散で割った残差の二乗和)。"""
    obs = np.concatenate([im.ravel() for im in images])
    out = np.empty((len(ys), len(xs)))
    for i, yv in enumerate(ys):
        for j, xv in enumerate(xs):
            th = dict(base, **{xname: xv, yname: yv})
            mu = np.concatenate([s.ravel() for s in fs.ledger.simcal_simulate(model, th)])
            var = K ** 2 * SIGMA_D ** 2 + 1.0 / 12 + K * np.maximum(mu - DARK, 0)
            out[i, j] = float(((obs - mu) ** 2 / var).sum())
    return out


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. 利得 x 照明 ------------------------------------------------------------ #
    gi = fs.ledger.simcal_model(
        chain=[{"op": "stage:scale"}, {"op": "stage:gain_offset", "args": {"offset": DARK}}],
        knobs=[{"name": "illum", "step": 0, "arg": "factor", "lo": 0.2, "hi": 5.0, "scale": "log"},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log", "unit": "DN"}],
        scene=chart(), noise=NOISE, label="chart -> illumination -> camera gain")
    truth1 = {"illum": 1.5, "gain": 600.0}
    imgs1 = capture(gi, truth1, 1)
    gio = fs.ledger.simcal_observe(gi, imgs1)
    scr = fs.ledger.simcal_screen(gio)
    try:
        fs.ledger.simcal_fit(gio)
        refused1 = None
    except MetricContractError as e:
        refused1 = str(e)
    r1 = fs.ledger.simcal_fit(gio, allow_undetermined=True)
    c1 = r1["determined_combos"][0]
    print("1) 利得 x 照明: ふるい %s → 当てはめは%s" % (scr["class"], "拒否" if refused1 else "受理(!)"))
    print("   決まる組 %s = %.1f(真値 1.5 x 600 = 900、ずれ %.2f %%)、1 つずつの値は出さない: %s"
          % (c1["combination"], c1["value"]["product"], 100 * abs(c1["value"]["product"] / 900 - 1), r1["theta_hat"]))
    fixed = fs.ledger.simcal_model(chain=gi["chain"], knobs=[dict(gi["knobs"][0], fixed=1.5), dict(gi["knobs"][1])],
                                   scene=gi["scene"], noise=NOISE)
    r1f = fs.ledger.simcal_fit(fs.ledger.simcal_observe(fixed, imgs1))
    print("   照明を 1.5 に固定すると利得 = %.1f(真値 600)" % r1f["theta_hat"]["gain"])
    assert refused1 and "illum^1 * gain^1" in refused1 and r1["theta_hat"] == {}
    assert abs(c1["value"]["product"] / 900 - 1) < 0.005 and abs(r1f["theta_hat"]["gain"] / 600 - 1) < 0.01

    # ---- 2. 薄膜: 1 波長と 31 波長 ------------------------------------------------- #
    def film(nm):
        return fs.ledger.simcal_model(
            chain=[{"op": "thin_film_reflectance", "args": {"n_sub": 3.88}},
                   {"op": "stage:as_image", "args": {"shape": (8, 8)}},
                   {"op": "stage:gain_offset", "args": {"gain": 1000.0, "offset": DARK}}],
            knobs=[{"name": "n_film", "step": 0, "arg": "n_film", "lo": 1.3, "hi": 1.7, "scale": "log"},
                   {"name": "d", "step": 0, "arg": "thickness_nm", "lo": 300.0, "hi": 700.0, "scale": "log",
                    "unit": "nm"}],
            scene=np.asarray(nm, dtype=float), noise=NOISE, label="film on silicon, %d wavelength(s)" % len(nm))

    truth2 = {"n_film": 1.46, "d": 520.0}
    f1 = film([550.0])
    f1o = fs.ledger.simcal_observe(f1, capture(f1, truth2, 2))
    r2a = fs.ledger.simcal_fit(f1o, allow_undetermined=True)
    c2 = r2a["determined_combos"][0]
    nd_true = 1.46 * 520.0 ** c2["weights"]["d"]
    print("2) 膜 550 nm 1 波長: 値は出さず、決まる組 %s = %.1f(真値で %.1f)"
          % (c2["combination"], c2["value"]["product"], nd_true))
    nm31 = np.linspace(400.0, 700.0, 31)
    f31 = film(nm31)
    imgs31 = capture(f31, truth2, 2)
    f31o = fs.ledger.simcal_observe(f31, imgs31)
    wrong = fs.ledger.simcal_fit(f31o, n_starts=2, seed=0)
    right = fs.ledger.simcal_fit(f31o, method="multistart", n_starts=16, seed=0)
    print("   31 波長、小さな計画からの LM: n = %.3f、d = %.1f nm、χ²/自由度 = %.1f —— 警告: %s"
          % (wrong["theta_hat"]["n_film"], wrong["theta_hat"]["d"], wrong["fit"]["chi2_red"],
             wrong["fit"]["warnings"][0][:60] + "…"))
    print("   31 波長、multistart: n = %.4f、d = %.1f nm、χ²/自由度 = %.2f(真値 1.46 / 520)"
          % (right["theta_hat"]["n_film"], right["theta_hat"]["d"], right["fit"]["chi2_red"]))
    assert r2a["theta_hat"] == {} and 0.9 < c2["weights"]["d"] < 1.1     # 1.07(Fresnel の項の分。2026-10-18 に重みを直して 0.94 から)
    assert abs(c2["value"]["product"] / nd_true - 1) < 0.01
    assert wrong["fit"]["chi2_red"] > 10 and wrong["fit"]["warnings"]
    assert abs(right["theta_hat"]["d"] - 520) < 8 and abs(right["theta_hat"]["n_film"] - 1.46) < 0.02

    # ---- 3. 効かないつまみ ---------------------------------------------------------- #
    def blur(scene):
        return fs.ledger.simcal_model(
            chain=[{"op": "stage:gaussian_blur"}, {"op": "stage:gain_offset", "args": {"offset": DARK}}],
            knobs=[{"name": "sigma", "step": 0, "arg": "sigma", "lo": 0.3, "hi": 3.0, "unit": "px"},
                   {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log"}],
            scene=scene, noise=NOISE)

    truth3 = {"sigma": 1.2, "gain": 900.0}
    flat, ch = blur(np.full((32, 32), 0.8)), blur(chart())
    sf, sch = fs.ledger.simcal_screen(flat), fs.ledger.simcal_screen(ch)
    try:
        fs.ledger.simcal_fit(fs.ledger.simcal_observe(flat, capture(flat, truth3, 3)))
        refused3 = None
    except MetricContractError as e:
        refused3 = str(e)
    r3 = fs.ledger.simcal_fit(fs.ledger.simcal_observe(ch, capture(ch, truth3, 3)))
    print("3) ボケ σ: 白い板では %s(全範囲で動かしても μ* = %.2g σ_雑音)→ 拒否 / チャートでは %s、σ = %.3f px(真値 1.2)"
          % (sf["class"]["sigma"], sf["mu_star_whitened"]["sigma"], sch["class"]["sigma"], r3["theta_hat"]["sigma"]))
    assert sf["class"]["sigma"] == "no_influence" and refused3 and "no_influence" in refused3
    assert sch["class"]["sigma"] == "determined" and abs(r3["theta_hat"]["sigma"] - 1.2) < 0.05

    # ---- 4. 位置合わせ -------------------------------------------------------------- #
    demo = fs.ledger.simcal_model()
    moved = [np.roll(demo["observed"]["images"][0], (2, -3), axis=(0, 1))]
    al = fs.ledger.simcal_observe(demo, moved, align=True)
    r4 = fs.ledger.simcal_fit(al)
    print("4) ずれた画像: 位相相関で (%d, %d) px を戻し、縁の %d 画素を外して f = %.2f px・利得 = %.1f(真値 %.0f / %.0f)"
          % (*al["observed"]["shifts"][0], int((~al["observed"]["mask"][0]).sum()), r4["theta_hat"]["f"],
             r4["theta_hat"]["gain"], demo["truth"]["f"], demo["truth"]["gain"]))
    assert al["observed"]["shifts"][0] == (2, -3) and abs(r4["theta_hat"]["f"] - demo["truth"]["f"]) < 0.6

    # ---- 図 ---------------------------------------------------------------------- #
    if figs.enabled():
        li = np.geomspace(0.4, 5.0, 61)
        lg = np.geomspace(150.0, 2500.0, 61)
        m1 = chi2_map(gi, imgs1, "illum", li, "gain", lg, truth1)
        dn = np.geomspace(1.3, 1.7, 71)
        dd = np.geomspace(300.0, 700.0, 71)
        m2a = chi2_map(f1, f1o["observed"]["images"], "n_film", dn, "d", dd, truth2)
        m2b = chi2_map(f31, imgs31, "n_film", dn, "d", dd, truth2)
        figs.save_grid("chi2_valleys",
                       [np.log10(m1 - m1.min() + 1.0)[::-1], np.log10(m2a - m2a.min() + 1.0)[::-1],
                        np.log10(m2b - m2b.min() + 1.0)[::-1]],
                       captions=["照明(横)x 利得(縦): 1 本の溝", "n(横)x d(縦)1 波長: 次数ごとの溝",
                                 "n x d 31 波長: 溝が 1 点に締まる"], ncols=3,
                       title="χ² の地形 —— 谷が点か、溝か(暗いほど合う、対数目盛)",
                       caption="どちらも対数の軸(照明 0.4〜5・利得 150〜2500 DN、n 1.3〜1.7・d 300〜700 nm)、上が大きい値。"
                               "照明と利得は積が同じなら同じ絵になるので、谷は積が一定の直線。1 波長の膜は n^1 d^0.94 が一定の"
                               "線が干渉の次数ごとに何本も並ぶ(どの溝の上でも 550 nm の反射率は同じ)。31 波長では 1 点に締まるが、"
                               "χ² は次数ごとに谷を持つので、出発点を誤ると隣の次数の谷に落ちる(次の図)。")
        spec_w = fs.ledger.simcal_simulate(f31, wrong["theta_hat"])[0][0]
        spec_r = fs.ledger.simcal_simulate(f31, right["theta_hat"])[0][0]
        figs.save_plot("film_fringe_orders",
                       [("観測(31 波長)", nm31, imgs31[0][0]), ("multistart(d = %.0f nm)" % right["theta_hat"]["d"], nm31, spec_r),
                        ("小さな計画の LM(d = %.0f nm)" % wrong["theta_hat"]["d"], nm31, spec_w)],
                       kinds=["scatter", "line", "line"], styles=[None, None, "dashed"],
                       colors=["reference", "right", "wrong"], xlabel="波長 [nm]", ylabel="画素値 [DN]",
                       title="違う干渉次数に落ちた当てはめは、χ² が 60 倍で告げる",
                       caption="シリコンの上の膜(n = 1.46、d = 520 nm)の分光反射。破線は隣の次数(d = 357 nm、n = 1.33)で、"
                               "縞の数が違う。simcal_fit はこの時も値を返すが、fit.warnings に「χ²/自由度 = 60、multistart か "
                               "simcal_discrepancy を」と書く。")
        names = list(sch["mu_star_whitened"])
        lg10 = lambda v: float(np.log10(max(v, 1e-16)))                       # noqa: E731
        figs.save_plot("screen_flat_vs_chart",
                       [("白い板", [0, 1], [lg10(sf["mu_star_whitened"][n]) for n in names]),
                        ("チャート", [0, 1], [lg10(sch["mu_star_whitened"][n]) for n in names]),
                        ("雑音の幅(log10 1.96)", [-0.5, 1.5], [np.log10(1.96)] * 2)],
                       kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"],
                       colors=["wrong", "right", "reference"], xlim=(-0.5, 1.5),
                       xlabel="σ(0)/ 利得(1)", ylabel="log10 μ*(雑音の標準偏差で数えた動き)",
                       title="ふるい: 白い板ではボケが画像を動かさない",
                       caption="Morris のふるいを雑音で割った画像の主成分ごとに回し、合成した μ*。全範囲を動かして雑音の"
                               "1.96 倍にも届かないつまみは「効かない」。白い板のボケは %.0e(丸めの屑、縁が無ければ PSF は見えない)、"
                               "チャートでは雑音の %.0f 倍動かす。" % (sf["mu_star_whitened"]["sigma"], sch["mu_star_whitened"]["sigma"]))
        figs.save_grid("alignment",
                       [moved[0], al["observed"]["images"][0], al["observed"]["mask"][0].astype(float),
                        r4["residual_maps"][0]],
                       captions=["ずれて写った画像", "位相相関で戻した", "使う画素(縁を外す)", "残差 / 雑音"],
                       signed=[False, False, False, True], gray=[True, True, True, False], ncols=4,
                       title="位置合わせ —— ずれを戻し、巻き込んだ縁は使わない",
                       caption="2 px 下・3 px 左にずれた撮像を phase_correlation_fft で整数画素だけ戻す。np.roll で回り込んだ"
                               "縁(114 画素)は当てはめから外す。残差は雑音の大きさで割ってあり、構造が無い。")
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  simcal_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
