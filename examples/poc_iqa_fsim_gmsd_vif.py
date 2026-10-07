# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""知覚指標 FSIM / FSIMc / GMSD / VIF を外から来た真値で 4 桁一致させる —— TID2013 の作者値ファイル 3 本と公表の順位相関表(2026-10-04)。

IQA 系列の第 2 弾(第 1 弾 = poc_iqa_tid2013: PSNR / SSIM)。第 1 弾が「未実装で公表値だけ表に」していた FSIM / FSIMc / VIFP を numpy + scipy
だけで実装し(新モジュール iqafsim)、配布物に無い GMSD も足した。真値は 3 段:
  * 作者値ファイル(FSIM.txt / FSIMc.txt / VIFP.txt、3,000 行 × 4 桁)と**行ごと** —— 丸め幅の中(≤ 1e-4)
  * TID2013 論文(Ponomarenko ほか 2015)Table 4 / 5 の順位相関 **4 桁**(Full と 7 部分集合)、readme の 3 桁表
  * GMSD だけは作者値が無く(配布物 2013 年、GMSD 2014 年)、二次資料(Nafchi ほか 2016)の |SROCC| 0.8044 / |KROCC| 0.6339 に ±0.005 —— 等級が 1 段低い
入力の規約は**実測で特定**(どのページにも書かれていない): FSIM.txt と VIFP.txt は PSNR / SSIM と同じ **Y′ limited(16–235 の整数)の灰色画像**、
FSIMc.txt は色 BMP → YIQ(full range)。つまり FSIM.txt は FSIMc 計算の中の FSIM 成分ではない(色画像の Y で測ると max 0.0318 ずれる)。

門 26 本(合成 10 本は常に走る): 恒等 FSIM = FSIMc = 1・GMSD = 0・VIF = 1、雑音 σ で単調(順位相関 ∓1)、FSIM / GMSD の対称と VIF の非対称、位相一致の
利得不変(ε = 1e-12 で 1e-10、既定 ε の残差は ε に比例)と値域、偶数核の 'same' の規約(2×2 平均 + 間引き = ブロック平均 —— scipy の 'same' は半画素
ずれる)、round(1.5) = 2、第 2 実装(モノジェニック位相一致)との相関、GMS 値域と VIF > 1(コントラスト強調)、fail-closed、公表表の 4 桁と 3 桁が同じ答え。
実データ(FULLSEYE_TID2013_DATA、既定 = 先頭 120 組 = 参照 I01 の 24 種 × 5 段、約 30 s): 行ごと ≤ 1e-4 の 3 本、反例、GMSD の負の相関。
``--full`` で 3,000 組(約 11 分、実測 674 s): 順位相関 Full / 7 部分集合が論文の 4 桁と(作者と同じ 4 桁丸めで Δ 0.0000、丸めない値は ± 0.001)、GMSD ±0.005、
歪み種 24 の表。

図(FULLSEYE_FIGURE_DIR があるとき、6 枚): MOS 散布 4 枚(fsim / fsimc / vifp / gmsd、題に SROCC と公表値)、歪み種別 SROCC の棒、
公表 / 作者値 / 再現の表(GMSD の行は「二次資料」と等級を明記)。

正直に: 4 桁一致は作者と同じ規約を踏んだからで性能の話ではない(SROCC: FSIMc 0.851 が 1 位、VIFP 0.608 は 13 位)。GMSD は二次資料との照合だけ。
steerable 版 VIF(論文の「VIF」0.677)は配布物に値ファイルが無く未実装。歪み 16–18(平均シフト・コントラスト・彩度)は 4 指標とも弱く、
彩度変化では輝度しか見ない FSIM / VIFP / GMSD の順位相関が 0.2 / −0.16 / 0.19 に落ちる(FSIMc は 0.84)。踏んだ罠: 偶数核の 'same' の半画素、
round(1.5)、ε の置き場(分母に足すと利得不変が 3e-5 崩れる)、GMSD の符号(lower is better、公表表は |ρ|)、公表表は 4 桁丸めの値から計算されている。
Run: set FULLSEYE_TID2013_DATA=<TID2013 の展開先>\\tid2013 & py -3.11 examples/poc_iqa_fsim_gmsd_vif.py [--full] [--pairs N]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import iqafsim as F  # noqa: E402
import iqatid as IQ  # noqa: E402

_GATES = []
ROW_TOL = 1e-4            # 作者値 4 桁 → 丸め半分 5e-5 + 余裕
CORR_TOL_RAW = 1e-3       # 丸めない自前の値 vs 論文の 4 桁
CORR_TOL_R4 = 3e-4        # 作者と同じ 4 桁丸め → 論文の 4 桁
GMSD_TOL = 5e-3           # 二次資料(他人の実装の値)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def synth_image(h=192, w=256, seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = 60.0 + 100.0 * xx / w
    img += 80.0 * (((yy - h / 2) ** 2 + (xx - w / 2) ** 2) < (h / 4) ** 2)
    img += 30.0 * np.sin(2 * np.pi * yy / 12.0) * (xx > w * 0.7)
    img += rng.normal(0, 1.5, (h, w))
    return np.clip(img, 0, 255)


def synthetic_part():
    print("== 1. 合成の門(常に走る)")
    g = synth_image()
    rgb = np.stack([np.clip(g * 1.1, 0, 255), g, np.clip(g * 0.8 + 20, 0, 255)], axis=-1)
    fp = F.fsim_pair(rgb, rgb)
    gate("恒等: FSIM = FSIMc = 1、GMSD = 0、VIF = 1(1e-9)", fp["fsim"] == 1.0 and fp["fsimc"] == 1.0 and F.gmsd(g, g) == 0.0 and abs(F.vifp(g, g) - 1) < 1e-9,
         "vif %.12f" % F.vifp(g, g))
    rng = np.random.default_rng(1)
    sig = [2.0, 5.0, 10.0, 20.0, 40.0]
    fs, gs, vs = [], [], []
    for s in sig:
        d = np.clip(g + rng.normal(0, s, g.shape), 0, 255)
        fs.append(F.fsim(g, d))
        gs.append(F.gmsd(g, d))
        vs.append(F.vifp(g, d))
    gate("単調: 雑音 σ = 2…40 で FSIM・VIF が厳密減少、GMSD が厳密増加(iqatid.rank_spearman で −1 / −1 / +1)",
         IQ.rank_spearman(sig, fs) == -1.0 and IQ.rank_spearman(sig, vs) == -1.0 and IQ.rank_spearman(sig, gs) == 1.0,
         "fsim %s gmsd %s vif %s" % (np.round(fs, 3).tolist(), np.round(gs, 3).tolist(), np.round(vs, 3).tolist()))
    d = np.clip(g + rng.normal(0, 10, g.shape), 0, 255)
    gate("対称: FSIM(a,b) = FSIM(b,a)、GMSD(a,b) = GMSD(b,a)(厳密)、VIF は非対称(参照の情報量で割る)",
         F.fsim(g, d) == F.fsim(d, g) and F.gmsd(g, d) == F.gmsd(d, g) and F.vifp(d, g) < F.vifp(g, d) - 0.05,
         "vif(g,d) %.4f vs vif(d,g) %.4f" % (F.vifp(g, d), F.vifp(d, g)))
    pc1, pc2 = F.phase_congruency_pc(g), F.phase_congruency_pc(2.0 * g)
    e1, e2 = F.phase_congruency_pc(g, epsilon=1e-12), F.phase_congruency_pc(2.0 * g, epsilon=1e-12)
    gate("位相一致: 利得 ×2 で不変(ε = 1e-12 なら 1e-10、既定 ε = 1e-4 の残差は ε に比例)、値域 [0, 1]",
         np.abs(e1 - e2).max() < 1e-10 and 0 < np.abs(pc1 - pc2).max() < 1e-4 and pc1.min() >= 0 and pc1.max() <= 1,
         "ε=1e-12: %.1e / ε=1e-4: %.1e" % (np.abs(e1 - e2).max(), np.abs(pc1 - pc2).max()))
    a = np.arange(48.0).reshape(6, 8)
    from scipy.signal import convolve2d
    gate("偶数核の 'same' は原実装の規約: 2×2 平均 + 間引き = ブロック平均(scipy の 'same' は半画素ずれて別の答え)",
         np.array_equal(F._average_downsample(a, 2), a.reshape(3, 2, 4, 2).mean(axis=(1, 3)))
         and not np.array_equal(F._conv2_same_ref(a, np.full((2, 2), .25)), convolve2d(a, np.full((2, 2), .25), mode="same")))
    gate("ダウンサンプル係数 F = round(min(H,W)/256): 384×512 → 2(1.5 は 0 から遠い側へ)、256 → 1、2.5 → 3(numpy の半偶数なら 2)",
         F._ref_round(1.5) == 2 and F._ref_round(1.0) == 1 and F._ref_round(2.5) == 3 and int(np.round(2.5)) == 2)
    import backends_transform2 as BT
    mono = np.asarray(BT.tf_phase_congruency(g / 255.0, 0.0, 0.5), dtype=np.float64)
    r = float(np.corrcoef(pc1.ravel(), mono.ravel())[0, 1])
    gate("第 2 実装: 既存 phase_congruency(Riesz / モノジェニック版)と同じ場所が光る(Pearson > 0.6; 同じ式ではないので一致でなく相関)", r > 0.6, "r = %.3f" % r)
    q = F.gmsd_map(g, d)
    enh = np.clip((g - g.mean()) * 1.4 + g.mean(), 0, 255)
    gate("GMS 地図 ∈ (0, 1]、VIF(コントラスト ×1.4)> 1 —— VIF は忠実度でなく情報量の比(作者値の最大 1.1379 も歪み 17)",
         q.min() > 0 and q.max() <= 1 and F.vifp(g, enh) > 1.0, "gms [%.3f, %.3f], vif_enh %.4f" % (q.min(), q.max(), F.vifp(g, enh)))
    gate("fail-closed: 形違い・1-D・平坦画像(PC = 0 → 0/0)・参照が平坦な VIF・data_range 0 で ValueError",
         _raises(lambda: F.fsim(g, g[:-1])) and _raises(lambda: F.phase_congruency_pc(np.zeros(5)))
         and _raises(lambda: F.fsim(np.zeros((8, 8)), np.zeros((8, 8)))) and _raises(lambda: F.vifp(np.zeros((40, 40)), np.ones((40, 40))))
         and _raises(lambda: F.gmsd(g, g, data_range=0.0)))
    pub = IQ.tid2013_published()
    gate("公表表: 論文 Table 4/5 の 4 桁(7 列)を 3 桁に丸めると readme の表(fsim 0.801 / fsimc 0.851 / vifp 0.608)に一致、GMSD は二次資料 0.8044 / 0.6339",
         all(round(F.TID2013_PAPER_SROCC[k][-1], 3) == pub[k][0] and round(F.TID2013_PAPER_KROCC[k][-1], 3) == pub[k][1] for k in ("fsim", "fsimc", "vifp"))
         and F.GMSD_TID2013_SECONDARY[:2] == (0.8044, 0.6339))


def _subset_corr(values, ix, idx, subset):
    m = np.isin(ix["dist_type"][idx], list(subset))
    return IQ.rank_spearman(ix["mos"][idx][m], values[m]), IQ.rank_kendall_b(ix["mos"][idx][m], values[m])


def real_part(root, n_pairs, full):
    print("== 2. 実データ(%s、%s)" % (root, "3,000 組" if full else "先頭 %d 組" % n_pairs))
    t0 = time.time()
    ix = IQ.tid2013_index(root)
    subset = None if full else n_pairs
    pairs = []
    rc = IQ.tid2013_evaluate(root, lambda a, b: pairs.append(F.fsim_pair(a, b)) or pairs[-1]["fsimc"], subset=subset, luma="rgb", index=ix)
    rf = IQ.tid2013_evaluate(root, F.fsim, subset=subset, luma="limited_u8", index=ix)
    rv = IQ.tid2013_evaluate(root, F.vifp, subset=subset, luma="limited_u8", index=ix)
    rg = IQ.tid2013_evaluate(root, F.gmsd, subset=subset, luma="rgb", index=ix)
    print("  %d 組: fsim_pair(rgb) %.1f s + fsim(Y′) %.1f s + vifp(Y′) %.1f s + gmsd %.1f s" % (rc["n"], rc["seconds"], rf["seconds"], rv["seconds"], rg["seconds"]))
    idx = rc["idx"]
    pub = IQ.tid2013_published()
    res = {"ix": ix, "idx": idx, "fsimc": rc, "fsim": rf, "vifp": rv, "gmsd": rg, "cmp": {}}
    for key, r, conv in (("fsimc", rc, "色 → YIQ full"), ("fsim", rf, "Y′ limited 灰色"), ("vifp", rv, "Y′ limited")):
        au = IQ.tid2013_metric_values(root, key)[idx]
        c = IQ.tid2013_compare(r["values"], au, r["mos"], published=pub[key])
        res["cmp"][key] = c
        gate("%s(%s)= %s.txt 行ごと ≤ %.0e(%d 組)" % (key, conv, key.upper(), ROW_TOL, c["n"]), c["diff_max"] <= ROW_TOL,
             "max %.2e at %s, rms %.1e" % (c["diff_max"], r["names"][c["argmax"]], c["diff_rms"]))
    fsim_rgb = np.array([p["fsim"] for p in pairs])
    dd = np.abs(fsim_rgb - IQ.tid2013_metric_values(root, "fsim")[idx])
    gate("反例: 色画像の full-range Y で測った FSIM は FSIM.txt と合わない(max > 1e-3)—— 作者は FSIM を Y′ limited の灰色画像で計算している",
         dd.max() > 1e-3, "max %.4f, mean %.4f" % (dd.max(), dd.mean()))
    gate("GMSD(作者値ファイル無し): 有限・[0, 0.5)・MOS と負の順位相関(lower is better)", np.all(np.isfinite(rg["values"])) and rg["values"].max() < 0.5 and rg["srocc"] < -0.7,
         "ρ %+.4f τ %+.4f" % (rg["srocc"], rg["krocc"]))
    if full:
        for key, r in (("fsim", rf), ("fsimc", rc), ("vifp", rv)):
            ps, pk = F.TID2013_PAPER_SROCC[key][-1], F.TID2013_PAPER_KROCC[key][-1]
            v4 = np.round(r["values"], 4)
            s4, k4 = IQ.rank_spearman(r["mos"], v4), IQ.rank_kendall_b(r["mos"], v4)
            r["srocc_r4"], r["krocc_r4"] = s4, k4
            gate("%s Full: SROCC %.4f / KROCC %.4f vs 論文 %.4f / %.4f(丸めない値 ± %.3f)" % (key, r["srocc"], r["krocc"], ps, pk, CORR_TOL_RAW),
                 abs(r["srocc"] - ps) <= CORR_TOL_RAW and abs(r["krocc"] - pk) <= CORR_TOL_RAW)
            gate("%s Full: 作者と同じ 4 桁丸めで %.4f / %.4f(± %.4f —— 丸めが歪み 18 の同一画像を同順位にする)" % (key, s4, k4, CORR_TOL_R4),
                 abs(s4 - ps) <= CORR_TOL_R4 and abs(k4 - pk) <= CORR_TOL_R4)
            got = [_subset_corr(v4, ix, idx, IQ.TID2013_SUBSETS[nm]) for nm in F.TID2013_SUBSET_ORDER]
            ds = max(abs(g_[0] - p_) for g_, p_ in zip(got, F.TID2013_PAPER_SROCC[key]))
            dk = max(abs(g_[1] - p_) for g_, p_ in zip(got, F.TID2013_PAPER_KROCC[key]))
            gate("%s 7 部分集合(Noise…Full)の SROCC / KROCC が論文 Table 4/5 と ± %.4f(4 桁丸め)" % (key, CORR_TOL_R4), ds <= CORR_TOL_R4 and dk <= CORR_TOL_R4,
                 "max Δs %.4f Δk %.4f; S = %s" % (ds, dk, " ".join("%.4f" % g_[0] for g_ in got)))
        gs, gk, src = F.GMSD_TID2013_SECONDARY
        gate("GMSD Full: |SROCC| %.4f / |KROCC| %.4f vs 二次資料 %.4f / %.4f(%s、± %.3f)" % (abs(rg["srocc"]), abs(rg["krocc"]), gs, gk, src, GMSD_TOL),
             abs(abs(rg["srocc"]) - gs) <= GMSD_TOL and abs(abs(rg["krocc"]) - gk) <= GMSD_TOL)
    by = {k: IQ.tid2013_by_distortion(res[k]["values"], ix, idx) for k in ("fsim", "fsimc", "vifp", "gmsd")}
    res["by"] = by
    n_per = 125 if full else n_pairs // 24
    t18 = {k: by[k][17]["srocc"] for k in by}
    if full:
        gate("歪み種 24 × %d 組の順位相関表: 彩度変化 18 は輝度だけの FSIM / VIFP / GMSD が崩れ、彩度を持つ FSIMc だけ残る" % n_per,
             len(by["fsim"]) == 24 and all(rw["n"] == n_per for rw in by["fsim"]) and t18["fsimc"] > 0.8 > max(t18["fsim"], t18["vifp"], abs(t18["gmsd"])),
             "type 18: fsim %.2f fsimc %.2f vifp %.2f gmsd %.2f" % (t18["fsim"], t18["fsimc"], t18["vifp"], t18["gmsd"]))
    else:
        # 参照 I01 だけの 120 組では歪み 18 の 5 枚は Y′ が参照と 1 画素も変わらない(第 1 弾で PSNR = inf だった組)→ FSIM = VIF = 1 が 5 つ並び
        # 順位相関は定義されない(nan)。欠陥でなく「輝度しか見ない指標には同じ画像」という事実 —— nan を黙って 0 にせず、ここで名指しする。
        gate("歪み種 24 × %d 組(参照 I01 だけ): 彩度変化 18 の 5 枚は Y′ が参照と同一で FSIM / VIF の順位相関が定義されない(nan)、FSIMc は定義される" % n_per,
             len(by["fsim"]) == 24 and all(rw["n"] == n_per for rw in by["fsim"]) and np.isnan(t18["fsim"]) and np.isnan(t18["vifp"]) and np.isfinite(t18["fsimc"]),
             "type 18: fsim %s fsimc %.2f vifp %s(--full で 125 組 / 種の表になる)" % (t18["fsim"], t18["fsimc"], t18["vifp"]))
    print("  (%.1f s)" % (time.time() - t0))
    return res


def figures(res, full):
    print("== 図")
    if res is None:
        g = synth_image()
        rng = np.random.default_rng(1)
        sig = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 48.0])
        fs, gs, vs = [], [], []
        for s in sig:
            d = np.clip(g + rng.normal(0, s, g.shape), 0, 255)
            fs.append(F.fsim(g, d))
            gs.append(F.gmsd(g, d))
            vs.append(F.vifp(g, d))
        figs.save_plot("iqa_fsim_gmsd_vif_vs_noise", [("FSIM", sig, fs), ("VIF (pixel)", sig, vs), ("GMSD", sig, gs)], xlabel="noise σ (8-bit scale)", ylabel="index",
                       title="synthetic: FSIM / VIF fall, GMSD rises with noise", size=(640, 400),
                       caption="実データが無いときの代替図(FULLSEYE_TID2013_DATA を設定すると TID2013 の 6 枚になる)。FSIM と VIF は 1 から下がり、GMSD は 0 から上がる。")
        print("  figures:", figs.errors())
        return
    ix, idx = res["ix"], res["idx"]
    mos = ix["mos"][idx]
    n = len(idx)
    for key, xl, pubv in (("fsim", "FSIM (Y′ limited gray)", F.TID2013_PAPER_SROCC["fsim"][-1]), ("fsimc", "FSIMc (RGB → YIQ)", F.TID2013_PAPER_SROCC["fsimc"][-1]),
                          ("vifp", "VIF, pixel domain (Y′ limited)", F.TID2013_PAPER_SROCC["vifp"][-1]), ("gmsd", "GMSD (RGB → Y), lower is better", F.GMSD_TID2013_SECONDARY[0])):
        r = res[key]
        src = "secondary source" if key == "gmsd" else "paper Table 4"
        figs.save_plot("iqa_tid2013_mos_vs_%s" % key, [("%d pairs" % n, r["values"], mos)], xlabel=xl, ylabel="MOS", kinds=["scatter"], size=(640, 420),
                       title="TID2013: MOS vs %s, SROCC = %.4f (%s %.4f%s)" % (key.upper(), r["srocc"], src, pubv, "" if full else "; full set"),
                       caption="%s と 971 人の MOS(%s)。%s" % (key.upper(), "3,000 組" if full else "先頭 %d 組 = 参照 I01 の 24 種 × 5 段" % n,
                                                              {"fsim": "作者値 FSIM.txt と行ごと 4 桁一致(Y′ limited の灰色画像を渡したとき)。",
                                                               "fsimc": "作者値 FSIMc.txt と 4 桁一致(色画像 → YIQ full range)。TID2013 全体で 1 位の指標。",
                                                               "vifp": "作者値 VIFP.txt(画素領域版)と 4 桁一致。1 を超える点はコントラスト強調(歪み 17)。",
                                                               "gmsd": "作者値ファイルは無い(配布物 2013 年、GMSD 2014 年)。小さいほど良いので相関は負、二次資料の |ρ| 0.8044 と比べる。"}[key]))
    tt = np.arange(1, 25, dtype=float)
    by = res["by"]

    def _col(key, sign=1.0):
        v = np.array([rw["srocc"] for rw in by[key]], dtype=float) * sign
        return np.where(np.isfinite(v), v, 0.0)                # 定義されない種(同一画像で nan)は 0 の高さで描き、caption に書く
    n_nan = int(sum(np.isnan(rw["srocc"]) for k in by for rw in by[k]))
    figs.save_plot("iqa_tid2013_srocc_by_distortion",
                   [("FSIM", tt - 0.15, _col("fsim")), ("FSIMc", tt - 0.05, _col("fsimc")), ("VIFP", tt + 0.05, _col("vifp")), ("−GMSD", tt + 0.15, _col("gmsd", -1.0))],
                   xlabel="distortion type (1..24, readme TABLE I)", ylabel="SROCC vs MOS (%d pairs each)" % by["fsim"][0]["n"], kinds=["scatter"] * 4, size=(900, 420), ylim=(-0.3, 1.05),
                   title="TID2013: SROCC by distortion type (one marker per index; GMSD sign flipped)",
                   caption="歪み種ごとの順位相関。18 彩度変化は輝度しか見ない FSIM / VIFP / GMSD が崩れ、彩度を持つ FSIMc だけ残る。17 コントラスト変化・16 平均シフトは 4 指標とも弱い。"
                           + ("" if full else " 既定の 120 組では 1 種 5 組(参照 I01 だけ)なので粗い —— --full で 125 組 / 種。")
                           + (" 高さ 0 の棒 %d 本は順位相関が定義されない種(5 枚とも Y′ が参照と同一で指標が全部 1)。" % n_nan if n_nan else ""))
    pub = IQ.tid2013_published()
    rows = []
    for key, conv in (("fsimc", "RGB → YIQ full"), ("fsim", "Y′ limited gray"), ("vifp", "Y′ limited gray")):
        c = res["cmp"][key]
        rows.append([key.upper(), conv, "%.1e" % c["diff_max"], "author file, 4 digits", "%.4f / %.4f" % (res[key]["srocc"], res[key]["krocc"]),
                     "%.4f / %.4f" % (F.TID2013_PAPER_SROCC[key][-1], F.TID2013_PAPER_KROCC[key][-1]), "%.3f / %.3f" % pub[key]])
    gs, gk, src = F.GMSD_TID2013_SECONDARY
    rows.append(["GMSD (|ρ|)", "RGB → Y full", "no author file", "secondary source*", "%.4f / %.4f" % (abs(res["gmsd"]["srocc"]), abs(res["gmsd"]["krocc"])),
                 "%.4f / %.4f*" % (gs, gk), "—"])
    figs.save_table("iqa_tid2013_published_vs_reproduced", ["metric", "input convention", "max |row diff|", "truth grade", "SROCC / KROCC here%s" % ("" if full else " (%d)" % n),
                                                            "paper Table 4/5", "readme"], rows,
                    title="TID2013: truth grade, author-file agreement and rank correlations",
                    caption=("真値の等級を列にした: FSIM / FSIMc / VIFP は作者値ファイル(4 桁)と行ごとに比べられる。GMSD は作者値が無く、二次資料(* = %s)の |ρ| との照合だけ —— 1 段低い等級。"
                             " 順位相関の列は丸めない自前の値(作者と同じ 4 桁丸めをすると論文の 4 桁に乗る)。") % src)
    print("  figures:", figs.errors())


def main() -> int:
    t_all = time.time()
    full = "--full" in sys.argv
    n_pairs = int(sys.argv[sys.argv.index("--pairs") + 1]) if "--pairs" in sys.argv else 120
    synthetic_part()
    root = IQ.tid2013_root()
    res = None
    if root is None:
        print("== 2. 実データ: [skip] FULLSEYE_TID2013_DATA が無い(画像・MOS・作者値は repo に入れない —— 配布条件は教育・研究目的のみ)")
    else:
        res = real_part(root, n_pairs, full)
    if figs.enabled():
        figures(res, full)
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
