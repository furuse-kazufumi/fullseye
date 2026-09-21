---
op: gcode_layer_image
dim: printpath
category: gcode
in: table
out: image2d
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# gcode_layer_image — PRINTPATH `gcode` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.gcode_layer_image(table: 'Any', layer: 'int', px_per_mm: 'float' = 10.0, line_width_mm: 'float' = 0.4, bounds=None, travel: 'bool' = False) -> 'np.ndarray'` (実装を直接呼ぶなら `import printpath; printpath.gcode_layer_image(table: 'Any', layer: 'int', px_per_mm: 'float' = 10.0, line_width_mm: 'float' = 0.4, bounds=None, travel: 'bool' = False) -> 'np.ndarray'`、台帳から引くなら `opsprintpath.get("gcode_layer_image")`)

## 使い方

1 層の経路を**線幅つきのラスタ** ``image2d``(0 / 1、y 下向き = 行)に描く。

押し出しのある線分だけを ``line_width_mm`` の太さで塗る(``travel=True`` なら移動も細線で)。画素は ``px_per_mm``、
範囲は ``bounds=(xmin, ymin, xmax, ymax)`` mm(無ければ表全体 + 2 mm の余白 —— 層をまたいで同じ範囲にしたければ
渡す)。これが「この層はこう見えるはず」の期待像で、カメラの層画像と ``print_layer_defect_map`` で比べる。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[print_layer_defect_map](../inspect/print_layer_defect_map.md)

## 同カテゴリ(`gcode`)

[gcode_read](gcode_read.md) · [gcode_write](gcode_write.md) · [gcode_extrusion_volume](gcode_extrusion_volume.md) · [gcode_time_estimate](gcode_time_estimate.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
