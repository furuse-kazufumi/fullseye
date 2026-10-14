---
id: inner-diameter-in-mm
title: 円形部品の内径を mm まで測る
title_en: Inner diameter of a round part, all the way to millimetres
category: 測る
ops: [add_metrology_object_circle_measure, apply_metrology_model, mm_per_px_from_reference, pixel_to_world]
examples: [example_inner_diameter_mm, poc_dimensional_inspection, poc_real_coin_metrology]
version: 0.2.0
inputs: [image]
pipeline: [gaussian, otsu, area_center, create_metrology_model, add_metrology_object_circle_measure, apply_metrology_model, mm_per_px_from_reference, pixel_to_world]
alternatives: [gen_measure_arc, measure_pos, hx_fit_circle_contour, cv_hough_circles, hough_circle_trans, table_px_to_mm]
limits: 参照半径が実物から ±6 px(`measure_length` 既定)より外れると縁が見つからない(+6.5 px で fail、実測)。丸い縁は −σ²/ρ だけ小さく出る。`n` は円周 3 px に 1 点で頭打ち(それ以上は独立に効かない、実測)。
calibration: 既知径の的(リングゲージ・基準穴)を**同じ円 op で**測り `mm_per_px_from_reference(2·radius_px, known_mm)` → `pixel_to_world(2·radius_px, mm_per_px)`。公称倍率は使わない。
---

# 円形部品の内径を mm まで測る

## できること

穴・リング・ピンの内径を、粗い中心出し → サブピクセルの円当てはめ → 実寸校正 → mm、まで一気通貫で出します。文書だけを渡した AI は `measure_pairs` / `apply_metrology_model` で **px のまま止まっていた**(2026-09-15)ので、最後の 2 段(`mm_per_px_from_reference` / `pixel_to_world`)を op として型連鎖に置いてあります。

## What it does

Bore, ring and pin diameters end to end: a coarse centre, a sub-pixel circle fit on radial measurement lines, a calibration from a reference of known size, and the result in millimetres. The last two steps exist as typed operators because an assistant working from the notes alone stopped at pixels.

## 向くところ / 向かないところ

**向く**: 平面視で撮った穴・リング・ピン。縁が背景と十分なコントラストを持ち、参照半径を ±6 px 以内で置けるとき。

**向かない**: ★透視の効く斜め撮影(円が楕円に写る —— `add_metrology_object_ellipse_measure` へ)。★縁が面取り・丸みを持つ実物では「どこが縁か」が定義依存で、面取り 5 → 6 px で答えが 11.7 px 飛ぶ(`subpixel_measuring.md` §3)。★円周の一部が欠けていても当てはめは通る —— `rms` を必ず門にする。

## 推奨パイプライン

`gaussian` → `otsu` → `area_center` → `create_metrology_model` → `add_metrology_object_circle_measure` → `apply_metrology_model` → `mm_per_px_from_reference` → `pixel_to_world`

`gaussian` で雑音を落とし → `otsu` で穴を 2 値化 → `area_center` で粗い中心と面積(半径の初期値 √(面積/π))→ `create_metrology_model` に `add_metrology_object_circle_measure(row, col, radius, n)` で参照円を積み → `apply_metrology_model` で半径方向の測定線からサブピクセル円フィット(`params["radius"]`、`rms`)。校正は**同じ op**で既知径の的を測って `mm_per_px_from_reference` → `pixel_to_world(2 * radius, mm_per_px)`。

## 代替

円周の一部だけ測るなら `gen_measure_arc` → `measure_pos`。輪郭からの当てはめは `hx_fit_circle_contour`、粗探索は `cv_hough_circles` / `hough_circle_trans`(半径レンジが直書きで峰が立たないことがある —— `poc_real_coin_metrology`)。結果の表ごと mm にするなら `table_px_to_mm`。

## 限界

- 参照半径のずれが `measure_length`(既定 ±6 px)を超えると縁が見つからず `params=None`(実測: +5.5 px で通り、+6.5 px で fail)。粗い中心出しを先に置くのはそのため。
- 丸い縁は直径誤差 ≈ −σ²/ρ で必ず小さく出る(道具でなく光学側の偏り)。
- `n`(円周の標本数)は 2πR/n が **3 px** を切ると独立に効かなくなり(std·√n が一定でなくなる、実測)、n を増やしても散らばりは 1/√n で下がらない。既定 40 は R ≈ 20 px 向け。目安は [`add_metrology_object_circle_measure`](../ops/measure1d/model/add_metrology_object_circle_measure.md) のノートの表。
- 欠け(円周の 25 % 無し)は n を増やしても直らない(偏り −0.005 → −0.020 px)。欠けた側で縁が見つからないだけなら `rms` はむしろ下がり、境界で偽の縁を拾えば跳ねる —— rms だけでは見えないので `edge_points` の本数も門にする(`example_inner_diameter_mm`)。

## 実寸校正

既知径の的(リングゲージ・基準穴・コイン)を**同じ光学系・同じ作動距離・同じ円 op**で測り、`mm_per_px_from_reference(2 * radius_px, known_mm)` で mm/px を出す。`example_inner_diameter_mm` は 10.00 mm の的と 6.13 mm の被測定を同じ画素ピッチで描き、mm で真値に戻ること(および公称倍率で置いたときのずれ)を示す。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

yy, xx = np.mgrid[0:160, 0:160].astype(float)
img = np.where(np.hypot(yy - 80.4, xx - 79.6) < 40.0, 0.2, 0.8)   # 暗い穴 R=40 px
model = fs.ledger.create_metrology_model()
fs.ledger.add_metrology_object_circle_measure(model, 80.0, 80.0, 41.0, n=72)
r = fs.ledger.apply_metrology_model(model, img, measure_length=6.0)[0]
mm_per_px = fs.ledger.mm_per_px_from_reference(2 * 100.0, 10.0)     # 的 10 mm = 200 px
print(fs.ledger.pixel_to_world(2 * r["params"]["radius"], mm_per_px), "mm  rms", r["rms"])
```

## 裏づけ

- op: `add_metrology_object_circle_measure` / `apply_metrology_model`(円当てはめ)、`mm_per_px_from_reference` / `pixel_to_world`(実寸)
- 例: [`example_inner_diameter_mm`](../../examples/example_inner_diameter_mm.py)、[`poc_dimensional_inspection`](../../examples/poc_dimensional_inspection.py)、[`poc_real_coin_metrology`](../../examples/poc_real_coin_metrology.py)
