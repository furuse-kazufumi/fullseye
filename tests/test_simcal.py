# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sim-to-real 較正の中核(simcal.py、opssimcal の model / fit)の門 —— 決まらない係数を黙って返さないこと。

* G2(同定不能の検出): 利得 x 照明(積しか決まらない)、単波長の薄膜(n と d は n^1 * d^~1 の組しか決まらない)、
  平らな像のボケ(効かないつまみ)を、点推定を出さずに名指しで拒否する。★探針: 交絡を消す(照明を固定する /
  31 波長にする / チャートを撮る)と同じ門が「拒否しない」側に倒れる —— 門が片側だけで通っていないことを両向きで確かめる。
* 物理の経路で作った合成の観測(ポアソンの電子 + 読み出し雑音 + 丸め、分散の式を往復させない)から真値へ戻る。
* EMVA 1288 の雑音モデル: simcal の分散の式が sensorchar.emva_snr_curve(式 21)の SNR と一致する(独立に書かれた 2 本)。
* 観測: 位相相関で整数画素のずれを戻し、巻き込んだ縁を外す。露出正規化と利得つまみの同時は拒否。
* 確率的な順方向モデル: 共通乱数の種で模型が決定的、標本の分散を雑音に足すと reduced chi^2 が 1 に戻る。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import simcal as sc  # noqa: E402
from metriccontract import MetricContractError  # noqa: E402

K, SD = 0.5, 6.0
NOISE_DARK64 = {"kind": "emva", "K": K, "sigma_d": SD, "dark": 64.0}


def capture(model, theta, seed, offset=64.0):
    rng = np.random.default_rng(seed)
    return [sc._physical_capture(y, offset, K, SD, rng) for y in sc.simcal_simulate(model, theta)]


def gain_illum_model(fix_illum=False):
    return sc.simcal_model(
        chain=[{"op": "stage:scale"}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
        knobs=[{"name": "illum", "step": 0, "arg": "factor", "lo": 0.2, "hi": 5.0, "scale": "log",
                "fixed": 1.5 if fix_illum else None},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log", "unit": "DN"}],
        scene=sc._chart(32), noise=NOISE_DARK64)


def film_model(nm):
    return sc.simcal_model(
        chain=[{"op": "thin_film_reflectance", "args": {"n_sub": 3.88}},
               {"op": "stage:as_image", "args": {"shape": (8, 8)}},
               {"op": "stage:gain_offset", "args": {"gain": 1000.0, "offset": 64.0}}],
        knobs=[{"name": "n_film", "step": 0, "arg": "n_film", "lo": 1.3, "hi": 1.7, "scale": "log"},
               {"name": "d", "step": 0, "arg": "thickness_nm", "lo": 300.0, "hi": 700.0, "scale": "log", "unit": "nm"}],
        scene=np.asarray(nm, dtype=float), noise=NOISE_DARK64)


def blur_model(scene):
    return sc.simcal_model(
        chain=[{"op": "stage:gaussian_blur"}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
        knobs=[{"name": "sigma", "step": 0, "arg": "sigma", "lo": 0.3, "hi": 3.0, "unit": "px"},
               {"name": "gain", "step": 1, "arg": "gain", "lo": 100.0, "hi": 3000.0, "scale": "log"}],
        scene=scene, noise=NOISE_DARK64)


# --------------------------------------------------------------------------- #
# G2: 決まらない係数を黙って返さない(両向き)                                   #
# --------------------------------------------------------------------------- #
def g2_refuses(model, truth, seed=1, **fit_kw):
    """門: 当てはめが点推定を出さずに拒否するか(True)/ 全部に値を返すか(False)。"""
    mo = sc.simcal_observe(model, capture(model, truth, seed))
    try:
        sc.simcal_fit(mo, **fit_kw)
    except MetricContractError:
        return True
    return False


def test_g2_gain_times_illumination_is_refused_and_the_product_is_reported():
    m = gain_illum_model()
    truth = {"illum": 1.5, "gain": 600.0}
    mo = sc.simcal_observe(m, capture(m, truth, 1))
    with pytest.raises(MetricContractError) as e:
        sc.simcal_fit(mo)
    msg = str(e.value)
    assert "illum" in msg and "gain" in msg and "confounded" in msg and "illum^1 * gain^1" in msg
    r = sc.simcal_fit(mo, allow_undetermined=True)
    assert r["status"] == "partial" and r["theta_hat"] == {}                       # 値は 1 つも出さない
    assert set(r["undetermined"]) == {"illum", "gain"}
    combo = r["determined_combos"][0]
    assert combo["combination"] == "illum^1 * gain^1"
    assert abs(combo["value"]["product"] / 900.0 - 1) < 0.005                        # 積は決まる(真値 1.5 x 600)
    # 探針: 照明を固定すれば交絡は消え、同じ門は拒否しない側に倒れる
    assert g2_refuses(m, truth) is True
    assert g2_refuses(gain_illum_model(fix_illum=True), {"gain": 600.0}) is False


def test_g2_single_wavelength_film_fixes_only_n_times_d():
    truth = {"n_film": 1.46, "d": 520.0}
    m1 = film_model([550.0])
    mo = sc.simcal_observe(m1, capture(m1, truth, 2))
    r = sc.simcal_fit(mo, allow_undetermined=True)
    assert r["theta_hat"] == {} and set(r["undetermined"]) == {"n_film", "d"}
    c = r["determined_combos"][0]
    w = c["weights"]
    assert abs(w["n_film"] - 1.0) < 1e-9 and 0.9 < w["d"] < 1.05, w          # n^1 * d^~1(位相 4 pi n d / lambda)
    # 探針: 31 波長(400-700 nm)では n と d が別々に決まる(交絡が消える → 拒否しない)
    m31 = film_model(np.linspace(400.0, 700.0, 31))
    assert g2_refuses(m1, truth, seed=2) is True
    assert g2_refuses(m31, truth, seed=2, method="multistart") is False
    r31 = sc.simcal_fit(sc.simcal_observe(m31, capture(m31, truth, 2)), method="multistart")
    assert abs(r31["theta_hat"]["n_film"] - 1.46) < 0.02 and abs(r31["theta_hat"]["d"] - 520.0) < 8.0


def test_g2_a_knob_without_influence_is_refused():
    flat = np.full((24, 24), 0.8)
    truth = {"sigma": 1.2, "gain": 900.0}
    m = blur_model(flat)
    mo = sc.simcal_observe(m, capture(m, truth, 3))
    with pytest.raises(MetricContractError, match="no_influence"):
        sc.simcal_fit(mo)
    r = sc.simcal_fit(mo, allow_undetermined=True)
    assert "sigma" not in r["theta_hat"] and "gain" in r["theta_hat"]
    assert r["undetermined"]["sigma"].startswith("no_influence")
    scr = sc.simcal_screen(m)
    assert scr["class"]["sigma"] == "no_influence" and scr["class"]["gain"] == "determined"
    # 探針: チャート(縁がある像)ならボケは決まる
    assert g2_refuses(blur_model(sc._chart(24)), truth, seed=3) is False


def test_screen_classes_and_output_dims():
    s = sc.simcal_screen(gain_illum_model())
    assert s["class"] == {"illum": "combination", "gain": "combination"}
    assert s["gamma_full"] is None                                                  # gamma = inf -> None(有限でない数は出さない)
    d = sc.simcal_screen(sc.simcal_model())
    assert set(d["class"].values()) == {"determined"} and d["output_dims"] >= 3 and not d["more_knobs_than_dims"]
    ds = sc.simcal_screen(sc.simcal_model(), method="sobol", size=4)
    assert set(ds["gsi_st"]) == {"f", "gain", "offset"} and min(ds["gsi_st"].values()) > 1e-3


# --------------------------------------------------------------------------- #
# 当てはめ                                                                       #
# --------------------------------------------------------------------------- #
def test_demo_fit_recovers_the_truth_from_physical_captures():
    m = sc.simcal_model()
    r = sc.simcal_fit(m)
    assert r["status"] == "accepted" and r["fit"]["converged"]
    t = m["truth"]
    assert abs(r["theta_hat"]["f"] - t["f"]) < 0.5
    assert abs(r["theta_hat"]["gain"] / t["gain"] - 1) < 0.01
    assert abs(r["theta_hat"]["offset"] - t["offset"]) < 3.0
    assert 0.85 < r["fit"]["chi2_red"] < 1.15                                       # 残差は雑音そのもの
    for meth in ("nm", "multistart"):
        r2 = sc.simcal_fit(m, method=meth)
        for k in t:
            assert abs(r2["theta_hat"][k] - r["theta_hat"][k]) <= 0.02 * abs(r["theta_hat"][k]) + 0.05, (meth, k)


def test_fit_refuses_without_noise_or_data_and_at_the_edge():
    m = sc.simcal_model()
    bare = sc.simcal_model(chain=m["chain"], knobs=[dict(k) for k in m["knobs"]], scene=m["scene"])
    with pytest.raises(MetricContractError, match="observed"):
        sc.simcal_fit(bare)
    obs_no_noise = sc.simcal_observe(bare, m["observed"]["images"])
    with pytest.raises(MetricContractError, match="noise"):
        sc.simcal_fit(obs_no_noise)
    with pytest.raises(MetricContractError, match="noise"):
        sc.simcal_screen(obs_no_noise)
    # 真値が範囲の外(f = 22 を 30..60 に閉じ込める)→ 端に張りつく → 拒否
    knobs = [dict(k) for k in m["knobs"]]
    knobs[0].update(lo=30.0, hi=60.0, init=45.0)
    tight = sc.simcal_model(chain=m["chain"], knobs=knobs, scene=m["scene"], noise=m["noise"])
    tight = sc.simcal_observe(tight, m["observed"]["images"])
    with pytest.raises(MetricContractError, match="at_bound"):
        sc.simcal_fit(tight)


def test_local_minimum_is_flagged_by_reduced_chi_square():
    """31 波長の膜は干渉次数ごとに谷がある。小さな計画からの LM は違う次数に落ちうる —— その時は chi^2 が告げる。"""
    truth = {"n_film": 1.46, "d": 520.0}
    m31 = film_model(np.linspace(400.0, 700.0, 31))
    mo = sc.simcal_observe(m31, capture(m31, truth, 2))
    bad = sc.simcal_fit(mo, n_starts=2, seed=0)
    assert bad["fit"]["chi2_red"] > 10 and abs(bad["theta_hat"]["d"] - 520.0) > 100     # 違う次数(実測 d = 357 nm)
    assert len(bad["fit"]["warnings"]) >= 1
    assert any("multistart" in w for w in bad["fit"]["warnings"])                       # 黙らない
    good = sc.simcal_fit(mo, method="multistart", n_starts=16, seed=0)
    assert good["fit"]["chi2_red"] < 1.5 and good["fit"]["warnings"] == []
    assert abs(good["theta_hat"]["d"] - 520.0) < 8.0


# --------------------------------------------------------------------------- #
# 模型・観測・雑音                                                                #
# --------------------------------------------------------------------------- #
def test_model_is_fail_closed():
    ok = dict(chain=[{"op": "stage:gain_offset"}], knobs=[{"name": "g", "arg": "gain", "lo": 1.0, "hi": 2.0}],
              scene=np.ones((4, 4)))
    sc.simcal_model(**ok)
    bad = [
        dict(ok, chain=[{"op": "no_such_op_anywhere"}]),
        dict(ok, knobs=[{"name": "g", "arg": "not_an_arg", "lo": 1.0, "hi": 2.0}]),
        dict(ok, knobs=[{"name": "g", "arg": "gain", "lo": 2.0, "hi": 1.0}]),
        dict(ok, knobs=[{"name": "g", "arg": "gain", "lo": -1.0, "hi": 2.0, "scale": "log"}]),
        dict(ok, knobs=[{"name": "g", "arg": "gain", "lo": 1.0, "hi": 2.0, "init": 3.0}]),
        dict(ok, knobs=[{"name": "g", "arg": "gain", "lo": 1.0, "hi": 2.0},
                        {"name": "h", "arg": "gain", "lo": 1.0, "hi": 2.0}]),
        dict(ok, noise={"kind": "poisson"}),
        dict(ok, noise={"kind": "emva", "K": 0.5, "sigma_d": 2.0, "dark": "no_such_knob"}),
        dict(ok, nuisance=["zz"]),
    ]
    for kw in bad:
        with pytest.raises(ValueError):
            sc.simcal_model(**kw)
    with pytest.raises(ValueError):
        sc.simcal_simulate(sc.simcal_model(**ok), {"nope": 1.0})
    with pytest.raises(ValueError):
        sc.simcal_simulate({})


def test_emva_variance_matches_sensorchar_snr_curve():
    import sensorchar
    eta, Kk, sd, dark = 0.6, 0.4, 7.0, 50.0
    m = sc.simcal_model(chain=[{"op": "stage:gain_offset"}], knobs=[{"name": "g", "arg": "gain", "lo": 1, "hi": 2}],
                        scene=np.ones((3, 3)), noise={"kind": "emva", "K": Kk, "sigma_d": sd, "dark": dark})
    mu_p = np.array([100.0, 1000.0, 20000.0])
    mu_y = dark + Kk * eta * mu_p
    var = sc._camera_var(m, mu_y, {"g": 1.5})
    snr = np.asarray(sensorchar.emva_snr_curve(mu_p, eta, sd, Kk))[:, 1]         # 列 = (mu_p, SNR, SNR_ideal)
    assert np.allclose((mu_y - dark) / np.sqrt(var), snr, rtol=1e-12)
    # 光子伝達の結果を雑音モデルとして受ける(sigma_d が推定できないときは上限を使う)
    ptc = {"K": 0.4, "sigma_d": None, "sigma_d_upper": 1.0, "dark": 50.0}
    m2 = sc.simcal_model(chain=m["chain"], knobs=[dict(k) for k in m["knobs"]], scene=m["scene"], noise=ptc)
    assert m2["noise"]["sigma_d"] == 1.0 and "upper" in m2["noise"]["sigma_d_source"]


def test_observe_aligns_masks_and_refuses_exposure_with_gain():
    m = sc.simcal_model()
    y = sc.simcal_simulate(m)[0]
    shifted = np.roll(y, (2, -3), axis=(0, 1))
    o = sc.simcal_observe(m, [shifted], align=True)
    assert o["observed"]["shifts"] == [(2, -3)]
    assert np.allclose(o["observed"]["images"][0][o["observed"]["mask"][0]], y[o["observed"]["mask"][0]])
    assert (~o["observed"]["mask"][0]).sum() == 2 * 24 + 3 * 24 - 2 * 3          # 巻き込んだ縁だけを外す
    with pytest.raises(MetricContractError, match="max_shift"):
        sc.simcal_observe(m, [np.roll(y, (9, 0), axis=(0, 1))], align=True, max_shift=4)
    with pytest.raises(MetricContractError, match="gain"):
        sc.simcal_observe(m, [y], exposure=[2.0])
    knobs = [dict(k) for k in m["knobs"]]
    knobs[1]["fixed"] = 900.0
    mf = sc.simcal_model(chain=m["chain"], knobs=knobs, scene=m["scene"], noise=m["noise"])
    of = sc.simcal_observe(mf, [2 * y], exposure=[2.0])
    assert np.allclose(of["observed"]["images"][0], y) and of["observed"]["var_scale"] == [0.25]
    with pytest.raises(ValueError):
        sc.simcal_observe(m, [y, y])
    with pytest.raises(ValueError):
        sc.simcal_observe(m, [y[:10]])
    roi = sc.simcal_observe(m, [y], roi=(2, 20, 3, 21))
    assert roi["observed"]["n_pixels"] == 18 * 18


def test_stochastic_model_common_random_numbers_and_sample_variance():
    def model(sample_var):
        return sc.simcal_model(
            chain=[{"op": "stage:mc_sample", "args": {"n_samples": 4}}, {"op": "stage:gain_offset", "args": {"offset": 64.0}}],
            knobs=[{"name": "gain", "step": 1, "arg": "gain", "lo": 1.0, "hi": 30.0, "scale": "log"}],
            scene=np.full((32, 32), 100.0), noise=NOISE_DARK64,
            stochastic={"seed": 11, "sample_var": sample_var, "n_rep": 64})
    m0, m1 = model(None), model("estimate")
    a, b = sc.simcal_simulate(m0, {"gain": 5.0}), sc.simcal_simulate(m0, {"gain": 5.0})
    assert np.array_equal(a[0], b[0])                                               # 共通乱数: 同じ種なら同じ絵
    assert not np.array_equal(a[0], sc.simcal_simulate(m0, {"gain": 5.0}, seed=12)[0])
    # 実物には標本雑音が無い(期待値 + カメラの雑音)。模型の標本雑音(DN で 5^2 x 100 / 4 = 625)は残差に乗る
    rng = np.random.default_rng(5)
    imgs = [sc._physical_capture(np.full((32, 32), 5.0 * 100.0 + 64.0), 64.0, K, SD, rng)]
    r0 = sc.simcal_fit(sc.simcal_observe(m0, imgs))
    r1 = sc.simcal_fit(sc.simcal_observe(m1, imgs))
    # 足さないと reduced chi^2 は (625 + 259) / 259 ~ 3.4、足すと ~1
    assert r0["fit"]["chi2_red"] > 2.5, r0["fit"]["chi2_red"]
    assert 0.8 < r1["fit"]["chi2_red"] < 1.25, r1["fit"]["chi2_red"]
    assert abs(r1["theta_hat"]["gain"] / 5.0 - 1) < 0.02


# --------------------------------------------------------------------------- #
# 台帳・公開経路・探針・要約                                                        #
# --------------------------------------------------------------------------- #
def test_ledger_public_tier_fuzzer_and_summaries():
    import fullseye as fs
    import opssimcal as osc
    import typed_catalog as tc
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opdocs
    names = list(sc.__all__)
    assert set(osc.list_ops("model")) | set(osc.list_ops("fit")) == set(names)
    assert osc.missing() == []
    rows = {r[0]: r for r in tc.catalog() if r[0] in names}
    assert set(rows) == set(names)
    gens = cf.make_generators()
    rng = np.random.default_rng(0)
    for t in ("simmodel", "calresult"):
        v = gens[t](rng)
        assert cf.TYPE_CHECKS[t](v), t
    # ★種は乱数を引かない(探針の種は型名の順に同じ乱数列から作られる)
    r1, r2 = np.random.default_rng(7), np.random.default_rng(7)
    gens["simmodel"](r1)
    gens["calresult"](r1)
    assert r1.random() == r2.random()
    assert not cf.TYPE_CHECKS["simmodel"]({"sort": "design"})
    assert not cf.TYPE_CHECKS["calresult"]({"sort": "calresult"})
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in names:
        assert hasattr(fs.ledger, name), name
        line = getattr(sc, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["simcal/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("ja", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)


def test_equal_magnitude_terms_keep_declaration_order_whatever_the_rounding_dust():
    """利得 × 照明のように |e| が等しい組の文字列は、1e-16 の屑の向きで入れ替わらない。

    2026-10-15、Windows では "illum^1 * gain^1"、CI の Linux では "gain^1 * illum^1" になり
    G2 の門が CI だけで赤になった(固有ベクトルの成分が丸めの屑だけ違う)。両向きの屑で同じ文字列。
    """
    knobs = [{"name": "illum", "scale": "log"}, {"name": "gain", "scale": "log"}]
    nrm = np.ones(2)
    base = np.array([1.0, 1.0]) / np.sqrt(2.0)
    texts = {sc._fmt_combo(base + np.array([d, -d]), nrm, knobs)[0] for d in (-1e-15, 0.0, 1e-15)}
    texts |= {sc._fmt_combo(-(base + np.array([d, -d])), nrm, knobs)[0] for d in (-1e-15, 1e-15)}
    assert texts == {"illum^1 * gain^1"}, texts
    # 本当に大きさが違えば、大きい方が先に来る(丸めは 1e-6 の相対まで)
    assert sc._fmt_combo(np.array([0.6, 0.8]), nrm, knobs)[0].startswith("gain^1")
