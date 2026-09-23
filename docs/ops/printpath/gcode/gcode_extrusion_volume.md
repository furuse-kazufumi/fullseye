---
op: gcode_extrusion_volume
dim: printpath
category: gcode
in: table
out: measurement
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gcode_extrusion_volume — PRINTPATH `gcode` op

- **データ種**: `table` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.gcode_extrusion_volume(table: 'Any', filament_mm: 'float' = 1.75) -> 'float'` (実装を直接呼ぶなら `import printpath; printpath.gcode_extrusion_volume(table: 'Any', filament_mm: 'float' = 1.75) -> 'float'`、台帳から引くなら `opsprintpath.get("gcode_extrusion_volume")`)

## 使い方

押し出したフィラメントの体積 [mm³] = Σe × π (d / 2)²(``measurement``)。重さは密度 × 体積(PLA ≈ 1.24 g/cm³)。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`gcode`)

[gcode_read](gcode_read.md) · [gcode_write](gcode_write.md) · [gcode_time_estimate](gcode_time_estimate.md) · [gcode_layer_image](gcode_layer_image.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
