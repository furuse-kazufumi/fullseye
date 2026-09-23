---
id: subpixel-2d-metrology
title: 画像から寸法をサブピクセルで測る
title_en: Measure dimensions from an image, below the pixel
category: 測る
ops: [measure_pos, measure_pairs, blob_label, blob_select]
examples: [poc_dimensional_inspection, poc_screw_thread_metrology, poc_calipers_under_illusion]
version: 0.2.3
---

# 画像から寸法をサブピクセルで測る

## できること

測定線に沿った輝度の勾配からエッジを**画素より細かく**求め、対になるエッジの間隔として寸法を返します。二値化して画素を数える方法と違い、しきい値の選び方で答えが動きません。

## What it does

Locate edges along a measurement line from the intensity gradient, at sub-pixel resolution, and read a dimension as the distance between paired edges. Unlike counting thresholded pixels, the answer does not move when the threshold does.

## 向くところ / 向かないところ

**向く**: 照明が安定していて、測る向きが分かっている工業計測。エッジが片側 3〜4 画素以上のなだらかさを持つとき。

**向かない**: 対象が測定線に対して大きく傾いている場合(投影された幅を測ってしまう)。テクスチャが細かくエッジが 1 画素で立つ場合は、サブピクセルの利得がほとんど出ません。★**再投影誤差や適合度が小さいことは、寸法が正しい証拠になりません** ——`poc_camera_calibration` がその分離を測っています。

★★**測定線の上に余計なエッジが載ると、測定器は黙って別の構造を対にします** —— 矢羽根つきのミュラー・リヤー錯視では、エッジが 2 本から 4 本に増えた結果、軸ではなく矢羽根のストローク(幅 5.7 px)が最良の対として返ります。`fuzzy_measure_pairing` に**想定幅を宣言する**と、間違った値を返す代わりに適合度が 0.9988 から **0.0225** へ落ち、「想定した構造は見つからない」という**見える拒否**になります。

★★**細い線には上下 2 つのエッジがあり、「線の位置」はどちらか(あるいは中心か)を言うまで定義されません**。`apply_metrology_model` には極性の指定が無いので、2 px 幅の線に直線を当てると採用点が上下のエッジを塊で行き来し、共線のはずの 2 区間が **0.450 度**ずれて返ります。両エッジを対にして中心を取ると 0.115 度まで下がります。

★★**探索半幅 `measure_length` を構造の幅以上に取ると、反対側の境界を掴みます** —— ただし**いつもではありません**。カフェウォール錯視で ずらし量 5 通り × 探索半幅 4 通りを全部測ると、外れるのは 20 通り中 4 通りだけでした。そして★**外したことは答えではなく残差に出ます**(角度は 0.1429 度 = 目には「ほぼ 0」、rms は 0.00 → 1.70)。**門は答えでなく `rms` に置いてください。**`poc_calipers_under_illusion` がこの全数を測っています。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

img = np.zeros((64, 128), float)
img[:, 40:88] = 1.0                      # 幅 48 px の帯

# 測定線は先に作る(中心・向き phi・長さ半幅・平均化幅・画像の形)
m = fs.ledger.gen_measure_rectangle2(32.0, 64.0, 0.0, 63.0, 3.0, img.shape)

edges = fs.ledger.measure_pos(img, m, sigma=1.0, threshold=0.1)
print([round(e["dist"], 3) for e in edges])            # [38.5, 86.5]

pair = fs.ledger.measure_pairs(img, m, sigma=1.0, threshold=0.1)[0]
print(round(pair["width"], 3))                         # 48.0(帯の幅ちょうど)
```

## 裏づけ

- op: `measure_pos` / `measure_pairs`(1-D 測定線)、`blob_label` / `blob_select`(領域を先に絞るとき)
- 例: [`poc_dimensional_inspection`](../../examples/poc_dimensional_inspection.py)、[`poc_screw_thread_metrology`](../../examples/poc_screw_thread_metrology.py)、[`poc_calipers_under_illusion`](../../examples/poc_calipers_under_illusion.py)(真値つきの錯視図で測定器そのものを採点する)
