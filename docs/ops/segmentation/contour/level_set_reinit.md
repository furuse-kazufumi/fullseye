---
op: level_set_reinit
dim: segmentation
category: contour
in: mask
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# level_set_reinit — SEGMENTATION `contour` op

- **データ種**: `mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.level_set_reinit(phi, *, method: 'str' = 'sussman', n_iter: 'int' = 100, dt: 'float' = 0.5, band: 'float' = 3.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.level_set_reinit(phi, *, method: 'str' = 'sussman', n_iter: 'int' = 100, dt: 'float' = 0.5, band: 'float' = 3.0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("level_set_reinit")`)

## 使い方

φ(内側 φ < 0)を同じ零等高線の符号付き距離に直す。

``method="sussman"`` = φ_τ + S(φ0)(|∇φ| − 1) = 0(Sussman–Smereka–Osher 1994)を Godunov の風上差分で
``n_iter`` 回(刻み ``dt`` ≤ 0.5)。界面に接する格子点(4 近傍で符号が変わる)は Russo–Smereka 2000 の subcell fix:
D = φ0 / Δφ0(Δφ0 = 中心差分の勾配の大きさと片側差分の最大)へ緩和させ、零等高線を動かさない。
``method="edt"`` = マスク φ < 0 から距離変換で作る符号付き距離(第 2 実装。零等高線は画素の中心の中間に量子化され、
最大で半画素動く)。bool のマスクを渡すと edt の符号付き距離を φ0 として使う。
返り値: ``phi``、``grad``(|φ| ≤ band での |∇φ| の 10/50/90 % 点と画素数)、``grad_before``(同、入力)、
``zero_hausdorff``(前後の零等高線の Hausdorff、画素)、``method``、``n_iter``。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [active_contours_and_level_sets](../guides/active_contours_and_level_sets.md) — 変分・動的輪郭とレベルセット — どの輪郭がどこで止まり、何を保証するか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_active_contours](../../../../examples/poc_active_contours.py) — `py -3.11 examples/poc_active_contours.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`contour`)

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
