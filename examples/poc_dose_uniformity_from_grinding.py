# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""何分すり潰せば 1 回分の薬の量が揃うか —— 粒径から含量のばらつき(CV)を閉形式と Monte Carlo で出し、粉砕則で必要な時間を逆算する(2026-10-06)。

:mod:`grind`(乳鉢の粉砕を測る)の続き。新モジュール doseunif(3 op)。よく混ざった粉から 1 回分を取ると、薬の粒の数が Poisson で
揺らぐだけで含量がばらつく: ``CV² = (πρ/6) · D63³ / D``(D63 = 個数基準の 6 次と 3 次のモーメントの比の 3 乗根、導出は
doseunif の docstring)。体積基準の粒度分布からは恒等式 ``D63³ = E_v[d³]`` で形を仮定せずに出る。

何が外から来るか:
  * **Monte Carlo**: 1 回分を何千回も作って(粒の数を引き、径を引いて質量を足す)標本の CV を測る —— 閉形式を使わない独立な経路。
  * **公開データ**: grind が読むレーザー回折の粒度分布(Zenodo 10.5281/zenodo.18064323、CC BY 4.0。repo の外、環境変数
    FULLSEYE_GRIND_DATA)。3 材料 × 独立 3 回 × 7 時点。
  * **χ² 分布**(scipy): 10 個の標準偏差の分布 → 第 1 段の合格の確率の閉形式(Monte Carlo の模擬と突き合わせる)。

正直に(門に固定):
  * 試走で「写真から出した CV が 4 つの径で一貫して 6 % 低い」と見えたのは、4 つの径が画素の単位で同じ 12 枚の画像だったから(門 4)。
    独立な束に分けると、主因は **縁に触れる粒を捨てる大粒の取りこぼし(平均 −5 %)**、次が **d⁶ の重い裾(平均は偏らないが中央値が低い)**。
    Miles–Lantuéjoul の重み + 対数正規の当てはめで平均の偏りはほぼ消え、散らばりは半分になる(門 5)。モーメントの bootstrap の区間は
    真値を覆い損ねる(門 6)。
  * 実データでは **対数正規の当てはめ(D16/D50/D84 から)は全く使えない**(粉砕した粉は二峰で、exp(4.5σ²) が爆発する)—— 形を仮定しない
    ヒストグラムの恒等式が要る(門 10)。D63 は粗い裾に支配される(装置の分解能が最も悪い所)。
  * CV は粒の数の揺らぎだけ(混合・偏析・錠剤の質量・分析誤差は入らない)= 下限。受入値の数は二次資料による(公定の本文と照合していない)。
  * 時間は粒度分布のファイル名の「粉砕 N 分」(壁時計)。粉砕則は D63 に当てた(D50 に当てるのと同じく仮定)。

門(既定 13 本 = numpy だけ 10 + データ 2 + 所要 1、データが無ければ 2 本は skip)。既定は Monte Carlo 1,000 回・画像 30 束(CI の所要に合わせた)、
--full は 8,000 回・200 束。
図: 粉砕時間と CV(3 材料、独立 3 回、目標の線、則ごとの必要時間)、偏りの内訳(束ごとの CV の比)、10 個の含量と受入値
(挽き始め・途中・終わり)、合格の確率と CV。
Run: py -3.11 examples/poc_dose_uniformity_from_grinding.py [--full]
"""
from __future__ import annotations

import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import doseunif as DU  # noqa: E402
import examplefig as figs  # noqa: E402
import grind as G  # noqa: E402

FULL = "--full" in sys.argv
N_BATCH = 200 if FULL else 30   # 既定 = CI の PoC の門の経路(CI は手元の約 9 倍遅い)。束の統計の主張は --full の 200 束で
N_REP = 8000 if FULL else 1000
MATERIALS = ("NaCl", "Citricacid", "MSG")
MAT_LABEL = {"NaCl": "NaCl", "Citricacid": "citric acid", "MSG": "MSG"}
#: 真密度 [g/cm³](教科書の値の丸め。CV は √ρ でしか効かない)
DENSITY = {"NaCl": 2.16, "Citricacid": 1.66, "MSG": 1.62}
DOSE_DEMO = 5.0               # mg(この乳鉢の粉で目標に届く量。0.02〜1 mg の低用量は届かない —— 表で示す)
DOSES_TABLE = (0.1, 1.0, 5.0, 20.0)
RUNS = ("1st", "2nd", "3rd")
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}


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
    except Exception as exc:  # noqa: BLE001
        print("    (wrong exception %s: %s)" % (type(exc).__name__, exc))
        return False
    return False


# ======================================================================================================================
def numpy_part() -> dict:
    print("== numpy だけの門(閉形式・Monte Carlo・ヒストグラムの恒等式・画像の偏り・逆算・合格の確率)")
    out: dict = {}
    t0 = time.time()
    # 門 1 閉形式 vs Monte Carlo
    zs = []
    for d, s, D in ((40.0, 0.35, 0.02), (10.0, 0.5, 0.01), (80.0, 0.3, 1.0), (25.0, 0.6, 0.2)):
        for samp in ("poisson", "fixed_count"):
            r = DU.dose_cv_lognormal(d, s, D, 1.3, method="monte_carlo", sampling=samp, n_rep=N_REP, seed=int(d), max_draws=60_000_000)
            zs.append(((r["cv_mc"] - r["cv_closed"]) / r["cv_mc_se"], r["cv_closed"], r["cv_mc"], r["particles_per_dose"]))
    zmax = max(abs(z[0]) for z in zs)
    _NUM["mc"] = zs
    gate("門 1 閉形式 vs Monte Carlo(径を引いて足すだけ、式を使わない): 4 条件 × Poisson / 粒の数を固定、λ = %.0f〜%.0f、CV %.3f〜%.3f、"
         "差 / 標準誤差 最大 %.2f(%d 回ずつ)" % (min(z[3] for z in zs), max(z[3] for z in zs), min(z[1] for z in zs), max(z[1] for z in zs), zmax, N_REP),
         zmax < 4.5)    # 8 本の最大。標準誤差は 20 束の散らばり(--full で 3.95 を一度見た。σ = 0.6 の重い裾では標本の CV が平均 −0.5 σ_se 低い)
    # 門 2 恒等式
    a = DU.dose_cv_lognormal(30.0, 0.4, 0.05, 1.5, basis="number")
    b = DU.dose_cv_lognormal(a["d_volume_median"], 0.4, 0.05, 1.5, basis="volume")
    sc = (DU.dose_cv_lognormal(60.0, 0.4, 0.05, 1.5)["cv"] / a["cv"], DU.dose_cv_lognormal(30.0, 0.4, 0.2, 1.5)["cv"] / a["cv"],
          DU.dose_cv_lognormal(30.0, 0.4, 0.05, 6.0)["cv"] / a["cv"])
    fx = DU.dose_cv_lognormal(30.0, 0.4, 0.05, 1.5, sampling="fixed_count")
    # 固定数 N(λ を丸めた整数): CV² = (E[m²]/E[m]² − 1)/N = (e^{9σ²} − 1)/N、Poisson は e^{9σ²}/λ(N = λ なら差は 1/N)
    fx_err = abs(fx["cv"] ** 2 - (a["cv"] ** 2 * a["particles_per_dose"] - 1.0) / fx["particles_per_dose"]) / fx["cv"] ** 2
    hand = math.sqrt(math.pi * 1.5 * 1e-9 * (a["d_volume_median"]) ** 3 * math.exp(4.5 * 0.16) / (6 * 0.05))
    e2 = max(abs(b["cv"] / a["cv"] - 1), abs(sc[0] / 2 ** 1.5 - 1), abs(sc[1] / 0.5 - 1), abs(sc[2] / 2 - 1), abs(hand / a["cv"] - 1))
    gate("門 2 恒等式: 個数基準 ↔ 体積基準(Hatch–Choate)、CV ∝ d^{3/2}・D^{−1/2}・ρ^{1/2}、体積基準の手計算 πρd_v³e^{4.5σ²}/(6D)、"
         "固定数 = (λ CV²_Poisson − 1)/N: 最大の差 %.1e / %.1e" % (e2, fx_err), e2 < 1e-12 and fx_err < 1e-9)
    # 門 3 ヒストグラムの恒等式(体積基準の表、形を仮定しない)vs 閉形式
    hs = []
    for d50, s in ((30.0, 0.4), (100.0, 0.5), (8.0, 0.6), (200.0, 0.35)):
        p = G.particle_size_synth(d50, s)
        h = DU.dose_cv_from_sizes(p, 0.05, 1.3)
        c = DU.dose_cv_lognormal(d50, s, 0.05, 1.3, basis="volume")
        hs.append((h["cv_histogram"] / c["cv"] - 1, h["cv_lognormal"] / c["cv"] - 1))
    _NUM["hist"] = hs
    gate("門 3 体積基準の表 → 恒等式 D63³ = E_v[d³](区間の中は ln d で一様): 装置の 74 区間で閉形式との差 %s(区間の離散化で一様に +)、"
         "D16/D50/D84 から対数正規 ≤ %.2f %%" % (" / ".join("%+.2f %%" % (100 * v[0]) for v in hs), 100 * max(abs(v[1]) for v in hs)),
         max(abs(v[0]) for v in hs) < 0.01 and max(abs(v[1]) for v in hs) < 0.01)
    out.update(bias_part())
    # 門 7 逆算の往復(合成の Bond 則)
    x0, k = 400.0, 0.004
    tt = np.array([0, 5, 10, 20, 40.0])
    d = np.array([G.comminution_energy(x0, law="bond", energy=k * t)["x_product"] for t in tt])
    rho, D = 1.5, 5.0
    g1 = DU.grind_time_for_dose_cv(tt, d, D, rho, target_cv=0.05, law="bond")
    d_req = (0.05 ** 2 * D / (math.pi / 6 * rho * 1e-9)) ** (1 / 3)
    t_hand = (d_req ** -0.5 - x0 ** -0.5) / (0.5 * k)
    g2 = DU.grind_time_for_dose_cv(tt, d, D, rho, target_cv=0.005, law="bond")
    g0 = DU.grind_time_for_dose_cv(tt, d, D, rho, target_cv=0.5, law="bond")
    e7 = abs(g1["t_req"] / t_hand - 1)
    gate("門 7 逆算の往復(Bond 則の D63(t) → CV 5 %% に要る時間): 手計算 %.2f、op %.2f(差 %.1e)。目標 0.5 %% はより長く %.1f(外挿の印 %s)、"
         "既に届いている目標は 0(%s)" % (t_hand, g1["t_req"], e7, g2["t_req"], g2["extrapolated"], g0["already_met"]),
         e7 < 1e-6 and g2["t_req"] > g1["t_req"] and g2["extrapolated"] and g0["t_req"] == 0.0 and g0["already_met"] and g1["law"] == "bond")
    # 門 8 合格の確率: χ² の閉形式 vs Monte Carlo
    rows = []
    for cv in (0.03, 0.05, 0.0625, 0.08):
        gw = DU.grind_time_for_dose_cv(tt, d, D, rho, target_cv=cv, ref_range=(0.0, 1e9), n_mc=40000)
        gn = DU.grind_time_for_dose_cv(tt, d, D, rho, target_cv=cv, n_mc=40000)
        rows.append((cv, gw["pass_probability_chi2"], gw["pass_probability_mc"], gn["pass_probability_mc"]))
    gp = DU.grind_time_for_dose_cv(tt, d, D, rho, pass_probability=0.95)
    out["pass_rows"] = rows
    _NUM["pass"] = rows
    e8 = max(abs(r[1] - r[2]) for r in rows)
    gate("門 8 第 1 段の合格の確率: χ² の閉形式 vs 模擬(平均のずれの項を外すと)最大の差 %.3f。項を入れると下がる(CV 6.25 %%: %.3f → %.3f)。"
         "「AV ≤ 15 相当」の CV 6.25 %% は約半分しか通らない。95 %% 通すには CV ≤ %.2f %%" % (e8, rows[2][1], rows[2][3], 100 * gp["target_cv"]),
         e8 < 0.01 and all(r[3] <= r[2] + 0.005 for r in rows) and 0.5 < rows[2][1] < 0.6 and 0.04 < gp["target_cv"] < 0.05)
    # 門 9 綴り壊し
    psd = G.particle_size_synth(30.0, 0.4)
    checks = [
        _raises(DU.dose_cv_lognormal, -1.0, 0.4, 0.05, 1.5), _raises(DU.dose_cv_lognormal, 30.0, 0.4, 0.05, 1.5, basis="mass"),
        _raises(DU.dose_cv_lognormal, 30.0, 0.4, 0.05, 1.5, method="mc"), _raises(DU.dose_cv_lognormal, 30.0, True, 0.05, 1.5),
        _raises(DU.dose_cv_lognormal, 1.0, 0.4, 1000.0, 1.5, method="monte_carlo", n_rep=1000),         # 引く数が上限を超える
        _raises(DU.dose_cv_lognormal, 300.0, 0.4, 0.001, 1.5, sampling="fixed_count"),               # 1 回分に 2 粒未満
        _raises(DU.dose_cv_from_sizes, [10.0] * 5, 0.05, 1.5), _raises(DU.dose_cv_from_sizes, [10.0] * 9 + [float("nan")], 0.05, 1.5),
        _raises(DU.dose_cv_from_sizes, np.full(20, 10.0), 0.05, 1.5, frame=(8, 8, 1.0)),
        _raises(DU.dose_cv_from_sizes, psd, 0.05, 1.5, estimator="moment"), _raises(DU.dose_cv_from_sizes, psd, 0.05, 1.5, frame=(64, 64, 1)),
        _raises(DU.dose_cv_from_sizes, {"edges": [1, 2, 3], "volume": [1, 1, 1]}, 0.05, 1.5),
        _raises(DU.grind_time_for_dose_cv, tt, d, D, rho, target_cv=0.05, pass_probability=0.9),
        _raises(DU.grind_time_for_dose_cv, tt, d, D, rho, target_cv=5.0), _raises(DU.grind_time_for_dose_cv, tt, d[:3], D, rho),
        _raises(DU.grind_time_for_dose_cv, tt, d, D, rho, law="walker"), _raises(DU.grind_time_for_dose_cv, tt, d, D, rho, ref_range=(99, 99.5)),
    ]
    gate("門 9 綴り壊し・測れない入力は ValueError(%d / %d)" % (sum(checks), len(checks)), all(checks))
    docs_ok = all((getattr(DU, n).__doc__ or "").strip() and "](" not in getattr(DU, n).__doc__ for n in DU.__all__)
    gate("門 12 入口: __all__ の %d op が実在し docstring あり、Markdown のリンク記法なし" % len(DU.__all__), docs_ok and "](" not in DU.__doc__)
    out["inv"] = (tt, d, g1)
    print("    (%.1f s)" % (time.time() - t0))
    return out


def _batch(seed0, d_med=24.0, sig=0.35, n_img=12, H=256):
    pitch = d_med / 12.0
    A, M = [], []
    for s in range(n_img):
        im = G.particle_image_synth(n=60, d_med=d_med, sigma_ln=sig, shape=(H, H), pitch=pitch, seed=seed0 + s)
        A.append(im["truth"]["diameters"])
        M.append(G.particle_image_d50(im["image"], pitch, basis="number")["diameters"])
    return np.concatenate(A), np.concatenate(M), (H, H, pitch)


def bias_part() -> dict:
    """画像の標本から出す CV の偏り: 4 つの径の試走の正体、独立な束での内訳、区間の被覆。"""
    t0 = time.time()
    D, rho, sig, d_med = 0.02, 1.3, 0.35, 24.0
    true = DU.dose_cv_lognormal(d_med, sig, D, rho)["cv"]
    # 門 4 試走の再現: 4 つの径・種 0〜11・画素ピッチ = 径/12 → 同じ画像
    ratios = []
    for dm in (40.0, 24.0, 14.0, 8.0):
        _, m, _ = _batch(0, d_med=dm)
        ratios.append(DU.dose_cv_from_sizes(m, D, rho, estimator="moment", n_boot=50)["cv"] / DU.dose_cv_lognormal(dm, sig, D, rho)["cv"])
    gate("門 4 試走の「4 つの径で一貫して −6 %%」の正体: 比 %s は小数 12 桁まで同じ = 画素の単位で同じ 12 枚を縮尺違いで測っていた"
         "(独立な 4 回ではない)" % " / ".join("%.4f" % r for r in ratios), np.ptp(ratios) < 1e-9 and abs(ratios[0] - 0.9395) < 0.002)
    keys = ("truth_moment", "measured_moment", "measured_moment_ML", "measured_lognormal_ML")
    res = {k: [] for k in keys}
    cover = {"boot_moment": 0, "boot_lognormal": 0, "delta_lognormal": 0}
    dom = []
    for b in range(N_BATCH):
        a, m, fr = _batch(10_000 + 100 * b)
        res["truth_moment"].append(DU.dose_cv_from_sizes(a, D, rho, estimator="moment", n_boot=50)["cv"] / true)
        r0 = DU.dose_cv_from_sizes(m, D, rho, estimator="moment", n_boot=50)
        r1 = DU.dose_cv_from_sizes(m, D, rho, frame=fr, n_boot=300, seed=b)
        res["measured_moment"].append(r0["cv"] / true)
        res["measured_moment_ML"].append(r1["cv_moment"] / true)
        res["measured_lognormal_ML"].append(r1["cv_lognormal"] / true)
        dom.append(r1["top1pct_share_d6"])
        cover["boot_moment"] += r1["ci_bootstrap"]["moment"][0] <= true <= r1["ci_bootstrap"]["moment"][1]
        cover["boot_lognormal"] += r1["ci_bootstrap"]["lognormal"][0] <= true <= r1["ci_bootstrap"]["lognormal"][1]
        cover["delta_lognormal"] += r1["ci_delta"][0] <= true <= r1["ci_delta"][1]
    st = {k: (float(np.mean(v)), float(np.median(v)), float(np.std(v))) for k, v in res.items()}
    cov = {k: v / N_BATCH for k, v in cover.items()}
    _NUM["bias"] = {"stats": st, "cover": cov, "dom": float(np.median(dom)), "n_batch": N_BATCH}
    tm, mm, mml, mll = (st[k] for k in keys)
    gate("門 5 偏りの内訳(独立な %d 束 × 12 枚、約 600 粒、CV の比 = 推定 / 真値の平均・中央値・散らばり): 真の径のモーメント %.3f / %.3f / ±%.3f"
         "(d⁶ の重い裾: 平均は偏らず中央値が低い、最大 1 %% の粒が Σd⁶ の %.0f %%)、縁の粒を捨てた測定 %.3f / %.3f(大粒の取りこぼし)、"
         "+ Miles–Lantuéjoul %.3f / %.3f、+ 対数正規 %.3f / %.3f / ±%.3f"
         % (N_BATCH, tm[0], tm[1], tm[2], 100 * np.median(dom), mm[0], mm[1], mml[0], mml[1], mll[0], mll[1], mll[2]),
         abs(tm[0] - 1) < 0.035 and tm[1] < 0.995 and mm[0] < 0.97 and mml[0] > mm[0] + 0.015 and abs(mll[0] - 1) < 0.025 and mll[2] < 0.6 * tm[2])
    gate("門 6 90 %% の区間が真値を覆う割合(%d 束): モーメントの bootstrap %.2f(重い裾で覆い損ねる)、対数正規の bootstrap %.2f、デルタ法(Kish の有効数)%.2f"
         % (N_BATCH, cov["boot_moment"], cov["boot_lognormal"], cov["delta_lognormal"]),
         cov["boot_moment"] < 0.8 and cov["delta_lognormal"] >= 0.78 and cov["boot_lognormal"] > cov["boot_moment"])
    print("    (画像の束 %.1f s)" % (time.time() - t0))
    return {"bias": res}


# ======================================================================================================================
def _data_dir():
    p = os.environ.get("FULLSEYE_GRIND_DATA", "").strip()
    if not p:
        return None, "環境変数 FULLSEYE_GRIND_DATA が無い(公開データは repo の外)"
    root = Path(p) / "data_public" / "powder_size_distribution" / "exp2"
    if not root.is_dir():
        return None, "FULLSEYE_GRIND_DATA に exp2 の粒度分布が無い"
    return root, ""


def data_part(out: dict, root: Path) -> dict:
    print("== 実データ(レーザー回折の粒度分布、3 材料 × 独立 3 回 × 7 時点)")
    t0 = time.time()
    rows = {}
    for m in MATERIALS:
        for run in RUNS:
            for f in sorted((root / m / run).glob("*.csv")):
                mt = re.search(r"grind(\d+)min", f.name)
                if not mt:
                    continue
                p = G.particle_size_read(str(f))
                h = DU.dose_cv_from_sizes(p, DOSE_DEMO, DENSITY[m])
                rows[(m, run, int(mt.group(1)))] = h
    n = len(rows)
    vals = np.array([[r["cv_histogram"], r["cv_lognormal"], r["d63"], r["coarse_share"], r["particles_per_dose"]] for r in rows.values()])
    fin = bool(np.all(np.isfinite(vals[:, [0, 2, 3, 4]])) and np.all(vals[:, 0] > 0))
    lr = vals[:, 1] / vals[:, 0]
    _NUM["real"] = {"n": n, "logn_ratio_median": float(np.median(lr)), "logn_ratio_max": float(lr.max()), "logn_ratio_min": float(lr.min()),
                    "coarse_median": float(np.median(vals[:, 3])), "d63": (float(vals[:, 2].min()), float(vals[:, 2].max()))}
    gate("門 10 実データ %d 本: 形を仮定しない D63 = %.0f〜%.0f µm(有限・正)。D16/D50/D84 から対数正規を当てた CV はその %.2f〜%.3g 倍(中央値 %.1f 倍)"
         "—— 粉砕した粉は二峰で exp(4.5σ²) が爆発し、対数正規は全く使えない。D63 のうち D90 より上の区間の寄与の中央値 %.0f %%"
         % (n, vals[:, 2].min(), vals[:, 2].max(), lr.min(), lr.max(), np.median(lr), 100 * np.median(vals[:, 3])),
         n == 63 and fin and np.median(lr) > 2.0)
    mono = []
    fits = {}
    for m in MATERIALS:
        for run in RUNS:
            mono.append(rows[(m, run, 25)]["cv"] < rows[(m, run, 3)]["cv"])
        keys = sorted(k for k in rows if k[0] == m)
        t = np.array([k[2] for k in keys], float)
        d63 = np.array([rows[k]["d63"] for k in keys])
        res = {}
        for dose in DOSES_TABLE:
            res[dose] = DU.grind_time_for_dose_cv(t, d63, dose, DENSITY[m])
        fits[m] = {"t": t, "d63": d63, "keys": keys, "res": res}
    tab = {m: {dose: fits[m]["res"][dose] for dose in DOSES_TABLE} for m in MATERIALS}
    _NUM["inverse"] = {m: {dose: (r["t_req"], r["law"], r["t_req_spread"], r["extrapolated"]) for dose, r in tab[m].items()} for m in MATERIALS}
    flag_ok = all((r["t_req"] > 25.0) == r["extrapolated"] for m in MATERIALS for r in tab[m].values())
    gate("門 11 CV は挽くほど下がる(25 min < 3 min: %d / 9 の材料 × 試行)。%.0f mg で目標 6.25 %% に要る時間(21 点に則を当て、則の幅): %s。"
         "0.1 mg は %s(外挿の印つき)" % (sum(mono), DOSE_DEMO,
                                      "、".join("%s %.0f min(%s、%.0f〜%.0f)%s" % (MAT_LABEL[m], tab[m][DOSE_DEMO]["t_req"], tab[m][DOSE_DEMO]["law"],
                                                                                   *tab[m][DOSE_DEMO]["t_req_spread"],
                                                                                   " 外挿" if tab[m][DOSE_DEMO]["extrapolated"] else "")
                                                for m in MATERIALS),
                                      "、".join("%s %.0f min" % (MAT_LABEL[m], tab[m][0.1]["t_req"]) for m in MATERIALS)),
         sum(mono) == 9 and flag_ok and all(tab[m][0.1]["extrapolated"] for m in MATERIALS))
    out.update({"rows": rows, "fits": fits})
    print("    (%.1f s)" % (time.time() - t0))
    return out


# ======================================================================================================================
def figures(out: dict) -> None:
    print("== 図")
    st = out["bias"]
    labels = ("true diameters, moment", "measured, moment", "measured, moment + edge weights", "measured, lognormal + edge weights")
    ser, kinds, cols = [], [], []
    rng = np.random.default_rng(0)
    for i, (k, lab, col) in enumerate(zip(st, labels, ("neutral", "wrong", "emphasis", "right"))):
        v = np.asarray(st[k])
        ser.append((lab, i + rng.uniform(-0.18, 0.18, v.size), v))
        kinds.append("scatter")
        cols.append(col)
    ser.append(("truth", [-0.4, 3.4], [1.0, 1.0]))
    kinds.append("line")
    cols.append("reference")
    figs.save_plot("cv_bias_decomposition", ser, xlabel="estimator (0 to 3)", ylabel="CV estimate / true CV, per batch of 12 images",
                   title="Where the low CV from photos comes from", kinds=kinds, colors=cols,
                   styles=[None] * 4 + ["dashed"], size=(760, 460),
                   caption="1 点 = 独立な 12 枚の束(約 600 粒)。縁に触れる粒を捨てると大きい粒ほど抜けて低く出る(赤)。縁の重みで平均は戻るが散らばりは大きいまま(橙)。"
                           "対数正規を当てると散らばりが半分(緑)。")
    if "fits" in out:
        for m in MATERIALS:
            f = out["fits"][m]
            r = f["res"][DOSE_DEMO]
            cv = r["cv_observed"]
            tt = np.linspace(1.0, max(60.0, 1.1 * min(r["t_req"], 120.0)), 120)
            ser = [("measured (3 runs)", f["t"], 100 * cv)]
            kinds, sty, cols = ["scatter"], [None], ["neutral"]
            c = math.pi / 6 * DENSITY[m] * 1e-9
            for lw, col in (("kick", "wrong"), ("bond", "reference"), ("rittinger", "emphasis")):
                fit = r["fits"][lw]
                dd = np.array([G.comminution_energy(fit["x0"], law=lw, energy=fit["k"] * t)["x_product"] for t in tt])
                ser.append(("%s: %.0f min" % (lw, r["t_req_by_law"][lw]), tt, 100 * np.sqrt(c * dd ** 3 / DOSE_DEMO)))
                kinds.append("line")
                sty.append("dashed")
                cols.append(col)
            ser.append(("target %.2f %% (AV 15, k 2.4)" % (100 * r["target_cv"]), [0, tt[-1]], [100 * r["target_cv"]] * 2))
            kinds.append("line")
            sty.append("dotted")
            cols.append("right")
            figs.save_plot("cv_vs_grinding_%s" % m, ser, xlabel="grinding time [min] (file label)", ylabel="content CV of one %.0f mg dose [%%]" % DOSE_DEMO,
                           title="%s: how long to grind for a uniform %.0f mg dose" % (MAT_LABEL[m], DOSE_DEMO), kinds=kinds, styles=sty, colors=cols,
                           size=(760, 460),
                           caption="レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。3 則の必要時間 %.0f〜%.0f min。%s"
                                   % (r["t_req_spread"] + (("目標が測った範囲の近くなので則はほぼ同じ答えを返す。0.1 mg(%.0f〜%.0f min)のような遠い外挿では則で大きく開く。"
                                                            % f["res"][0.1]["t_req_spread"]) if r["t_req_spread"][1] < 1.2 * r["t_req_spread"][0]
                                                           else "則で答えが開く —— 外挿の幅として読む。",)))
        _ten_units(out)
        rows = [[MAT_LABEL[m]] + ["%.0f%s" % (out["fits"][m]["res"][dose]["t_req"], "*" if out["fits"][m]["res"][dose]["extrapolated"] else "")
                                  for dose in DOSES_TABLE] for m in MATERIALS]
        figs.save_table("grinding_time_by_dose", ["material"] + ["%g mg" % d for d in DOSES_TABLE], rows,
                        title="Minutes to CV 6.25 %",
                        caption="最良の則で、CV 6.25 % に要る粉砕時間 [min]。* は測った 25 min を超える外挿。乳鉢で挽いた塩・有機酸は 0.1〜1 mg の低用量には"
                                "届かない(粗い裾が残る)。低用量はこの粉砕では作れない、という答え。")
    pr = out["pass_rows"]
    figs.save_plot("pass_probability_vs_cv", [
        ("chi-square bound (mean on target)", [100 * r[0] for r in pr], [r[1] for r in pr]),
        ("simulation, mean term off", [100 * r[0] for r in pr], [r[2] for r in pr]),
        ("simulation, with |M - mean| term", [100 * r[0] for r in pr], [r[3] for r in pr])],
        xlabel="true content CV [%]", ylabel="probability to pass stage 1 (10 units)", title="CV 6.25 % passes only about half the time",
        kinds=["line", "scatter", "scatter"], styles=["dashed", None, None], colors=["reference", "emphasis", "wrong"], size=(720, 440),
        caption="10 個の標準偏差は標本ごとに揺らぐので、「AV ≤ 15 相当」の CV 6.25 %% の粉は第 1 段を約半分しか通らない(χ² の閉形式 %.2f、平均のずれの項も入れた模擬 %.2f)。"
                % (pr[2][1], pr[2][3]))


def _ten_units(out: dict) -> None:
    """NaCl の 3 / 10 / 25 min の CV で 5 mg の 10 個の含量を 1 回引き(正規近似)、受入値と第 1 段の合格の確率(模擬 20,000 回)を出す。"""
    rng = np.random.default_rng(7)
    f = out["fits"]["NaCl"]
    r = f["res"][DOSE_DEMO]
    ser, kinds, cols, probs = [], [], [], []
    for j, (mn, col) in enumerate(((3, "wrong"), (10, "emphasis"), (25, "right"))):
        cv = float(np.mean([r["cv_observed"][i] for i, k in enumerate(f["keys"]) if k[2] == mn]))
        x = 100 * (1 + cv * rng.standard_normal(10))
        xb, s = x.mean(), x.std(ddof=1)
        av = abs(min(max(xb, 98.5), 101.5) - xb) + 2.4 * s
        p = DU._stage1_pass_mc(cv, 10, 2.4, 15.0, (98.5, 101.5), 20000, 1)
        probs.append((mn, cv, p))
        ser.append(("%d min: CV %.1f %%, this draw AV %.1f" % (mn, 100 * cv, av), j + np.linspace(-0.3, 0.3, 10), x))
        kinds.append("scatter")
        cols.append(col)
    ser.append(("label claim", [-0.5, 2.5], [100, 100]))
    kinds.append("line")
    cols.append("reference")
    figs.save_plot("ten_units_NaCl", ser, xlabel="grinding stage (3, 10, 25 min)", ylabel="content of each unit [% of label]",
                   title="Ten %.0f mg doses of ground NaCl" % DOSE_DEMO, kinds=kinds, colors=cols, styles=[None] * 3 + ["dashed"], size=(720, 440),
                   caption="同じ粉を挽く時間だけ変えて %.0f mg を 10 個取った含量(粒の数の揺らぎだけ、正規近似の 1 回の模擬)。第 1 段に通る確率は %s。"
                           % (DOSE_DEMO, "、".join("%d min %.0f %%" % (mn, 100 * p) for mn, _, p in probs)))


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    out = numpy_part()
    root, why = _data_dir()
    if root is not None:
        out = data_part(out, root)
    else:
        skip("門 10〜11(実データ)", why)
    el = time.time() - t_all
    budget = 120.0 if FULL else 30.0
    gate("門 13 所要 %.1f s ≤ %.0f s" % (el, budget), el <= budget)
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
