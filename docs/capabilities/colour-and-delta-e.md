---
id: colour-and-delta-e
title: 色を測る(XYZ / Lab / 色差)
title_en: Measure colour (XYZ / Lab / colour difference)
category: 光と色
ops: [rgb_to_lab, xyz_to_lab, delta_e_2000, cie_xyz_from_wavelength]
examples: [poc_white_balance, poc_pigment_unmixing]
version: 0.1.11
inputs: [rgbimage]
pipeline: [rgb_to_lab, delta_e_2000]
alternatives: [rgb_to_xyz, xyz_to_lab, delta_e_76, delta_e_map, cie_xyz_from_wavelength, srgb_to_linear]
limits: 符号化 RGB を線形として扱うと全部ずれる。白色点(D50 / D65)の違う Lab を直接比べない。色恒常性に勝ち続ける手法は無い(`poc_white_balance`)。
calibration: 画素 → mm は関係しない。校正は**線形化**(`srgb_to_linear`)と**白色点**で、色差 ΔE は無次元。
---

# 色を測る(XYZ / Lab / 色差)

## できること

分光反射率または RGB から CIE XYZ・Lab を求め、CIE76 / CIEDE2000 の色差を出します。色差は画像全体の地図としても返せます。

## What it does

From spectral reflectance or RGB, compute CIE XYZ and Lab, then colour differences under CIE76 or CIEDE2000. The difference can also be returned as a per-pixel map.

## 向くところ / 向かないところ

**向く**: 塗装・印刷・繊維・食品の色合わせ、経時変化の追跡。

**向かない**: ★**符号化された RGB を線形として扱う**と全部ずれます。白色点(D50 / D65)の違う Lab を直接比べるのも同じ種類の誤りです。★色恒常性には**勝ち続ける手法がありません** —— どの手法にも効く条件があることを`poc_white_balance` が測っています。

## 最初の 1 本

```python
import fullseye as fs

lab_a = fs.ledger.rgb_to_lab((0.80, 0.20, 0.20))
lab_b = fs.ledger.rgb_to_lab((0.78, 0.24, 0.19))
print('dE2000 =', fs.ledger.delta_e_2000(lab_a, lab_b))
```

## 推奨パイプライン

`rgb_to_lab` → `delta_e_2000`

`rgb_to_lab` で基準と被測定の RGB(線形)を Lab に → `delta_e_2000` で画素ごとの色差地図(または 1 色ずつ)。

## 代替

XYZ を経由して白色点を扱うなら `rgb_to_xyz` → `xyz_to_lab`。CIE76 なら `delta_e_76`、RGB から直接なら `delta_e_map`。分光からは `cie_xyz_from_wavelength`。

## 限界

符号化 RGB を線形として扱うと全部ずれる。白色点(D50 / D65)の違う Lab を直接比べない。色恒常性に勝ち続ける手法は無い(`poc_white_balance`)。

## 実寸校正

画素 → mm は関係しない。校正は**線形化**(`srgb_to_linear`)と**白色点**で、色差 ΔE は無次元。

## 裏づけ

- op: `rgb_to_lab` / `xyz_to_lab` / `delta_e_2000` / `cie_xyz_from_wavelength`
- 例: [`poc_white_balance`](../../examples/poc_white_balance.py)、[`poc_pigment_unmixing`](../../examples/poc_pigment_unmixing.py)
