# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""良品を何枚撮れば「いつもと違う」が言えるか —— 良品統計の変動モデルを、誤検出率を宣言して使う。

外観検査の古典(ViEW の ALCON2015 型、異常検知 29 件の多く)は「良品を何枚も撮り、画素ごとに
いつもの値といつものばらつきを覚え、外れた画素を欠陥とする」。けれど現場の実装は閾値 k を
**手で**決めることが多く、「この k で 1 枚あたり何画素が誤検出になるか」を言えない。この PoC は
``varmodel_*``(5 op)で k を**宣言した誤検出率から**決め、その約束が守られるか・どこで破れるかを、
合成の閉形式と公開実データの両方で数える。評価は方法に依存しない ``anomeval`` の物差し
(画素 AUROC・AUPRO)で、RPCA(``dc_rpca_sparse``)とゴールデン比較(``compare_to_golden``)とも比べる。

多段(各段に op の外の真値か実データの門):

1. **閉形式の誤検出率**(合成): 画素ごとに独立な正規の良品で、宣言 far と、当てはめに使わなかった
   良品で数えた誤検出率を突き合わせる。std(t の予測区間)・pooled・moderated(経験ベイズ)・
   mad(ピボット)のどれも二項の 4σ の帯に入る。雑音が画素ごとに違うのに pooled を使うと帯から外れる。
2. **良品が少ないとき**(合成): n = 5 で std の k は t_4 の裾で 9.4(far 1e-3)。縮小した分散
   (moderated、推定した事前分布の自由度 5.8、真値 6)は k を 5.1 まで下げ、同じ誤検出率で
   5σ の傷の検出率を 0.13 から 0.52 に上げる。
3. **位置合わせの探針**(合成): 1〜2 px ずれた良品群は ``align="check"`` が**拒否**する。許容を
   緩めて無理に通すと、縁の上の帯が 2 倍以上に太り、縁の上の傷を見逃す。``align="translate"``
   (Fourier シフト)で合わせると元に戻る。
4. **汚れた良品群の探針**(合成): 20 枚の「良品」のうち 3 枚に同じ場所の傷。std はそこの帯が太って
   本物の傷を見逃し、mad(中央値と MAD)は見つける。
5. **公開実データ**(VisA pcb1、CC BY 4.0): 良品 5 / 20 / 80 枚で学び、試験 200 枚(良品 100・不良 100)
   で画素 AUROC・AUPRO・良品の持ち出しで数えた誤検出率。RPCA・ゴールデン比較と同じ物差しで比べる。
   位置合わせ前と後(ずれが帯を太らせる)も実データで見る。宣言の誤検出率は実画像では守られない
   (残る位置ずれ・圧縮・照明) —— それを ``varmodel_calibrate``(持ち出した良品で k を測り直す)で直す。
6. **向かない題材の探針**(DAGM 2007 Class1、CC BY 4.0): 確率的なテクスチャは画像ごとに模様が違い、
   平均像に構造が無い。位置合わせは「測れない」と報告され、画素ごとの帯はテクスチャ全体のばらつきに
   退化し、検出は偶然並み。この題材は周期・テクスチャの op の仕事で、変動モデルの仕事ではない。

予想(2026-10-18、着手前): ★「良品を 80 枚使えば、宣言した誤検出率がそのまま実画像でも守られる」。
**外れた**: VisA pcb1 では 80 枚でも宣言 1e-3 に対し試験の良品で 3.8 %。学習に使わなかった良品で k を
測り直す較正(``varmodel_calibrate``)で 2.4 % までしか下がらない —— 学習用と試験用の良品の間に、並進では
取れない撮影の違いがある(z 図の縁に縞が残る)。閉形式は「画素ごとに独立な正規」という模型の約束であって、
実画像の約束ではない。数は正直に出す: 画素 AUROC はゴールデン比較(0.826)が変動モデル(0.808)より上、
欠陥を 1 つずつ数える AUPRO は変動モデル 0.678 対ゴールデン比較 0.519 で逆になる。

実データ(repo には同梱しない。環境変数 ``FULLSEYE_VISA_DATA`` に VisA を展開した dir
(``split_csv/1cls.csv`` と ``pcb1/`` がある所)を渡す。無ければ合成の章だけを走らせ、実データの章は
記録値を印字する。CI は合成のみ):

  Zou, Y., Jeong, J., Pemula, L., Zhang, D., Dabeer, O. (2022). SPot-the-Difference Self-Supervised
  Pre-training for Anomaly Detection and Segmentation. ECCV 2022. データセット VisA:
  https://github.com/amazon-science/spot-diff (S3: amazon-visual-anomaly/VisA_20220922.tar)、
  "The data is released under the CC BY 4.0 license."(同梱の LICENSE-DATASET も CC BY 4.0 の本文)。
  改変: 灰色化と 4×4 の平均で縮小。ダウンロード物は信頼しない入力として扱い、画像と CSV を読むだけ。

  Wieler, M., Hahn, T., Hamprecht, F. A. Weakly Supervised Learning for Industrial Optical Inspection
  (DAGM 2007). Zenodo 12750201、CC BY 4.0。環境変数 ``FULLSEYE_DAGM_DATA`` に ``Class1/`` を展開した
  dir の親を渡す。改変: 4×4 の平均で縮小。

Fullseye 寄与: 「良品統計の変動モデル」を誤検出率の宣言つきの op 族にした(位置合わせの確認と拒否、
少数の良品の縮小、頑健版、領域ごとの説明、持ち出しの較正)。評価の物差し ``anomeval`` は方法に依存しない。
"""
from __future__ import annotations

import csv
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402  公開経路 fs.ledger.<名前>

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DATA = os.environ.get("FULLSEYE_VISA_DATA", "").strip()
DAGM = os.environ.get("FULLSEYE_DAGM_DATA", "").strip()        # Class1 を展開した dir の親
VISA_CLASS = "pcb1"
VISA_SOURCE = ("VisA (Zou et al., ECCV 2022), github.com/amazon-science/spot-diff, CC BY 4.0; "
               "gray + 4x4 mean downsampling")
DOWN = 4
FAR = 1e-3

#: 実データの章の記録値(2026-10-18、FULLSEYE_VISA_DATA ありで実行)。CI ではこれを印字する。
RECORDED = {"lines": [
    '方法(良品 n 枚)                       k  AUROC  AUPRO   画像AU      誤検出率     領域検出',
    'std n=5                       9.43  0.768  0.645  0.799    0.0237     0.59',
    'std+cal n=5                  26.79  0.768  0.645  0.799    0.0041     0.02',
    'moderated n=5                 6.39  0.793  0.663  0.769    0.0313     0.69',
    'moderated+cal n=5            15.93  0.793  0.663  0.769    0.0074     0.29',
    'mad n=5                      47.61  0.758  0.578  0.761    0.0064     0.01',
    'mad+cal n=5                  74.75  0.758  0.578  0.761    0.0035     0.01',
    'std n=20                      3.98  0.802  0.675  0.803    0.0331     0.72',
    'std+cal n=20                  5.19  0.802  0.675  0.803    0.0235     0.68',
    'moderated n=20                3.91  0.808  0.678  0.810    0.0338     0.74',
    'moderated+cal n=20            5.12  0.808  0.678  0.810    0.0238     0.68',
    'mad n=20                      5.26  0.787  0.665  0.780    0.0349     0.73',
    'mad+cal n=20                 15.13  0.787  0.665  0.780    0.0074     0.29',
    'std n=80                      3.44  0.807  0.682  0.785    0.0383     0.76',
    'std+cal n=80                  4.86  0.807  0.682  0.785    0.0242     0.69',
    'moderated n=80                3.44  0.808  0.683  0.786    0.0385     0.76',
    'moderated+cal n=80            4.87  0.808  0.683  0.786    0.0241     0.69',
    'mad n=80                      3.68  0.804  0.667  0.806    0.0471     0.80',
    'mad+cal n=80                 13.96  0.804  0.667  0.806    0.0075     0.30',
    'moderated, 合わせない n=20            -  0.705  0.460  0.727    0.0158     0.37',
    'ゴールデン比較(20 枚の平均) n=20            -  0.826  0.519  0.757    0.0010     0.00',
    'RPCA(dc_rpca_sparse) n=20        -  0.566  0.607  0.500    0.0000     0.00',
    '無理に通した帯の幅 = 縁(勾配の上位 20 %)で合わせた帯の 1.55 倍',
]}
#: DAGM 2007 の章の記録値(同日、FULLSEYE_DAGM_DATA ありで実行)。
RECORDED_DAGM = '位置合わせ observable=False、帯の幅 = 画像全体のばらつきの 0.93 倍、画素 AUROC 0.465、画像 AUROC 0.566(試験 300 枚・不良 34、楕円の弱い注釈)'

#: 上の実行記録から図に使う AUPRO だけを機械可読にしたもの。VisA 本体が無い環境でも、
#: 公開済みの実行結果のグラフを描画倍率どおりに再生成するために使う。
RECORDED_AUPRO = {
    "std": [0.645, 0.675, 0.682],
    "moderated": [0.663, 0.678, 0.683],
    "mad": [0.578, 0.665, 0.667],
    "合わせない帯(n=20)": [0.460, 0.460],
    "ゴールデン比較(n=20)": [0.519, 0.519],
    "RPCA(1 枚ずつ)": [0.607, 0.607],
}

ok_all = []


def check(name, cond, detail=""):
    ok_all.append(bool(cond))
    print("   [%s] %s%s" % ("OK" if cond else "NG", name, (" —— " + detail) if detail else ""))
    return bool(cond)


# --------------------------------------------------------------------------- #
# 1. 閉形式の誤検出率                                                           #
# --------------------------------------------------------------------------- #
def _sigma(kind, rng, shape):
    if kind == "invchi2":                         # σ² ~ d0 s0²/χ²_{d0}, d0 = 6, s0 = 0.1
        return np.sqrt(6.0 / rng.chisquare(6.0, shape)) * 0.1
    if kind == "const":
        return np.full(shape, 0.1)
    return rng.uniform(0.05, 0.2, shape)


def stage1_far():
    print("\n1) 閉形式の誤検出率(合成: 画素ごとに独立な正規の良品)")
    side = 96 if REDUCED else 160
    reps = 4 if REDUCED else 6
    cases = [("std", 5, 1e-2, "uniform"), ("std", 20, 1e-3, "uniform"),
             ("pooled", 5, 1e-2, "const"), ("moderated", 5, 1e-2, "invchi2"),
             ("moderated", 20, 1e-3, "invchi2"), ("mad", 20, 1e-2, "uniform"),
             ("pooled", 5, 1e-2, "uniform")]                      # 最後 = 仮定違反の探針
    rows = []
    for sp, n, far, kind in cases:
        tot = nv = 0
        rel = 0.0
        k = 0.0
        for rep in range(reps):
            rng = np.random.default_rng([18, rep, n, len(sp), len(kind)])
            mu = rng.uniform(0, 1, (side, side))
            sig = _sigma(kind, rng, (side, side))
            m = fs.ledger.varmodel_fit(mu + sig * rng.standard_normal((n, side, side)), spread=sp, far=far)
            r = fs.ledger.varmodel_score(mu + sig * rng.standard_normal((side, side)), m)
            tot += r["n_exceed"]
            nv += r["n_valid"]
            rel = m["mc_far_rel_se"]
            k = m["k"]
        p = tot / nv
        band = 4.0 * math.sqrt(far * (1 - far) / nv + (rel * far) ** 2)
        rows.append((sp, n, far, kind, k, p, band))
        print("   %-9s n=%-3d 雑音=%-8s 宣言 %.0e  k=%.2f  実測 %.5f(帯 ±%.5f, %d 画素)"
              % (sp, n, kind, far, k, p, band, nv))
    for sp, n, far, kind, k, p, band in rows[:-1]:
        check("%s n=%d: 実測が宣言の 4σ 帯に入る" % (sp, n), abs(p - far) < band,
              "%.5f vs %.0e ± %.5f" % (p, far, band))
    sp, n, far, kind, k, p, band = rows[-1]
    check("探針: 画素ごとに雑音が違うのに pooled → 宣言を守れない", p > far + 3 * band,
          "%.4f > %.4f" % (p, far + 3 * band))
    return rows


# --------------------------------------------------------------------------- #
# 2. 良品が少ないとき                                                           #
# --------------------------------------------------------------------------- #
def stage2_few():
    print("\n2) 良品が少ないとき(合成: 画素の分散が逆カイ二乗の事前分布、5σ の傷)")
    side = 96 if REDUCED else 128
    ns = (3, 5, 10, 20) if REDUCED else (3, 5, 10, 20, 40, 80)
    out = {}
    for n in ns:
        rng = np.random.default_rng([28, n])
        mu = rng.uniform(0, 1, (side, side))
        sig = _sigma("invchi2", rng, (side, side))
        st = mu + sig * rng.standard_normal((n, side, side))
        test = mu + sig * rng.standard_normal((side, side)) + 5.0 * sig     # 全画素に 5σ の傷
        row = {}
        for sp in ("std", "moderated"):
            m = fs.ledger.varmodel_fit(st, spread=sp, far=FAR)
            r = fs.ledger.varmodel_score(test, m)
            row[sp] = (m["k"], r["n_exceed"] / r["n_valid"], m["d0"])
        out[n] = row
        print("   n=%-3d std: k=%.2f 検出率 %.3f | moderated: k=%.2f 検出率 %.3f(推定 d0 = %.1f、真値 6)"
              % (n, row["std"][0], row["std"][1], row["moderated"][0], row["moderated"][1], row["moderated"][2]))
    check("n=5 で縮小が k を下げる(std > 8、moderated < 5.5)", out[5]["std"][0] > 8 and out[5]["moderated"][0] < 5.5,
          "%.2f / %.2f" % (out[5]["std"][0], out[5]["moderated"][0]))
    check("n=5 で 5σ の傷の検出率が上がる(同じ宣言 1e-3)", out[5]["moderated"][1] > out[5]["std"][1] + 0.15,
          "%.3f → %.3f" % (out[5]["std"][1], out[5]["moderated"][1]))
    check("事前分布の自由度 d0 を推定(n=5、真値 6 の ±25 %)", 4.5 < out[5]["moderated"][2] < 7.5,
          "%.2f" % out[5]["moderated"][2])
    return out


# --------------------------------------------------------------------------- #
# 3. 位置合わせの探針                                                          #
# --------------------------------------------------------------------------- #
def _shift(img, dr, dc):
    """作り手の並進(大きい像を Fourier で動かしてから内側を切る = 実カメラの並進に近い)。"""
    h, w = img.shape
    F = np.fft.fft2(img)
    fr = np.fft.fftfreq(h)[:, None]
    fc = np.fft.fftfreq(w)[None, :]
    return np.fft.ifft2(F * np.exp(-2j * np.pi * (fr * dr + fc * dc))).real


def stage3_alignment():
    print("\n3) 位置合わせの探針(合成: 縁のある模様、良品は 1〜2 px ずれて撮れる)")
    rng = np.random.default_rng(38)
    big = ndi.gaussian_filter(rng.random((176, 176)), 2.5, mode="wrap")
    big = (big - big.min()) / np.ptp(big)
    big = np.where(big > 0.5, 0.8, 0.2) + 0.15 * big                 # 縁の立った模様
    big = ndi.gaussian_filter(big, 0.8, mode="wrap")
    n = 20
    offs = rng.uniform(-2.0, 2.0, (n, 2))
    crop = (slice(24, 152), slice(24, 152))
    shifted = np.stack([_shift(big, r, c)[crop] + 0.01 * rng.standard_normal((128, 128)) for r, c in offs])
    aligned = np.stack([big[crop] + 0.01 * rng.standard_normal((128, 128)) for _ in range(n)])
    refused = False
    try:
        fs.ledger.varmodel_fit(shifted, spread="std", far=FAR)
    except ValueError as exc:
        refused = True
        print("   拒否: %s" % str(exc)[:150])
    check("ずれた良品群を align='check' が拒否する", refused)
    al = fs.ledger.varmodel_alignment(shifted)
    err = al["offset"] - offs
    err -= np.median(err, axis=0)
    check("並進の推定が作り手の真値と 0.1 px 以内(共通の並進を除く)", np.abs(err).max() < 0.1,
          "最大 %.3f px、Cramér–Rao の下限 %.4f px" % (np.abs(err).max(), al["shift_sd_px"]))
    good = fs.ledger.varmodel_fit(aligned, spread="std", far=FAR)
    forced = fs.ledger.varmodel_fit(shifted, spread="std", far=FAR, max_misalign_px=5.0)
    reg = fs.ledger.varmodel_fit(shifted, spread="std", far=FAR, align="translate")
    v = reg["valid"]
    g = np.hypot(*np.gradient(big[crop]))
    edge = v & (g > np.percentile(g[v], 80))
    flat = v & (g < np.percentile(g[v], 30))
    infl = {k: float(np.median(m["spread"][edge]) / np.median(good["spread"][edge]))
            for k, m in (("forced", forced), ("reg", reg))}
    infl_flat = float(np.median(forced["spread"][flat]) / np.median(good["spread"][flat]))
    print("   縁の上の帯の幅(合わせた良品群を 1 とする): 無理に通す %.2f 倍 / Fourier シフトで合わせる %.2f 倍"
          "(平らな所は %.2f 倍)" % (infl["forced"], infl["reg"], infl_flat))
    check("ずれは縁の上の帯を 2 倍以上に太らせる", infl["forced"] > 2.0, "%.2f 倍" % infl["forced"])
    check("合わせれば 1.3 倍以内に戻る", infl["reg"] < 1.3, "%.2f 倍" % infl["reg"])
    # 縁の上の傷(+0.08 = 雑音の 8 倍)を見つけられるか
    test = big[crop] + 0.01 * rng.standard_normal((128, 128))
    defect = np.zeros((128, 128), bool)
    ys, xs = np.nonzero(edge)
    pick = rng.choice(ys.size, 60, replace=False)
    for y, x in zip(ys[pick], xs[pick]):
        defect[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = True
    defect &= v
    test = test + 0.08 * defect
    det = {}
    for k, m in (("good", good), ("forced", forced), ("reg", reg)):
        r = fs.ledger.varmodel_score(test, m, align="translate")
        det[k] = float(r["exceed"][defect].mean())
    print("   縁の上の傷(雑音の 8 倍)の検出率: 揃った群 %.2f / 無理に通した群 %.2f / 合わせた群 %.2f"
          % (det["good"], det["forced"], det["reg"]))
    check("太った帯は縁の上の傷を見逃す(検出率が半分以下)", det["forced"] < 0.5 * det["good"],
          "%.2f vs %.2f" % (det["forced"], det["good"]))
    figs.save_grid("band_width_alignment", [good["spread"], forced["spread"], reg["spread"], big[crop]],
                   captions=["揃った良品群の帯の幅", "1〜2 px ずれた群を無理に通す",
                             "Fourier シフトで合わせた群", "模様(縁で帯が太る)"],
                   ncols=4, vrange=[(0, 0.05)] * 3 + [None], gray=[False, False, False, True],
                   title="ずれは縁の上の帯を太らせる(画素ごとの標準偏差、128×128 px)",
                   caption="同じ模様の良品 20 枚。左: 揃った群の画素ごとの標準偏差 = 雑音 0.01 だけ。"
                           "中: 1〜2 px ずれた群を許容を緩めて通すと、縁の上だけ帯が %.1f 倍に太る。"
                           "右: 並進を測って Fourier シフトで合わせると %.2f 倍に戻る。"
                           "太った帯の上では雑音の 8 倍の傷の検出率が %.2f → %.2f に落ちる。"
                           % (infl["forced"], infl["reg"], det["good"], det["forced"]))
    return infl, det


# --------------------------------------------------------------------------- #
# 4. 汚れた良品群                                                              #
# --------------------------------------------------------------------------- #
def stage4_contamination():
    print("\n4) 汚れた良品群の探針(合成: 20 枚中 3 枚の「良品」に同じ場所の傷)")
    rng = np.random.default_rng(48)
    # ★地の模様が弱いと、汚れた 3 枚の傷が位相相関の山を引っ張り、0.65 px の「ずれ」として拒否された
    #   (実測。拒否は正しい振る舞い —— 汚れた良品は位置合わせも汚す)。ここは帯の比較なので模様を強くする。
    mu = ndi.gaussian_filter(rng.random((96, 96)), 2)
    mu = 0.2 + 0.6 * (mu - mu.min()) / np.ptp(mu)
    st = mu + 0.02 * rng.standard_normal((20, 96, 96))
    st[:3, 30:40, 50:60] += 0.3
    test = mu + 0.02 * rng.standard_normal((96, 96))
    test[30:40, 50:60] += 0.2
    test[70:76, 20:26] += 0.2                                     # 汚れていない場所の傷(対照)
    res = {}
    for sp in ("std", "mad"):
        m = fs.ledger.varmodel_fit(st, spread=sp, far=FAR)
        r = fs.ledger.varmodel_score(test, m)
        res[sp] = (float(r["exceed"][30:40, 50:60].mean()), float(r["exceed"][70:76, 20:26].mean()),
                   m, r)
        print("   %-4s 汚れた場所の傷の検出率 %.2f / 汚れていない場所 %.2f / 汚れた場所の帯の幅 %.3f"
              % (sp, res[sp][0], res[sp][1], float(np.median(m["spread"][30:40, 50:60]))))
    check("std は汚れた場所の傷を見逃す(< 10 %)", res["std"][0] < 0.1, "%.2f" % res["std"][0])
    check("mad は同じ傷を見つける(> 90 %)", res["mad"][0] > 0.9, "%.2f" % res["mad"][0])
    check("対照: 汚れていない場所はどちらも見つける", min(res["std"][1], res["mad"][1]) > 0.9)
    up = np.ones((3, 3))                                           # 96 px は題が入らないので最近傍で 3 倍
    figs.save_grid("contaminated_good_set", [np.kron(res["std"][2]["spread"], up), np.kron(res["mad"][2]["spread"], up),
                                             np.kron(res["std"][3]["z"], up), np.kron(res["mad"][3]["z"], up)],
                   captions=["std の帯の幅", "mad の帯の幅", "std の z 図", "mad の z 図"],
                   ncols=4, signed=[False, False, True, True], vrange=[(0, 0.12), (0, 0.12), (-12, 12), (-12, 12)],
                   title="「良品」3 枚に同じ場所の傷: std は帯が太って見逃し、mad は見つける",
                   caption="20 枚の良品のうち 3 枚の同じ場所(右上の四角)に +0.3 の傷。std は傷を良品のばらつき"
                           "として覚え、帯が太る(左上)ので、同じ場所の本物の傷(+0.2 = 雑音の 10 倍)の z が小さい。"
                           "中央値と MAD は 3 枚の外れを無視する。左下の傷は汚れていない場所の対照。")
    return res


# --------------------------------------------------------------------------- #
# 5. 公開実データ VisA                                                          #
# --------------------------------------------------------------------------- #
def _load(root, rel, mask=False):
    from PIL import Image                                         # noqa: PLC0415
    im = np.asarray(Image.open(os.path.join(root, rel)).convert("L"), dtype=np.float64)
    im = (im > 0).astype(np.float64) if mask else im / 255.0
    h, w = im.shape
    h -= h % DOWN
    w -= w % DOWN
    r = im[:h, :w].reshape(h // DOWN, DOWN, w // DOWN, DOWN).mean(axis=(1, 3))
    return r >= 0.25 if mask else r


def _visa(root):
    rows = list(csv.DictReader(open(os.path.join(root, "split_csv", "1cls.csv"), encoding="utf-8")))
    tr = sorted(r["image"] for r in rows if r["object"] == VISA_CLASS and r["split"] == "train")
    te = sorted((r for r in rows if r["object"] == VISA_CLASS and r["split"] == "test"),
                key=lambda r: r["image"])
    train = np.stack([_load(root, p) for p in tr[:200]])
    test = np.stack([_load(root, r["image"]) for r in te])
    mask = np.stack([_load(root, r["mask"], True) if r["mask"] else np.zeros(test.shape[1:], bool)
                     for r in te])
    normal = np.array([r["label"] == "normal" for r in te])
    return train, test, mask, normal


def _score_all(model, test, fallback):
    """試験画像を全部当てる。合わせられない画像(拒否)は**部品ごと不良**として全面を高いスコアにする。"""
    Z, EX, refused = [], [], 0
    for x in test:
        try:
            r = fs.ledger.varmodel_score(x, model, align="translate")
            Z.append(np.abs(r["z"]))
            EX.append(r["exceed"])
        except ValueError:
            refused += 1
            Z.append(np.full(x.shape, fallback))
            EX.append(np.ones(x.shape, bool))
    return np.stack(Z), np.stack(EX), refused


def _metrics(Z, EX, mask, normal):
    au = fs.ledger.anomaly_pixel_auroc(Z, mask)["auroc"]
    pro = fs.ledger.anomaly_pro(Z, mask, fpr_max=0.3)["aupro"]
    img = fs.ledger.anomaly_image_auroc(Z.reshape(len(Z), -1).max(axis=1), ~normal)["auroc"]
    far = float(EX[normal].mean())
    ro = fs.ledger.anomaly_region_overlap(EX[~normal], mask[~normal], min_overlap=0.3)
    return {"auroc": au, "aupro": pro, "image_auroc": img, "far_test_normal": far,
            "regions_detected": ro["detected_fraction"], "regions_hit": ro["hit_any"]}


def _save_visa_metrics_recorded():
    """2026-10-18 の実行記録から、実データ章のグラフを再描画する。"""
    figs.save_plot("visa_metrics_vs_n",
                   [(sp, [5, 20, 80], RECORDED_AUPRO[sp])
                    for sp in ("std", "moderated", "mad")]
                   + [(lab, [5, 80], RECORDED_AUPRO[lab]) for lab in
                      ("合わせない帯(n=20)", "ゴールデン比較(n=20)", "RPCA(1 枚ずつ)")],
                   styles=[None, None, None, "dashed", "dashed", "dashed"],
                   colors=["emphasis", "right", "neutral", "wrong", "reference", "neutral"],
                   xlabel="良品の枚数 n", ylabel="AUPRO(FPR ≤ 0.3)",
                   title="VisA %s: 良品の枚数と AUPRO(破線 = 比べる相手)" % VISA_CLASS,
                   source=VISA_SOURCE,
                   caption="VisA %s の試験 200 枚(CC BY 4.0)。良品 5 / 20 / 80 枚で学んだ変動モデルの AUPRO(実線)と、"
                           "同じ物差しで測った比べる相手(破線: 位置合わせしない帯・ゴールデン比較・RPCA)。"
                           "20 枚で頭打ちになり、位置合わせの有無の差(0.68 対 0.46)が枚数の差より大きい。"
                           % VISA_CLASS)


def stage5_real():
    print("\n5) 公開実データ(VisA %s、CC BY 4.0、灰色・1/%d 縮小)" % (VISA_CLASS, DOWN))
    if not DATA or not os.path.isfile(os.path.join(DATA, "split_csv", "1cls.csv")):
        print("   FULLSEYE_VISA_DATA が無いので実データの章は走らせない。")
        if RECORDED:
            print("   記録値(2026-10-18):")
            for line in RECORDED["lines"]:
                print("     " + line)
            _save_visa_metrics_recorded()
        return None
    t0 = time.perf_counter()
    train, test, mask, normal = _visa(DATA)
    print("   良品(学習用) %d 枚、試験 %d 枚(良品 %d・不良 %d)、%s px、欠陥の領域 %d 個"
          % (len(train), len(test), normal.sum(), (~normal).sum(), test.shape[1:],
             fs.ledger.anomaly_region_overlap(mask, mask)["n_regions"]))
    hold = train[120:200]                                          # 較正用の持ち出し(学習に使わない)
    res = {}
    lines = []
    # 位置合わせ前と後
    try:
        fs.ledger.varmodel_fit(train[:20], spread="std", far=FAR)
        refused = False
    except ValueError as exc:
        refused = True
        print("   位置合わせの確認: %s" % str(exc)[:160])
    check("実データ: そのままの良品群は位置ずれで拒否される", refused)
    for n in (5, 20, 80):
        st = train[:n]
        for sp in ("std", "moderated", "mad"):
            m = fs.ledger.varmodel_fit(st, spread=sp, far=FAR, align="translate", max_misalign_px=1.0,
                                       spread_floor=0.5 / 255)
            Z, EX, nref = _score_all(m, test, 1e3)
            res[(n, sp)] = _metrics(Z, EX, mask, normal)
            res[(n, sp)]["refused"] = nref
            res[(n, sp)]["k"] = m["k"]
            if n == 20 and sp == "moderated":
                keep = (m, Z, EX)
            c = fs.ledger.varmodel_calibrate(m, hold)
            Zc, EXc, _ = _score_all(c, test, 1e3)
            res[(n, sp + "+cal")] = _metrics(Zc, EXc, mask, normal)
            res[(n, sp + "+cal")]["k"] = c["k"]
            res[(n, sp + "+cal")]["far_hold_declared_k"] = c["calibration_far_declared_k"]
            print("   ... n=%d %s: AUROC %.3f AUPRO %.3f 誤検出率 %.4f(較正後 %.4f、k %.2f → %.2f)"
                  % (n, sp, res[(n, sp)]["auroc"], res[(n, sp)]["aupro"], res[(n, sp)]["far_test_normal"],
                     res[(n, sp + "+cal")]["far_test_normal"], m["k"], c["k"]), flush=True)
    # 位置合わせしないで無理に通した帯(ずれが帯を太らせる)
    mf = fs.ledger.varmodel_fit(train[:20], spread="moderated", far=FAR, max_misalign_px=40.0,
                                spread_floor=0.5 / 255)
    Zf = []
    for x in test:
        Zf.append(np.abs((x - mf["center"]) / np.where(mf["spread"] > 0, mf["spread"], 1.0)))
    Zf = np.stack(Zf)
    EXf = Zf > mf["k"]
    res[(20, "moderated, 合わせない")] = _metrics(Zf, EXf, mask, normal)
    # 帯の太りは縁で起きる(平らな所は動かない): 中心像の勾配の上位 20 % の画素で比べる
    v0 = keep[0]["valid"]
    gr = np.hypot(*np.gradient(keep[0]["center"]))
    edge = v0 & (gr > np.percentile(gr[v0], 80))
    infl = float(np.median(mf["spread"][edge]) / np.median(keep[0]["spread"][edge]))
    # 比べる相手: ゴールデン比較(良品 20 枚の平均像 = ゴールデン)と RPCA(1 枚ずつ)
    golden = keep[0]["center"]
    Zg, Zr = [], []
    for x in test:
        g = fs.compare_to_golden(x, golden, align=True, threshold=0.1, max_shift=40, data_range=1.0)
        Zg.append(g["diff"])
        Zr.append(np.abs(fs.apply(x, "dc_rpca_sparse", 0.5, 0.0) - 0.5))
    for name, Zx in (("ゴールデン比較(20 枚の平均)", np.stack(Zg)), ("RPCA(dc_rpca_sparse)", np.stack(Zr))):
        thr = np.quantile(Zx[normal], 1 - FAR)                     # 比較のため良品の分位で閾値(試験の良品を使う = 甘め)
        res[(20, name)] = _metrics(Zx, Zx > thr, mask, normal)
    t = time.perf_counter() - t0
    print("   %-28s %5s %6s %6s %6s %9s %8s" % ("方法(良品 n 枚)", "k", "AUROC", "AUPRO", "画像AU", "誤検出率", "領域検出"))
    for (n, sp), v in res.items():
        line = "%-28s %5s %6.3f %6.3f %6.3f %9.4f %8.2f" % (
            "%s n=%d" % (sp, n), ("%.2f" % v["k"]) if "k" in v else "-", v["auroc"], v["aupro"],
            v["image_auroc"], v["far_test_normal"], v["regions_detected"])
        print("   " + line)
        lines.append(line)
    print("   無理に通した帯の幅は、縁(勾配の上位 20 %%)で合わせた帯の %.2f 倍。所要 %.0f 秒。" % (infl, t))
    lines.append("無理に通した帯の幅 = 縁で合わせた帯の %.2f 倍" % infl)
    a20 = res[(20, "moderated")]
    check("実データ: 合わせると画素 AUROC が上がる(ずれが帯を太らせる)",
          a20["auroc"] > res[(20, "moderated, 合わせない")]["auroc"] + 0.02,
          "%.3f vs %.3f" % (a20["auroc"], res[(20, "moderated, 合わせない")]["auroc"]))
    check("実データ: 閉形式の k は誤検出を過小に言う(試験の良品で宣言 1e-3 の 2 倍超)",
          res[(80, "std")]["far_test_normal"] > 2 * FAR, "%.4f" % res[(80, "std")]["far_test_normal"])
    check("実データ: 持ち出しで較正すると誤検出率が下がる(n=80 std)",
          res[(80, "std+cal")]["far_test_normal"] < res[(80, "std")]["far_test_normal"],
          "%.4f → %.4f" % (res[(80, "std")]["far_test_normal"], res[(80, "std+cal")]["far_test_normal"]))
    figs.save_plot("visa_metrics_vs_n",
                   [(sp, [5, 20, 80], [res[(n, sp)]["aupro"] for n in (5, 20, 80)])
                    for sp in ("std", "moderated", "mad")]
                   + [(lab, [5, 80], [res[(20, key)]["aupro"]] * 2) for lab, key in
                      (("合わせない帯(n=20)", "moderated, 合わせない"),
                       ("ゴールデン比較(n=20)", "ゴールデン比較(20 枚の平均)"),
                       ("RPCA(1 枚ずつ)", "RPCA(dc_rpca_sparse)"))],
                   styles=[None, None, None, "dashed", "dashed", "dashed"],
                   colors=["emphasis", "right", "neutral", "wrong", "reference", "neutral"],
                   xlabel="良品の枚数 n", ylabel="AUPRO(FPR ≤ 0.3)",
                   title="VisA %s: 良品の枚数と AUPRO(破線 = 比べる相手)" % VISA_CLASS, source=VISA_SOURCE,
                   caption="VisA %s の試験 200 枚(CC BY 4.0)。良品 5 / 20 / 80 枚で学んだ変動モデルの AUPRO(実線)と、"
                           "同じ物差しで測った比べる相手(破線: 位置合わせしない帯・ゴールデン比較・RPCA)。"
                           "20 枚で頭打ちになり、位置合わせの有無の差(0.68 対 0.46)が枚数の差より大きい。"
                           % VISA_CLASS)
    i = int(np.nonzero(~normal)[0][0])
    m, Z, EX = keep
    r = fs.ledger.varmodel_score(test[i], m, align="translate")
    print("   説明の例(不良 %d 枚目、上位 3 領域):" % i)
    for g in r["regions"][:3]:
        print("     面積 %d px、ピーク %+.1f σ(%s)、重心 (%.0f, %.0f)、外接矩形 %s"
              % (g["area"], g["peak_z"], g["polarity"], g["centroid"][0], g["centroid"][1], g["bbox"]))
    # 図は欠陥の周り(±48 px)だけを切り出す: 基板の印字(部品の型番)を図に載せない
    rr, cc = np.nonzero(mask[i])
    r0, r1 = max(0, rr.min() - 12), min(test.shape[1], rr.max() + 49)   # 上は印字の手前で止める
    c0, c1 = max(0, cc.min() - 48), min(test.shape[2], cc.max() + 49)
    win = (slice(r0, r1), slice(c0, c1))
    zg, zr = np.stack(Zg)[i], np.stack(Zr)[i]
    figs.save_grid("visa_explanation",
                   [test[i][win], mask[i][win].astype(float), r["z"][win], r["exceed"][win].astype(float),
                    zg[win], zr[win]],
                   captions=["試験画像(不良、切り出し)", "真値マスク", "変動モデルの z 図", "宣言 1e-3 の帯の外",
                             "ゴールデン比較の差分", "RPCA の疎な残差"],
                   ncols=3, signed=[False, False, True, False, False, False],
                   gray=[True, True, False, True, False, False],
                   vrange=[None, None, (-15, 15), None, None, None],
                   title="VisA %s の不良 1 枚: 同じ切り出しで 3 つの方法の欠陥図" % VISA_CLASS,
                   caption="VisA %s(CC BY 4.0、灰色・1/4 縮小、欠陥の周りを切り出し、基板の印字は入れない)。変動モデルは良品 20 枚"
                           "(moderated)、z は画素ごとに良品のばらつきの何倍外れたか(青 = 良品より明るい、橙 = 暗い。黒 = 位置合わせで像の外にはみ出し、採点しない画素)。"
                           "ゴールデン比較は同じ 20 枚の平均像との差、RPCA は 1 枚の低ランク分解の残差。"
                           "並進で合わせても縁に残る z の縞は、学習用と試験用の撮影の違い(並進で取れない残り)。"
                           % VISA_CLASS)
    return res, lines


# --------------------------------------------------------------------------- #
# 6. 向かない題材: 確率的なテクスチャ(DAGM 2007)                                #
# --------------------------------------------------------------------------- #
def stage6_texture():
    print("\n6) 向かない題材の探針(DAGM 2007 Class1、CC BY 4.0: 位置の決まらない確率的なテクスチャ)")
    root = os.path.join(DAGM, "Class1") if DAGM else ""
    if not root or not os.path.isfile(os.path.join(root, "Train", "Label", "Labels.txt")):
        print("   FULLSEYE_DAGM_DATA が無いのでこの章は走らせない。")
        if RECORDED_DAGM:
            print("   記録値(2026-10-18): " + RECORDED_DAGM)
        return None
    from PIL import Image                                         # noqa: PLC0415

    def rows(split):
        with open(os.path.join(root, split, "Label", "Labels.txt"), encoding="utf-8") as fh:
            return [ln.split("\t") for ln in fh.read().splitlines()[1:] if ln.strip()]

    def load(path, mask=False):
        im = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
        im = (im > 0).astype(np.float64) if mask else im / 255.0
        r = im.reshape(128, 4, 128, 4).mean(axis=(1, 3))
        return r >= 0.25 if mask else r

    good = [r[2] for r in rows("Train") if r[1] == "0"][:80]
    st = np.stack([load(os.path.join(root, "Train", p)) for p in good])
    m = fs.ledger.varmodel_fit(st, spread="moderated", far=FAR)
    Z, M, lab = [], [], []
    for r in rows("Test")[:300]:
        x = load(os.path.join(root, "Test", r[2]))
        Z.append(np.abs(fs.ledger.varmodel_score(x, m)["z"]))
        lab.append(r[1] == "1")
        M.append(load(os.path.join(root, "Test", "Label", r[4].strip()), True) if r[1] == "1"
                 else np.zeros((128, 128), bool))
    Z, M, lab = np.stack(Z), np.stack(M), np.array(lab)
    au = fs.ledger.anomaly_pixel_auroc(Z, M)["auroc"]
    img = fs.ledger.anomaly_image_auroc(Z.reshape(len(Z), -1).max(axis=1), lab)["auroc"]
    ratio = float(np.median(m["spread"][m["valid"]]) / st.std(axis=(1, 2)).mean())
    line = ("位置合わせ observable=%s、帯の幅 = 画像全体のばらつきの %.2f 倍、画素 AUROC %.3f、画像 AUROC %.3f"
            "(試験 %d 枚・不良 %d、楕円の弱い注釈)" % (m["alignment"]["observable"], ratio, au, img, len(lab), lab.sum()))
    print("   " + line)
    check("DAGM: 平均像に構造が無い → 位置合わせは「測れない」と報告", not m["alignment"]["observable"])
    check("DAGM: 画素ごとの帯はテクスチャ全体のばらつきに退化し、検出は偶然並み(AUROC < 0.65)",
          ratio > 0.8 and au < 0.65 and img < 0.65, line)
    return line


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    c0 = time.process_time()
    print("良品統計の変動モデル: 誤検出率を宣言して「いつもと違う」を言う")
    print("=" * 68)
    rows = stage1_far()
    few = stage2_few()
    infl, det = stage3_alignment()
    cont = stage4_contamination()
    real = stage5_real()
    tex = stage6_texture()
    xs = list(range(1, len(rows) + 1))
    figs.save_plot("far_declared_vs_measured",
                   [("実測 / 宣言", xs, [r[5] / r[2] for r in rows]),
                    ("二項 4σ の帯(上)", xs, [1 + r[6] / r[2] for r in rows]),
                    ("二項 4σ の帯(下)", xs, [1 - r[6] / r[2] for r in rows]),
                    ("宣言どおり = 1", [0.5, len(rows) + 0.5], [1.0, 1.0])],
                   xlabel="条件の番号(説明は図の下)",
                   ylabel="数えた誤検出率 / 宣言",
                   title="宣言どおりの誤検出率: 6 通りは帯の中、仮定を破った 7 だけ 2 倍",
                   kinds=["scatter", "scatter", "scatter", "line"], styles=[None, None, None, "dashed"],
                   colors=["emphasis", "neutral", "neutral", "reference"], size=(760, 380),
                   caption="画素ごとに独立な正規の良品(合成)。当てはめに使わなかった良品で数えた誤検出率を宣言で割った値。"
                           "1 = std n=5、2 = std n=20、3 = pooled n=5、4 = moderated n=5、5 = moderated n=20、6 = mad n=20、"
                           "7 = pooled n=5(雑音が画素ごとに違う)。"
                           "4 種のばらつきの推定(1〜6)は二項の 4σ の帯に入り、画素ごとに雑音が違うのに 1 つの分散を"
                           "使った 7 だけが宣言の 2 倍に外れる。")
    print("\n6) まとめ")
    print("   合成: 宣言 far は 4 種とも 4σ 帯で守られる(仮定違反の pooled だけ外れる)。n=5 の k は std %.1f → "
          "moderated %.1f。ずれは縁の帯を %.1f 倍に太らせ、傷の検出率を %.2f → %.2f に落とす。汚れた良品群で std "
          "の検出 %.2f、mad %.2f。" % (few[5]["std"][0], few[5]["moderated"][0], infl["forced"], det["good"],
                                       det["forced"], cont["std"][0], cont["mad"][0]))
    if real is None and not RECORDED:
        print("   実データの章は未実行(記録値なし)。")
    if figs.errors():
        print("   図の書き出しで失敗:", "; ".join(figs.errors()))
    print("   所要: CPU %.1f 秒(壁時計 %.1f 秒)" % (time.process_time() - c0, time.perf_counter() - t0))
    if not all(ok_all):
        print("NG が残っている(%d 件)" % ok_all.count(False))
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
