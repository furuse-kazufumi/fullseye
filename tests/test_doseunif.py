# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""doseunif の門(粒径 → 1 回分の含量の CV → 必要な粉砕時間)。

numpy + scipy(常に走る):
 1. 閉形式 vs Monte Carlo(式を使わない経路)、Poisson と粒の数の固定
 2. 恒等式: 個数基準 ↔ 体積基準、CV ∝ d^{3/2}・D^{−1/2}・ρ^{1/2}、固定数の閉形式
 3. 体積基準の表 → D63³ = E_v[d³](形を仮定しない)vs 閉形式 1 % 以内
 4. 画像の標本の偏り: 縁の粒を捨てると低く、Miles–Lantuéjoul + 対数正規で戻る(独立な束)
 5. 逆算の往復(合成の Bond 則)と外挿・既達の印
 6. 合格の確率: χ² の閉形式 vs 模擬
 7. 綴り壊し・測れない入力は ValueError
 8. 入口: __all__ が実在、docstring に Markdown のリンク記法なし
実データ(環境変数 FULLSEYE_GRIND_DATA が無ければ skip):
 9. 63 本の D63 が有限・正、CV は 25 min < 3 min、対数正規の当てはめは中央値で 2 倍以上外れる
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

import doseunif as DU
import grind as G


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


# ── 1. 閉形式 vs Monte Carlo ──────────────────────────────────────────────
@pytest.mark.parametrize("sampling", ["poisson", "fixed_count"])
def test_closed_form_matches_monte_carlo(sampling):
    for d, s, D in ((40.0, 0.35, 0.02), (80.0, 0.3, 1.0)):
        r = DU.dose_cv_lognormal(d, s, D, 1.3, method="monte_carlo", sampling=sampling, n_rep=2000, seed=11)
        assert abs(r["cv_mc"] - r["cv_closed"]) < 4.0 * r["cv_mc_se"], (d, s, D, sampling)
        assert r["cv"] == r["cv_mc"] and r["draws"] > 0 and r["dose_mean_mg"] == pytest.approx(D, rel=0.02)


# ── 2. 恒等式 ─────────────────────────────────────────────────────────────
def test_identities_and_scaling():
    a = DU.dose_cv_lognormal(30.0, 0.4, 0.05, 1.5)
    b = DU.dose_cv_lognormal(a["d_volume_median"], 0.4, 0.05, 1.5, basis="volume")
    assert b["cv"] == pytest.approx(a["cv"], rel=1e-13) and a["d_volume_median"] == pytest.approx(30 * math.exp(3 * 0.16), rel=1e-14)
    assert DU.dose_cv_lognormal(60.0, 0.4, 0.05, 1.5)["cv"] / a["cv"] == pytest.approx(2 ** 1.5, rel=1e-13)
    assert DU.dose_cv_lognormal(30.0, 0.4, 0.2, 1.5)["cv"] / a["cv"] == pytest.approx(0.5, rel=1e-13)
    assert DU.dose_cv_lognormal(30.0, 0.4, 0.05, 6.0)["cv"] / a["cv"] == pytest.approx(2.0, rel=1e-13)
    hand = math.sqrt(math.pi * 1.5e-9 * a["d_volume_median"] ** 3 * math.exp(4.5 * 0.16) / (6 * 0.05))
    assert hand == pytest.approx(a["cv"], rel=1e-13)
    f = DU.dose_cv_lognormal(30.0, 0.4, 0.05, 1.5, sampling="fixed_count")
    assert f["cv"] ** 2 == pytest.approx((math.exp(9 * 0.16) - 1) / f["particles_per_dose"], rel=1e-13)
    assert a["d63"] ** 3 == pytest.approx(30 ** 3 * math.exp(13.5 * 0.16), rel=1e-13)


# ── 3. 表の恒等式 ───────────────────────────────────────────────────────
def test_size_table_identity_matches_closed_form():
    for d50, s in ((30.0, 0.4), (100.0, 0.5), (8.0, 0.6)):
        p = G.particle_size_synth(d50, s)
        h = DU.dose_cv_from_sizes(p, 0.05, 1.3)
        c = DU.dose_cv_lognormal(d50, s, 0.05, 1.3, basis="volume")
        assert h["source"] == "psd" and h["estimator"] == "histogram" and h["ci_bootstrap"] is None
        assert 0.0 < h["cv_histogram"] / c["cv"] - 1 < 0.01          # 区間の離散化は一様に + 側(実測 +0.6 %)
        assert abs(h["cv_lognormal"] / c["cv"] - 1) < 0.01
        assert 0.0 < h["coarse_share"] < 1.0 and h["particles_per_dose"] == pytest.approx(c["particles_per_dose"], rel=0.03)


# ── 4. 画像の標本の偏り(軽い版: 16 束 × 8 枚。PoC は 60 束 × 12 枚)──────────
def test_image_sample_bias_and_edge_correction():
    D, rho, sig, dm = 0.02, 1.3, 0.35, 24.0
    true = DU.dose_cv_lognormal(dm, sig, D, rho)["cv"]
    raw, fixed = [], []
    for b in range(16):
        ds = []
        for s in range(8):
            im = G.particle_image_synth(n=60, d_med=dm, sigma_ln=sig, shape=(256, 256), pitch=2.0, seed=50_000 + 100 * b + s)
            ds.append(G.particle_image_d50(im["image"], 2.0, basis="number")["diameters"])
        d = np.concatenate(ds)
        raw.append(DU.dose_cv_from_sizes(d, D, rho, estimator="moment", n_boot=50)["cv"] / true)
        r = DU.dose_cv_from_sizes(d, D, rho, frame=(256, 256, 2.0), n_boot=50)
        fixed.append(r["cv"] / true)
        assert r["edge_corrected"] and r["ci_delta"][0] < r["cv"] < r["ci_delta"][1] and 0 < r["top1pct_share_d6"] < 1
    assert np.mean(raw) < 0.98                        # 縁の粒を捨てると大粒が抜けて低い
    assert abs(np.mean(fixed) - 1) < 0.04 and np.std(fixed) < np.std(raw)


# ── 5. 逆算 ─────────────────────────────────────────────────────────────
def test_inverse_round_trip_and_flags():
    x0, k = 400.0, 0.004
    tt = np.array([0, 5, 10, 20, 40.0])
    d = np.array([G.comminution_energy(x0, law="bond", energy=k * t)["x_product"] for t in tt])
    g = DU.grind_time_for_dose_cv(tt, d, 5.0, 1.5, target_cv=0.05, law="bond")
    d_req = (0.05 ** 2 * 5.0 / (math.pi / 6 * 1.5e-9)) ** (1 / 3)
    assert g["d63_req"] == pytest.approx(d_req, rel=1e-13)
    assert g["t_req"] == pytest.approx((d_req ** -0.5 - x0 ** -0.5) / (0.5 * k), rel=1e-6) and not g["extrapolated"]
    assert DU.grind_time_for_dose_cv(tt, d, 5.0, 1.5, target_cv=0.005, law="bond")["extrapolated"]
    g0 = DU.grind_time_for_dose_cv(tt, d, 5.0, 1.5, target_cv=0.5)
    assert g0["t_req"] == 0.0 and g0["already_met"]
    assert g["cv_observed"].shape == tt.shape and np.all(np.diff(g["cv_observed"]) < 0)


# ── 6. 合格の確率 ───────────────────────────────────────────────────────
def test_pass_probability_closed_form_and_simulation():
    tt = np.array([0, 5, 10.0])
    d = np.array([300.0, 200.0, 150.0])
    g = DU.grind_time_for_dose_cv(tt, d, 5.0, 1.5, ref_range=(0.0, 1e9), n_mc=40000)
    assert g["target_cv"] == pytest.approx(0.0625, rel=1e-12)
    assert abs(g["pass_probability_chi2"] - g["pass_probability_mc"]) < 0.01 and 0.55 < g["pass_probability_chi2"] < 0.58
    gm = DU.grind_time_for_dose_cv(tt, d, 5.0, 1.5, n_mc=40000)
    assert gm["pass_probability_mc"] < g["pass_probability_mc"]
    p95 = DU.grind_time_for_dose_cv(tt, d, 5.0, 1.5, pass_probability=0.95)
    assert p95["pass_probability_chi2"] == pytest.approx(0.95, abs=1e-9) and 0.044 < p95["target_cv"] < 0.047


# ── 7. fail-closed ──────────────────────────────────────────────────────
def test_spelling_breaks_fail_closed():
    psd = G.particle_size_synth(30.0, 0.4)
    tt, d = np.array([0, 5, 10.0]), np.array([300.0, 200.0, 150.0])
    assert all([
        _raises(DU.dose_cv_lognormal, 0.0, 0.4, 0.05, 1.5), _raises(DU.dose_cv_lognormal, 30.0, 0.4, 0.05, 1.5, basis="Number"),
        _raises(DU.dose_cv_lognormal, 30.0, 0.4, 0.05, 1.5, sampling="binomial"), _raises(DU.dose_cv_lognormal, 30.0, 2.5, 0.05, 1.5),
        _raises(DU.dose_cv_lognormal, 1.0, 0.4, 1000.0, 1.5, method="monte_carlo", n_rep=1000),
        _raises(DU.dose_cv_lognormal, 30.0, 0.4, 0.05, 1.5, method="monte_carlo", n_rep=10),
        _raises(DU.dose_cv_from_sizes, [10.0] * 9, 0.05, 1.5), _raises(DU.dose_cv_from_sizes, [[10.0] * 20], 0.05, 1.5),
        _raises(DU.dose_cv_from_sizes, [10.0] * 19 + [-1.0], 0.05, 1.5), _raises(DU.dose_cv_from_sizes, [10.0] * 20, 0.05, 1.5, ci=0.3),
        _raises(DU.dose_cv_from_sizes, np.full(20, 10.0), 0.05, 1.5, frame=(4, 4, 1.0)),
        _raises(DU.dose_cv_from_sizes, psd, 0.05, 1.5, estimator="moment"),
        _raises(DU.grind_time_for_dose_cv, tt, d, 5.0, 1.5, target_cv=0.05, pass_probability=0.5),
        _raises(DU.grind_time_for_dose_cv, tt, d, 5.0, 1.5, pass_probability=1.0),
        _raises(DU.grind_time_for_dose_cv, tt[:2], d[:2], 5.0, 1.5), _raises(DU.grind_time_for_dose_cv, tt, d, 5.0, 1.5, law="Bond"),
    ])


# ── 8. 入口 ─────────────────────────────────────────────────────────────
def test_entry_points_exist_and_docstrings_have_no_markdown_links():
    assert DU.__all__ == ["dose_cv_lognormal", "dose_cv_from_sizes", "grind_time_for_dose_cv"]
    for name in DU.__all__:
        doc = getattr(DU, name).__doc__ or ""
        assert doc.strip() and "](" not in doc, name
    assert "](" not in DU.__doc__


# ── 9. 実データ ─────────────────────────────────────────────────────────
@pytest.mark.skipif(not os.environ.get("FULLSEYE_GRIND_DATA"), reason="FULLSEYE_GRIND_DATA が無い(公開データは repo の外)")
def test_real_size_tables():
    root = Path(os.environ["FULLSEYE_GRIND_DATA"]) / "data_public" / "powder_size_distribution" / "exp2"
    files = sorted(root.glob("*/*/*.csv"))
    if not files:
        pytest.skip("粒度分布の CSV が無い")
    cv, ratio = {}, []
    for f in files:
        m = re.search(r"grind(\d+)min", f.name)
        if not m:
            continue
        h = DU.dose_cv_from_sizes(G.particle_size_read(str(f)), 5.0, 1.6)
        assert math.isfinite(h["d63"]) and h["d63"] > 0 and math.isfinite(h["cv"])
        cv[(f.parent.parent.name, f.parent.name, int(m.group(1)))] = h["cv"]
        ratio.append(h["cv_lognormal"] / h["cv_histogram"])
    assert len(cv) == 63
    assert all(cv[(mat, run, 25)] < cv[(mat, run, 3)] for (mat, run, mn) in cv if mn == 3)
    assert np.median(ratio) > 2.0                    # D16/D50/D84 の対数正規は粉砕した粉で使えない


# ── 10. docstring の呼び出し例が走る ─────────────────────────────────────────
def test_usage_example_in_the_module_docstring_runs(capsys):
    import textwrap

    import doseunif as _M
    doc = _M.__doc__
    i = doc.index("呼び出し例")
    block = doc[doc.index("::", i) + 2:]
    lines = []
    for ln in block.splitlines()[1:]:
        if ln.strip() and not ln.startswith("    "):
            break
        lines.append(ln)
    code = textwrap.dedent("\n".join(lines))
    assert code.count("\n") >= 8 and "print(" in code
    exec(compile(code, "<doseunif usage>", "exec"), {})
    out = capsys.readouterr().out.strip()
    assert out and "nan" not in out.lower() and "inf" not in out.lower()
