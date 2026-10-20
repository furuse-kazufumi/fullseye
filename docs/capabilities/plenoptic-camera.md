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
decoded = plenoptic_decode(raw, calibration, angular=(15, 15))
image = lightfield.lf_refocus(decoded, slope=0.5)
slopes, confidence = lightfield.lf_depth_from_focus(decoded, sweep)
```

## 推奨パイプライン

`mla_surface` → `plenoptic_system` → `plenoptic_capture` → `plenoptic_mla_calibrate` → `plenoptic_decode` → `plenoptic_refocus_depth`。

## 代替

既存の生画像には `lf_from_mla`、再合焦には `lf_refocus`、焦点深度には `lf_depth_from_focus` を使う。

## 限界

幾何光学モデルであり、回折と画素間クロストークは扱わない。

## 実寸校正

一様な白色面から MLA のピッチ、回転、原点を校正し、距離既知の三平面でスロープからメートルへの変換を確認する。
