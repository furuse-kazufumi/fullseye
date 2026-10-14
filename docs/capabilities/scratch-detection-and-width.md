---
id: scratch-detection-and-width
title: 微細スクラッチを見つけて、幅を測る
title_en: Detect fine scratches and measure their width
category: 測る
ops: [lines_gauss, bothat, measure_pairs, table_px_to_mm]
examples: [example_scratch_width, poc_crack_width, poc_solar_el_inspection]
version: 0.2.0
inputs: [image]
pipeline: [gaussian, lines_gauss, select_contours, fit_line_contours, gen_measure_rectangle2, measure_pairs, table_px_to_mm]
alternatives: [bothat, tophat, sk_frangi, laplace_of_gauss, fuzzy_measure_pairing, mm_per_px_from_reference]
limits: `lines_gauss` は線の**幅も極性も返さない**(暗線・明線を同じ輪郭にする、実測)。幅 1〜3 px は `measure_pairs` の危険域(エッジ間距離 / PSF 幅 < 3.09 で大きい側へ偏り、失敗を返さない)—— 画素以下の幅は輝度欠損の積分で測る(`poc_crack_width`)。
calibration: 既知幅の的(スケールバー・基準溝)を同じ光学系で `measure_pairs` にかけ `mm_per_px_from_reference` → `table_px_to_mm`。0.1 mm を切る幅は mm/px の 1 % がそのまま効く。
---

# 微細スクラッチを見つけて、幅を測る

## できること

線状の傷を**どこにあるか**(検出)と**どれだけ太いか**(幅)の 2 段で扱います。検出は Hessian リッジ応答(`lines_gauss`)か暗い細部だけを浮かせる形態学(`bothat`)、幅は検出した線に**直交する測定線**を張って `measure_pairs` で両側のエッジをサブピクセルで取り、`table_px_to_mm` で mm にします。

## What it does

Two stages: *where* (ridge response `lines_gauss`, or the black-top-hat `bothat` that lifts only dark fine detail) and *how wide* (a measurement line across the detected line, `measure_pairs` for the two sub-pixel edges, `table_px_to_mm` for millimetres).

## 向くところ / 向かないところ

**向く**: 研磨面・ガラス・EL 画像の線状欠陥。幅が **3 px 以上**あり、背景より暗い(または明るい)ことが分かっているとき。

**向かない**: ★幅が 1〜3 px の傷。`measure_pairs` は対が互いを押し広げるので**必ず大きい側**へ偏り、しかも失敗を返しません(w/σ 2.06 で +2.43 px、1.58 でも「対が見つかった」と答える)。画素以下の幅は**輝度欠損の積分**で測ってください —— `poc_crack_width` が 0.25 px まで連続に追えることを示しています。★`lines_gauss` は Frangi 応答の二値化で、HALCON の同名 op と違い**線幅も極性も返しません**(暗線・明線どちらも同じ輪郭になる —— 2026-09-15 実測)。

## 推奨パイプライン

`gaussian` → `lines_gauss` → `select_contours` → `fit_line_contours` → `gen_measure_rectangle2` → `measure_pairs` → `table_px_to_mm`

`gaussian` で画素雑音を落とし(σ は傷の幅より小さく)→ `lines_gauss` で線状構造の輪郭 → `select_contours` で短いゴミを捨て → `fit_line_contours` で各輪郭を直線にして向き φ と中点を得る → その中点で φ + 90° の `gen_measure_rectangle2` を張り → `measure_pairs` で幅 [px] → `table_px_to_mm` で mm 列を足す。傷が暗いときは `measure_pairs` が返す最初の対の極性が「立ち下がり → 立ち上がり」であることを確かめる(極性の順序は問わない op なので、明るい縁の幅が返ることがある)。

## 代替

検出は用途で差し替える: 暗い細部だけなら `bothat`(白トップハット `tophat` は**明るい**細部用で、暗線には 0 を返す —— 実測)、スケールを振るなら `sk_frangi`、ブロブ寄りなら `laplace_of_gauss`(0.5 がゼロ交差)。幅の対が複数出るなら `fuzzy_measure_pairing` で想定幅に近い対を先頭にする。使い分けの表は [`docs/ops/2d/guides/gallery2d_contour_measure.md`](../ops/2d/guides/gallery2d_contour_measure.md) の「線状欠陥の op の使い分け」。

## 限界

- `measure_pairs` は信頼度も失敗も返さない。危険域(エッジ間距離 / PSF 幅 < 3.09)は呼ぶ側が見張る —— [`subpixel_measuring.md` §2](../ops/measure1d/guides/subpixel_measuring.md)。
- 斜めの測定線に cos 補正は無い。`fit_line_contours` で得た向きに直交させてから測る。
- 幅 1〜3 px では偏りが幅と同じ桁になる。`example_scratch_width` が真値 1〜3 px で `measure_pairs`(σ 0.5 / 1.0)と積分法を並べ、どこから `measure_pairs` が使えるかを数字で出す。

## 実寸校正

既知幅の的(スケールバー、基準溝)を**同じ光学系・同じ作動距離**で `measure_pairs` にかけ、`mm_per_px_from_reference(width_px, known_mm)` で mm/px を出す。図面値や公称倍率で置かない(作動距離 10 % で全寸法 10 %)。傷の表は `table_px_to_mm` で `width_mm` 列を足す。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = np.full((96, 128), 0.6)
img[47:49, 10:118] = 0.1                        # 幅 2 px の暗い横傷
cs = fs.apply(fs.apply(img, "gaussian", 0.1, 0.5), "lines_gauss", 0.5, 0.5)
print("線状構造の輪郭", len(cs["cs"]))            # 極性も幅も返さない
meas = fs.ledger.gen_measure_rectangle2(row=48, col=64, phi=np.pi / 2,
                                        length1=12, length2=5, shape=img.shape)
pairs = fs.ledger.measure_pairs(img, meas, sigma=0.5, threshold=0.1)
mm_per_px = fs.ledger.mm_per_px_from_reference(200.0, 10.0)   # 的 10 mm = 200 px
print(fs.ledger.table_px_to_mm(pairs, mm_per_px)[0]["width_mm"])
```

## 裏づけ

- op: `lines_gauss` / `bothat`(検出)、`measure_pairs`(幅)、`table_px_to_mm` / `mm_per_px_from_reference`(実寸)
- 例: [`example_scratch_width`](../../examples/example_scratch_width.py)(真値 1〜3 px の傷で幅の偏りを測る)、[`poc_crack_width`](../../examples/poc_crack_width.py)(画素以下の幅は積分で)、[`poc_solar_el_inspection`](../../examples/poc_solar_el_inspection.py)
