---
op: gcode_write
dim: printpath
category: gcode
in: table × text
out: text
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# gcode_write — PRINTPATH `gcode` op

- **データ種**: `table × text` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.gcode_write(table: 'Any', path: 'str', layer_tags: 'bool' = True) -> 'str'` (実装を直接呼ぶなら `import printpath; printpath.gcode_write(table: 'Any', path: 'str', layer_tags: 'bool' = True) -> 'str'`、台帳から引くなら `opsprintpath.get("gcode_write")`)

## 使い方

線分の表を G-code(G21 / G90 / M82、G1 の絶対座標と絶対 E)に書く。返りは書いたパス(``text``)。

``gcode_read`` と往復できる(層は ``;LAYER:n`` で書く)。移動だけの線分は E を進めない。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`text` を入力に取れる)

[gcode_read](gcode_read.md) · [read_3mf](../format/read_3mf.md) · [write_3mf](../format/write_3mf.md)

## 同カテゴリ(`gcode`)

[gcode_read](gcode_read.md) · [gcode_extrusion_volume](gcode_extrusion_volume.md) · [gcode_time_estimate](gcode_time_estimate.md) · [gcode_layer_image](gcode_layer_image.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
