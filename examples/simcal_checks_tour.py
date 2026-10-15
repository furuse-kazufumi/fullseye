# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""simcal_checks_tour — 合わせた係数はどこまで信じてよいか: 下界・プロファイル・過適合・モデルの食い違い。

    py -3.11 examples/simcal_checks_tour.py
    FULLSEYE_FIGURE_DIR=out/figures/simcal_checks_tour py -3.11 examples/simcal_checks_tour.py    # 図も出す

【この例が示すこと】
1. **40 種の真値で回収を採点する(G1)** —— ボケ・周辺減光・利得・黒レベルの 4 つのつまみを、ラテン超方格で選んだ 40 組の真値で
   撮り(物理の経路: 電子のポアソン + 読み出し雑音 + 丸め)、合わせる。4 つ全部が Cramér-Rao 下界の 3 倍以内に入った組を数える。
   同じ採点を、カメラの雑音を 1/4 に見誤った雑音モデルでやり直すと**落ちる** —— 下界を信じてよいのは雑音モデルが正しいときだけ。
2. **ボケが小さすぎると上限しか言えない** —— σ = 0.12 px のボケ。当てはめは σ = 0(範囲の端)に落ちて拒否する。プロファイル尤度
   (他のつまみを合わせ直しながら σ を動かす)も同じ答えで、上側では χ² が 3.84 を越えるが、下側は σ = 0 まで行っても越えない。
   言えるのは「σ < 0.29 px」だけ(画素より細いボケは、この雑音では 0 と区別できない)。σ = 1.2 px なら両側で閉じる。
3. **8 次の周辺減光の多項式(G3)** —— 平らな板を 4 段の露光で撮る。cos⁴ の模型(つまみ 3 つ)は全部の門を通る。8 次の多項式
   (つまみ 10 個)は当てはまりは同じくらい良いのに、係数は ±2 の範囲いっぱいに暴れる。当てはめが「交絡」で拒否し、無理に
   通しても過適合の門(自由なつまみ 10 > 画像が持つ方向 6)が拒否する。その門を外すと、残りの門は全部すり抜ける。
4. **族の外(光軸のずれたレンズ)** —— 光軸が (5, −4) px ずれた周辺減光を、中心の模型で合わせる。数は返るが、残差 PCA は
   雑音を越える構造を 1 成分見つけ、その形は「ずれた減光 − 中心の減光」と相関する。不確かさは楽観側だと注記する。

【グラウンドトゥルース】合成の真値(作った値)、Cramér-Rao 下界は既存の mathestimation.crlb_gaussian と一致することを
テストが確かめる(直線の模型)。Tracy-Widom の 99 % 点は純雑音で 1 % 前後しか越えない(テストで実測)。
"""
from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
from metriccontract import MetricContractError  # noqa: E402

K, SIGMA_D = 0.5, 6.0
L = fs.ledger


def chart(n=48):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    img = np.full((n, n), 0.55)
    img[:, : n // 3] = 0.25 + 0.75 * ((xx[:, : n // 3] // 2) % 2)
    img[np.hypot(xx - 0.68 * n, yy - 0.5 * n) < n / 5.0] = 1.0
    img[: n // 4, n // 3:] = 0.35
    return img


def capture(model, theta, seed, dark):
    """物理の経路で撮る(分散の式は使わない)。"""
    rng = np.random.default_rng(seed)
    out = []
    for mu in L.simcal_simulate(model, theta):
        e = rng.poisson(np.maximum(mu - dark, 0.0) / K)
        out.append(np.round(K * (e + SIGMA_D * rng.standard_normal(mu.shape)) + dark))
    return out


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. G1: 40 種の真値 -------------------------------------------------------- #
    def g1_model(k_model):
        return L.simcal_model(
            chain=[{"op": "stage:gaussian_blur"}, {"op": "stage:radial_cos4"}, {"op": "stage:gain_offset"}],
            knobs=[{"name": "sigma", "step": 0, "arg": "sigma", "lo": 0.4, "hi": 2.5, "unit": "px"},
                   {"name": "f", "step": 1, "arg": "f", "lo": 20.0, "hi": 120.0, "unit": "px"},
                   {"name": "gain", "step": 2, "arg": "gain", "lo": 300.0, "hi": 3000.0, "unit": "DN", "scale": "log"},
                   {"name": "offset", "step": 2, "arg": "offset", "lo": 20.0, "hi": 200.0, "unit": "DN"}],
            scene=chart(), noise={"kind": "emva", "K": k_model, "sigma_d": SIGMA_D * K / k_model, "dark": "offset"},
            label="chart -> blur -> cos^4 -> gain/offset")

    names = ["sigma", "f", "gain", "offset"]
    plan = L.doe_lhs(40, [(n, 0.0, 1.0) for n in names], seed=7)
    U = 0.05 + 0.9 * (plan["coded"] + 1.0) / 2.0

    def score(k_model):
        m = g1_model(k_model)
        zs = []
        for i, u in enumerate(U):
            truth = {}
            for j, kn in enumerate(m["knobs"]):
                lo, hi = kn["lo"], kn["hi"]
                truth[kn["name"]] = lo * (hi / lo) ** u[j] if kn["scale"] == "log" else lo + u[j] * (hi - lo)
            mo = L.simcal_observe(m, capture(m, truth, 1000 + i, truth["offset"]))
            r = L.simcal_fit(mo, allow_undetermined=True)
            crlb = L.simcal_identifiability(r, at=truth, profile=False)["identifiability"]["crlb"]
            zs.append([(r["theta_hat"].get(n, np.inf) - truth[n]) / crlb[n] for n in names])
        Z = np.asarray(zs)
        return Z, int((np.abs(Z) < 3).all(axis=1).sum())

    Z, ok = score(K)
    Zb, okb = score(K / 4)
    print("1) G1: 40 組の真値のうち 4 つとも 3 σ_CRLB 以内 = %d 組(%.1f %%)、z の標準偏差 %.2f"
          % (ok, 100 * ok / 40, Z.std()))
    print("   雑音を 1/4 に見誤った模型では %d 組(%.1f %%)—— 門は赤" % (okb, 100 * okb / 40))
    assert ok >= 38 and okb < 38

    # ---- 2. 上限しか言えないボケ --------------------------------------------------- #
    bm = L.simcal_model(
        chain=[{"op": "stage:gaussian_blur"}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
        knobs=[{"name": "sigma", "step": 0, "arg": "sigma", "lo": 0.0, "hi": 3.0, "unit": "px"},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log", "unit": "DN"}],
        scene=chart(32), noise={"kind": "emva", "K": K, "sigma_d": SIGMA_D, "dark": 64.0})
    small = L.simcal_identifiability(L.simcal_fit(L.simcal_observe(bm, capture(bm, {"sigma": 0.12, "gain": 900.0}, 4,
                                                                                  64.0)), allow_undetermined=True))
    big = L.simcal_identifiability(L.simcal_fit(L.simcal_observe(bm, capture(bm, {"sigma": 1.2, "gain": 900.0}, 4, 64.0))))
    ps, pb = small["identifiability"]["profile"]["sigma"], big["identifiability"]["profile"]["sigma"]
    print("2) σ = 0.12 px: 当てはめは %s / プロファイルは %s(上限 %.3f px、下限なし)/ σ = 1.2 px: %s [%.4f, %.4f] px"
          % (small["undetermined"]["sigma"].split(":")[0], ps["class"], ps["upper"], pb["class"], pb["lower"], pb["upper"]))
    assert ps["class"] == "upper_only" and "sigma" not in small["theta_hat"] and pb["class"] == "determined"

    # ---- 3. G3: 8 次の多項式 -------------------------------------------------------- #
    flat = np.ones((40, 40))
    conds = [{0: {"factor": e}} for e in (0.4, 0.7, 1.0, 1.4)]
    noise = {"kind": "emva", "K": K, "sigma_d": SIGMA_D, "dark": "offset"}
    go = [{"name": "gain", "step": 2, "arg": "gain", "lo": 300.0, "hi": 3000.0, "unit": "DN", "scale": "log"},
          {"name": "offset", "step": 2, "arg": "offset", "lo": 20.0, "hi": 200.0, "unit": "DN"}]
    cos4 = L.simcal_model(chain=[{"op": "stage:scale"}, {"op": "stage:radial_cos4"}, {"op": "stage:gain_offset"}],
                          knobs=[{"name": "f", "step": 1, "arg": "f", "lo": 15.0, "hi": 150.0, "unit": "px"}] + go,
                          scene=flat, conditions=conds, noise=noise, label="flat field, cos^4")
    poly = L.simcal_model(chain=[{"op": "stage:scale"}, {"op": "stage:radial_poly"}, {"op": "stage:gain_offset"}],
                          knobs=[{"name": "c%d" % k, "step": 1, "arg": "c%d" % k, "lo": -2.0, "hi": 2.0, "init": 0.0}
                                 for k in range(1, 9)] + go,
                          scene=flat, conditions=conds, noise=noise, label="flat field, 8th-order polynomial")
    truth3 = {"f": 40.0, "gain": 1200.0, "offset": 80.0}
    tr, ho = capture(cos4, truth3, 1, 80.0), capture(cos4, truth3, 10001, 80.0)
    va = L.simcal_validate(L.simcal_identifiability(L.simcal_fit(L.simcal_observe(cos4, tr))), ho)
    mp = L.simcal_observe(poly, tr)
    try:
        L.simcal_fit(mp)
        refused = None
    except MetricContractError as e:
        refused = str(e).splitlines()[0]
    forced = L.simcal_fit(mp, allow_undetermined=True)
    vp = L.simcal_validate(forced, ho)
    loose = L.simcal_validate(forced, ho, dims=100)
    coefs = forced["diagnostics"]["endpoint_not_an_estimate"]
    print("3) cos⁴: %s、門 %s、χ²/自由度 学習 %.3f・保留 %.3f" % (va["status"], "全部通過" if va["validation"]["passed"] else
                                                       va["validation"]["failed"], va["errors"]["train"], va["errors"]["holdout"]))
    print("   8 次: 当てはめ → %s" % refused)
    print("   無理に通すと: 学習 %.3f・保留 %.3f(cos⁴ と同じくらい合う)、係数 %s"
          % (vp["errors"]["train"], vp["errors"]["holdout"], ", ".join("%+.2f" % coefs["c%d" % k] for k in range(1, 9))))
    print("   過適合の門: %s(自由なつまみ %d > 画像の方向 %d)/ その門を外すと失敗 %s"
          % (vp["validation"]["failed"], vp["validation"]["n_free"], vp["validation"]["output_dims"],
             loose["validation"]["failed"] or "なし(全部すり抜ける)"))
    assert va["status"] == "accepted" and refused and "knobs_within_dims" in vp["validation"]["failed"]
    assert vp["status"] == "refused" and loose["validation"]["failed"] == []

    # ---- 4. 族の外: 光軸のずれたレンズ ---------------------------------------------- #
    shifted = copy.deepcopy(cos4)
    shifted["chain"][1]["args"].update(cx=19.5 + 5.0, cy=19.5 - 4.0)
    tr4 = capture(shifted, truth3, 2, 80.0)
    r4 = L.simcal_discrepancy(L.simcal_fit(L.simcal_observe(cos4, tr4)))
    d4 = r4["discrepancy"]
    din = va if va.get("discrepancy") else L.simcal_discrepancy(va)
    true_v = L.simcal_simulate(shifted, truth3)[2] - L.simcal_simulate(cos4, r4["theta_hat"])[2]
    corr = abs(float(np.corrcoef(d4["loading_maps"][0].ravel(), true_v.ravel())[0, 1]))
    print("4) 光軸のずれ: f = %.2f px(真値 40)、χ²/自由度 %.1f、残差 PCA は %d 成分(特異値 %.0f > 端 %.1f)、"
          "形は「ずれた減光 − 中心の減光」と相関 %.2f / 族の中は %d 成分"
          % (r4["theta_hat"]["f"], r4["fit"]["chi2_red"], d4["n_structural"], d4["singular_values"][0],
             d4["edge_tracy_widom"], corr, din["discrepancy"]["n_structural"]))
    print("   " + "\n   ".join(L.simcal_report(r4)["text"].splitlines()))
    assert d4["verdict"] == "structure" and corr > 0.8 and din["discrepancy"]["n_structural"] == 0

    # ---- 図 ---------------------------------------------------------------------- #
    if figs.enabled():
        xs = np.arange(40)
        figs.save_plot("g1_zscores",
                       [(n, xs + 0.15 * j, np.clip(Z[:, j], -5, 5)) for j, n in enumerate(names)]
                       + [("±3 σ_CRLB", [-1, 40], [3, 3]), ("", [-1, 40], [-3, -3])],
                       kinds=["scatter"] * 4 + ["line", "line"], styles=[None] * 4 + ["dashed", "dashed"],
                       colors=["emphasis", "right", "neutral", "wrong", "reference", "reference"],
                       xlim=(-1, 40), ylim=(-5, 5), xlabel="真値の組(ラテン超方格の 40 組)",
                       ylabel="(推定 − 真値) / σ_CRLB",
                       title="40 組中 %d 組で 4 つとも ±3 σ_CRLB の内 —— 推定は下界に届いている" % ok,
                       caption="ボケ・周辺減光・利得・黒レベルを、ラテン超方格の 40 組の真値で撮って合わせた。縦軸は誤差を"
                               "Cramér-Rao 下界(雑音モデルから計算)で割ったもので、標準偏差 %.2f(1 なら下界どおり)。"
                               "雑音を 1/4 に見誤った模型では %d 組しか入らない。" % (Z.std(), okb))
        def _in_frame(tr):                                                     # 枠の外の点(遠い試し打ち)は描かない
            a = np.array(tr)
            return a[(a[:, 0] <= 2.0) & (a[:, 1] <= 30.0)]
        tr_s = _in_frame(ps["trace"])
        tr_b = _in_frame(pb["trace"])
        figs.save_plot("profile_upper_only",
                       [("σ = 0.12 px の画像", tr_s[:, 0], tr_s[:, 1]), ("σ = 1.2 px の画像", tr_b[:, 0], tr_b[:, 1]),
                        ("χ²₁(95 %) = 3.84", [0, 2], [3.84, 3.84])],
                       kinds=["line", "line", "line"], styles=[None, None, "dashed"],
                       colors=["wrong", "right", "reference"], xlim=(0, 2.0), ylim=(0, 30),
                       xlabel="ボケ σ [px](他のつまみは合わせ直す)", ylabel="Δχ²",
                       title="プロファイル尤度 —— 小さいボケは上限しか言えない",
                       caption="σ を固定して利得を合わせ直したときの χ² の増え方。σ = 1.2 px の画像は両側で 3.84 を越え、"
                               "区間 [%.3f, %.3f] px。σ = 0.12 px の画像は下側が σ = 0 まで越えない —— 言えるのは"
                               "「σ < %.2f px」だけなので点推定は出さない。" % (pb["lower"], pb["upper"], ps["upper"]))
        rr = np.hypot(*(np.mgrid[0:40, 0:40] - 19.5)) / np.hypot(20, 20)
        rho = np.linspace(0, 1.4, 85)                                         # 1 = 画像の隅、その先は外挿
        vc = 1.0 / (1.0 + (rho * np.hypot(20, 20) / va["theta_hat"]["f"]) ** 2) ** 2
        vp_curve = 1.0 + sum(coefs["c%d" % k] * rho ** k for k in range(1, 9))
        vt = 1.0 / (1.0 + (rho * np.hypot(20, 20) / 40.0) ** 2) ** 2
        g_c, g_p = va["theta_hat"]["gain"], coefs["gain"]
        figs.save_plot("poly8_vs_cos4",
                       [("真の減光 cos⁴(f = 40 px)", rho, vt), ("cos⁴ の当てはめ", rho, vc * g_c / truth3["gain"]),
                        ("8 次の多項式の当てはめ", rho, np.clip(vp_curve * g_p / truth3["gain"], -1.0, 2.0)),
                        ("画像の隅(ここから先は外挿)", [1.0, 1.0], [-1.0, 2.0])],
                       kinds=["line"] * 4, styles=["dashed", None, None, "dotted"],
                       colors=["reference", "right", "wrong", "neutral"], ylim=(-1.0, 2.0),
                       xlabel="中心からの距離(対角の半分 = 1)", ylabel="明るさ(真の利得で割った)",
                       title="8 次の多項式も画像の中ではよく合う —— 一歩外へ出ると暴れる",
                       caption="平らな板を 4 段の露光で撮った画像に、cos⁴(つまみ 3)と 8 次の多項式(つまみ 10)を合わせた。"
                               "曲線は画素のある範囲(〜1)で重なるが、多項式の係数は %s で、隅の外では cos⁴ から離れていく"
                               "(縦は −1〜2 で切ってある)。当てはめは交絡で拒否し、"
                               "過適合の門は「自由なつまみ %d > 画像が持つ方向 %d」で拒否する。"
                               % (", ".join("%+.1f" % coefs["c%d" % k] for k in range(1, 9)),
                                  vp["validation"]["n_free"], vp["validation"]["output_dims"]))
        del rr
        figs.save_grid("out_of_family",
                       [tr4[2], r4["residual_maps"][2], d4["loading_maps"][0], true_v],
                       captions=["光軸のずれたレンズの平板", "中心の模型の残差 / 雑音", "残差 PCA の第 1 成分",
                                 "ずれた減光 − 中心の減光(真値)"],
                       signed=[False, True, True, True], gray=[True, False, False, False], ncols=4,
                       title="族の外のデータ —— 数は返るが、残差が足りないものの形を描く",
                       caption="光軸が (5, −4) px ずれた周辺減光を中心の cos⁴ で合わせた。χ²/自由度 %.1f、4 枚の残差の PCA は "
                               "Tracy-Widom 99 %% の端を越える成分を %d 個持ち、その形は真のずれと相関 %.2f。"
                               "simcal_discrepancy は「不確かさは楽観側」と注記する。" % (r4["fit"]["chi2_red"],
                                                                              d4["n_structural"], corr))
    assert not figs.errors(), figs.errors()

    out["g1_inside"] = ok
    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  simcal_checks_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
