---
op: contours_to_gcode
dim: printpath
category: slice
in: table
out: table
examples: [poc_one_stroke_epicycles, poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# contours_to_gcode — PRINTPATH `slice` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contours_to_gcode(contours: 'Any', z: 'float', layer: 'int' = 0, layer_mm: 'float' = 0.2, line_width_mm: 'float' = 0.4, filament_mm: 'float' = 1.75, feed_mm_min: 'float' = 1800.0) -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import printpath; printpath.contours_to_gcode(contours: 'Any', z: 'float', layer: 'int' = 0, layer_mm: 'float' = 0.2, line_width_mm: 'float' = 0.4, filament_mm: 'float' = 1.75, feed_mm_min: 'float' = 1800.0) -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsprintpath.get("contours_to_gcode")`)

## 使い方

輪郭(``mesh_slice_contours`` の表)を**周回する経路の表**に(``gcode_read`` と同じ列)。

最小のスライサ: 各輪を順に一周し、押し出し量は ``線分長 × 線幅 × 層厚 / フィラメント断面積``。輪と輪の間は
移動(e = 0)。真値つきの合成 G-code を作るための道具で、インフィルやリトラクトは持たない。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`
- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[gcode_write](../gcode/gcode_write.md) · [gcode_extrusion_volume](../gcode/gcode_extrusion_volume.md) · [gcode_time_estimate](../gcode/gcode_time_estimate.md) · [gcode_layer_image](../gcode/gcode_layer_image.md)

## 同カテゴリ(`slice`)

[mesh_slice_contours](mesh_slice_contours.md) · [mesh_slice_stack](mesh_slice_stack.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
