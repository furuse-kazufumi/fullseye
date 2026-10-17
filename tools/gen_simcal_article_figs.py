# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Qiita の sim-to-real 較正シリーズ(第 1 回)の図を、examples の simcal ツアーと同じ組み立てで作る。

    py -3.11 tools/gen_simcal_article_figs.py

出力: docs/articles/assets/qiita_simcal_series/<図>_{ja,en}.png と numbers.json(本文の数字の出どころ)。
図はすべて Fullseye 自身の描画(examplefig = annotate 族)で引く。真値・門の値は破線で描く。

数字の照合: 本文に書いた数字は numbers.json と、examples/simcal_tour.py・simcal_checks_tour.py の
実行ログの両方に一致させる(同じ模型・同じ乱数の種)。干渉次数の門の表だけは、ツアーが保留画像を
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
    nums = {k: v for k, v in d.items() if not k.startswith("_")}
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
