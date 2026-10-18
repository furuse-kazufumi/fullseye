---
id: crop-weed-cover-grade
title: 圃場の RGB から作物と雑草を色と肌理で分け、雑草の被度を宣言した境で段階にする(学習器なし)
title_en: Separating crop from weeds in field RGB by colour and texture, and grading weed cover at declared edges (no learned network)
category: 見つける
ops: [plant_color_index, superpixel_color_texture_features, fisher_lda_fit, fisher_lda_score, cover_ratio_grade]
examples: [poc_weed_rice_ratio]
version: 0.6.1
inputs: [rgbimage, labels2d, matrix, signal]
pipeline: [superpixel_color_texture_features, fisher_lda_fit, fisher_lda_score, cover_ratio_grade]
alternatives: [plant_color_index, snic_superpixels, class_ndim_norm]
limits: 判別は 10 特徴の 1 次式で、色と肌理が作物と雑草でほとんど同じ(雑草イネ)だと位置の精度は IoU 0.4 程度。季節の違う飛行への汎化は弱い(撮影日を丸ごと外すと日の中の相関 0.14 の日がある)。暗い画素は色度が決まらず値を作らない。
calibration: 画像は uint8 か [0, 1] の float。照明の色が変わる圃場では、白板か灰色の板で白を合わせてから色指標を取る(色度座標の指標は一様な明るさの倍率には不変だが、色温度の変化には不変でない)。
---

# 圃場の RGB から作物と雑草を色と肌理で分け、雑草の被度を宣言した境で段階にする(学習器なし)

## できること

水田や畑の RGB 画像(UAV・定点カメラ)から、作物の画素と雑草の画素を分け、雑草の程度を段階(少ない / 中程度 / 多い / 甚大)で答えます。深層学習は使わず、色の指標と肌理の特徴を領域ごとに出し、2 クラスの Fisher 線形判別(閉形式)で分けます。

`plant_color_index` は可視 3 バンドの植物の色指標 6 つ(ExG・ExR・ExGR・CIVE・NGRDI・VEG)を 1 つの口で返します。ExGR は 0 が植物と背景の境という閾値の要らない指標です。暗い画素は色度が雑音で決まるので、値を作らず NaN と `valid=False` で返します。`superpixel_color_texture_features` はラベル画像(格子でも超画素でも)の領域ごとに、色指標の平均・色度・明るさの平均とばらつき・勾配の大きさ・構造テンソルの向きの揃い(稲の細長い葉は揃い、広葉や塊の雑草は揃わない)を出します。`fisher_lda_fit` / `fisher_lda_score` は 2 クラスの線形判別、`cover_ratio_grade` は被度を**評価の前に宣言した境**(既定は植生調査の被度階級 5 / 25 / 50 %)で段階にします。

## What it does

Five ops for field RGB: six visible-band plant colour indices (ExG, ExR, ExGR, CIVE, NGRDI, VEG; dark pixels are left undefined rather than set to zero), ten colour and texture features per region of a label image (including structure-tensor orientation coherence, which separates aligned crop leaves from isotropic weed patches), a closed-form two-class Fisher discriminant (fit and score), and a grader that splits a cover fraction at edges declared before evaluation (default 5 / 25 / 50 %, the Braun-Blanquet cover classes). The PoC scores them on a public UAV dataset of weedy rice with pixel masks (CC BY 4.0): grade agreement kappa 0.424 on the held-out test split (permutation p = 0.0005), cover correlation 0.826, and an honest leave-one-date-out check where one late-season flight drops to r = 0.14.

## 向くところ / 向かないところ

**向く**: 学習データが数百枚しかなく、判定の根拠(どの特徴がどちら向きに効いたか)を数値で示したいとき。雑草の色や葉の形が作物と違う圃場(広葉雑草・ノビエの明るい群落)。段階の境を先に決めておき、その境に対する判定の脆さ(`margin`)を見たいとき。

**向かない**: 作物と雑草がほぼ同じ見た目のとき —— PoC の雑草イネ(栽培イネと同じ種)では位置の精度は IoU 0.40 にとどまります。季節・生育段階の違う飛行への汎化は弱く、撮影日を丸ごと外すと日の中の相関が 0.14 まで落ちる日がありました。個体の数え上げや種の同定はしません。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

L = fs.ledger
h, w = 96, 128
yy, xx = np.mgrid[0:h, 0:w]
img = np.empty((h, w, 3))
img[:] = (0.17, 0.34, 0.12)                                      # 作物: 濃い緑
img[:, 64:] = (0.36, 0.50, 0.20)                                 # 右半分は雑草: 明るい黄緑
img += 0.04 * np.sin(0.8 * xx)[..., None]                         # 葉の肌理
lab = (yy // 16) * (w // 16) + xx // 16 + 1                       # 16 px 角の格子
f = L.superpixel_color_texture_features(np.clip(img, 0, 1), lab)
y = (f["centroids"][:, 1] >= 64).astype(int)                      # 区画の重心が右なら雑草
model = L.fisher_lda_fit(f["X"], y)
pred = L.fisher_lda_score(model, f["X"])["label"]
frac = float((pred * f["sizes"]).sum() / f["sizes"].sum())
print(frac, L.cover_ratio_grade(frac)["grade"])                   # 0.5 [3]
```

走らせて見るなら `py -3.11 examples/poc_weed_rice_ratio.py`(実データの章は `FULLSEYE_WEEDYRICE_DATA` を指定したとき)。

## 推奨パイプライン

`superpixel_color_texture_features` → `fisher_lda_fit` → `fisher_lda_score` → `cover_ratio_grade`

領域ごとに色と肌理の特徴を出し(`superpixel_color_texture_features`、領域は 16 px 角の格子か `snic_superpixels`。返りの表の `X` が特徴の行列 = matrix)→ 注釈の 2 割未満 / 8 割超の領域だけで、0/1 の列(signal)を添えて判別を学び(`fisher_lda_fit`)→ 新しい画像の領域を採点して画素に戻し(`fisher_lda_score`)→ 雑草の面積の割合を宣言した境で段階にする(`cover_ratio_grade`)。

## 代替

植物と背景(土・水)を分けるだけなら `plant_color_index` の ExGR > 0(閾値なし)。領域は `snic_superpixels` でも作れる(PoC の実データでは格子の方が良かった)。正規分布のクラスとの距離で分けるなら `learn_ndim_norm` / `class_ndim_norm`。

## 限界

判別は 10 特徴の 1 次式で、作物と雑草の見た目がほぼ同じだと位置の精度は低い(雑草イネで IoU 0.40)。季節の違う飛行への汎化は弱い。データ付属の分割は同じ飛行の隣り合うコマを train と test に分けるので、test の数字は見た飛行の別のコマの成績。暗い画素は値を作らない(NaN)。

## 実寸校正

色度座標の指標は一様な明るさの倍率に不変だが、照明の色温度の変化には不変でない。圃場ごとに白板か灰色の板で白を合わせてから使う。被度の段階の境は評価の前に決め、注釈の分布から決めない。

## 裏づけ

- op: `plant_color_index`、`superpixel_color_texture_features`、`fisher_lda_fit`、`fisher_lda_score`、`cover_ratio_grade`
- 例: [`poc_weed_rice_ratio`](../../examples/poc_weed_rice_ratio.py)
