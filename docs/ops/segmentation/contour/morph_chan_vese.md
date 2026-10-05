---
op: morph_chan_vese
dim: segmentation
category: contour
in: image2d × mask
out: table
examples: [poc_active_contours]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# morph_chan_vese — SEGMENTATION `contour` op

- **データ種**: `image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.morph_chan_vese(image, init, *, n_iter: 'int' = 100, smoothing: 'int' = 1, lambda1: 'float' = 1.0, lambda2: 'float' = 1.0, phase: 'int' = 0, record_every: 'int' = 0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segcontour; segcontour.morph_chan_vese(image, init, *, n_iter: 'int' = 100, smoothing: 'int' = 1, lambda1: 'float' = 1.0, lambda2: 'float' = 1.0, phase: 'int' = 0, record_every: 'int' = 0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("morph_chan_vese")`)

## 使い方

形態学的 Chan–Vese(Márquez-Neila–Baumela–Álvarez 2014 の MorphACWE)。1 反復 = データ段 + 平滑段。

データ段: c1 = 内側の平均、c0 = 外側の平均、aux = |∇u|(λ1 (I − c1)² − λ2 (I − c0)²)、aux < 0 の画素を内側、
aux > 0 を外側に(|∇u| ≠ 0 = 境界の近くだけが動く)。平滑段: 曲率の作用素(SI∘IS と IS∘SI を交互)を ``smoothing`` 回。
``phase`` = 最初に使う作用素(0 = SI∘IS)。skimage の実装は交互の位相をモジュールの大域状態に持つので、
同じ入力でも直前の呼び出しで結果が変わりうる —— ここは呼び出しごとに ``phase`` から始める(決定的)。
当てはめのエネルギー E_fit = λ1 Σ_in (I − c1)² + λ2 Σ_out (I − c0)² を各段の前後で記録する。
門(厳密): c を固定した E_fit は画素ごとの和なので、データ段で反転した画素はどれも E_fit を下げ(または等しく)、
その後 c を平均に更新するとさらに下がる ⇒ データ段の前後で E_fit は単調非増加(``n_data_increase`` = 0)。
平滑段は E_fit を上げうる(``fit_after_smooth`` で実測)。
返り値: ``mask``、``fit_before_data`` / ``fit_after_data`` / ``fit_after_smooth``(反復ごと)、``n_data_increase``、
``history``、``n_iter``、``n_changed``(反復ごとに変わった画素数)。

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

[snake_evolve](snake_evolve.md) · [gvf_field](gvf_field.md) · [chan_vese_energy](chan_vese_energy.md) · [chan_vese_evolve](chan_vese_evolve.md) · [morph_geodesic_ac](morph_geodesic_ac.md) · [edge_stop_g](edge_stop_g.md) · [level_set_reinit](level_set_reinit.md) · [drle_evolve](drle_evolve.md)

---
*Provenance: segcontour.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
