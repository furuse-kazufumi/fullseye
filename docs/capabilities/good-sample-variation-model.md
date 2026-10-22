---
id: good-sample-variation-model
title: 良品を並べて「いつもと違う」を言う(良品統計の変動モデル、誤検出率の宣言つき)
title_en: Flag what differs from aligned good samples (a per-pixel variation model with a declared false-alarm rate)
category: 見つける
ops: [varmodel_alignment, varmodel_band_k, varmodel_fit, varmodel_calibrate, varmodel_score, anomaly_pixel_auroc, anomaly_pro, anomaly_image_auroc, anomaly_region_overlap, compare_to_golden]
examples: [poc_good_sample_variation_model, anomaly_eval_metrics]
version: 0.6.1
inputs: [video, image2d]
pipeline: [varmodel_alignment, varmodel_fit, varmodel_calibrate, varmodel_score]
alternatives: [compare_to_golden, dc_rpca_sparse, anomaly_pro]
limits: 並進だけを合わせる。回転・拡大・照明の違いが残る実画像では宣言の誤検出率は守られない(VisA pcb1 で宣言 1e-3 に対し 3.8 %、持ち出しの較正後も 2.4 %)。確率的なテクスチャには効かない(DAGM 2007 で偶然並み)。
calibration: 帯は画素値の単位のまま。欠陥の大きさを実寸で言うなら、既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。
---

# 良品を並べて「いつもと違う」を言う(良品統計の変動モデル、誤検出率の宣言つき)

## できること

位置をそろえた良品の画像を何枚か渡すと、画素ごとの「いつもの値」(中心)と「いつものばらつき」を覚え、新しい 1 枚のどの画素が許容帯の外にあるか、何 σ 外れたかを領域ごとに説明します。外観検査の古典(良品統計・バリエーションモデル)ですが、帯の幅 k を手で決めずに、**1 画素あたりの誤検出率を宣言して**分布から決めます。

- ★**帯の幅は宣言した誤検出率から閉形式で出ます**(検査対象の欠陥で調整しません)。正規の良品なら新しい 1 枚の偏差は t 分布の予測区間に従うので `k = t⁻¹_{n−1}(1 − far/2)·√(1+1/n)`。合成の良品(画素ごとに独立な正規)で数えた誤検出率は、std・pooled・moderated・mad の 4 種とも宣言の二項 4σ の帯に入ります。
- ★★**良品が少ないときの縮小**: n = 5 だと画素ごとの分散は大きく揺れ、std の k は t₄ の裾で 9.4(far 1e-3)。`moderated`(Smyth 2004 の経験ベイズ、全画素の分散から事前分布を推定して縮小)は k を 5.1 に下げ、同じ誤検出率で 5σ の傷の検出率を 0.13 から 0.52 に上げます。事前分布の自由度は真値 6 に対し 5.8 と推定されます。
- ★★**位置合わせを確かめ、ずれた良品群は拒否します**。1〜2 px ずれた良品群で帯を作ると、縁の上だけ帯が 22 倍に太り、縁の上の傷(雑音の 8 倍)は 1 つも見つかりません。`align="check"` はずれを 1/20 px 刻みで測り(合成の真値と 0.03 px 以内)、許容を超えた群を `ValueError` で止めます。`align="translate"` は Fourier シフトで合わせ(全域通過なので白色雑音の分散を変えません。双線形の補間は雑音を均して帯を細らせます)、帯は 1.07 倍に戻ります。
- ★**汚れた良品群に強い頑健版**: 20 枚の「良品」の 3 枚に同じ場所の傷があると、std は傷をばらつきとして覚えて同じ場所の本物の傷を見逃します(検出率 0.00)。`mad`(中央値と MAD)は 0.98。MAD の k は位置と尺度によらない量(ピボット)なので、n と far だけからモンテカルロで決まり、乱数の誤差も返します。
- ★**構造の無い良品は「測れない」と言います**。平らな面や確率的なテクスチャは平均像に構造が無く、並進は測れません(Cramér–Rao の下限が無限大)。その場合は拒否せず `observable=False` と報告します —— 構造が無ければ、ずれが帯を太らせることもないからです。
- ★**実画像で宣言が守られないときの較正**: 閉形式は「画素ごとに独立な正規」の約束です。`varmodel_calibrate` は当てはめに使わなかった良品で |z| の分位を数え、k を測り直します(欠陥は見ません)。
- **評価は方法に依存しない物差しで**: `anomaly_pixel_auroc` / `anomaly_pro`(AUPRO、FPR 0.3 まで)/ `anomaly_image_auroc` / `anomaly_region_overlap`。RPCA・ゴールデン比較・本族を同じ門で比べられます。

## What it does

A per-pixel variation model learned from aligned good samples, with the band half-width derived from a declared per-pixel false-alarm rate rather than tuned by hand: a t prediction interval for mean/std, an empirical-Bayes moderated t (Smyth 2004) for few samples, and a Monte-Carlo pivot for the robust median/MAD variant. Measured false-alarm rates on synthetic normal good samples fall inside the binomial 4-sigma band for all four estimators. The stack's alignment is measured to 1/20 px and a misaligned stack is refused (or registered by an all-pass Fourier shift); forcing a 1-2 px misaligned stack fattens the band on edges 22-fold and misses every edge defect. Held-out calibration re-derives k from good images when real data break the model, and every out-of-band region is explained by area, sign and peak sigma. Method-independent metrics (pixel AUROC, AUPRO to FPR 0.3, image AUROC, per-region overlap) compare it with RPCA and golden comparison.

## 向くところ / 向かないところ

- 向く: 同じ品物を同じ治具・同じ照明で撮る外観検査(基板・印刷・成形品・ラベル)。品物ごとの模様が**同じ**であることが前提です。
- **向かない: 確率的なテクスチャ**(布・木目・鋳肌)。1 枚ごとに模様が違うので平均像に構造が無く、帯はテクスチャ全体のばらつきに退化します。DAGM 2007 Class1 では検出は偶然並みでした。周期・テクスチャの op の仕事です。
- 位置合わせは**並進だけ**です。回転・拡大・ゆがみが残る品物は、先に `find_shape_model`(形状マッチ)や `frame_align`(相似変換)で合わせてから渡してください(合わせ残しは `varmodel_alignment` の余裕で分かります)。
- 実画像では宣言の誤検出率は守られないことがあります(残る位置ずれ・圧縮・照明の揺れ・空間相関)。数を約束に使うなら `varmodel_calibrate` を通してください。
- 帯の外の画素数の p 値(`count_pvalue`)は画素の独立を仮定するので、空間相関のある雑音では楽観側です(判定には使いません)。

## 推奨パイプライン

`varmodel_alignment` → `varmodel_fit` → `varmodel_calibrate` → `varmodel_score`

良品群のずれを測り(許容を超えたら `align="translate"` で合わせるか治具を直す)→ 宣言した誤検出率で帯を当てはめ → 当てはめに使わなかった良品で帯の幅を測り直し → 試験の 1 枚を当てて、帯の外を領域ごとに説明する。方法の比べ合いは `anomaly_pixel_auroc` / `anomaly_pro`。

## 代替

良品が 1 枚しか無いなら `compare_to_golden`(基準 1 枚との差、閾値は手で決める)。周期的な背景の上の孤立した欠陥なら `dc_rpca_sparse`(1 枚の低ランク分解)。

## 限界

位置合わせは並進だけです。回転・拡大・照明の違いが残る実画像では、閉形式の誤検出率は守られません(VisA pcb1 で宣言 1e-3 に対し 3.8 %、持ち出しの良品で較正しても 2.4 %)。確率的なテクスチャ(DAGM 2007)では偶然並みです。

## 実寸校正

帯は画素値の単位のままです。欠陥の大きさを実寸で言うなら、既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

rng = np.random.default_rng(0)
yy, xx = np.mgrid[0:64, 0:64]
base = 0.5 + 0.3 * np.sin(xx / 4.0) * np.cos(yy / 5.0)         # 良品の模様
goods = base + 0.02 * rng.standard_normal((20, 64, 64))         # 位置のそろった良品 20 枚
model = fs.ledger.varmodel_fit(goods, spread="moderated", far=1e-3)
print("k = %.2f(宣言 1e-3、%s)" % (model["k"], model["k_source"]))

test = base + 0.02 * rng.standard_normal((64, 64))
test[20:24, 30:34] += 0.2                                        # 雑音の 10 倍の傷
r = fs.ledger.varmodel_score(test, model)
for g in r["regions"][:3]:
    print("面積 %d px、ピーク %+.1f σ(%s)、外接矩形 %s" % (g["area"], g["peak_z"], g["polarity"], g["bbox"]))
```

## 裏づけ

- op: `varmodel_alignment` / `varmodel_band_k` / `varmodel_fit` / `varmodel_calibrate` / `varmodel_score`、評価 `anomaly_pixel_auroc` / `anomaly_pro` / `anomaly_image_auroc` / `anomaly_region_overlap`
- 例: [`poc_good_sample_variation_model`](../../examples/poc_good_sample_variation_model.py) —— 合成の閉形式(宣言 = 実測)、少数の良品の縮小、位置ずれと汚れの探針、公開実データ VisA(CC BY 4.0)で RPCA・ゴールデン比較と同じ物差し、DAGM 2007 で向かない題材。[`anomaly_eval_metrics`](../../examples/anomaly_eval_metrics.py) —— 画素 AUROC と PRO が違うものを数えること。
- 既存 op と組む: `compare_to_golden`(基準 1 枚との差)・`dc_rpca_sparse`(1 枚の低ランク分解)・`inspect_batch` / `judge`(ロットの判定)・`pod_false_call`(誤検出確率の報告)
- 先行: G. K. Smyth, *Stat. Appl. Genet. Mol. Biol.* 3(1):3, 2004; P. J. Rousseeuw & C. Croux, *JASA* 88:1273, 1993; M. Guizar-Sicairos, S. T. Thurman, J. R. Fienup, *Opt. Lett.* 33:156, 2008; P. Bergmann ほか, *CVPR* 2020(PRO); J. A. Hanley & B. J. McNeil, *Radiology* 143:29, 1982。
