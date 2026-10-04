# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開の正解で画質指標を門にする —— TID2013 の 3,000 組と 971 人の MOS で Fullseye の PSNR / SSIM を検算する(2026-10-04)。

TID2013(Ponomarenko ほか 2015、https://www.ponomarenko.info/tid2013.htm)は 25 枚の参照 × 24 種の歪み × 5 段 = 3,000 枚に、
971 人の対比較から得た MOS を付けた公開データ。配布物には作者が計算した 14 指標の値(psnr.txt / ssim.txt / fsim.txt …)と、
MOS との順位相関表(PSNR 0.640 / 0.470、SSIM 0.637 / 0.464、FSIMc 0.851 / 0.667 …)が同梱されている。この PoC はそれを 3 段の門にする:

  * 門 A(実装の正しさ): Fullseye の ``imgmetrics.psnr`` を RGB 3 チャネルで → 作者の psnrc.txt と、作者の輝度規約 Y′(BT.601 limited range、
    16〜235 の整数、:func:`iqatid.luma_limited_u8`)で → psnr.txt と、``imgmetrics.ssim``(既定: 11×11 ガウス σ1.5、縁を落とす、ダウンサンプル無し)
    を Y′ で → ssim.txt と、**3,000 組の行ごと**に比べる(PSNR ≤ 0.0005 dB、SSIM ≤ 0.0001 = 作者値の 4 桁の丸め幅)。
  * 門 B(公表値の再現): 自前の値と MOS の Spearman(平均順位)/ Kendall τ_b が公表の 0.640 / 0.470(PSNR)、0.637 / 0.464(SSIM)に ≤ 0.001。
    作者値 14 本からも同じ定義で公表表を再現(≤ 0.001)—— τ_a だと 4 本外れるので、公表の Kendall は τ_b。
  * 合成の門(常に走る): 順位相関の閉形式(単調 1・反転 −1・同順位ありの手計算値・第 2 実装 graphinv との一致)、Y′ の端点 16 / 235、
    PSNR の +1 LSB = 48.13 dB、SSIM の恒等 = 1、公表表 14 本。

図(FULLSEYE_FIGURE_DIR があるとき): MOS vs PSNR / SSIM の散布(3,000 点、題に SROCC)、歪み種 24 ごとの SROCC の棒、作者値との差の
ヒストグラム、14 指標の公表表 + 再現値の表、1 組の参照・歪み・SSIM map のグリッド。

正直に: Fullseye の SSIM が作者値に 4 桁一致するのは、作者と同じ原実装(Wang 2004 の ssim_index.m)の規約を踏んでいるからで、SSIM の
性能の話ではない(SROCC 0.637 は 14 本中 10 位、FSIMc 0.851 が 1 位)。輝度が limited range の整数だという規約はページにも readme にも無く、
実測で特定した(full range だと PSNR −1.32 dB、SSIM 最大 0.05 ずれて門にならない)。歪み 18「彩度変化」の 125 組のうち 106 組は Y′ が参照と
1 画素も変わらず、輝度だけの PSNR は inf・SSIM は 1.0 になる —— 作者は psnr.txt にその行を 100000.0 と書いている(inf を捨てずに作者の印に
写して行ごと比べ、順位相関では最大の順位として扱う。最初の版はここで fail-closed して止まった —— 「完全一致は無い」という思い込みが
門に化けていた)。作者の印は 111 行で、こちらの inf は 106 行。残り 5 行(参照 I12 の彩度変化 5 段)は輝度が **ちょうど k.5** に落ちる
28 画素の丸めの向きが作者の算術と食い違い、1 LSB 差で 86.6 dB になる(半偶数・半切り上げ・float32・整数式のどれでも 111 にならない)。
これは「同じ式でも算術の順序で答えが変わる」実例で、行ごとの門は印の行を**別に数えて**報告する(黙って除外しない)。同じ 28 画素のせいで
参照 I12 の全 120 組は PSNR が最大 0.0006 dB ずれる(作者値の 4 桁丸め幅 0.00005 の外)ので、I12 の行は ≤ 0.001 dB の別の門にし、残り 2,769 組は
≤ 0.0005 dB(実測 0.00017 dB —— 4 桁丸めの幅 0.00005 の 3 倍で、作者側の算術(float 精度か MSE の丸め)の差と推測。SSIM は 0.00005 で丸め幅そのもの)。FSIM / FSIMc / VIF / PSNR-HVS 系は Fullseye に無く、
表には公表値だけを載せる。MS-SSIM は作者値(Metrix MUX)と 0.004 までしか合わず門にしない。画像と MOS は **repo に入れない**(配布条件は
教育・研究目的のみ、改変版の再配布は著者許可)。実データの門は FULLSEYE_TID2013_DATA があるときだけで、CI では合成の門だけ走る。
3,000 組の所要は約 2 分(PSNR 2 回 + SSIM 1 回 + BMP 読み、Windows・1 コア)。
Run: set FULLSEYE_TID2013_DATA=C:\\dev\\data\\tid2013\\tid2013 & py -3.11 examples/poc_iqa_tid2013.py
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import iqatid as IQ  # noqa: E402
import imgmetrics as IM  # noqa: E402
import examplefig as figs  # noqa: E402

_GATES = []
PSNR_TOL_DB = 0.0005
SSIM_TOL = 0.0001
CORR_TOL = 0.001
AUTHOR_INF = 100000.0       # 作者が psnr.txt に書く「完全一致」の印(歪み 18 彩度変化で Y′ が変わらない 106 組)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def hist_image(diffs, nbins=41, w=560, h=300, title=""):
    """差のヒストグラムを Fullseye の棒グラフで描く(値は 0 中心の対称な範囲)。"""
    d = np.asarray(diffs, float)
    lim = max(float(np.abs(d).max()), 1e-12)
    edges = np.linspace(-lim, lim, nbins + 1)
    cnt, _ = np.histogram(d, bins=edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return figs.render_plot([("count", centers, cnt.astype(float))], xlabel="Fullseye − author", ylabel="pairs", title=title,
                            size=(w, h), kinds=["bar"])


def main() -> int:
    t_all = time.time()
    print("== 1. 合成の門(順位相関・輝度規約・指標の恒等)")
    x = np.arange(60, dtype=float)
    gate("Spearman: 単調増加 1・反転 −1", abs(IQ.rank_spearman(x, np.exp(x / 7)) - 1) < 1e-12 and abs(IQ.rank_spearman(x, -x ** 3) + 1) < 1e-12)
    gate("Kendall τ_b: 単調増加 1・反転 −1", abs(IQ.rank_kendall_b(x, np.exp(x / 7)) - 1) < 1e-12 and abs(IQ.rank_kendall_b(x, -x ** 3) + 1) < 1e-12)
    rho = IQ.rank_spearman([1, 2, 3, 4, 5], [1, 2, 2, 4, 3])
    tau = IQ.rank_kendall_b([1, 2, 3, 4, 5], [1, 2, 2, 4, 3])
    gate("同順位ありの手計算値: ρ = 8.5/√95、τ_b = 7/√90", abs(rho - 8.5 / math.sqrt(95)) < 1e-12 and abs(tau - 7 / math.sqrt(90)) < 1e-12,
         "ρ = %.5f, τ_b = %.5f" % (rho, tau))
    try:
        import graphinv as GI
        rng = np.random.default_rng(7)
        xa = rng.integers(0, 40, 400).astype(float)
        ya = np.round((xa + rng.normal(0, 10, 400)) / 3) * 3
        gate("第 2 実装(graphinv._spearman)と一致 1e-12", abs(IQ.rank_spearman(xa, ya) - GI._spearman(xa, ya)) < 1e-12 and np.allclose(IQ.rank_data(xa), GI._rank(xa)))
    except ImportError:
        gate("第 2 実装(graphinv)", False, "import failed")
    yb = IQ.luma_limited_u8(np.zeros((2, 2, 3), np.uint8))[0, 0]
    yw = IQ.luma_limited_u8(np.full((2, 2, 3), 255, np.uint8))[0, 0]
    gate("limited-range Y′: 黒 16・白 235、full との差 1.321 dB", int(yb) == 16 and int(yw) == 235 and abs(20 * math.log10(255 / 219) - 1.3213) < 1e-3)
    gate("PSNR の +1 LSB = 20 log10(255) = 48.13 dB", abs(IM.psnr(np.zeros((8, 8), np.uint8), np.ones((8, 8), np.uint8)) - 20 * math.log10(255)) < 1e-9)
    img = np.random.default_rng(0).integers(0, 256, (48, 64), dtype=np.uint8)
    gate("SSIM の恒等 = 1、PSNR の恒等 = inf", abs(IM.ssim(img, img) - 1) < 1e-12 and math.isinf(IM.psnr(img, img)))
    pub = IQ.tid2013_published()
    gate("公表表 14 本、PSNR 0.640/0.470・SSIM 0.637/0.464", len(pub) == 14 and pub["psnr"] == (0.640, 0.470) and pub["ssim"] == (0.637, 0.464))

    root = IQ.tid2013_root()
    real = None
    if root is None:
        print("== 2. 実データ: FULLSEYE_TID2013_DATA が無いので skip(画像と MOS は repo に無い —— 配布条件は教育・研究目的のみ)")
    else:
        print("== 2. 実データ(%s)" % root)
        t0 = time.time()
        ix = IQ.tid2013_index(root)
        gate("台帳 3,000 行・名前集合がディスクと一致・参照 25 枚", len(ix["names"]) == 3000 and len(ix["ref_files"]) == 25)
        author = {k: IQ.tid2013_metric_values(root, k) for k in pub}
        # 門 B′: 作者値 14 本から公表表を再現(定義の確認: 平均順位・τ_b)
        worst = 0.0
        repro = {}
        for k in pub:
            c = IQ.tid2013_compare(author[k], author[k], ix["mos"], published=pub[k])
            repro[k] = (c["srocc"], c["krocc"])
            worst = max(worst, abs(c["d_srocc_published"]), abs(c["d_krocc_published"]))
        gate("作者値 14 本 → 公表の SROCC / τ_b を ≤ %.3f で再現(最大差 %.5f)" % (CORR_TOL, worst), worst <= CORR_TOL, "(%.1f s)" % (time.time() - t0))
        # 門 A: Fullseye の値を 3,000 組に
        t1 = time.time()
        r_c = IQ.tid2013_evaluate(root, IM.psnr, luma="rgb", index=ix)
        r_p = IQ.tid2013_evaluate(root, IM.psnr, luma="limited_u8", index=ix)
        r_s = IQ.tid2013_evaluate(root, IM.ssim, luma="limited_u8", index=ix)
        t_eval = time.time() - t1
        print("  3,000 組 × (PSNR RGB + PSNR Y′ + SSIM Y′) = %.1f s(PSNR %.1f + %.1f, SSIM %.1f)" % (t_eval, r_c["seconds"], r_p["seconds"], r_s["seconds"]))
        c_c = IQ.tid2013_compare(r_c["values"], author["psnrc"], ix["mos"], published=pub["psnrc"])
        c_p = IQ.tid2013_compare(r_p["values"], author["psnr"], ix["mos"], published=pub["psnr"], inf_as=AUTHOR_INF)
        c_s = IQ.tid2013_compare(r_s["values"], author["ssim"], ix["mos"], published=pub["ssim"])
        gate("PSNR(RGB) = psnrc.txt 行ごと ≤ %.4f dB、inf なし" % PSNR_TOL_DB, c_c["diff_max"] <= PSNR_TOL_DB and c_c["n_inf"] == 0, "max %.5f dB at %s" % (c_c["diff_max"], ix["names"][c_c["argmax"]]))
        mm = c_p["sentinel_mismatch_values"]
        gate("PSNR(Y′): 自分の inf 106 組は全部 作者の印 100000.0 の行(彩度変化 18)、自分が inf で作者が数値の行は 0",
             r_p["n_inf"] == 106 and len(c_p["inf_not_sentinel_idx"]) == 0 and c_p["n_sentinel_author"] == 111,
             "inf %d, author sentinel %d" % (r_p["n_inf"], c_p["n_sentinel_author"]))
        gate("PSNR(Y′): 作者が印・自分は有限の行は 5(参照 I12、28 画素がちょうど k.5)で、どれも ≥ 80 dB(1 LSB の丸め違い)",
             len(mm) == 5 and all(ix["names"][i].lower().startswith("i12_18") for i in c_p["sentinel_mismatch_idx"]) and min(mm) >= 80.0,
             "%s" % [(ix["names"][i], round(v, 2)) for i, v in zip(c_p["sentinel_mismatch_idx"], mm)])
        # 参照 I12 は輝度がちょうど k.5 の画素が 28 あり、作者の算術と 1 LSB 食い違う → I12 の全行で MSE がわずかに違う(最大 0.0006 dB)。
        # 黙って除外せず、参照ごとに分けて門にする。
        v_fin = np.where(np.isinf(r_p["values"]), AUTHOR_INF, r_p["values"])
        d_row = np.abs(v_fin - author["psnr"])
        not_sent = author["psnr"] != AUTHOR_INF
        is12 = ix["ref"] == 12
        d_other = d_row[not_sent & ~is12].max()
        d_12 = d_row[not_sent & is12].max()
        gate("PSNR(Y′ limited) = psnr.txt 行ごと ≤ %.4f dB(印の行と参照 I12 を除く %d 組)" % (PSNR_TOL_DB, int((not_sent & ~is12).sum())),
             d_other <= PSNR_TOL_DB, "max %.5f dB" % d_other)
        gate("PSNR(Y′) 参照 I12 の %d 組: ≤ 0.001 dB(28 画素の k.5 丸め違いぶん)" % int((not_sent & is12).sum()), d_12 <= 0.001,
             "max %.5f dB at %s" % (d_12, ix["names"][int(np.argmax(np.where(not_sent & is12, d_row, -1)))]))
        gate("SSIM(Y′ limited) = ssim.txt 行ごと ≤ %.4f" % SSIM_TOL, c_s["diff_max"] <= SSIM_TOL, "max %.6f at %s, mean %+.6f" % (c_s["diff_max"], ix["names"][c_s["argmax"]], c_s["diff_mean"]))
        gate("PSNR: SROCC %.4f / τ_b %.4f vs 公表 0.640 / 0.470(≤ %.3f)" % (c_p["srocc"], c_p["krocc"], CORR_TOL),
             abs(c_p["d_srocc_published"]) <= CORR_TOL and abs(c_p["d_krocc_published"]) <= CORR_TOL)
        gate("SSIM: SROCC %.4f / τ_b %.4f vs 公表 0.637 / 0.464(≤ %.3f)" % (c_s["srocc"], c_s["krocc"], CORR_TOL),
             abs(c_s["d_srocc_published"]) <= CORR_TOL and abs(c_s["d_krocc_published"]) <= CORR_TOL)
        gate("PSNRc: SROCC %.4f / τ_b %.4f vs 公表 0.687 / 0.496(≤ %.3f)" % (c_c["srocc"], c_c["krocc"], CORR_TOL),
             abs(c_c["d_srocc_published"]) <= CORR_TOL and abs(c_c["d_krocc_published"]) <= CORR_TOL)
        # full range で測ると門が落ちることを示す(規約の違いが答えを変える)
        def y_full(rgb):
            return np.round(0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.uint8)
        r_f = IQ.tid2013_evaluate(root, lambda a, b: IM.psnr(y_full(a), y_full(b)), subset=50, luma="rgb", index=ix)
        d_f = r_f["values"] - author["psnr"][:50]
        gate("反例: full-range Y で測った PSNR は作者値から −1.3 dB(規約が答えを変える)", d_f.max() < -1.2 and d_f.min() > -1.4, "mean %+.3f dB" % d_f.mean())
        by_p = IQ.tid2013_by_distortion(r_p["values"], ix)
        by_s = IQ.tid2013_by_distortion(r_s["values"], ix)
        gate("歪み種 24 × 125 組", len(by_p) == 24 and all(rw["n"] == 125 for rw in by_p))
        print("  (%.1f s)" % (time.time() - t0))
        real = {"ix": ix, "author": author, "repro": repro, "r_c": r_c, "r_p": r_p, "r_s": r_s, "c_c": c_c, "c_p": c_p, "c_s": c_s, "by_p": by_p, "by_s": by_s}

    if figs.enabled():
        print("== 図")
        if real:
            ix, r_p, r_s = real["ix"], real["r_p"], real["r_s"]
            fin_p = np.isfinite(r_p["values"])
            figs.save_plot("tid2013_mos_vs_psnr", [("%d finite pairs" % int(fin_p.sum()), r_p["values"][fin_p], ix["mos"][fin_p])], xlabel="PSNR (Y′ limited) [dB]", ylabel="MOS",
                           title="TID2013: MOS vs PSNR, SROCC = %.3f (published 0.640)" % r_p["srocc"], kinds=["scatter"], size=(640, 420),
                           caption="971 人の MOS と Fullseye の PSNR(作者の輝度規約 Y′、psnr.txt と 4 桁一致)。順位相関は公表値どおり低い —— PSNR は歪み種が混ざると主観に合わない。"
                                   " 彩度変化で Y′ が変わらない %d 組(PSNR = inf、MOS 3.4〜6.0)は図に載らない(順位相関には最大の順位で入れてある)。" % int((~fin_p).sum()))
            figs.save_plot("tid2013_mos_vs_ssim", [("3,000 組", r_s["values"], ix["mos"])], xlabel="SSIM (Y′ limited)", ylabel="MOS",
                           title="TID2013: MOS vs SSIM, SROCC = %.3f (published 0.637)" % r_s["srocc"], kinds=["scatter"], size=(640, 420),
                           caption="同じ 3,000 組と Fullseye の SSIM(Wang 2004 の既定、ssim.txt と 4 桁一致)。SSIM が高いのに MOS が低い塊(右下)は平均シフト・コントラスト変化など SSIM が鈍い歪み。")
            tt = np.arange(1, 25, dtype=float)
            figs.save_plot("tid2013_srocc_by_distortion", [("PSNR", tt - 0.2, [rw["srocc"] for rw in real["by_p"]]), ("SSIM", tt + 0.2, [rw["srocc"] for rw in real["by_s"]])],
                           xlabel="distortion type (1..24, readme TABLE I)", ylabel="SROCC vs MOS (125 pairs each)", title="TID2013: SROCC by distortion type",
                           kinds=["bar", "bar"], size=(760, 380), ylim=(-0.2, 1.0),
                           caption="歪み種ごとの順位相関(各 25 参照 × 5 段)。単一の歪み種の中では PSNR も SSIM も 0.8〜0.95 と高く、全体の 0.64 は歪み種をまたぐ比較で崩れる。"
                                   " 低い種: %s。" % ", ".join("%d %s (PSNR %.2f / SSIM %.2f)" % (rw["type"], rw["name"][:28], rw["srocc"], rs["srocc"])
                                                           for rw, rs in zip(real["by_p"], real["by_s"]) if min(rw["srocc"], rs["srocc"]) < 0.5))
            fin = (real["author"]["psnr"] != AUTHOR_INF) & (ix["ref"] != 12)
            hp = hist_image(real["r_p"]["values"][fin] - real["author"]["psnr"][fin], title="PSNR: Fullseye − psnr.txt [dB] (%d rows, ref I12 excluded)" % int(fin.sum()))
            hs = hist_image(real["r_s"]["values"] - real["author"]["ssim"], title="SSIM: Fullseye − ssim.txt (3000 rows)")
            figs.save_grid("tid2013_author_diff_hist", [hp, hs], ncols=2,
                           captions=["PSNR(Y′): max |diff| %.5f dB over %d rows" % (float(np.abs(real["r_p"]["values"][fin] - real["author"]["psnr"][fin]).max()), int(fin.sum())),
                                     "SSIM(Y′): max |diff| %.6f over 3000 rows" % real["c_s"]["diff_max"]],
                           caption="作者値との行ごとの差。SSIM は作者値の 4 桁丸めの幅(±0.00005)に収まり、PSNR は ±0.0002 dB(丸め幅の 3 倍、作者側の算術の差と推測)"
                                   " —— 同じ規約を踏んだ証拠で、指標の良さの証拠ではない。 PSNR の図は、作者が完全一致の印(100000.0)を書いた 111 行(こちらも 106 行は inf、5 行は 86.6 dB)と、輝度がちょうど k.5 の 28 画素で"
                                   " 作者と 1 LSB 食い違う参照 I12 の行(最大 0.0006 dB、別の門)を除く。")
            rows = []
            for k, (ps, pk) in sorted(pub.items(), key=lambda kv: -kv[1][0]):
                rs_, rk_ = real["repro"][k]
                mine = {"psnrc": real["c_c"], "psnr": real["c_p"], "ssim": real["c_s"]}.get(k)
                rows.append([k, "%.3f" % ps, "%.4f" % rs_, "%.3f" % pk, "%.4f" % rk_,
                             ("%.4f / %.4f" % (mine["srocc"], mine["krocc"])) if mine else "— (not in Fullseye)"])
            figs.save_table("tid2013_published_vs_reproduced", ["metric", "SROCC pub", "SROCC (author values)", "KROCC pub", "τ_b (author values)", "Fullseye SROCC / τ_b"], rows,
                            title="TID2013: published rank correlations vs reproduction",
                            caption="公表表(ページ / readme TABLE III・IV)と、同梱の作者値 + mos.txt から平均順位・τ_b で再現した値、Fullseye 実装がある 3 本の自前値。FSIM / VIF 等は未実装で公表値のみ。")
            # 1 組: 参照・歪み・SSIM map
            k0 = ix["names"].index(next(n for n in ix["names"] if n.lower() == "i03_08_3.bmp"))
            from PIL import Image
            ref = np.asarray(Image.open(ix["ref_files"][2]).convert("RGB"))
            dis = np.asarray(Image.open(ix["dist_files"][k0]).convert("RGB"))
            smap = IM.ssim_map(IQ.luma_limited_u8(ref), IQ.luma_limited_u8(dis))
            figs.save_grid("tid2013_pair_ssim_map", [ref, dis, smap], ncols=3, gray=[False, False, False], vrange=[None, None, (0.0, 1.0)],
                           captions=["I03 reference", "i03_08_3 (Gaussian blur L3), MOS %.2f" % ix["mos"][k0],
                                     "SSIM map, mean %.4f (ssim.txt %.4f)" % (float(smap.mean()), real["author"]["ssim"][k0])],
                           caption="1 組の例。SSIM map は縁(窓半径 5 画素)を落とした 374 × 502。暗い所ほど構造が壊れている。")
        else:
            # 合成だけのとき: 順位相関の挙動を 1 枚
            rng = np.random.default_rng(1)
            xs = rng.normal(size=300)
            figs.save_plot("tid2013_rank_sanity", [("noise σ=0.5", xs, xs + rng.normal(0, 0.5, 300))], xlabel="x", ylabel="y", kinds=["scatter"],
                           title="rank corr sanity: ρ = %.3f" % IQ.rank_spearman(xs, xs + 0.5 * rng.normal(size=300)),
                           caption="実データが無いときの代替図(FULLSEYE_TID2013_DATA を設定すると TID2013 の図になる)。")
        print("  figures:", figs.errors())

    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if n_ng:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
