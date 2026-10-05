# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""grind の門(乳鉢の粉砕を測る: 粒度分布の D10/D50/D90、粉砕則、一次の破砕速度、独立試行、AE の帯域電力、画像からの D50)。

numpy だけの門(常に走る):
 1. 粉砕則の閉形式(Reddy の式 (5)〜(7))と一般式の n = 1 / 1.5 / 2、作業指数の形、エネルギー ↔ 径の往復、無限大の供給
 2. 対数正規の体積分布 → D10/D50/D90(log_edges)1 %、lower_cumsum は 1 区間(−11.98 %)小さい
 3. 則の当てはめの往復(雑音なし)と、x0 が要らない当てはめは inf を返す
 4. 一次の破砕速度の往復と S = a x^α
 5. AE の帯域電力: 正弦波で A²、帯の外は 0、Parseval
 6. 独立試行の比較の z と cv
 7. 画像の粒子 → D10/D50/D90(体積基準・個数基準、縁の規約を揃えた真値)0.5 %
 8. CSV の往復と壊れた入力
 9. 綴り壊しと測れない入力は ValueError
10. 入口: __all__ が実在、docstring に Markdown のリンク記法なし
実データの門(環境変数 FULLSEYE_GRIND_DATA が無ければ skip):
11. 装置の Dx(50) = log_edges(全ファイル)、Kick はどの材料でも最良にならない
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

import grind as G


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    return False


# ── 1. 粉砕則の閉形式 ─────────────────────────────────────────────────────
def test_comminution_closed_forms_and_round_trip():
    C = 3.0
    assert G.comminution_energy(500, 50, law="kick", C=C)["E"] == pytest.approx(C * math.log(10), rel=1e-14)
    eb = G.comminution_energy(500, 50, law="bond", C=C)["E"]
    assert eb == pytest.approx(2 * C * (1 / math.sqrt(50) - 1 / math.sqrt(500)), rel=1e-14)
    er = G.comminution_energy(500, 50, law="rittinger", C=C)["E"]
    assert er == pytest.approx(C * (1 / 50 - 1 / 500), rel=1e-14)
    assert G.comminution_energy(500, 50, law="walker", n=1.5, C=C)["E"] == pytest.approx(eb, rel=1e-14)
    assert G.comminution_energy(500, 50, law="walker", n=2.0, C=C)["E"] == pytest.approx(er, rel=1e-14)
    assert G.comminution_energy(500, 50, law="walker", n=1 + 1e-7, C=C)["E"] == pytest.approx(C * math.log(10), rel=1e-6)
    assert G.comminution_energy(2000, 100, law="bond_wi", C=12.0)["E"] == pytest.approx(120 * (0.1 - 1 / math.sqrt(2000)), rel=1e-14)
    for law in G.LAWS:
        e = G.comminution_energy(500, 50, law=law, C=C)["E"]
        assert G.comminution_energy(500, law=law, C=C, energy=e)["x_product"] == pytest.approx(50, rel=1e-12)
    assert G.comminution_energy(math.inf, 100, law="rittinger", C=2.0)["E"] == pytest.approx(0.02, rel=1e-14)


# ── 2. 対数正規 → Dx ─────────────────────────────────────────────────────
def test_lognormal_synth_dx_and_the_lower_cumsum_bias():
    errs = []
    for d50, s in ((30.0, 0.4), (100.0, 0.5), (200.0, 0.3), (8.0, 0.6)):
        p = G.particle_size_synth(d50, s)
        for q, k in ((10, "d10"), (50, "d50"), (90, "d90")):
            errs.append(abs(G.particle_size_dx(p, q) / p["truth"][k] - 1))
        b = G.particle_size_dx(p, 50, "lower_cumsum") / G.particle_size_dx(p) - 1
        assert b == pytest.approx(1 / G.INSTRUMENT_RATIO - 1, abs=0.01)
        assert G.particle_size_oversize(p, d50) == pytest.approx(0.5, abs=0.01)
    assert len(errs) == 12
    assert max(errs) < 0.01


# ── 3. 則の当てはめ ─────────────────────────────────────────────────────
def test_law_fit_round_trip_and_infinite_feed():
    t = np.repeat([0.8, 1.4, 1.8, 2.6, 4.0, 5.4, 6.6], 3)
    for law in G.LAWS:
        k = G.comminution_energy(400.0, x_product=80.0, law=law)["E"] / t.max()
        x = np.array([G.comminution_energy(400.0, law=law, energy=k * tt)["x_product"] for tt in t])
        r = G.comminution_law_fit(t, x)
        assert r["best_fixed"] == law and r["n_points"] == 21
        f = r["fits"][law]
        assert f["rms_log"] < 1e-9 and f["k"] == pytest.approx(k, rel=1e-7) and f["x0"] == pytest.approx(400, rel=1e-7)
        assert r["fits"]["walker"]["n"] == pytest.approx(G.LAWS[law], abs=0.02)
    # 供給の項が要らない世界(x0 = inf の Rittinger)
    x = np.array([G.comminution_energy(math.inf, law="rittinger", energy=0.01 * tt)["x_product"] for tt in t])
    assert math.isinf(G.comminution_law_fit(t, x, law="rittinger")["fits"]["rittinger"]["x0"])


# ── 4. 一次の破砕速度 ─────────────────────────────────────────────────────
def test_first_order_breakage_round_trip():
    tt = np.array([0.8, 1.4, 1.8, 2.6, 4.0, 5.4, 6.6])
    xs = np.array([150.0, 250.0, 400.0])
    S = 0.05 * (xs / 100) ** 0.8
    b = G.breakage_first_order_fit(tt, 0.6 * np.exp(-S[:, None] * tt), x=xs)
    assert np.allclose(b["S_per_x"], S, rtol=1e-12) and b["alpha"] == pytest.approx(0.8, abs=1e-10) and b["apparent"]
    one = G.breakage_first_order_fit(tt, 0.6 * np.exp(-0.1 * tt))
    assert one["S"] == pytest.approx(0.1, rel=1e-12) and one["w0"] == pytest.approx(0.6, rel=1e-12)
    assert one["S_early"] == pytest.approx(one["S_late"], rel=1e-10)
    slow = G.breakage_first_order_fit(tt, 0.6 * np.exp(-0.3 * np.sqrt(tt)))     # 遅くなる = 一次から外れる
    assert slow["S_early"] > slow["S_late"]


# ── 5. AE ───────────────────────────────────────────────────────────────
def test_ae_band_power_tone_and_parseval():
    n, fs, A = 400000, 2e6, 0.05
    t = np.arange(n) / fs
    p = G.ae_band_power(A * np.sin(2 * np.pi * 300e3 * t), fs)
    assert p["power_fft"] == pytest.approx(A ** 2, rel=1e-9) and p["ratio"] == pytest.approx(1.0, abs=1e-3)
    assert G.ae_band_power(A * np.sin(2 * np.pi * 50e3 * t), fs)["power_fft"] < 1e-9 * A ** 2
    w = G.ae_band_power(np.random.default_rng(0).normal(0, 0.01, n), fs)
    assert w["ratio"] == pytest.approx(1.0, abs=0.05)
    assert w["band_series"].size == w["times"].size > 10
    c = G.ae_size_correspondence([10.0, 5.0, 2.0, 30.0, 8.0], [300.0, 150.0, 40.0, 320.0, 60.0], ["a", "a", "a", "b", "b"])
    assert c["groups"]["a"]["sign_agree"] == 1.0 and c["groups"]["a"]["spearman"] == pytest.approx(1.0)
    assert c["groups"]["b"]["n"] == 2 and c["pooled"]["n"] == 5


# ── 6. 独立試行 ─────────────────────────────────────────────────────────
def test_replicate_compare():
    rng = np.random.default_rng(4)
    a = 100 * np.exp(rng.normal(0, 0.05, (3, 7)))
    b = 50 * np.exp(rng.normal(0, 0.05, (3, 7)))
    r = G.replicate_compare({"a": a, "b": b})
    se = np.sqrt(np.log(a).std(0, ddof=1) ** 2 / 3 + np.log(b).std(0, ddof=1) ** 2 / 3)
    assert np.allclose(r["separation"]["a|b"]["z"], np.abs(np.log(a).mean(0) - np.log(b).mean(0)) / se)
    assert 0.02 < r["spread"]["a"]["cv_pooled"] < 0.09


# ── 7. 画像 → D50 ───────────────────────────────────────────────────────
def test_particle_image_d50_volume_and_number_basis():
    errs, ratio = [], []
    for seed in range(3):
        im = G.particle_image_synth(60, 14.0, 0.35, (256, 256), seed=seed)
        tr = im["truth"]
        d = tr["diameters"][~tr["touches_border"]]
        for basis, w in (("volume", d ** 3), ("number", np.ones_like(d))):
            r = G.particle_image_d50(im["image"], 1.0, basis=basis)
            assert r["n"] == d.size
            errs += [abs(r[k] / v - 1) for k, v in zip(("d10", "d50", "d90"), G._weighted_quantiles(d, w, (10, 50, 90)))]
        ratio.append(G.particle_image_d50(im["image"], 1.0)["d50"] / G.particle_image_d50(im["image"], 1.0, basis="number")["d50"])
    assert len(errs) == 18
    assert max(errs) < 0.005
    assert min(ratio) > 1.1


# ── 8. CSV ──────────────────────────────────────────────────────────────
def test_csv_readers_round_trip_and_reject(tmp_path):
    p = G.particle_size_synth(120.0, 0.45)
    lines = ["Sample Name,synthetic,,", "Dx (50),%.17g,," % G.particle_size_dx(p), "SizeClasses(μm),VolumeDensity(%),q,I"]
    lines += ["%.17g,%.17g,0,0" % (float(e), float(v)) for e, v in zip(p["edges"], p["volume"])]
    f = tmp_path / "psd.csv"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    r = G.particle_size_read(str(f))
    assert G.particle_size_dx(r) == pytest.approx(r["dx50_reported"], rel=1e-14) and r["n_rows"] == 74
    assert all("psd.csv" not in str(v) for v in r.values())
    ae = tmp_path / "ae.csv"
    raw = [32768, 49152, 16384, 32768]
    ae.write_text("\n".join(["h,%d" % i for i in range(12)] + [str(v) for v in raw]) + "\n", encoding="utf-8")
    assert np.allclose(G.ae_read_csv(str(ae)), [0.0, 0.5, -0.5, 0.0])
    assert _raises(G.ae_read_csv, str(ae), 3) and _raises(G.particle_size_read, str(tmp_path / "missing.csv"))
    bad = tmp_path / "bad.csv"
    bad.write_text("SizeClasses(μm),VolumeDensity(%)\n1,2\n2,3\n3,4\n", encoding="utf-8")     # 最後の行が 0 でない
    assert _raises(G.particle_size_read, str(bad))


# ── 9. 綴り壊し ─────────────────────────────────────────────────────────
def test_spelling_breaks_fail_closed():
    p = G.particle_size_synth(100, 0.4)
    tone = np.sin(np.arange(4096) / 3.0)
    cases = [
        _raises(G.particle_size_dx, p, 50, "log-edges"), _raises(G.particle_size_dx, p, 0), _raises(G.particle_size_dx, p, True),
        _raises(G.particle_size_dx, {"edges": [1, 2, 3]}), _raises(G.comminution_energy, 500, 50, law="Bond"),
        _raises(G.comminution_energy, 500, 600), _raises(G.comminution_energy, 500, 50, energy=1.0),
        _raises(G.comminution_energy, 500, 50, n=2), _raises(G.comminution_energy, math.inf, 50, law="kick"),
        _raises(G.comminution_law_fit, [1, 2], [3, 4]), _raises(G.comminution_law_fit, [1, 2, 3], [3, 4, 5], law="rittenger"),
        _raises(G.comminution_law_fit, [1, 1, 1], [3, 4, 5]), _raises(G.breakage_first_order_fit, [1, 2, 3], [0.5, 0.0, 0.2]),
        _raises(G.replicate_compare, {"a": np.ones((1, 3))}), _raises(G.replicate_compare, {"a": np.ones((2, 3)), "b": np.ones((2, 4))}),
        _raises(G.ae_band_power, tone, 2e6, 2e5, 1e5), _raises(G.ae_band_power, tone, 2e6, start=4000),
        _raises(G.particle_image_d50, np.zeros((40, 40)), 1.0), _raises(G.particle_image_synth, 0),
        _raises(G.particle_size_synth, 100, 2.0), _raises(G.ae_size_correspondence, [1.0, -2.0], [3.0, 4.0]),
    ]
    assert len(cases) == 21
    assert all(cases), [i for i, c in enumerate(cases) if not c]


# ── 10. 入口 ────────────────────────────────────────────────────────────
def test_entry_points_exist_and_docstrings_have_no_markdown_links():
    assert len(G.__all__) >= 14
    for name in G.__all__:
        obj = getattr(G, name)
        if callable(obj):
            assert (obj.__doc__ or "").strip(), name
            assert "](" not in obj.__doc__, name
    assert "](" not in G.__doc__


# ── 11. 実データ ────────────────────────────────────────────────────────
@pytest.mark.skipif(not os.environ.get("FULLSEYE_GRIND_DATA"), reason="FULLSEYE_GRIND_DATA が無い(公開データは repo の外)")
def test_real_data_d50_definition_and_kick_never_best():
    root = Path(os.environ["FULLSEYE_GRIND_DATA"])
    files = sorted((root / "data_public" / "powder_size_distribution").glob("exp*/*/*/*.csv"))
    if not files:
        pytest.skip("粒度分布の CSV が無い")
    rel = []
    by = {}
    for f in files:
        p = G.particle_size_read(str(f))
        rel.append(abs(G.particle_size_dx(p) / p["dx50_reported"] - 1))
        m = re.search(r"grind(\d+)min", f.name)
        if f.parts[-4] == "exp2" and m:
            by.setdefault(f.parent.parent.name, []).append((int(m.group(1)), G.particle_size_dx(p)))
    assert len(rel) >= 90
    assert max(rel) < 1e-9
    assert len(by) == 3
    for mat, pts in by.items():
        assert len(pts) == 21, mat
        t = np.array([q[0] for q in pts], float)      # 壁時計の分(正味の時間にほぼ比例)
        d = np.array([q[1] for q in pts])
        assert G.comminution_law_fit(t, d)["best_fixed"] != "kick", mat
