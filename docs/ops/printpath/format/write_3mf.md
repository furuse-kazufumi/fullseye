---
op: write_3mf
dim: printpath
category: format
in: text × mesh
out: text
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# write_3mf — PRINTPATH `format` op

- **データ種**: `text × mesh` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.write_3mf(path: 'str', mesh: 'Any') -> 'str'` (実装を直接呼ぶなら `import printpath; printpath.write_3mf(path: 'str', mesh: 'Any') -> 'str'`、台帳から引くなら `opsprintpath.get("write_3mf")`)

## 使い方

三角形メッシュを 3MF(最小構成: ``[Content_Types].xml`` / ``_rels/.rels`` / ``3D/3dmodel.model``、単位 mm)に書く。返りはパス(``text``)。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`text` を入力に取れる)

[gcode_read](../gcode/gcode_read.md) · [gcode_write](../gcode/gcode_write.md) · [read_3mf](read_3mf.md)

## 同カテゴリ(`format`)

[read_3mf](read_3mf.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
