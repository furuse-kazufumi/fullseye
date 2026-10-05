# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""乳鉢の粉砕を測る —— 粒度分布の D50、粉砕則、独立 3 回のばらつき、AE の帯域電力。真値は公開されたレーザー回折の実測(2026-10-05)。

物理シミュ × Fullseye 系列(granular / scoop に続く粉体の 3 本目)。題材はロボットが乳鉢で粉を挽き、音響放射(AE)で
挽き具合を見張る研究。その公開データ(Zenodo 概念 DOI 10.5281/zenodo.18064323、CC BY 4.0)の **レーザー回折の粒度分布**
(NaCl / クエン酸 / グルタミン酸ナトリウム × 独立 3 回 × 粉砕 3〜25 min の 7 時点、+ 粉砕前・60 min・手作業)と AE の生波形を
外の真値にして、新モジュール grind(13 op)を学習なしに組む。

何が外から来るか:
  * **粒度分布そのもの**(装置の出力)と、装置が書いた ``Dx (50)``(op の D50 の定義を突き合わせる相手)。
  * **粉砕則の式**: Reddy(国立冶金研究所の紀要 pp. 67–76)の式 (1)・(5)〜(7) —— 一般式 dE = −C dx/xⁿ、Kick n = 1・Bond 1.5・
    Rittinger 2。**一次の破砕速度**: Deniz 2004 の式 (1)〜(3)(出典 Austin)。原典(Bond 1952、Austin 1972 / 1984)は未読。
  * **AE の帯域電力の定義**: 公開の解析コード(MIT)の ``calculate_fft_power`` を同じ 6 本で走らせた値を定数で持ち、op と照合。

門(既定 = numpy だけ 12 本 + データ 10 本、データが無ければ 10 本は skip): 粉砕則の閉形式と往復、対数正規の D10/D50/D90、
則の当てはめの往復、則の見分けの効き(合成のモンテカルロ)、一次の速度の往復、AE の帯域電力(正弦波・Parseval)、独立試行の比較、
画像からの D50(合成、体積基準と個数基準)、綴り壊し、CSV の往復、入口、所要; データ: D50 の定義、則の当てはめ、実データの
設計での見分けの効き、粉砕前への外挿、独立 3 回のばらつき、材料の差、一次の速度、AE の定義の照合、AE と D50、60 min の破れ。
--full: モンテカルロを 10 倍。
図(既定の出力先は out/figures/<PoC 名>/、FULLSEYE_FIGURE_DIR で変更): D50 が下がる曲線に独立 3 回と 3 則の当てはめ、
粒度分布が細かくなっていく GIF、AE のスペクトログラム(挽き始めと挽き終わり)、AE の帯域電力 vs D50、篩上の一次の速度、
則の見分けの表、60 min で則が破れる所、合成画像の粒子と体積基準 vs 個数基準。
データの置き場は環境変数 FULLSEYE_GRIND_DATA(PROVENANCE.md のあるディレクトリ。repo にデータは入れない)。
Run: py -3.11 examples/poc_powder_grinding_ae.py [--full]
"""
from __future__ import annotations

import csv
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import grind as G  # noqa: E402

FULL = "--full" in sys.argv
MATERIALS = ("NaCl", "Citricacid", "MSG")
MAT_LABEL = {"NaCl": "NaCl", "Citricacid": "citric acid", "MSG": "MSG"}
MINUTES = (3, 5, 7, 10, 15, 20, 25)
RUNS = ("1st", "2nd", "3rd")
SECONDS_PER_ACQ = 12.0          # 版 2 の README: "33 acquisitions x 12 s = 6.6 min"
AE_RATE = 2e6
AE_START, AE_STOP = 200013, None             # 解析コードの既定の始点(雑音の区間を飛ばす)。終点 1200012 は標本数 1,200,000 を超え、
#                                              解析コードは min() で黙って切る —— op は fail-closed なので「最後まで」を None で明示する
#: 公開の解析コード(ae_fft.calculate_fft_power、MIT)を同じ 6 本で走らせた値 [V²] (2026-10-05 に scratchpad で実行)
REFERENCE_AE_POWER = {
    "20251216_164441NaCl_grind3min.csv": 0.00018462775031331843,
    "20251216_151403NaCl_grind25min.csv": 3.111497860785546e-05,
    "20251218_120529Citricacid_grind3min.csv": 0.0008062444986932577,
    "20251218_135047Citricacid_grind25min.csv": 7.145653582323819e-06,
    "20260217_134646MSG_grind3min.csv": 0.0022086658617882,
    "20260217_152824MSG_grind25min.csv": 0.00018405327236989207,
}
MC_SEEDS = 200 if FULL else 20
_GATES: list[tuple[str, bool]] = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, *a, **k):
    try:
        fn(*a, **k)
    except ValueError:
        return True
    except Exception as exc:  # noqa: BLE001  別の例外は fail-closed ではない
        print("    (wrong exception %s: %s)" % (type(exc).__name__, exc))
        return False
    return False


def _predict(law, fit, t):
    """当てはめた則の径(comminution_energy の逆で E = k t)。"""
    return np.array([G.comminution_energy(fit["x0"], law="walker" if law == "walker" else law,
                                          n=fit["n"] if law == "walker" else None, energy=fit["k"] * float(tt))["x_product"]
                     for tt in np.atleast_1d(t)])


def identifiability(t, x0, ratio, noise, seeds, rng_seed=0):
    """3 則のどれかで作った D50(t)(x0 → x0/ratio、log 雑音 σ = noise)に 3 則を当て、正しい則が勝つ割合。"""
    t = np.asarray(t, float)
    tmax = float(t.max())
    hit = {}
    rng = np.random.default_rng(rng_seed)
    for law in G.LAWS:
        e_end = G.comminution_energy(x0, x_product=x0 / ratio, law=law)["E"]
        k = e_end / tmax
        clean = np.array([G.comminution_energy(x0, law=law, energy=k * tt)["x_product"] for tt in t])
        win = 0
        for _ in range(seeds):
            noisy = clean * np.exp(rng.normal(0.0, noise, clean.size))
            rms = {lw: G.comminution_law_fit(t, noisy, law=lw)["fits"][lw]["rms_log"] for lw in G.LAWS}
            win += int(min(rms, key=rms.get) == law)
        hit[law] = win / seeds
    return hit


# ======================================================================================================================
# numpy だけの門
# ======================================================================================================================
def numpy_part() -> dict:
    print("== numpy だけの門(粉砕則・粒度分布・AE・画像の閉形式と往復)")
    t0 = time.time()
    out: dict = {}
    # 門 1 粉砕則の閉形式
    x1, x2, C = 500.0, 50.0, 3.0
    ek = G.comminution_energy(x1, x2, law="kick", C=C)["E"]
    eb = G.comminution_energy(x1, x2, law="bond", C=C)["E"]
    er = G.comminution_energy(x1, x2, law="rittinger", C=C)["E"]
    e_hand = (C * math.log(10.0), 2 * C * (1 / math.sqrt(50) - 1 / math.sqrt(500)), C * (1 / 50 - 1 / 500))
    e_walk = (G.comminution_energy(x1, x2, law="walker", n=1.5, C=C)["E"], G.comminution_energy(x1, x2, law="walker", n=2.0, C=C)["E"],
              G.comminution_energy(x1, x2, law="walker", n=1.0 + 1e-7, C=C)["E"])
    wi = G.comminution_energy(2000.0, 100.0, law="bond_wi", C=12.0)["E"]
    wi_hand = 10 * 12.0 * (1 / math.sqrt(100) - 1 / math.sqrt(2000))
    rt = max(abs(G.comminution_energy(x1, law=lw, C=C, energy=G.comminution_energy(x1, x2, law=lw, C=C)["E"])["x_product"] / x2 - 1)
             for lw in G.LAWS)
    inf_feed = G.comminution_energy(math.inf, 100.0, law="rittinger", C=2.0)["E"]
    e1 = max(abs(ek / e_hand[0] - 1), abs(eb / e_hand[1] - 1), abs(er / e_hand[2] - 1), abs(e_walk[0] / eb - 1), abs(e_walk[1] / er - 1))
    gate("門 1 粉砕則の閉形式(Kick ln、Bond 2C(1/√x₂ − 1/√x₁)、Rittinger、一般式の n = 1.5 / 2 / 1⁺、作業指数の形、往復、無限大の供給)",
         e1 < 1e-12 and abs(e_walk[2] / ek - 1) < 1e-6 and abs(wi / wi_hand - 1) < 1e-12 and rt < 1e-12 and abs(inf_feed - 0.02) < 1e-15,
         "手計算との差 %.1e、n → 1 で Kick との差 %.1e、Wi 形 %.1e、往復 %.1e、E(∞ → 100 µm) = %.4f(= C/x)"
         % (e1, abs(e_walk[2] / ek - 1), abs(wi / wi_hand - 1), rt, inf_feed))
    # 門 2 対数正規の体積分布 → D10/D50/D90
    errs, lc = [], []
    for d50, s in ((30.0, 0.4), (100.0, 0.5), (200.0, 0.3), (8.0, 0.6)):
        p = G.particle_size_synth(d50, s)
        for q, key in ((10, "d10"), (50, "d50"), (90, "d90")):
            errs.append(abs(G.particle_size_dx(p, q) / p["truth"][key] - 1))
        lc.append(G.particle_size_dx(p, 50, "lower_cumsum") / G.particle_size_dx(p, 50) - 1)
    assert len(errs) == 12 and len(lc) == 4
    gate("門 2 対数正規の体積分布(装置の 74 区間)→ D10/D50/D90(log_edges)", max(errs) < 0.01
         and all(abs(v - (1 / G.INSTRUMENT_RATIO - 1)) < 0.01 for v in lc),
         "最大 %.2f %%(区間の中の分布が log で一様の近似)、lower_cumsum は %.2f〜%.2f %%(1 区間 = %.2f %%)"
         % (100 * max(errs), 100 * min(lc), 100 * max(lc), 100 * (1 / G.INSTRUMENT_RATIO - 1)))
    # 門 3 則の当てはめの往復(雑音なし)
    t = np.repeat([0.8, 1.4, 1.8, 2.6, 4.0, 5.4, 6.6], 3)
    ok3, d3 = True, []
    for law in G.LAWS:
        k = G.comminution_energy(400.0, x_product=400.0 / 5, law=law)["E"] / t.max()
        x = np.array([G.comminution_energy(400.0, law=law, energy=k * tt)["x_product"] for tt in t])
        r = G.comminution_law_fit(t, x)
        f = r["fits"][law]
        ok3 &= r["best_fixed"] == law and f["rms_log"] < 1e-9 and abs(f["k"] / k - 1) < 1e-7 and abs(f["x0"] / 400 - 1) < 1e-7 \
            and abs(r["fits"]["walker"]["n"] - LAWn(law)) < 0.02
        d3.append("%s: rms %.0e、n̂ %.3f" % (law, f["rms_log"], r["fits"]["walker"]["n"]))
    gate("門 3 則の当てはめの往復(雑音なし、x₀ 400 → 80 µm、7 時点 × 3)", ok3, "; ".join(d3))
    # 門 4 見分けの効き(合成のモンテカルロ): 縮みの比で効きが変わる
    t0_mc = time.time()
    hit20 = identifiability(t, 400.0, 20.0, 0.10, MC_SEEDS, 1)
    hit3 = identifiability(t, 400.0, 2.7, 0.05, MC_SEEDS, 2)
    out["mc_synth"] = {"ratio20": hit20, "ratio2.7": hit3}
    gate("門 4 3 則の見分け: 縮み 20 倍・雑音 10 % なら 9 割以上見分けられ、2.7 倍・5 % では平均 85 % 以下(当てずっぽうではないが当てにならない)",
         min(hit20.values()) >= 0.9 and float(np.mean(list(hit3.values()))) <= 0.85,
         "20 倍: %s / 2.7 倍: %s(%d 回ずつ、%.1f s)" % (_fmt_hit(hit20), _fmt_hit(hit3), MC_SEEDS, time.time() - t0_mc))
    # 門 5 一次の速度の往復
    tt = np.array([0.8, 1.4, 1.8, 2.6, 4.0, 5.4, 6.6])
    xs = np.array([150.0, 250.0, 400.0])
    S_true = 0.05 * (xs / 100.0) ** 0.8
    W = 0.6 * np.exp(-S_true[:, None] * tt[None, :])
    b = G.breakage_first_order_fit(tt, W, x=xs)
    b1 = G.breakage_first_order_fit(tt, W[1])
    gate("門 5 一次の破砕速度の往復 w = w₀ e^{−St}、S = a x^α(Deniz の式 (2)・(3))",
         max(abs(b["S_per_x"] / S_true - 1)) < 1e-12 and abs(b["alpha"] - 0.8) < 1e-10 and abs(b1["S_early"] / b1["S_late"] - 1) < 1e-10
         and b1["r2"] > 1 - 1e-12 and b["apparent"],
         "S の差 %.1e、α̂ = %.6f、前半 / 後半の S の比 %.6f"
         % (max(abs(b["S_per_x"] / S_true - 1)), b["alpha"], b1["S_early"] / b1["S_late"]))
    # 門 6 AE の帯域電力
    n = 400000
    tsig = np.arange(n) / AE_RATE
    A = 0.05
    tone = A * np.sin(2 * np.pi * 300e3 * tsig)                      # 300 kHz は FFT の格子の上(N = 4e5、Δf = 5 Hz)
    out_band = A * np.sin(2 * np.pi * 50e3 * tsig)
    p_in, p_out = G.ae_band_power(tone, AE_RATE), G.ae_band_power(out_band, AE_RATE)
    noise = np.random.default_rng(3).normal(0, 0.01, n)
    p_n = G.ae_band_power(noise, AE_RATE)
    gate("門 6 AE の帯域電力: 振幅 A の正弦波で A²(解析コードの定義)、帯の外は 0、Parseval で FFT ≈ 2 × STFT",
         abs(p_in["power_fft"] / A ** 2 - 1) < 1e-9 and abs(p_in["ratio"] - 1) < 1e-3 and p_out["power_fft"] < 1e-9 * A ** 2
         and abs(p_n["ratio"] - 1) < 0.05,
         "正弦波 %.10f A²、比 %.5f、帯の外 %.1e A²、白色雑音の比 %.4f"
         % (p_in["power_fft"] / A ** 2, p_in["ratio"], p_out["power_fft"] / A ** 2, p_n["ratio"]))
    # 門 7 独立試行の比較
    rng = np.random.default_rng(4)
    ga = 100.0 * np.exp(rng.normal(0, 0.05, (3, 7)))
    gb = 50.0 * np.exp(rng.normal(0, 0.05, (3, 7)))
    rc = G.replicate_compare({"a": ga, "b": gb})
    z = rc["separation"]["a|b"]
    m1 = np.log(ga).mean(0) - np.log(gb).mean(0)
    se = np.sqrt(np.log(ga).std(0, ddof=1) ** 2 / 3 + np.log(gb).std(0, ddof=1) ** 2 / 3)
    gate("門 7 独立試行の比較(変動係数と、群の差を標準誤差の何倍か)", np.max(np.abs(z["z"] - np.abs(m1) / se)) < 1e-12
         and 0.02 < rc["spread"]["a"]["cv_pooled"] < 0.09 and z["min_z"] > 5,
         "cv %.3f / %.3f(真 0.05)、最小の z %.1f" % (rc["spread"]["a"]["cv_pooled"], rc["spread"]["b"]["cv_pooled"], z["min_z"]))
    # 門 8 画像からの D50(合成)
    e8, ratio8 = [], []
    for seed in range(4):
        im = G.particle_image_synth(80, 14.0, 0.35, (320, 320), seed=seed)
        tr = im["truth"]
        dd = tr["diameters"][~tr["touches_border"]]
        for basis, wts in (("volume", dd ** 3), ("number", np.ones_like(dd))):
            r = G.particle_image_d50(im["image"], im["pitch"], basis=basis)
            tq = G._weighted_quantiles(dd, wts, (10, 50, 90))
            e8 += [abs(r[k] / v - 1) for k, v in zip(("d10", "d50", "d90"), tq)]
        ratio8.append(G.particle_image_d50(im["image"], 1.0)["d50"] / G.particle_image_d50(im["image"], 1.0, basis="number")["d50"])
        if seed == 0:
            out["img"] = im
    assert len(e8) == 24
    gate("門 8 画像の粒子 → D10/D50/D90(合成、縁の規約を真値と揃える)、体積基準と個数基準は別の分布",
         max(e8) < 0.005 and min(ratio8) > 1.15, "最大 %.2f %%、体積 / 個数の D50 の比 %.2f〜%.2f"
         % (100 * max(e8), min(ratio8), max(ratio8)))
    # 門 9 綴り壊し・fail-closed
    p = G.particle_size_synth(100, 0.4)
    bad = dict(p)
    bad["volume"] = np.r_[p["volume"][:-1], 1.0]
    cases = [
        _raises(G.particle_size_dx, p, 50, "log-edges"), _raises(G.particle_size_dx, p, 0), _raises(G.particle_size_dx, p, 100),
        _raises(G.particle_size_dx, bad), _raises(G.particle_size_dx, {"edges": [1, 2, 3]}),
        _raises(G.comminution_energy, 500, 50, law="Bond"), _raises(G.comminution_energy, 500, 600),
        _raises(G.comminution_energy, 500, 50, energy=1.0), _raises(G.comminution_energy, 500), _raises(G.comminution_energy, 500, 50, n=2),
        _raises(G.comminution_energy, math.inf, 50, law="kick"), _raises(G.comminution_law_fit, [1, 2], [3, 4]),
        _raises(G.comminution_law_fit, [1, 2, 3], [3, -4, 5]), _raises(G.comminution_law_fit, [1, 2, 3], [3, 4, 5], law="rittenger"),
        _raises(G.breakage_first_order_fit, [1, 2, 3], [0.5, 0.0, 0.2]), _raises(G.breakage_first_order_fit, [1, 2, 3], [[0.5, 0.4, 0.2]]),
        _raises(G.replicate_compare, {"a": np.ones((1, 3))}), _raises(G.ae_band_power, tone, AE_RATE, 2e5, 1e5),
        _raises(G.ae_band_power, tone, AE_RATE, 1e5, 2e6), _raises(G.particle_image_d50, np.zeros((40, 40)), 1.0),
        _raises(G.particle_image_d50, out["img"]["image"], 1.0, basis="mass"), _raises(G.particle_size_synth, 100, 2.0),
    ]
    gate("門 9 綴り壊しと測れない入力は ValueError(%d 通り)" % len(cases), all(cases), "通った %d / %d" % (sum(cases), len(cases)))
    # 門 10 CSV の往復(装置の形を写した合成 CSV)
    with tempfile.TemporaryDirectory() as td:
        p = G.particle_size_synth(120.0, 0.45)
        d50 = G.particle_size_dx(p)
        lines = ["Sample Name,synthetic,,", "Dx (50),%.17g,," % d50, "SizeClasses(μm),VolumeDensity(%),Scatter Angle q,Scatter Intensity"]
        lines += ["%.17g,%.17g,0,0" % (float(e), float(v)) for e, v in zip(p["edges"], p["volume"])]
        fp = Path(td) / "psd.csv"
        fp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rd = G.particle_size_read(str(fp))
        ae = Path(td) / "ae.csv"
        raw = np.round(32768 + 32768 * 0.5 * np.sin(np.arange(1000) / 7.0)).astype(int)
        ae.write_text("\n".join(["Start date time,x"] + ["h,%d" % i for i in range(11)] + [str(v) for v in raw]) + "\n", encoding="utf-8")
        sig = G.ae_read_csv(str(ae))
        broken = Path(td) / "broken.csv"
        broken.write_text("Sample Name,x\nSizeClasses(μm),VolumeDensity(%)\n1,2\n2,abc\n3,0\n", encoding="utf-8")
        ok10 = (abs(G.particle_size_dx(rd) / rd["dx50_reported"] - 1) < 1e-14 and rd["n_rows"] == 74 and "path" not in str(sorted(rd))
                and sig.size == 1000 and abs(sig.max() - raw.max() / 32768 + 1) < 1e-15 and _raises(G.particle_size_read, str(broken))
                and _raises(G.ae_read_csv, str(ae), 3) and _raises(G.particle_size_read, str(Path(td) / "missing.csv")))
    gate("門 10 CSV の往復(粒度分布と AE、壊れた行・無いファイル・ヘッダの数違いは拒否)", ok10,
         "D50 の往復 %.1e、AE %d 標本" % (abs(G.particle_size_dx(rd) / rd["dx50_reported"] - 1), sig.size))
    # 門 11 入口
    missing = [nm for nm in G.__all__ if not hasattr(G, nm)]
    bad_doc = [nm for nm in G.__all__ if callable(getattr(G, nm, None))
               and (not (getattr(G, nm).__doc__ or "").strip() or "](" in getattr(G, nm).__doc__)]
    gate("門 11 入口: __all__ が実在し、docstring があり Markdown のリンク記法を含まない",
         not missing and not bad_doc and "](" not in (G.__doc__ or ""), "欠け %s、docstring %s" % (missing or "なし", bad_doc or "ok"))
    dt = time.time() - t0
    out["t_numpy"] = dt
    gate("門 12 numpy の門の所要 ≤ %d s" % (60 if FULL else 8), dt <= (60 if FULL else 8), "%.2f s" % dt)
    return out


def LAWn(law):
    return G.LAWS[law]


def _fmt_hit(h):
    return " ".join("%s %.0f%%" % (k[:4], 100 * v) for k, v in h.items())


# ======================================================================================================================
# 実データの門(FULLSEYE_GRIND_DATA)
# ======================================================================================================================
def _data_dir():
    d = os.environ.get("FULLSEYE_GRIND_DATA", "")
    if not d:
        return None, "環境変数 FULLSEYE_GRIND_DATA が無い"
    p = Path(d)
    if not (p / "data_public" / "powder_size_distribution" / "exp2").is_dir() or not (p / "ae_runs.csv").is_file():
        return None, "FULLSEYE_GRIND_DATA に exp2 の粒度分布か ae_runs.csv が無い"
    return p, ""


def load_data(root: Path) -> dict:
    runs = {}
    with open(root / "ae_runs.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            runs[(r["material"], r["run"], int(r["grind_min"]))] = int(r["n_acquisitions"])
    exp2 = {}
    for f in sorted((root / "data_public" / "powder_size_distribution" / "exp2").glob("*/*/*.csv")):
        mat, run = f.parent.parent.name, f.parent.name
        m = re.search(r"grind(\d+)min", f.name)
        exp2[(mat, run, int(m.group(1)))] = G.particle_size_read(str(f))
    add = {}
    adir = root / "data" / "powder_size_distribution" / "additional_experiments"
    for f in sorted(adir.glob("*/*.csv")):
        m = re.match(r"\d{8}_\d{6}_(\w+?)_(initial|grind_robot60min|grind_manual10min)_meas(\d)\.csv", f.name)
        if m:
            add[(m.group(1), m.group(2), int(m.group(3)))] = G.particle_size_read(str(f))
    exp3 = [G.particle_size_read(str(f)) for f in sorted((root / "data_public" / "powder_size_distribution" / "exp3").glob("*/*/*.csv"))]
    ae = {}
    for f in sorted((root / "data_public" / "ae" / "exp2").glob("*/1st/*.csv")):
        m = re.search(r"grind(\d+)min", f.name)
        ae[(f.parent.parent.name, int(m.group(1)))] = (f.name, G.ae_read_csv(str(f)))
    return {"runs": runs, "exp2": exp2, "add": add, "exp3": exp3, "ae": ae}


def data_part(out: dict, root: Path) -> dict:
    print("== 実データの門(公開データのレーザー回折と AE、CC BY 4.0)")
    t0 = time.time()
    D = load_data(root)
    out["D"] = D
    # 門 13 D50 の定義
    allp = list(D["exp2"].values()) + list(D["add"].values()) + D["exp3"]
    rel = [abs(G.particle_size_dx(p) / p["dx50_reported"] - 1) for p in allp]
    lc = [G.particle_size_dx(p, 50, "lower_cumsum") / p["dx50_reported"] - 1 for p in allp]
    assert len(rel) >= 117
    out["d50_def"] = (max(rel), min(lc), max(lc), len(rel))
    gate("門 13 D50 の定義: 装置の Dx(50) = 端の累積を log(径) で補間(全 %d 本)、解析コードの学習の段の定義は 1 区間小さい" % len(rel),
         max(rel) < 1e-9 and -0.125 < min(lc) and max(lc) < -0.115,
         "log_edges の最大差 %.1e、lower_cumsum %.2f〜%.2f %%" % (max(rel), 100 * min(lc), 100 * max(lc)))
    # 表: 材料 × 試行 × 時点
    T, X = {}, {}
    for mat in MATERIALS:
        tt, xx = [], []
        for run in RUNS:
            for mn in MINUTES:
                tt.append(D["runs"][(mat, run, mn)] * SECONDS_PER_ACQ / 60.0)
                xx.append(G.particle_size_dx(D["exp2"][(mat, run, mn)]))
        T[mat], X[mat] = np.array(tt), np.array(xx)
    assert all(T[m].size == 21 for m in MATERIALS)
    out["T"], out["X"] = T, X
    # 門 14 則の当てはめ
    fits = {m: G.comminution_law_fit(T[m], X[m]) for m in MATERIALS}
    out["fits"] = fits
    det = []
    for m in MATERIALS:
        f = fits[m]["fits"]
        det.append("%s: 最良 %s(rms %.3f)、Kick %.3f / Bond %.3f / Rittinger %.3f、n̂ %.2f"
                   % (MAT_LABEL[m], fits[m]["best_fixed"], f[fits[m]["best_fixed"]]["rms_log"], f["kick"]["rms_log"],
                      f["bond"]["rms_log"], f["rittinger"]["rms_log"], f["walker"]["n"]))
    best_rms = [fits[m]["fits"][fits[m]["best_fixed"]]["rms_log"] for m in MATERIALS]
    kick_never = all(fits[m]["best_fixed"] != "kick" for m in MATERIALS)
    gate("門 14 粉砕則の当てはめ(D50 vs 正味の時間、3 回 × 7 時点 = 21 点 / 材料): Kick はどの材料でも最良にならない", max(best_rms) < 0.20 and kick_never,
         "; ".join(det))
    # 門 15 実データの設計での見分けの効き
    t_mc = time.time()
    mc = {}
    for i, m in enumerate(MATERIALS):
        f = fits[m]["fits"][fits[m]["best_fixed"]]
        x_fit = _predict(fits[m]["best_fixed"], f, [T[m].min(), T[m].max()])
        mc[m] = identifiability(T[m], float(x_fit[0]), float(x_fit[0] / x_fit[1]), f["rms_log"], MC_SEEDS, 10 + i)
    out["mc_real"] = mc
    gate("門 15 その材料の縮みと残差の大きさで 3 則を見分けられるか(合成のモンテカルロ、%d 回)" % MC_SEEDS,
         all(0.0 <= v <= 1.0 for h in mc.values() for v in h.values()),
         "; ".join("%s %s" % (MAT_LABEL[m], _fmt_hit(mc[m])) for m in MATERIALS) + "(%.1f s、記録の門)" % (time.time() - t_mc))
    # 門 16 粉砕前への外挿(当てはめに使っていない測定)
    init = {m: np.mean([G.particle_size_dx(D["add"][(m, "initial", k)]) for k in (1, 2, 3)]) for m in MATERIALS}
    out["init"] = init
    ext = {m: {lw: fits[m]["fits"][lw]["x0"] / init[m] - 1 for lw in ("kick", "bond", "rittinger", "walker")} for m in MATERIALS}
    out["ext"] = ext
    best_ext = [ext[m][fits[m]["best_fixed"]] for m in MATERIALS]
    gate("門 16 最良の則を t = 0 へ外挿 vs 粉砕前の実測(当てはめに使っていない、装置の設定は違う)", max(abs(v) for v in best_ext) < 0.25,
         "; ".join("%s: 実測 %.0f µm、最良 %+.0f %%(Kick %+.0f / Bond %+.0f / Rittinger %s / n 自由 %s)"
                   % (MAT_LABEL[m], init[m], 100 * ext[m][fits[m]["best_fixed"]], 100 * ext[m]["kick"], 100 * ext[m]["bond"],
                      _pct(ext[m]["rittinger"]), _pct(ext[m]["walker"])) for m in MATERIALS))
    # 門 17 独立 3 回のばらつき vs 同じ粉の繰り返し測定
    groups = {m: X[m].reshape(3, 7) for m in MATERIALS}
    rc = G.replicate_compare(groups)
    out["rc"] = rc
    meas_cv = {}
    for m in MATERIALS:
        for cond in ("initial", "grind_robot60min", "grind_manual10min"):
            v = np.array([G.particle_size_dx(D["add"][(m, cond, k)]) for k in (1, 2, 3)])
            meas_cv[(m, cond)] = float(v.std(ddof=1) / v.mean())
    out["meas_cv"] = meas_cv
    cvp = [rc["spread"][m]["cv_pooled"] for m in MATERIALS]
    gate("門 17 独立 3 回のばらつき(D50 の変動係数、7 時点の二乗平均)", max(cvp) < 0.15,
         "; ".join("%s %.1f %%(最大 %.1f %% @ %d min)" % (MAT_LABEL[m], 100 * rc["spread"][m]["cv_pooled"], 100 * rc["spread"][m]["cv_max"],
                                                       MINUTES[int(np.argmax(rc["spread"][m]["cv"]))]) for m in MATERIALS)
         + "。同じ粉の繰り返し測定(版 2、独立試行ではない)の変動係数 %.1f〜%.1f %%" % (100 * min(meas_cv.values()), 100 * max(meas_cv.values())))
    # 門 18 材料の差
    sep = rc["separation"]
    z25 = {v["pair"]: float(v["z"][-1]) for v in sep.values()}
    weak = [(v["pair"], MINUTES[v["argmin"]], v["min_z"]) for v in sep.values() if v["min_z"] < 3]
    gate("門 18 材料の差: 25 min の D50 は全ての組で独立試行の標準誤差の 3 倍より離れる", min(z25.values()) > 3,
         "25 min の z: %s; 離れない時点: %s" % (", ".join("%s–%s %.1f" % (MAT_LABEL[a], MAT_LABEL[b], z) for (a, b), z in z25.items()),
                                          ", ".join("%s–%s @ %d min (z %.1f)" % (MAT_LABEL[a], MAT_LABEL[b], mn, z) for (a, b), mn, z in weak) or "なし"))
    # 門 19 一次の速度(篩上 R(x))
    xs = np.array([150.0, 200.0, 300.0])
    fo = {}
    for m in MATERIALS:
        R = np.array([[G.particle_size_oversize(D["exp2"][(m, run, mn)], x) for run in RUNS for mn in MINUTES] for x in xs])
        fo[m] = G.breakage_first_order_fit(T[m], R, x=xs)
    out["fo"] = fo
    out["fo_x"] = xs
    r200 = [fo[m]["rows"][1] for m in MATERIALS]
    gate("門 19 篩上 R(200 µm) の一次の速度(見かけ: 最上位の区間ではない)—— 3 材料とも後半で遅くなる(一次から外れる)",
         all(r["S"] > 0 and r["S_early"] > r["S_late"] for r in r200),
         "; ".join("%s S %.3f /min、r² %.2f、前半 / 後半 %.2f / %.2f、α %.2f" % (MAT_LABEL[m], r["S"], r["r2"], r["S_early"], r["S_late"], fo[m]["alpha"])
                   for m, r in zip(MATERIALS, r200)))
    # 門 20 AE の定義の照合(解析コードの値)
    rel_ae, bands = [], {}
    for (m, mn), (name, sig) in sorted(D["ae"].items()):
        b = G.ae_band_power(sig, AE_RATE, start=AE_START, stop=AE_STOP)
        bands[(m, mn)] = b
        if name in REFERENCE_AE_POWER:
            rel_ae.append(abs(b["power_fft"] / REFERENCE_AE_POWER[name] - 1))
    out["bands"] = bands
    ratios = [b["ratio"] for b in bands.values()]
    gate("門 20 AE の帯域電力 = 解析コードの値(同じ 6 本)、Parseval の比", len(rel_ae) == 6 and max(rel_ae) < 1e-9
         and all(0.9 < r < 1.15 for r in ratios), "最大差 %.1e、FFT / (2 STFT) %.3f〜%.3f" % (max(rel_ae) if rel_ae else float("nan"), min(ratios), max(ratios)))
    # 門 21 AE と D50
    P, Dd, grp = [], [], []
    for m in MATERIALS:
        for mn in (3, 25):
            P.append(bands[(m, mn)]["power_fft"] * 1e6)
            Dd.append(G.particle_size_dx(D["exp2"][(m, "1st", mn)]))
            grp.append(m)
    cor = G.ae_size_correspondence(P, Dd, grp)
    out["ae_cor"] = (P, Dd, grp, cor)
    gate("門 21 AE の帯域電力は D50 と同じ向きに下がる(材料ごと、1st の試行の 3 min と 25 min の最後の取得)",
         all(cor["groups"][m]["sign_agree"] == 1.0 for m in MATERIALS),
         "; ".join("%s: %.1f → %.1f mV²、D50 %.0f → %.1f µm、α %.2f(n = %d)" % (MAT_LABEL[m], P[2 * i], P[2 * i + 1], Dd[2 * i], Dd[2 * i + 1],
                                                                       cor["groups"][m]["alpha"], cor["groups"][m]["n"]) for i, m in enumerate(MATERIALS))
         + "; 3 材料を混ぜた順位相関 %.2f" % cor["pooled"]["spearman"])
    # 門 22 60 min で則が破れる
    br = {}
    for m in MATERIALS:
        d60 = np.mean([G.particle_size_dx(D["add"][(m, "grind_robot60min", k)]) for k in (1, 2, 3)])
        t60 = 60.0 * (T[m].max() / 25.0)            # 25 min の取得の間隔で外挿(60 min の AE の取得回数は公開されていない)
        lw = fits[m]["best_fixed"]
        pred = float(_predict(lw, fits[m]["fits"][lw], [t60])[0])
        br[m] = {"d60": d60, "pred": pred, "d25": float(np.mean(X[m].reshape(3, 7)[:, -1])), "t60": t60}
    out["br"] = br
    gate("門 22 60 min: クエン酸は 25 min より粗くなる(凝集)—— 単調に細かくなる則はどれも表せない",
         br["Citricacid"]["d60"] > br["Citricacid"]["d25"],
         "; ".join("%s: 25 min %.1f → 60 min %.1f µm(則の予測 %.1f)" % (MAT_LABEL[m], v["d25"], v["d60"], v["pred"]) for m, v in br.items()))
    out["t_data"] = time.time() - t0
    print("  実データの門の所要 %.2f s" % out["t_data"])
    return out


def _pct(v):
    return "∞" if not math.isfinite(v) else "%+.0f %%" % (100 * v)


# ======================================================================================================================
# 図
# ======================================================================================================================
def figures(out: dict) -> None:
    print("== 図")
    im = out["img"]
    import blob2d
    lab = blob2d.blob_label(im["image"] > 0.02)
    rv = G.particle_image_d50(im["image"], 1.0)
    rn = G.particle_image_d50(im["image"], 1.0, basis="number")
    figs.save_grid("synthetic_particles_labels", [im["image"], blob2d.blob_overlay(im["image"], lab)],
                   captions=["coverage image (pitch 1 um/px)", "labels (border particles excluded from D50)"],
                   title="Image -> D50 (synthetic gate only)")
    d = np.sort(rv["diameters"])
    cv = np.cumsum(d ** 3) / np.sum(d ** 3)
    cn = np.arange(1, d.size + 1) / d.size
    figs.save_plot("image_volume_vs_number_basis", [("volume basis", d, cv), ("number basis", d, cn),
                                                    ("D50 volume %.1f um" % rv["d50"], [rv["d50"]] * 2, [0, 1]),
                                                    ("D50 number %.1f um" % rn["d50"], [rn["d50"]] * 2, [0, 1])],
                   xlabel="equivalent diameter [um]", ylabel="cumulative fraction", title="Same particles, two distributions",
                   styles=[None, None, "dashed", "dashed"], colors=["emphasis", "neutral", "emphasis", "neutral"],
                   caption="同じ画像の同じ粒子でも、体積基準の D50 は個数基準の %.2f 倍。レーザー回折は体積基準。" % (rv["d50"] / rn["d50"]))
    syn = out["mc_synth"]
    figs.save_table("law_identifiability_synthetic", ["true law", "ratio 20x, noise 10 %", "ratio 2.7x, noise 5 %"],
                    [[lw, "%.0f %%" % (100 * syn["ratio20"][lw]), "%.0f %%" % (100 * syn["ratio2.7"][lw])] for lw in G.LAWS],
                    title="How often the right comminution law wins (synthetic)",
                    caption="縮みが小さいと、雑音 5 %% でも 3 則の区別がつかない(%d 回ずつ)。" % MC_SEEDS)
    if "D" in out:
        _figures_data(out)
    else:
        print("  実データの図はデータがあるときだけ")
    print("  figures:", figs.errors() or "ok")


def _figures_data(out: dict) -> None:
    T, X, fits = out["T"], out["X"], out["fits"]
    for m in MATERIALS:
        tt = np.linspace(0.0, T[m].max() * 1.05, 120)
        ser = []
        for k, run in enumerate(RUNS):
            sl = slice(7 * k, 7 * k + 7)
            ser.append(("run %s" % run, T[m][sl], np.log10(X[m][sl])))
        kinds = ["scatter"] * 3
        styles, colors = [None] * 3, ["neutral"] * 3
        for lw, col in (("kick", "wrong"), ("bond", "reference"), ("rittinger", "emphasis")):
            f = fits[m]["fits"][lw]
            ser.append(("%s (rms %.3f)" % (lw, f["rms_log"]), tt[1:], np.log10(_predict(lw, f, tt[1:]))))
            kinds.append("line")
            styles.append("dashed")
            colors.append(col)
        ser.append(("before grinding (measured)", [0.0], [math.log10(out["init"][m])]))
        kinds.append("scatter")
        styles.append(None)
        colors.append("right")
        figs.save_plot("d50_vs_time_%s" % m, ser, xlabel="net grinding time [min] (acquisitions x 12 s)", ylabel="log10 D50 [um]",
                       title="%s: D50 falls with grinding, 3 independent runs" % MAT_LABEL[m], kinds=kinds, styles=styles, colors=colors,
                       size=(720, 440),
                       caption="%s の D50(独立 3 回)と 3 則の当てはめ。最良 %s。緑の点は粉砕前の実測(当てはめに使っていない)。"
                               % (MAT_LABEL[m], fits[m]["best_fixed"]))
    # 粒度分布が細かくなっていく GIF(1st の試行、累積の体積)
    frames = []
    for m in MATERIALS:
        pass
    D = out["D"]
    for idx, mn in enumerate((0,) + MINUTES):
        ser, cols, sty = [], [], []
        for m, col in zip(MATERIALS, ("reference", "emphasis", "wrong")):
            p = D["add"][(m, "initial", 1)] if mn == 0 else D["exp2"][(m, "1st", mn)]
            e = p["edges"]
            c = np.concatenate([[0.0], np.cumsum(p["volume"][:-1])]) / np.sum(p["volume"])
            ser.append(("%s D50 %.0f um" % (MAT_LABEL[m], G.particle_size_dx(p)), np.log10(e), c))
            cols.append(col)
            sty.append(None)
        img = figs.render_plot(ser, xlabel="log10 size [um]", ylabel="cumulative volume fraction",
                               title="Particle size distribution, %s" % ("before grinding" if mn == 0 else "%d min" % mn),
                               size=(720, 440), xlim=(-1.05, 3.1), ylim=(0, 1), colors=cols, styles=sty)
        frames.append(img)
    figs.save_gif("psd_fining_during_grinding", frames, fps=1.5,
                  caption="1st の試行の累積粒度分布が、粉砕前 → 3 → 25 min で左(細かい側)へ動く。")
    # AE のスペクトログラム(NaCl、3 min と 25 min の最後の取得)
    for m in ("NaCl",):
        panels, caps = [], []
        for mn in (3, 25):
            # 表示は窓 1024(0.5 ms)で時間を細かく: 0〜1 MHz の 513 行 × 約 1950 コマを等倍で
            b = G.ae_band_power(out["D"]["ae"][(m, mn)][1], AE_RATE, start=AE_START, stop=AE_STOP, win=1024)
            S = b["spectrogram_db"]
            keep = b["freqs"] <= 1.0e6
            panels.append(np.flipud(S[keep]))
            caps.append("%s %d min (0-1 MHz, %d frames)" % (MAT_LABEL[m], mn, S.shape[1]))
        lo = min(np.percentile(p, 5) for p in panels)
        hi = max(np.percentile(p, 99.5) for p in panels)
        panels = [np.clip((p - lo) / (hi - lo), 0, 1) for p in panels]
        figs.save_grid("ae_spectrogram_%s" % m, panels, captions=caps, title="AE spectrogram, same colour scale (dB), low frequency at the bottom",
                       ncols=1)
    P, Dd, grp, cor = out["ae_cor"]
    ser, cols = [], []
    for i, (m, col) in enumerate(zip(MATERIALS, ("reference", "emphasis", "wrong"))):
        ser.append(("%s alpha %.2f" % (MAT_LABEL[m], cor["groups"][m]["alpha"]), np.log10(Dd[2 * i:2 * i + 2]), np.log10(P[2 * i:2 * i + 2])))
        cols.append(col)
    figs.save_plot("ae_power_vs_d50", ser, xlabel="log10 D50 [um]", ylabel="log10 AE band power 0.1-1 MHz [mV^2]",
                   title="AE power falls with D50 (run 1st, last acquisition of 3 and 25 min)", colors=cols, size=(720, 440),
                   caption="各材料 2 点しか取っていない(データ量の上限)ので、傾き α は 2 点の比。材料で水準が桁で違う。")
    ser = []
    for m in ("NaCl", "MSG", "Citricacid"):
        b = out["bands"][(m, 25)]
        ser.append(("%s 25 min" % MAT_LABEL[m], b["times"], b["band_series"] * 1e6))
    figs.save_plot("ae_band_power_in_time", ser, xlabel="time in acquisition [s]", ylabel="band power [mV^2] (STFT density)",
                   title="AE band power inside one 0.5 s acquisition", size=(720, 400))
    # 一次の速度
    ser, kinds, sty, cols = [], [], [], []
    for m, col in zip(MATERIALS, ("reference", "emphasis", "wrong")):
        R = np.array([G.particle_size_oversize(out["D"]["exp2"][(m, run, mn)], 200.0) for run in RUNS for mn in MINUTES])
        r = out["fo"][m]["rows"][1]
        ser.append(("%s" % MAT_LABEL[m], out["T"][m], np.log(R)))
        kinds.append("scatter")
        sty.append(None)
        cols.append(col)
        tt = np.linspace(0, out["T"][m].max(), 50)
        ser.append(("", tt, math.log(r["w0"]) - r["S"] * tt))
        kinds.append("line")
        sty.append("dashed")
        cols.append(col)
    figs.save_plot("first_order_oversize_200um", ser, xlabel="net grinding time [min]", ylabel="ln R(200 um)",
                   title="Apparent first-order breakage of the coarse fraction", kinds=kinds, styles=sty, colors=cols, size=(720, 440))
    # 60 min で則が破れる
    br = out["br"]
    rows = [[MAT_LABEL[m], "%.1f" % v["d25"], "%.1f" % v["d60"], "%.1f" % v["pred"], out["fits"][m]["best_fixed"]] for m, v in br.items()]
    figs.save_table("where_the_laws_break_60min", ["material", "D50 25 min [um]", "D50 60 min [um]", "law prediction [um]", "law"], rows,
                    title="Past the plateau the monotone laws break",
                    caption="クエン酸は 60 min で 25 min より粗い(凝集)。単調に細かくなる則はどれも表せない。60 min は装置の設定も違う。")
    mc = out["mc_real"]
    figs.save_table("law_identifiability_real_design", ["material", "kick", "bond", "rittinger", "best fit"],
                    [[MAT_LABEL[m]] + ["%.0f %%" % (100 * mc[m][lw]) for lw in G.LAWS] + [out["fits"][m]["best_fixed"]] for m in MATERIALS],
                    title="Can this data tell the laws apart?",
                    caption="その材料の時点・縮み・残差で 3 則を作り直して当てたとき、正しい則が勝つ割合(%d 回)。" % MC_SEEDS)


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    out = numpy_part()
    root, why = _data_dir()
    if root is not None:
        out = data_part(out, root)
    else:
        skip("門 13〜22(実データ)", why)
    if figs.enabled():
        figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
