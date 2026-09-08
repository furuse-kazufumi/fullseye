---
id: subpixel-2d-metrology
title: 画像から寸法をサブピクセルで測る
title_en: Measure dimensions from an image, below the pixel
category: 測る
ops: [measure_pos, measure_pairs, blob_label, blob_select]
examples: [poc_dimensional_inspection, poc_screw_thread_metrology]
version: 0.1.11
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

## 裏づけ

- op: `measure_pos` / `measure_pairs`(1-D 測定線)、`blob_label` / `blob_select`(領域を先に絞るとき)
- 例: [`poc_dimensional_inspection`](../../examples/poc_dimensional_inspection.py)、[`poc_screw_thread_metrology`](../../examples/poc_screw_thread_metrology.py)
