# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sim-to-real 較正の検査(simcalcheck.py、opssimcal の check / report)の門 —— 推定の妥当性・過適合・モデルの食い違い。

* G1(回収): 合成の真値 40 種(ラテン超方格、範囲の 5〜95 %)のうち 95 % 以上で、4 つのつまみ全部が
  |推定 − 真値| < 3 σ_CRLB。観測は物理の経路(ポアソンの電子 + 読み出し雑音 + 丸め)で作る。★探針: 雑音モデルの
  分散を 1/4 に見誤ると CRLB が半分になり、同じ門が赤になる(門が数えているのは雑音モデルの正しさでもある)。
* Cramér-Rao 下界は mathestimation.crlb_gaussian(直線の模型、既存の op)と一致する。
* プロファイル尤度(Raue ら 2009): ボケが小さすぎると上限しか言えない(当てはめは端で拒否、プロファイルは上限だけを返す)。
* G3: 8 次の周辺減光の多項式は当てはめで拒否され、無理に通しても過適合の門(自由なつまみ > 出力の次元)が拒否する。
  ★探針: 次元の門を外すと 8 次の多項式は他の門を全部すり抜ける —— 拒否しているのは次元の門だと確かめる。
  族の外のデータ(光軸のずれたレンズ)では、残差 PCA が雑音を越える構造を検出する。族の中では検出しない。
* LOCKED は 1 回だけ(2 回目は拒否)。Tracy-Widom 99 % の端は純雑音で 1 % 前後しか越えない。
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import doe  # noqa: E402
import simcal as sc  # noqa: E402
import simcalcheck as ck  # noqa: E402
from metriccontract import MetricContractError  # noqa: E402

K, SD = 0.5, 6.0


def capture(model, theta, seed, offset=None, **stage_over):
    m = model
    if stage_over:
        m = copy.deepcopy(model)
        for i, kw in stage_over.items():
            m["chain"][int(i)]["args"].update(kw)
    rng = np.random.default_rng(seed)
    off = theta["offset"] if offset is None else offset
    return [sc._physical_capture(y, off, K, SD, rng) for y in sc.simcal_simulate(m, theta)]


def g1_model(noise_K=K):
    return sc.simcal_model(
        chain=[{"op": "stage:gaussian_blur"}, {"op": "stage:radial_cos4"}, {"op": "stage:gain_offset"}],
        knobs=[{"name": "sigma", "step": 0, "arg": "sigma", "lo": 0.4, "hi": 2.5, "unit": "px"},
               {"name": "f", "step": 1, "arg": "f", "lo": 20.0, "hi": 120.0, "unit": "px"},
               {"name": "gain", "step": 2, "arg": "gain", "lo": 300.0, "hi": 3000.0, "unit": "DN", "scale": "log"},
               {"name": "offset", "step": 2, "arg": "offset", "lo": 20.0, "hi": 200.0, "unit": "DN"}],
        scene=sc._chart(48), noise={"kind": "emva", "K": noise_K, "sigma_d": SD * K / noise_K, "dark": "offset"})


def g1_coverage(model, n=40, seed=7):
    """門 G1: 真値 n 種のうち、全つまみが 3 sigma_CRLB に入った割合と z の表。"""
    knobs = model["knobs"]
    d = doe.doe_lhs(n, [(k["name"], 0.0, 1.0) for k in knobs], seed=seed)
    U = 0.05 + 0.9 * (d["coded"] + 1.0) / 2.0
    ok, zs = 0, []
    for i, u in enumerate(U):
        truth = {k["name"]: sc._from_u(float(u[j]), k) for j, k in enumerate(knobs)}
        mo = sc.simcal_observe(model, capture(model, truth, 1000 + i))
        r = sc.simcal_fit(mo, allow_undetermined=True)
        crlb = ck.simcal_identifiability(r, at=truth, profile=False)["identifiability"]["crlb"]
        z = {nm: (r["theta_hat"][nm] - truth[nm]) / crlb[nm] if nm in r["theta_hat"] else math.inf for nm in truth}
        zs.append(z)
        ok += all(abs(v) < 3.0 for v in z.values())
    return ok / n, zs


def test_g1_recovery_within_three_crlb_on_40_truths():
    frac, zs = g1_coverage(g1_model())
    assert frac >= 0.95, frac
    allz = np.array([[z[k] for k in ("sigma", "f", "gain", "offset")] for z in zs])
    assert np.isfinite(allz).all()
    assert 0.6 < allz.std() < 1.4                                          # z は標準正規に近い(CRLB に届いている)
    # 探針: 雑音の分散を 1/4 に見誤る(K を 1/4、暗雑音は電子で同じ DN)→ CRLB が半分 → 門が赤
    frac_bad, _ = g1_coverage(g1_model(noise_K=K / 4))
    assert frac_bad < 0.95, frac_bad


def test_crlb_matches_mathestimation_for_a_straight_line():
    import mathestimation
    x = np.linspace(0.0, 10.0, 25)
    sig = 0.7
    m = sc.simcal_model(chain=[{"op": "stage:gain_offset"}],
                        knobs=[{"name": "b", "arg": "gain", "lo": 0.1, "hi": 5.0},
                               {"name": "a", "arg": "offset", "lo": -5.0, "hi": 5.0}],
                        scene=x, noise={"kind": "gaussian", "sigma": sig})
    rng = np.random.default_rng(3)
    truth = {"a": 1.2, "b": 2.1}
    mo = sc.simcal_observe(m, [(truth["a"] + truth["b"] * x + sig * rng.standard_normal(x.size))[None, :]])
    r = sc.simcal_fit(mo)
    idf = ck.simcal_identifiability(r, at=truth, profile=False)["identifiability"]
    ref = mathestimation.crlb_gaussian(x, (truth["a"], truth["b"]), sig, model="line")
    assert abs(idf["crlb"]["a"] / ref["std"][0] - 1) < 1e-5 and abs(idf["crlb"]["b"] / ref["std"][1] - 1) < 1e-5


def test_profile_withdraws_a_one_sided_estimate():
    m = sc.simcal_model(
        chain=[{"op": "stage:gaussian_blur"}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
        knobs=[{"name": "sigma", "step": 0, "arg": "sigma", "lo": 0.0, "hi": 3.0, "unit": "px"},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log"}],
        scene=sc._chart(32), noise={"kind": "emva", "K": K, "sigma_d": SD, "dark": 64.0})
    truth = {"sigma": 0.12, "gain": 900.0}
    mo = sc.simcal_observe(m, capture(m, truth, 4, offset=64.0))
    r = sc.simcal_fit(mo, allow_undetermined=True)
    i = ck.simcal_identifiability(r)
    p = i["identifiability"]["profile"]
    assert p["gain"]["class"] == "determined"
    assert p["sigma"]["class"] == "upper_only" and p["sigma"]["lower"] is None and 0.12 < p["sigma"]["upper"] < 1.0
    # 当てはめは sigma = 0(範囲の端)に落ちて既に拒否している(at_bound)。プロファイルも同じ答え: 言えるのは上限だけ
    assert "sigma" not in i["theta_hat"] and i["undetermined"]["sigma"].split(":")[0] in ("at_bound", "profile")
    assert i["status"] == "partial" and "gain" in i["theta_hat"]


def test_identifiability_and_uncertainty_on_the_demo():
    r = sc.simcal_fit()
    i = ck.simcal_identifiability(r)
    p, crlb = i["identifiability"]["profile"], i["identifiability"]["crlb"]
    assert i["status"] == "accepted" and all(v["class"] == "determined" for v in p.values())
    for k, v in p.items():                                                  # ほぼ二次: 尤度比の区間 ~ +-1.96 CRLB
        assert abs((v["upper"] - v["lower"]) / (2 * 1.959964 * crlb[k]) - 1) < 0.1, k
        assert v["trace"] and all(np.isfinite(t).all() for t in v["trace"])
    lap = ck.simcal_uncertainty(i)["uncertainty"]
    boot = ck.simcal_uncertainty(i, method="bootstrap", n_boot=40, seed=1)["uncertainty"]
    for k in crlb:
        assert abs(lap["std"][k] / crlb[k] - 1) < 1e-6
        assert 0.6 < boot["std"][k] / lap["std"][k] < 1.5, k
    gl = sc.simcal_model(chain=[{"op": "stage:scale"}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
                         knobs=[{"name": "illum", "step": 0, "arg": "factor", "lo": 0.2, "hi": 5.0, "scale": "log"},
                                {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log"}],
                         scene=sc._chart(24), noise={"kind": "emva", "K": K, "sigma_d": SD, "dark": 64.0})
    rp = sc.simcal_fit(sc.simcal_observe(gl, capture(gl, {"illum": 1.5, "gain": 600.0}, 5, offset=64.0)),
                       allow_undetermined=True)
    with pytest.raises(MetricContractError, match="no point estimate"):
        ck.simcal_uncertainty(rp)
    ip = ck.simcal_identifiability(rp)
    assert ip["identifiability"]["condition"] is None or ip["identifiability"]["condition"] > 1e6
    assert ip["identifiability"]["warnings"]


# --------------------------------------------------------------------------- #
# G3: 過適合と族の外                                                              #
# --------------------------------------------------------------------------- #
FLAT = np.ones((40, 40))
CONDS = [{0: {"factor": e}} for e in (0.4, 0.7, 1.0, 1.4)]
NOISE = {"kind": "emva", "K": K, "sigma_d": SD, "dark": "offset"}
GO = [{"name": "gain", "step": 2, "arg": "gain", "lo": 300.0, "hi": 3000.0, "unit": "DN", "scale": "log"},
      {"name": "offset", "step": 2, "arg": "offset", "lo": 20.0, "hi": 200.0, "unit": "DN"}]
TRUTH = {"f": 40.0, "gain": 1200.0, "offset": 80.0}


def cos4_model():
    return sc.simcal_model(chain=[{"op": "stage:scale"}, {"op": "stage:radial_cos4"}, {"op": "stage:gain_offset"}],
                           knobs=[{"name": "f", "step": 1, "arg": "f", "lo": 15.0, "hi": 150.0, "unit": "px"}] + GO,
                           scene=FLAT, conditions=CONDS, noise=NOISE)


def poly8_model():
    return sc.simcal_model(chain=[{"op": "stage:scale"}, {"op": "stage:radial_poly"}, {"op": "stage:gain_offset"}],
                           knobs=[{"name": "c%d" % k, "step": 1, "arg": "c%d" % k, "lo": -2.0, "hi": 2.0, "init": 0.0}
                                  for k in range(1, 9)] + GO,
                           scene=FLAT, conditions=CONDS, noise=NOISE)


def test_g3_eighth_order_vignetting_polynomial_is_rejected():
    A = cos4_model()
    tr, ho = capture(A, TRUTH, 1), capture(A, TRUTH, 10001)
    good = ck.simcal_validate(sc.simcal_fit(sc.simcal_observe(A, tr)), ho)
    assert good["status"] == "accepted" and good["validation"]["passed"], good["validation"]["failed"]
    B = poly8_model()
    mb = sc.simcal_observe(B, tr)
    with pytest.raises(MetricContractError, match="confounded"):
        sc.simcal_fit(mb)                                                        # 1 段目: 当てはめが拒否
    forced = sc.simcal_fit(mb, allow_undetermined=True)
    v = ck.simcal_validate(forced, ho)
    assert v["status"] == "refused" and "knobs_within_dims" in v["validation"]["failed"]   # 2 段目: 過適合の門
    assert v["validation"]["output_dims"] < 10 and v["theta_hat"] == {}
    # 探針: 次元の門を外す(dims を大きく与える)と、8 次の多項式は残りの門を全部すり抜ける
    loose = ck.simcal_validate(forced, ho, dims=100)
    assert loose["validation"]["failed"] == [], loose["validation"]["failed"]


def test_g3_residual_pca_detects_an_out_of_family_lens():
    A = cos4_model()
    centre = (39 / 2.0 + 5.0, 39 / 2.0 - 4.0)
    tr = capture(A, TRUTH, 2, **{"1": {"cx": centre[0], "cy": centre[1]}})
    r = sc.simcal_fit(sc.simcal_observe(A, tr))
    d = ck.simcal_discrepancy(r)["discrepancy"]
    assert d["verdict"] == "structure" and d["n_structural"] >= 1 and d["optimistic_uncertainty"]
    assert d["mode"] == "conditions_x_pixels"
    # 残差の第 1 成分の形は「ずれた減光 - 中心の減光」と強く相関する
    true_v = sc._st_radial_cos4(FLAT, TRUTH["f"], *centre)
    fit_v = sc._st_radial_cos4(FLAT, r["theta_hat"]["f"])
    diff = TRUTH["gain"] * true_v - r["theta_hat"]["gain"] * fit_v
    corr = abs(np.corrcoef(d["loading_maps"][0].ravel(), diff.ravel())[0, 1])
    assert corr > 0.8, corr
    # 族の中: 構造なし
    tr_in = capture(A, TRUTH, 3)
    d_in = ck.simcal_discrepancy(sc.simcal_fit(sc.simcal_observe(A, tr_in)))["discrepancy"]
    assert d_in["verdict"] == "white" and d_in["n_structural"] == 0


def test_tracy_widom_edge_false_positive_rate():
    rng = np.random.default_rng(0)
    for n, p in ((4, 1600), (40, 40)):
        e = ck._tw_edge(n, p, 0.99)
        hits = sum(np.linalg.svd(rng.standard_normal((n, p)), compute_uv=False)[0] > e for _ in range(300))
        assert hits / 300 < 0.04, (n, p, hits)
        assert e > math.sqrt(n) + math.sqrt(p)                                 # 素の Marchenko-Pastur の端より外


def demo_capture(offset):
    """例の模型の真値で撮り直す(robust.py の分割: OBSERVED = 種 + 10000、LOCKED = 種 + 20000)。"""
    m = sc.simcal_model()
    t = m["truth"]
    rng = np.random.default_rng(sc._RNG_SEED_DEMO + offset)
    return [sc._physical_capture(y, t["offset"], 0.5, 6.0, rng) for y in sc.simcal_simulate(m, t)]


def test_locked_split_is_scored_once_and_holdout_images_are_accepted():
    r = sc.simcal_fit()
    locked = demo_capture(20000)
    v = ck.simcal_validate(r, holdout=demo_capture(10000), locked=locked)
    assert v["errors"]["locked"] is not None and 0.7 < v["errors"]["locked"] < 1.4
    with pytest.raises(MetricContractError, match="LOCKED"):
        ck.simcal_validate(v, holdout=locked, locked=locked)


def test_stochastic_model_without_sample_variance_is_noted():
    m = sc.simcal_model(
        chain=[{"op": "stage:mc_sample", "args": {"n_samples": 4}}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
        knobs=[{"name": "gain", "step": 1, "arg": "gain", "lo": 1.0, "hi": 30.0, "scale": "log"}],
        scene=np.full((32, 32), 100.0), noise={"kind": "emva", "K": K, "sigma_d": SD, "dark": 64.0},
        stochastic={"seed": 11})
    rng = np.random.default_rng(5)
    imgs = [sc._physical_capture(np.full((32, 32), 564.0), 64.0, K, SD, rng)]
    d = ck.simcal_discrepancy(sc.simcal_fit(sc.simcal_observe(m, imgs)))["discrepancy"]
    assert any("sample variance" in n for n in d["notes"])


def test_report_lists_what_was_not_run():
    r = sc.simcal_fit()
    rep = ck.simcal_report(r)
    assert rep["status"] == "accepted" and rep["gates"]["validation"] == "not run"
    assert {row["class"] for row in rep["rows"]} == {"estimated"} and "not run" in rep["text"]
    full = ck.simcal_report(ck.simcal_discrepancy(ck.simcal_validate(ck.simcal_identifiability(r), demo_capture(10000))))
    assert "not run" not in full["text"] and full["gates"]["discrepancy"]["passed"]
    with pytest.raises(ValueError):
        ck.simcal_report({})


def test_ledger_public_tier_fuzzer_and_summaries():
    import fullseye as fs
    import opssimcal as osc
    import typed_catalog as tc
    sys.path.insert(0, str(ROOT / "tools"))
    import opdocs
    names = list(ck.__all__)
    assert set(osc.list_ops("check")) | set(osc.list_ops("report")) == set(names)
    assert osc.missing() == []
    rows = {r[0]: r for r in tc.catalog() if r[0] in names}
    assert set(rows) == set(names)
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in names:
        assert hasattr(fs.ledger, name), name
        line = getattr(ck, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["simcal/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("ja", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)


def test_wrong_fringe_order_is_not_rejected_by_the_validation_gates_only_warned():
    """★穴の固定(2026-10-15): 隣の干渉次数に落ちた当てはめ(χ²/自由度 60)は、§6 の過適合の門 5 つを全部通る。

    門はどれも相対比較(初期値より良い・保留 / 学習・利得と黒レベルだけの模型より良い・範囲・次元)で、
    「雑音の何倍外れているか」の絶対の門が無いから。いまこの誤りを告げるのは fit.warnings(χ² が雑音の
    +4 sd を超える)だけ —— 1 x 31 の画像は残差 PCA にも小さすぎる。絶対の χ² の門を足したらこの assert を反転する。
    """
    sys.path.insert(0, str(ROOT / "tests"))
    import test_simcal as T
    truth = {"n_film": 1.46, "d": 520.0}
    m = T.film_model(np.linspace(400.0, 700.0, 31))
    mo = sc.simcal_observe(m, T.capture(m, truth, 2))
    wrong = sc.simcal_fit(mo, n_starts=2, seed=0)
    assert wrong["fit"]["chi2_red"] > 10 and len(wrong["fit"]["warnings"]) >= 1
    v = ck.simcal_validate(wrong, T.capture(m, truth, 10002))
    assert v["status"] == "accepted" and v["validation"]["failed"] == []          # 門は通してしまう(穴)
    assert v["errors"]["holdout"] > 10                                            # 数は残っている
    with pytest.raises(MetricContractError, match="too small"):
        ck.simcal_discrepancy(wrong)
