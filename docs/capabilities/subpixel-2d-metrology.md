---
id: subpixel-2d-metrology
title: 画像から寸法をサブピクセルで測る
title_en: Measure dimensions from an image, below the pixel
category: 測る
ops: [measure_pos, measure_pairs, blob_label, blob_select]
examples: [poc_dimensional_inspection, poc_screw_thread_metrology]
version: 0.1.11
inputs: [image]
pipeline: [gen_measure_rectangle2, measure_pos, measure_pairs, table_px_to_mm]
alternatives: [fuzzy_measure_pairing, gen_measure_arc, create_metrology_model, blob_label, blob_select, mm_per_px_from_reference]
limits: 斜めの測定線に cos 補正が無い。エッジ間距離 / PSF 幅 < 3.09 で幅が大きく出るのに失敗を返さない。縁の定義で 16 px 動く(guides/subpixel_measuring.md)。
calibration: 既知寸法の的を**同じ op で**測って `mm_per_px_from_reference` → `table_px_to_mm` で表ごと mm に。公称倍率は使わない(作動距離 10 % で全寸法 10 %)。
---

# 画像から寸法をサブピクセルで測る

## できること

測定線に沿った輝度の勾配からエッジを**画素より細かく**求め、対になるエッジの間隔として寸法を返します。二値化して画素を数える方法と違い、しきい値の選び方で答えが動きません。

## What it does

Locate edges along a measurement line from the intensity gradient, at sub-pixel resolution, and read a dimension as the distance between paired edges. Unlike counting thresholded pixels, the answer does not move when the threshold does.

## 向くところ / 向かないところ

**向く**: 照明が安定していて、測る向きが分かっている工業計測。エッジが片側 3〜4 画素以上のなだらかさを持つとき。

**向かない**: 対象が測定線に対して大きく傾いている場合(投影された幅を測ってしまう)。テクスチャが細かくエッジが 1 画素で立つ場合は、サブピクセルの利得がほとんど出ません。★**再投影誤差や適合度が小さいことは、寸法が正しい証拠になりません** ——`poc_camera_calibration` がその分離を測っています。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = np.zeros((64, 128), float)
img[:, 40:88] = 1.0                      # 幅 48 px の帯
prof = fs.ledger.measure_pos(img, row=32, col0=0, col1=127)
print(prof)                              # エッジ位置(サブピクセル)
```

## 推奨パイプライン

`gen_measure_rectangle2` → `measure_pos` → `measure_pairs` → `table_px_to_mm`

`gen_measure_rectangle2` で測定線を置き → `measure_pos` でエッジ位置(副画素)→ `measure_pairs` で対にして幅 [px] → `table_px_to_mm` で mm 列を足す。

## 代替

想定幅に近い対を選ぶなら `fuzzy_measure_pairing`、円周なら `gen_measure_arc`、図形をまとめて当てはめるなら `create_metrology_model` 系。測る場所を先に絞るなら `blob_label` / `blob_select`。

## 限界

斜めの測定線に cos 補正が無い。エッジ間距離 / PSF 幅 < 3.09 で幅が大きく出るのに失敗を返さない。縁の定義で 16 px 動く(guides/subpixel_measuring.md)。

## 実寸校正

既知寸法の的を**同じ op で**測って `mm_per_px_from_reference` → `table_px_to_mm` で表ごと mm に。公称倍率は使わない(作動距離 10 % で全寸法 10 %)。

## 裏づけ

- op: `measure_pos` / `measure_pairs`(1-D 測定線)、`blob_label` / `blob_select`(領域を先に絞るとき)
- 例: [`poc_dimensional_inspection`](../../examples/poc_dimensional_inspection.py)、[`poc_screw_thread_metrology`](../../examples/poc_screw_thread_metrology.py)
