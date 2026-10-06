---
op: curvature_flow
dim: segmentation
category: contour
in: mask
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# curvature_flow — SEGMENTATION `contour` op

- **データ種**: `mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.curvature_flow(phi, *, t_end: 'float' = 50.0, dt: 'float' = 0.2, eta: 'float' = 1e-08, record_every: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.curvature_flow(phi, *, t_end: 'float' = 50.0, dt: 'float' = 0.2, eta: 'float' = 1e-08, record_every: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("curvature_flow")`)

## 使い方

平均曲率流(曲線短縮流)のレベルセット版 φ_t = |∇φ| div(∇φ/|∇φ|)(φ < 0 が内側、凸な所から縮む)。

陽的な中心差分: φ_t = (φ_xx φ_y² − 2 φ_x φ_y φ_xy + φ_yy φ_x²) / (φ_x² + φ_y² + η)、刻み dt ≤ 0.25(安定条件)。
``phi`` = φ か bool のマスク(符号付き距離に直す)。面積は各刻みで ``clip(0.5 − φ/|∇φ|, 0, 1)`` の和。
門: 単純閉曲線の囲む面積は dA/dt = −∮ κ ds = −2π(回転数 1、凸でなくても)。円なら r(t)² = r0² − 2t。
返り値: ``phi``、``mask``、``times``、``areas``、``area_rate``(面積 vs 時間の最小二乗の傾き)、``area_rate_theory`` = −2π、
``history``(record_every 刻みごとのマスク)、``n_steps``。

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

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_chan_vese](morph_chan_vese.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
