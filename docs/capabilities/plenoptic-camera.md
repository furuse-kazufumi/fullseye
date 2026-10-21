---
id: plenoptic-camera
title: 処方から撮るプレノプティックカメラ
title_en: Prescription-based plenoptic camera
category: 描く
ops: [mla_surface, plenoptic_system, plenoptic_capture, plenoptic_mla_calibrate, plenoptic_decode, plenoptic_refocus_depth]
examples: [poc_plenoptic_camera]
version: 0.7.0
inputs: [table, image2d, lightfield]
pipeline: [mla_surface, plenoptic_system, plenoptic_capture, plenoptic_mla_calibrate, plenoptic_decode, plenoptic_refocus_depth]
alternatives: [lf_from_mla, lf_refocus, lf_depth_from_focus, trace_sensor_rays]
limits: 幾何光学のみで回折と画素間クロストークは扱わない。
calibration: 一様な白色面で MLA 格子を校正し、距離既知の三平面で深度を確認する。
---

# 処方から撮るプレノプティックカメラ

## できること

主レンズ処方、マイクロレンズアレイ、センサを組み合わせ、一回の撮影から生のマイクロ画像と四次元ライトフィールドを作る。出力は既存のライトフィールド処理へ直接渡せる。

## What it does

It traces a prescription, microlens array and sensor, then decodes the raw frame to the repository's `(V,U,H,W)` light-field array for direct refocus and depth processing.

## 向くところ / 向かないところ

再合焦、三次元検査、F ナンバー整合の設計検討に向く。回折限界、センサの電気的クロストーク、実機固有の迷光評価には向かない。

## 最初の 1 本

```python
import numpy as np
import lightfield
import plenoptic

truth, _ = lightfield.lf_synthesize((0.5,), (5, 5), (16, 20), seed=17,
                                     occlusion=False)
raw = lightfield.lf_to_mla(truth)
calibration = {"origin_px": np.array([2.0, 2.0]),
               "basis_px": np.array([[5.0, 0.0], [0.0, 5.0]]),
               "white_image": np.ones_like(raw)}
decoded = plenoptic.plenoptic_decode(raw, calibration, angular=(5, 5))
image = lightfield.lf_refocus(decoded, slope=0.5)
sweep = np.linspace(-1.0, 1.0, 9)
slopes, confidence = lightfield.lf_depth_from_focus(decoded, sweep)
print(image.shape, slopes.shape, confidence.shape)
```

## 推奨パイプライン

`mla_surface` → `plenoptic_system` → `plenoptic_capture` → `plenoptic_mla_calibrate` → `plenoptic_decode` → `plenoptic_refocus_depth`。

## 代替

既存の生画像には `lf_from_mla`、再合焦には `lf_refocus`、焦点深度には `lf_depth_from_focus` を使う。

## 限界

幾何光学モデルであり、回折と画素間クロストークは扱わない。

## 実寸校正

一様な白色面から MLA のピッチ、回転、原点を校正し、距離既知の三平面でスロープからメートルへの変換を確認する。

## 生画像が実機らしく見える条件

プレノプティック生画像には、円盤状マイクロ像の格子、円盤間の暗い隅、各円盤内で反転・移動する場面断片が現れ、復号後の EPI には視差に応じた斜線が現れる。この PoC の白色面では暗い隅が 21.33 %（正方格子の閉形式 `1 - π/4` は 21.46 %）、円盤端の輝度比が `9.92e-6`、最強の非直流ピークが `1/15 = 0.06667 cycle/pixel` だった。EPI の点像移動は 1 view あたり 0.6 px である。開口を除く探針では暗い隅が 0 % となり、この門を通らない。

The raw-frame resemblance is measured rather than asserted: a lattice of
microimage discs has dark inter-disc corners and shifted, inverted scene
fragments inside the discs, while decoding produces slanted disparity lines in
the EPI.  The white-frame measurements are 21.33% dark corners (closed form
`1 - pi/4 = 21.46%`), a `9.92e-6` rim/core intensity ratio, and the strongest
off-centre spectral peak at `1/15 = 0.06667 cycle/pixel`; the EPI track moves
0.6 px per view.  Removing the aperture gives 0% dark corners and fails the gate.
