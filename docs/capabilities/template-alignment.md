---
id: template-alignment
title: 位置決め(テンプレート照合で測定線を追従させる)
title_en: Locate a part by template matching and move the measurement model with it
category: 見つける
ops: [ncc_locate, shape_locate, align_metrology_model, translate_measure]
examples: [poc_template_tracking, gallery2d_contour_measure, poc_search_sweep_width]
version: 0.2.0
inputs: [image]
pipeline: [gaussian, ncc_locate, shape_locate, create_metrology_model, add_metrology_object_circle_measure, align_metrology_model, apply_metrology_model]
alternatives: [edges_sub_pix, fit_line_contours, translate_measure, gen_measure_rectangle2, rotate_image, affine_trans_image]
limits: `ncc_locate` は平行移動だけ、`shape_locate` は 30° 刻みの回転(それ以外の角度は最寄りに丸まる)。スコアが高いことは位置が正しい証拠にならない(繰り返し構造で 1.00 のまま外す —— `align-and-stack` の `frame_align` と同じ形)。`align_metrology_model` は平行移動だけで回転・スケールは扱わない。
calibration: 位置決め自体は px で閉じる。追従させた測定モデルの結果を mm にするときは `table_px_to_mm`(mm/px は `mm_per_px_from_reference`)。
---

# 位置決め(テンプレート照合で測定線を追従させる)

## できること

ワークが画面内で動いても同じ場所を測るために、テンプレート照合で位置(と 30° 刻みの向き)を出し、そのずれを**測定モデルに反映**してから当てはめます。照合 → 位置決め → 計測、が型で繋がります。

## What it does

Find the part with template matching (translation, or rotation in 30° steps), then shift the measurement model by that offset before applying it — so the same feature is measured wherever the part landed.

## 向くところ / 向かないところ

**向く**: 据え置きの検査機で、ワークが平行移動(+ 粗い回転)だけする場面。テンプレートに**構造がある**とき(平坦なテンプレートはスコア 0)。

**向かない**: ★30° 未満の回転や倍率変化。★繰り返し模様(格子・網点)—— NCC の最大は複数の同じ峰を持ち、スコアだけでは区別できない。★`ops.set_match_template` は**同じスレッド**で設定する(未設定なら 0 スコアの配列を返す fail-safe)。

## 推奨パイプライン

`gaussian` → `ncc_locate` → `shape_locate` → `create_metrology_model` → `add_metrology_object_circle_measure` → `align_metrology_model` → `apply_metrology_model`

`gaussian` で雑音を落とし → `ncc_locate` で `[score, row, col]`(回転が要るなら `shape_locate` で `[score, row, col, angle]`)→ 基準位置との差 (drow, dcol) を取り → 基準画像で作った `create_metrology_model` + `add_metrology_object_*` を `align_metrology_model(model, drow, dcol)` で移し → `apply_metrology_model`。測定線 1 本だけなら `translate_measure`。

## 代替

縁で位置決めするなら `edges_sub_pix` → `fit_line_contours`(向きと交点)。測定線を 1 本だけ動かすなら `translate_measure`。回転が大きいなら `rotate_image` / `affine_trans_image` で画像側を戻してから測る(補間で縁がなまる分は測定に乗る)。

## 限界

- `ncc_locate` の位置は整数画素(テンプレート中心)。サブピクセルの位置決めが要るなら、その後の計測モデルの当てはめ(`apply_metrology_model` の `params`)を位置として使う。
- `shape_locate` の回転は 30° 刻み。
- `align_metrology_model` は平行移動のみ。傾いたワークは参照形状の法線が実物からずれ、`measure_length` の外に出る。
- スコアの高さは正しさの証拠ではない(`poc_template_tracking` / `align-and-stack`)。

## 実寸校正

位置決めは px で閉じる。追従させた測定結果を mm にするなら `mm_per_px_from_reference` → `table_px_to_mm`(倍率が一定の平面視が前提)。

## 最初の 1 本

```python
import fullseye as fs
import ops
import numpy as np

yy, xx = np.mgrid[0:96, 0:96].astype(float)
ref = np.where(np.hypot(yy - 40, xx - 40) < 8, 1.0, 0.2)        # 基準画像
img = np.roll(ref, (7, -5), axis=(0, 1))                        # 動いたワーク
ops.set_match_template(ref[28:52, 28:52].copy())                 # 同じスレッドで設定
score, row, col = fs.apply(img, "ncc_locate", 0.5, 0.5)
drow, dcol = row - 40.0, col - 40.0
model = fs.ledger.create_metrology_model()
fs.ledger.add_metrology_object_circle_measure(model, 40.0, 40.0, 8.0, n=40)
moved = fs.ledger.align_metrology_model(model, drow, dcol)
print(fs.ledger.apply_metrology_model(moved, img)[0]["params"])   # 中心 (47, 35) 付近
```

## 裏づけ

- op: `ncc_locate` / `shape_locate`(照合)、`align_metrology_model` / `translate_measure`(追従)
- 例: [`poc_template_tracking`](../../examples/poc_template_tracking.py)、[`gallery2d_contour_measure`](../../examples/gallery2d_contour_measure.py)、[`poc_search_sweep_width`](../../examples/poc_search_sweep_width.py)
