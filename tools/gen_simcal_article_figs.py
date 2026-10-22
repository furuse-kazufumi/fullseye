# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Qiita の sim-to-real 較正シリーズ(第 1・2 回)の図を作る。第 1 回は examples の simcal ツアーと同じ組み立て、第 2 回は
実写の PoC 4 本(薄膜・テレセン・ピクセルシフト・相互反射)の章の関数をそのまま呼ぶ。

    py -3.11 tools/gen_simcal_article_figs.py

出力: docs/articles/assets/qiita_simcal_series/<図>_{ja,en}.png と numbers.json(本文の数字の出どころ)。
図はすべて Fullseye 自身の描画(examplefig = annotate 族)で引く。真値・門の値は破線で描く。

数字の照合: 本文に書いた数字は numbers.json と、examples/simcal_tour.py・simcal_checks_tour.py の
実行ログの両方に一致させる(同じ模型・同じ乱数の種)。第 2 回の数字は numbers.json の "part2" と、各 PoC の印字
(examples/poc_simcal_thin_film.py ・ poc_simcal_telecentric.py ・ poc_simcal_pixel_shift.py ・ poc_pocket_interreflection.py)
の両方に合わせる。第 2 回は実データ(各 PoC が取得してキャッシュする公開画像)が要る。干渉次数の門の表だけは、ツアーが保留画像を
撮らないので、ここで種 10002 の保留画像を撮って simcal_validate を回す(tests/test_simcal_checks.py の
test_wrong_fringe_order_is_rejected_by_the_absolute_chi2_gate と同じ手順)。
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "articles" / "assets" / "qiita_simcal_series"

TXT = {
    "ja": {
        "valley_title": "利得 x 照明: 谷の底は 1 本の線(破線 = 積 900 の真値)",
        "valley_floor": "照明を固定して合わせた利得",
        "valley_truth": "真値の線 利得 = 900 / 照明",
        "valley_x": "log10 照明",
        "valley_y": "log10 利得 [DN]",
        "chi_title": "線の上ならどこでも同じだけ合う(破線 = 雑音どおりの 1)",
        "chi_series": "照明を固定したときの χ²/自由度",
        "chi_ref": "χ²/自由度 = 1",
        "chi_x": "log10 照明",
        "chi_y": "χ²/自由度",
        "film_title": "隣の干渉次数に落ちた当てはめ(破線)と、正しい次数",
        "film_obs": "観測(31 波長)",
        "film_right": "multistart d = %.0f nm",
        "film_wrong": "小さな計画の LM d = %.0f nm",
        "film_x": "波長 [nm]",
        "film_y": "画素値 [DN]",
        "gate_title": "simcal_validate の 6 つの門: 隣の次数は絶対 χ² の門だけで落ちる",
        "gate_header": ["門", "比べるもの", "隣の次数", "正しい次数"],
        "gate_desc": {
            "beats_initial": "初期値より良いか",
            "holdout_over_train": "保留 / 学習 ≤ 1 + τ",
            "beats_gain_offset": "利得と黒だけの模型より良いか",
            "estimate_plausible": "範囲・事前・端",
            "knobs_within_dims": "つまみ ≤ 画像の方向の数",
            "fit_consistent_with_noise": "絶対: χ² の上側確率 p ≥ 0.001",
        },
        "pass": "通る", "fail": "落ちる",
        "oof_title": "族の外: 光軸のずれたレンズを中心の模型で合わせる",
        "oof_caps": ["撮った平板", "残差 / 雑音", "残差 PCA 第 1 成分", "真のずれ(ずれ − 中心)"],
        "sv_title": "残差 PCA の特異値(破線 = Tracy-Widom 99 % の端)",
        "sv_out": "光軸がずれたレンズ",
        "sv_in": "族の中(ずれなし)",
        "sv_edge": "端 %.1f",
        "sv_x": "成分の番号",
        "sv_y": "log10 特異値",
    },
    "en": {
        "valley_title": "Gain x illumination: the valley floor is a line (dashed = true product 900)",
        "valley_floor": "gain fitted with illumination held fixed",
        "valley_truth": "truth: gain = 900 / illumination",
        "valley_x": "log10 illumination",
        "valley_y": "log10 gain [DN]",
        "chi_title": "Every point on the line fits equally well (dashed = 1, pure noise)",
        "chi_series": "reduced chi^2 with illumination fixed",
        "chi_ref": "reduced chi^2 = 1",
        "chi_x": "log10 illumination",
        "chi_y": "reduced chi^2",
        "film_title": "A fit stuck one interference order away (dashed) vs the right order",
        "film_obs": "observed (31 wavelengths)",
        "film_right": "multistart d = %.0f nm",
        "film_wrong": "LM from a small design d = %.0f nm",
        "film_x": "wavelength [nm]",
        "film_y": "pixel value [DN]",
        "gate_title": "The six gates of simcal_validate: the wrong order fails only the absolute chi^2 gate",
        "gate_header": ["gate", "what it compares", "wrong order", "right order"],
        "gate_desc": {
            "beats_initial": "better than the start point",
            "holdout_over_train": "holdout / train <= 1 + tau",
            "beats_gain_offset": "better than gain+offset only",
            "estimate_plausible": "bounds, priors, edges",
            "knobs_within_dims": "knobs <= image directions",
            "fit_consistent_with_noise": "absolute: chi^2 tail p >= 0.001",
        },
        "pass": "pass", "fail": "FAIL",
        "oof_title": "Out of family: an off-axis lens fitted with a centred model",
        "oof_caps": ["captured flat", "residual / noise", "residual PCA comp. 1", "true miss (off - centred)"],
        "sv_title": "Residual PCA singular values (dashed = Tracy-Widom 99 % edge)",
        "sv_out": "off-axis lens",
        "sv_in": "in family (centred)",
        "sv_edge": "edge %.1f",
        "sv_x": "component",
        "sv_y": "log10 singular value",
    },
}


def compute() -> dict:
    """図と本文の数字を 1 回だけ計算する(ツアーと同じ模型・同じ種)。"""
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "examples"))
    import fullseye as fs                      # noqa: E402
    import simcal_tour as T1                   # noqa: E402
    import simcal_checks_tour as T2            # noqa: E402
    L = fs.ledger
    d: dict = {}

    # ---- 1. 利得 x 照明(simcal_tour 1 と同じ) ------------------------------------ #
    gi = L.simcal_model(
        chain=[{"op": "stage:scale"}, {"op": "stage:gain_offset", "args": {"offset": T1.DARK}}],
        knobs=[{"name": "illum", "step": 0, "arg": "factor", "lo": 0.2, "hi": 5.0, "scale": "log"},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log", "unit": "DN"}],
        scene=T1.chart(), noise=T1.NOISE, label="chart -> illumination -> camera gain")
    imgs1 = T1.capture(gi, {"illum": 1.5, "gain": 600.0}, 1)
    r1 = L.simcal_fit(L.simcal_observe(gi, imgs1), allow_undetermined=True)
    d["gain_illum_product"] = float(r1["determined_combos"][0]["value"]["product"])
    d["gain_illum_theta_hat"] = dict(r1["theta_hat"])
    floor = []
    for il in np.geomspace(0.4, 4.0, 13):
        mk = L.simcal_model(chain=gi["chain"], knobs=[dict(gi["knobs"][0], fixed=float(il)), dict(gi["knobs"][1])],
                            scene=gi["scene"], noise=T1.NOISE)
        rf = L.simcal_fit(L.simcal_observe(mk, imgs1))
        floor.append((float(il), float(rf["theta_hat"]["gain"]), float(rf["fit"]["chi2_red"])))
    d["valley_floor"] = floor

    # ---- 2. 膜 31 波長: 隣の干渉次数(simcal_tour 2 + 保留画像で simcal_validate) ---- #
    def film(nm):
        return L.simcal_model(
            chain=[{"op": "thin_film_reflectance", "args": {"n_sub": 3.88}},
                   {"op": "stage:as_image", "args": {"shape": (8, 8)}},
                   {"op": "stage:gain_offset", "args": {"gain": 1000.0, "offset": T1.DARK}}],
            knobs=[{"name": "n_film", "step": 0, "arg": "n_film", "lo": 1.3, "hi": 1.7, "scale": "log"},
                   {"name": "d", "step": 0, "arg": "thickness_nm", "lo": 300.0, "hi": 700.0, "scale": "log",
                    "unit": "nm"}],
            scene=np.asarray(nm, dtype=float), noise=T1.NOISE, label="film on silicon, %d wavelength(s)" % len(nm))

    truth2 = {"n_film": 1.46, "d": 520.0}
    nm31 = np.linspace(400.0, 700.0, 31)
    f31 = film(nm31)
    imgs31 = T1.capture(f31, truth2, 2)
    f31o = L.simcal_observe(f31, imgs31)
    hold = T1.capture(f31, truth2, 10002)
    wrong = L.simcal_fit(f31o, n_starts=2, seed=0)
    right = L.simcal_fit(f31o, method="multistart", n_starts=16, seed=0)
    vw, vr = L.simcal_validate(wrong, hold), L.simcal_validate(right, hold)
    d["film"] = {
        "nm": nm31.tolist(), "observed": imgs31[0][0].tolist(),
        "spec_wrong": L.simcal_simulate(f31, wrong["theta_hat"])[0][0].tolist(),
        "spec_right": L.simcal_simulate(f31, right["theta_hat"])[0][0].tolist(),
        "wrong_theta": dict(wrong["theta_hat"]), "right_theta": dict(right["theta_hat"]),
        "wrong_chi2_red": float(wrong["fit"]["chi2_red"]), "right_chi2_red": float(right["fit"]["chi2_red"]),
        "wrong_status": vw["status"], "right_status": vr["status"],
        "wrong_failed": list(vw["validation"]["failed"]), "right_failed": list(vr["validation"]["failed"]),
        "gates": {k: {"wrong": bool(vw["validation"]["gates"][k]["passed"]),
                      "right": bool(vr["validation"]["gates"][k]["passed"])}
                  for k in vw["validation"]["gates"]},
        "abs_gate_wrong": {s: {kk: float(vv) for kk, vv in vw["validation"]["gates"]["fit_consistent_with_noise"][s].items()}
                           for s in ("train", "holdout")},
        "abs_gate_right": {s: {kk: float(vv) for kk, vv in vr["validation"]["gates"]["fit_consistent_with_noise"][s].items()}
                           for s in ("train", "holdout")},
    }

    # ---- 3. 族の外(simcal_checks_tour 3, 4 と同じ) ------------------------------- #
    flat = np.ones((40, 40))
    conds = [{0: {"factor": e}} for e in (0.4, 0.7, 1.0, 1.4)]
    noise = {"kind": "emva", "K": T2.K, "sigma_d": T2.SIGMA_D, "dark": "offset"}
    go = [{"name": "gain", "step": 2, "arg": "gain", "lo": 300.0, "hi": 3000.0, "unit": "DN", "scale": "log"},
          {"name": "offset", "step": 2, "arg": "offset", "lo": 20.0, "hi": 200.0, "unit": "DN"}]
    cos4 = L.simcal_model(chain=[{"op": "stage:scale"}, {"op": "stage:radial_cos4"}, {"op": "stage:gain_offset"}],
                          knobs=[{"name": "f", "step": 1, "arg": "f", "lo": 15.0, "hi": 150.0, "unit": "px"}] + go,
                          scene=flat, conditions=conds, noise=noise, label="flat field, cos^4")
    truth3 = {"f": 40.0, "gain": 1200.0, "offset": 80.0}
    tr, ho = T2.capture(cos4, truth3, 1, 80.0), T2.capture(cos4, truth3, 10001, 80.0)
    va = L.simcal_validate(L.simcal_identifiability(L.simcal_fit(L.simcal_observe(cos4, tr))), ho)
    din = va if va.get("discrepancy") else L.simcal_discrepancy(va)
    shifted = copy.deepcopy(cos4)
    shifted["chain"][1]["args"].update(cx=19.5 + 5.0, cy=19.5 - 4.0)
    tr4 = T2.capture(shifted, truth3, 2, 80.0)
    r4 = L.simcal_discrepancy(L.simcal_fit(L.simcal_observe(cos4, tr4)))
    d4 = r4["discrepancy"]
    true_v = L.simcal_simulate(shifted, truth3)[2] - L.simcal_simulate(cos4, r4["theta_hat"])[2]
    corr = abs(float(np.corrcoef(d4["loading_maps"][0].ravel(), true_v.ravel())[0, 1]))
    d["oof"] = {
        "f_hat": float(r4["theta_hat"]["f"]), "chi2_red": float(r4["fit"]["chi2_red"]),
        "n_structural": int(d4["n_structural"]), "sv": [float(s) for s in d4["singular_values"]],
        "edge": float(d4["edge_tracy_widom"]), "corr": corr,
        "in_family_n_structural": int(din["discrepancy"]["n_structural"]),
        "in_family_sv": [float(s) for s in din["discrepancy"]["singular_values"]],
        "in_family_edge": float(din["discrepancy"]["edge_tracy_widom"]),
    }
    d["_maps"] = [tr4[2], r4["residual_maps"][2], d4["loading_maps"][0], true_v]
    return d


def draw(d: dict, lang: str, tmp: Path) -> list[Path]:
    """1 言語ぶんの図を tmp に書き、書いたファイルを返す。"""
    os.environ["FULLSEYE_FIGURE_DIR"] = str(tmp)
    import examplefig as figs                  # noqa: E402
    figs.reset()
    t = TXT[lang]
    fl = np.asarray(d["valley_floor"])
    lx = np.log10(fl[:, 0])
    figs.save_plot("valley_floor",
                   [(t["valley_floor"], lx, np.log10(fl[:, 1])),
                    (t["valley_truth"], lx, np.log10(900.0 / fl[:, 0]))],
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   xlabel=t["valley_x"], ylabel=t["valley_y"], title=t["valley_title"], size=(720, 420))
    figs.save_plot("valley_chi2",
                   [(t["chi_series"], lx, fl[:, 2]), (t["chi_ref"], [lx[0], lx[-1]], [1.0, 1.0])],
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   xlabel=t["chi_x"], ylabel=t["chi_y"], title=t["chi_title"], ylim=(0.0, 2.0), size=(720, 420))
    f = d["film"]
    figs.save_plot("film_orders",
                   [(t["film_obs"], f["nm"], f["observed"]),
                    (t["film_right"] % f["right_theta"]["d"], f["nm"], f["spec_right"]),
                    (t["film_wrong"] % f["wrong_theta"]["d"], f["nm"], f["spec_wrong"])],
                   kinds=["scatter", "line", "line"], styles=[None, None, "dashed"],
                   colors=["reference", "right", "wrong"], xlabel=t["film_x"], ylabel=t["film_y"],
                   title=t["film_title"], size=(720, 420))
    rows = []
    for k, g in f["gates"].items():
        rows.append([k, t["gate_desc"].get(k, ""), t["pass"] if g["wrong"] else t["fail"],
                     t["pass"] if g["right"] else t["fail"]])
    aw, ar = f["abs_gate_wrong"], f["abs_gate_right"]
    rows.append(["", "chi^2/nu train / holdout", "%.1f / %.1f" % (aw["train"]["chi2_per_nu"], aw["holdout"]["chi2_per_nu"]),
                 "%.2f / %.2f" % (ar["train"]["chi2_per_nu"], ar["holdout"]["chi2_per_nu"])])
    figs.save_table("gates", t["gate_header"], rows, title=t["gate_title"])
    figs.save_grid("out_of_family_maps", d["_maps"], captions=t["oof_caps"],
                   signed=[False, True, True, True], gray=[True, False, False, False], ncols=4, title=t["oof_title"])
    o = d["oof"]
    n = min(len(o["sv"]), len(o["in_family_sv"]))
    xs = np.arange(1, n + 1)
    figs.save_plot("pca_singular_values",
                   [(t["sv_out"], xs, np.log10(o["sv"][:n])), (t["sv_in"], xs + 0.08, np.log10(o["in_family_sv"][:n])),
                    (t["sv_edge"] % o["edge"], [0.5, n + 0.5], [np.log10(o["edge"])] * 2)],
                   kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"],
                   colors=["wrong", "right", "reference"], xlim=(0.5, n + 0.5),
                   xlabel=t["sv_x"], ylabel=t["sv_y"], title=t["sv_title"], size=(720, 420))
    errs = figs.errors()
    if errs:
        raise RuntimeError("figure errors: %s" % errs)
    written = []
    for e in figs.manifest():
        src = tmp / e["file"]
        name = e["name"] + "_" + lang + ".png"
        dst = OUT / name
        shutil.copyfile(src, dst)
        written.append(dst)
    return written


# ====================================================================================== #
# 第 2 回: 実写の較正と、収束させて解く順方向模型                                            #
# ====================================================================================== #
TXT2 = {
    "ja": {
        "fp_title": "実測の膜厚: 区間 [%.1f, %.1f] nm に基準 %.1f nm が入る(貧しい模型は狭いのに外す)",
        "fp_rich": "豊かな模型(他のつまみは合わせ直す)",
        "fp_poor": "直入射・材料表の n(拒否)",
        "fp_95": "χ²₁(95 %) = 3.84",
        "fp_ref": "基準 %.1f nm",
        "fp_x": "膜厚 d [nm]",
        "fp_y": "Δχ²",
        "fr_title": "残差を雑音の床で割る: 貧しい模型は全帯域でうねる",
        "fr_rich": "豊かな模型",
        "fr_poor": "直入射・材料表の n",
        "fr_band": "±1 σ",
        "fr_x": "波長 [nm]",
        "fr_y": "(実測 − 模型) / σ",
        "tb_title": "リング x 30° の残差の平均 / 純粋誤差(破線 = ±2): 雑音では説明できない形が残る",
        "tb_series": "残差の平均 / 純粋誤差の標準誤差",
        "tb_x": "リング(1〜8)の順に並べた区間の番号",
        "tb_y": "z",
        "tp_title": "入射瞳までの距離の逆数 1/L [/m]: 当てはめ(線 = ±2σ)と通常のレンズ",
        "tp_fit": "当てはめ(実画像)",
        "tp_f100": "通常のレンズ f = 100 mm",
        "tp_f25": "通常のレンズ f = 25 mm",
        "tp_x": "",
        "tp_y": "log10 (1/L [/m])",
        "ps_title": "升ごとの差(simcal − 位相相関)[画素]: 0 の周りに散る",
        "ps_13": "組 1→3",
        "ps_24": "組 2→4",
        "ps_zero": "差 0",
        "ps_x": "升の番号(dr は 0〜15、dc は 16〜31)",
        "ps_y": "差 [画素]",
        "pb_title": "反射の回数と、収束解との差(破線 = 雑音 %.2f %%)",
        "pb_actual": "収束解との実際の差",
        "pb_gci": "見積もり(GCI 型)",
        "pb_noise": "雑音の大きさ",
        "pb_x": "反射の回数 k",
        "pb_y": "log10 (像の最大値に対する差)",
        "pt_title": "反射の数え方が 3 通りの模型に、同じ観測を合わせる(真値 反射率 0.70・照明 1.00)",
        "pt_header": ["模型", "反射率", "照明", "χ²/ν(学習)", "残差 PCA", "判定"],
        "pt_names": {"direct": "直接光だけ", "one": "1 回反射", "converged": "収束解"},
        "pt_pca": "%d 成分(構造)", "pt_white": "0 成分(白色)",
        "pt_refused": "不合格", "pt_accepted": "合格",
    },
    "en": {
        "fp_title": "Measured thickness: [%.1f, %.1f] nm contains the reference %.1f nm (the poor model is narrow and misses)",
        "fp_rich": "rich model (other knobs refitted)",
        "fp_poor": "normal incidence, table index (rejected)",
        "fp_95": "chi^2_1 (95 %) = 3.84",
        "fp_ref": "reference %.1f nm",
        "fp_x": "thickness d [nm]",
        "fp_y": "delta chi^2",
        "fr_title": "Residual over the noise floor: the poor model undulates across the whole band",
        "fr_rich": "rich model",
        "fr_poor": "normal incidence, table index",
        "fr_band": "+-1 sigma",
        "fr_x": "wavelength [nm]",
        "fr_y": "(measured - model) / sigma",
        "tb_title": "Mean residual per ring x 30 deg over pure error (dashed = +-2): a shape noise cannot explain",
        "tb_series": "mean residual / standard error from pure error",
        "tb_x": "bin index, ordered by ring (1 to 8)",
        "tb_y": "z",
        "tp_title": "Inverse entrance-pupil distance 1/L [/m]: fit (line = +-2 sigma) and ordinary lenses",
        "tp_fit": "fit (real image)",
        "tp_f100": "ordinary lens f = 100 mm",
        "tp_f25": "ordinary lens f = 25 mm",
        "tp_x": "",
        "tp_y": "log10 (1/L [/m])",
        "ps_title": "Per-tile difference (simcal - phase correlation) [pixel]: scatter around zero",
        "ps_13": "pair 1->3",
        "ps_24": "pair 2->4",
        "ps_zero": "difference 0",
        "ps_x": "tile index (dr is 0-15, dc is 16-31)",
        "ps_y": "difference [pixel]",
        "pb_title": "Bounce count vs the gap to the converged image (dashed = noise %.2f %%)",
        "pb_actual": "actual gap to the converged image",
        "pb_gci": "estimate (GCI style)",
        "pb_noise": "noise level",
        "pb_x": "bounces k",
        "pb_y": "log10 (gap / image maximum)",
        "pt_title": "One observation fitted by three ways of counting reflections (truth albedo 0.70, light 1.00)",
        "pt_header": ["model", "albedo", "light", "chi^2/nu (train)", "residual PCA", "verdict"],
        "pt_names": {"direct": "direct light only", "one": "one bounce", "converged": "converged"},
        "pt_pca": "%d components (structure)", "pt_white": "0 components (white)",
        "pt_refused": "rejected", "pt_accepted": "accepted",
    },
}


def compute_part2() -> dict:
    """第 2 回の数字と図の元データ。各 PoC の章の関数をそのまま呼ぶ(PoC の印字とここの数字は同じ計算)。"""
    sys.path.insert(0, str(ROOT / "examples"))
    import poc_pocket_interreflection as P4         # noqa: E402
    import poc_simcal_pixel_shift as P3             # noqa: E402
    import poc_simcal_telecentric as P2             # noqa: E402
    import poc_simcal_thin_film as P1               # noqa: E402
    from scipy.stats import chi2 as _chi2           # noqa: E402
    q: dict = {}

    # ---- 薄膜: 実測の顕微分光(同梱データ)と実物の顕微鏡写真 ---------------------- #
    lam, Y, _cov = P1.load_spectra()
    sigma, _g, white = P1.noise_floor(lam, Y)
    A0, B0, _dn = P1.cauchy_of_table(lam)
    real = P1.chapter_real_spectrum(lam, Y, sigma, (A0, B0))
    poor = P1.chapter_poor(lam, Y, sigma, (A0, B0), white)
    cam = P1.chapter_micrograph(P1.load_blocks(), (A0, B0))
    N1 = P1.NUMBERS
    gates = real["val"]["validation"]["gates"]
    y = Y[:, 0]
    fit_rich = P1.spectrum_line(lam=lam, **real["end"])[0]
    pn = poor["normal"]["fit"]["diagnostics"]["endpoint_not_an_estimate"]
    fit_poor = P1.spectrum_line(lam=lam, A=A0, B=B0, **pn)[0]
    tr_rich = np.array(real["ident"]["identifiability"]["profile"]["d"]["trace"])
    tr_poor = np.array(poor["normal"]["d"]["trace"])
    pf = poor["freeA"]["d"]
    pnd = poor["nodisp"]["d"]
    q["film"] = {
        "ref_nm": float(P1.REF_NM), "sigma": float(sigma), "white_sigma": float(white),
        "d_lo": float(N1["real_d_lo"]), "d_hi": float(N1["real_d_hi"]), "d_width": float(N1["real_d_width"]),
        "rich_chi2_train": float(gates["fit_consistent_with_noise"]["train"]["chi2_per_nu"]),
        "rich_chi2_holdout": float(gates["fit_consistent_with_noise"]["holdout"]["chi2_per_nu"]),
        "rich_status": real["val"]["status"], "rich_failed": list(real["val"]["validation"]["failed"]),
        "n_holdout": int(len(real["ho"])),
        "profile_class": {k: v[0] for k, v in N1["real_prof"].items()},
        "B_upper": float(N1["real_prof"]["B"][2]),
        "poor_normal_chi2": float(N1["poor_normal_chi2"]), "poor_normal_d": [float(v) for v in N1["poor_normal_d"]],
        "poor_normal_status": poor["normal"]["val"]["status"],
        "poor_normal_failed": list(poor["normal"]["val"]["validation"]["failed"]),
        "poor_nodisp_chi2": float(N1["poor_nodisp_chi2"]),
        "poor_nodisp_d": [float(pnd["lower"]), float(pnd["upper"])],
        "poor_freeA_chi2": float(N1["poor_freeA_chi2"]),
        "poor_freeA_d": [float(pf["lower"]), float(pf["upper"])],
        "poor_freeA_status": poor["freeA"]["val"]["status"],
        "cam_d": float(cam["fit"]["theta_hat"]["d"]), "cam_d_lo": float(N1["cam_d_lo"]), "cam_d_hi": float(N1["cam_d_hi"]),
        "cam_chi2": float(N1["cam_chi2"]), "cam_struct": int(N1["cam_struct"]),
        "cam_T": float(cam["fit"]["theta_hat"]["T"]), "cam_gamma": float(cam["fit"]["theta_hat"]["gamma"]),
        "cam_determined": sorted(cam["fit"]["theta_hat"].keys()),
    }
    q["_film"] = {"lam": lam, "rr": (y - fit_rich) / sigma, "rp": (y - fit_poor) / sigma, "tr_rich": tr_rich,
                  "tr_poor": tr_poor}

    # ---- テレセンの実画像 ----------------------------------------------------------- #
    tm = P2._load_sibling("poc_telecentric_metrology")
    syn = P2.chapter_synthetic(tm.lenses())
    rt = P2.chapter_real(tm, syn)
    if rt is None:
        raise RuntimeError("telecentric real image is not available (needs the cached public image)")
    N2 = P2.NUMBERS
    bins = rt["bins"]
    bz = np.array([bm / (rt["s_pe"] / np.sqrt(n)) for _k, _b, bm, n in bins])
    g6 = rt["vA"]["validation"]["gates"]["fit_consistent_with_noise"]
    rms = float(np.sqrt(np.mean(rt["Rt"][rt["Mt"]] ** 2)))
    inv_ento, inv_fa = 1000.0 / syn["L_ento"], 1000.0 / syn["L_fa25"]
    q["tele"] = {
        "px_per_mm": float(N2["real_px_per_mm"]), "px_se": float(N2["real_px_se"]),
        "paper_K1": float(tm.PAPER["K1_px_per_mm"]), "paper_K2": [float(v) for v in tm.PAPER["K2_px_per_mm"]],
        "inv_L": float(N2["real_inv_L"]), "inv_L_se": float(N2["real_inv_L_se"]),
        "pupil_min_m": float(N2["real_pupil_min_m"]), "inv_L_sigma": float(abs(N2["real_inv_L"]) / N2["real_inv_L_se"]),
        "inv_L_ento": float(inv_ento), "inv_L_f25": float(inv_fa),
        "sigma_pure_error": float(rt["s_pe"]), "sigma_total": float(rt["s_tot"]), "resid_rms": rms,
        "pure_chi2_train": float(g6["train"]["chi2_per_nu"]), "pure_p_train": float(g6["train"]["p"]),
        "pure_chi2_holdout": float(g6["holdout"]["chi2_per_nu"]),
        "pure_status": rt["vA"]["status"], "pure_failed": list(rt["vA"]["validation"]["failed"]),
        "pca_verdict": rt["vA"]["discrepancy"]["verdict"],
        "n_bins": int(len(bz)), "bins_chi2": float((bz ** 2).sum()), "bins_p": float(_chi2.sf((bz ** 2).sum(), len(bz))),
        "total_passed": bool(rt["vB"]["validation"]["passed"]),
        "jack_over_laplace_invL": float(rt["jk"]["inv_L"] / rt["lap"]["inv_L"]),
        "n_points": int(rt["Mt"].sum()),
        "synthetic_jack_over_laplace_discrepant": float(N2["syn_disc_ratio"]),
        "synthetic_jack_over_laplace_clean": float(N2["syn_clean_ratio"]),
    }
    q["_tele"] = {"bz": bz}

    # ---- ピクセルシフトの実データ ---------------------------------------------------- #
    rp = P3.chapter_real()
    if rp is None:
        raise RuntimeError("pixel-shift real frames are not available (needs the cached public frames)")
    N3 = P3.NUMBERS
    pairs = rp["pairs"]
    keys = (((0, 2), "13"), ((1, 3), "24"))
    diffs = {n: pairs[k]["diff"] for k, n in keys}
    q["pshift"] = {
        "K": float(N3["real_K"]), "p_13": float(N3["real_p_02"]), "p_24": float(N3["real_p_13"]),
        "n_tiles": {n: int(len(pairs[k]["rows"])) for k, n in keys},
        "n_determined": {n: int(len(pairs[k]["both"])) for k, n in keys},
        "chi2_median": {n: float(np.median([w["chi2"] for w in pairs[k]["rows"]])) for k, n in keys},
        "mean_diff_px": {n: [float(v) for v in diffs[n].mean(0)] for n in diffs},
        "max_abs_diff_px": float(max(np.abs(d_).max() for d_ in diffs.values())),
        "mean_shift_px": {n: [float(v) for v in pairs[k]["est"].mean(0)] for k, n in keys},
        "chi2_diag_mosaic": float(N3["real_chi2_diag_mosaic"]), "chi2_cross": float(N3["real_chi2_cross"]),
        "cross_status": rp["cross"]["status"],
    }
    q["_pshift"] = diffs

    # ---- 相互反射(PoC の main と同じ順) ----------------------------------------------- #
    roi, crop = P4.roi_crop()
    r0_, r1_, c0, c1 = crop
    P4.ROI_C = roi[r0_:r1_, c0:c1]
    truth, tt, kappa, mesh = P4.chapter_render(crop)
    rows, need, noise_rel = P4.chapter_bounces(kappa)
    mus = [P4.DARK + kappa * truth["image"][r0_:r1_, c0:c1, 1], P4.DARK + kappa * tt["image"][r0_:r1_, c0:c1, 1]]
    train, hold = P4.capture(mus, P4.SEED), P4.capture(mus, P4.SEED + 10000)
    forward = P4.make_forward(kappa, crop)
    res = P4.chapter_calibrate(forward, train, hold)
    ratios, mae = P4.chapter_bulczak(forward, train)
    share = truth["indirect_share"][r0_:r1_, c0:c1][P4.ROI_C]
    q["pocket"] = {
        "rho_true": P4.RHO_TRUE, "I_true": P4.I_TRUE, "noise_rel": float(noise_rel), "need": int(need),
        "need_actual_gap": float(rows[need]["error_vs_converged"]),
        "share_mean": float(share.mean()), "share_max": float(share.max()),
        "rows": [{"k": int(x["bounces"]), "increment": x["increment"], "ratio": x["observed_ratio"],
                  "asymptotic": bool(x["asymptotic"]), "gci": x["gci"], "actual": float(x["error_vs_converged"])}
                 for x in rows],
        "models": {n: {"rho": float(r["rho"]), "intensity": float(r["intensity"]),
                       "chi2_train": float(r["chi2_train"]), "chi2_hold": float(r["chi2_hold"]),
                       "n_struct": int(r["n_struct"]), "verdict": r["verdict"], "failed": list(r["failed"]),
                       "rel_rms": float(r["rel_rms"])} for n, r in res.items()},
        "mae_dn": {k: float(v) for k, v in mae.items()},
        "mae_noise_only_dn": float(np.sqrt(2 / np.pi) * np.sqrt(P4.emva_var(train[0][P4.ROI_C])).mean()),
        "mae_ratio_one_over_direct": float(mae["one"] / mae["direct"]),
        "cited_ratio_range": [float(min(ratios)), float(max(ratios))],
        "mesh": [[float(a), float(b), float(c_)] for a, b, c_ in mesh],
    }
    return q


def draw_part2(d: dict, lang: str, tmp: Path) -> list[Path]:
    """第 2 回の図を 1 言語ぶん tmp に書き、書いたファイルを返す。"""
    os.environ["FULLSEYE_FIGURE_DIR"] = str(tmp)
    import examplefig as figs                  # noqa: E402
    figs.reset()
    t = TXT2[lang]
    f, fm = d["film"], d["_film"]
    lam = fm["lam"]
    tr, tp = fm["tr_rich"], fm["tr_poor"]
    tr = tr[tr[:, 1] <= 12.0]
    tp = tp[tp[:, 1] <= 12.0]
    figs.save_plot(
        "film_real_profile",
        [(t["fp_rich"], tr[:, 0], tr[:, 1]), (t["fp_poor"], tp[:, 0], tp[:, 1]),
         (t["fp_95"], [88, 104], [3.84, 3.84]), (t["fp_ref"] % f["ref_nm"], [f["ref_nm"], f["ref_nm"]], [0, 12])],
        kinds=["line"] * 4, styles=[None, None, "dashed", "dotted"],
        colors=["right", "wrong", "reference", "emphasis"], xlim=(88, 104), ylim=(0, 12),
        xlabel=t["fp_x"], ylabel=t["fp_y"], title=t["fp_title"] % (f["d_lo"], f["d_hi"], f["ref_nm"]), size=(840, 420))
    lim = float(np.ceil(1.1 * max(np.abs(fm["rr"]).max(), np.abs(fm["rp"]).max())))
    figs.save_plot(
        "film_real_residuals",
        [(t["fr_rich"], lam, fm["rr"]), (t["fr_poor"], lam, fm["rp"]),
         (t["fr_band"], [lam[0], lam[-1]], [1, 1]), ("", [lam[0], lam[-1]], [-1, -1])],
        kinds=["line"] * 4, styles=[None, None, "dashed", "dashed"],
        colors=["right", "wrong", "reference", "reference"], ylim=(-lim, lim),
        xlabel=t["fr_x"], ylabel=t["fr_y"], title=t["fr_title"], size=(840, 420))
    bz = d["_tele"]["bz"]
    xs = np.arange(1, len(bz) + 1)
    figs.save_plot(
        "tele_ring_bins",
        [(t["tb_series"], xs, bz), ("±2", [0.5, len(bz) + 0.5], [2, 2]), ("", [0.5, len(bz) + 0.5], [-2, -2])],
        kinds=["scatter", "line", "line"], styles=[None, "dashed", "dashed"],
        colors=["emphasis", "reference", "reference"], xlim=(0.5, len(bz) + 0.5),
        xlabel=t["tb_x"], ylabel=t["tb_y"], title=t["tb_title"], size=(840, 420))
    te = d["tele"]
    lo, hi = te["inv_L"] - 2 * te["inv_L_se"], te["inv_L"] + 2 * te["inv_L_se"]
    figs.save_plot(
        "tele_pupil",
        [(t["tp_fit"], [3.0], [np.log10(te["inv_L"])]), ("", [3.0, 3.0], [np.log10(lo), np.log10(hi)]),
         (t["tp_f100"], [4.0], [np.log10(te["inv_L_ento"])]), (t["tp_f25"], [5.0], [np.log10(te["inv_L_f25"])])],
        kinds=["scatter", "line", "scatter", "scatter"], styles=[None, None, None, None],
        colors=["right", "right", "wrong", "wrong"], xlim=(0.4, 5.6),
        xlabel=t["tp_x"], ylabel=t["tp_y"], title=t["tp_title"], size=(720, 420))
    ps = d["_pshift"]
    n13, n24 = len(ps["13"]), len(ps["24"])
    figs.save_plot(
        "pshift_tile_diff",
        [(t["ps_13"], np.r_[np.arange(n13), 16 + np.arange(n13)], np.r_[ps["13"][:, 0], ps["13"][:, 1]]),
         (t["ps_24"], np.r_[np.arange(n24), 16 + np.arange(n24)] + 0.3, np.r_[ps["24"][:, 0], ps["24"][:, 1]]),
         (t["ps_zero"], [-0.5, 32], [0, 0])],
        kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"],
        colors=["emphasis", "right", "reference"], xlim=(-0.5, 32),
        xlabel=t["ps_x"], ylabel=t["ps_y"], title=t["ps_title"], size=(840, 420))
    pk = d["pocket"]
    ks = [r["k"] for r in pk["rows"]]
    act = [np.log10(r["actual"]) for r in pk["rows"]]
    gk = [r["k"] for r in pk["rows"] if r["gci"] is not None]
    gv = [np.log10(r["gci"]) for r in pk["rows"] if r["gci"] is not None]
    figs.save_plot(
        "pocket_bounces",
        [(t["pb_actual"], ks, act), (t["pb_gci"], gk, gv),
         (t["pb_noise"], [ks[0], ks[-1]], [np.log10(pk["noise_rel"])] * 2)],
        kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"],
        colors=["emphasis", "right", "reference"], xlabel=t["pb_x"], ylabel=t["pb_y"],
        title=t["pb_title"] % (100 * pk["noise_rel"]), size=(720, 420))
    rows = []
    for k in ("direct", "one", "converged"):
        m = pk["models"][k]
        rows.append([t["pt_names"][k], "%.3f" % m["rho"], "%.3f" % m["intensity"], "%.2f" % m["chi2_train"],
                     (t["pt_pca"] % m["n_struct"]) if m["n_struct"] else t["pt_white"],
                     t["pt_refused"] if m["failed"] else t["pt_accepted"]])
    figs.save_table("pocket_models", t["pt_header"], rows, title=t["pt_title"],
                    col_w=125)
    errs = figs.errors()
    if errs:
        raise RuntimeError("figure errors: %s" % errs)
    written = []
    for e in figs.manifest():
        dst = OUT / (e["name"] + "_" + lang + ".png")
        shutil.copyfile(tmp / e["file"], dst)
        written.append(dst)
    return written


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    d = compute()
    # 本文の数字の門: ツアーの印字と同じ値か(ずれたら図を書かない)
    assert abs(d["gain_illum_product"] - 899.4) < 0.05, d["gain_illum_product"]
    assert d["gain_illum_theta_hat"] == {}
    f = d["film"]
    assert f["wrong_status"] == "refused" and f["wrong_failed"] == ["fit_consistent_with_noise"], f["wrong_failed"]
    assert f["right_status"] == "accepted" and f["right_failed"] == []
    assert abs(f["wrong_chi2_red"] - 60.4) < 0.05 and abs(f["wrong_theta"]["d"] - 356.5) < 0.05
    o = d["oof"]
    assert o["n_structural"] == 1 and o["in_family_n_structural"] == 0 and round(o["corr"], 2) == 0.99, o
    written = []
    for lang in ("ja", "en"):
        with tempfile.TemporaryDirectory() as td:
            written += draw(d, lang, Path(td))
    # ---- 第 2 回 ------------------------------------------------------------------- #
    os.environ.setdefault("FULLSEYE_POC_BUDGET", "full")
    q = compute_part2()
    for lang in ("ja", "en"):
        with tempfile.TemporaryDirectory() as td:
            written += draw_part2(q, lang, Path(td))
    nums = {k: v for k, v in d.items() if not k.startswith("_")}
    nums["part2"] = {k: v for k, v in q.items() if not k.startswith("_")}
    for k in ("nm", "observed", "spec_wrong", "spec_right"):
        nums["film"].pop(k)
    (OUT / "numbers.json").write_text(json.dumps(nums, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    for p in written:
        print(p.relative_to(ROOT).as_posix())
    print("product %.1f | wrong d %.1f chi2/nu %.1f -> %s %s | right d %.1f | oof corr %.3f sv1 %.0f edge %.1f"
          % (d["gain_illum_product"], f["wrong_theta"]["d"], f["wrong_chi2_red"], f["wrong_status"], f["wrong_failed"],
             f["right_theta"]["d"], o["corr"], o["sv"][0], o["edge"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
