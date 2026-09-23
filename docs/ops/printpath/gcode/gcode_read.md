---
op: gcode_read
dim: printpath
category: gcode
in: text
out: table
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gcode_read — PRINTPATH `gcode` op

- **データ種**: `text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gcode_read(path: 'str', layer_from: 'str' = 'auto') -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import printpath; printpath.gcode_read(path: 'str', layer_from: 'str' = 'auto') -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsprintpath.get("gcode_read")`)

## 使い方

G-code(RepRap / Marlin 系)を**線分の表** ``table`` に読む: 列 ``x0 y0 z0 x1 y1 z1``(mm)、``e``(その線分で
押し出したフィラメント長 mm、移動だけなら 0)、``f``(送り mm/min)、``layer``(層番号)。

解釈するのは G0 / G1(直線移動)、G90 / G91(座標の絶対 / 相対)、M82 / M83(E の絶対 / 相対)、G92(座標の
リセット)、G20 / G21(インチ / mm)、``;`` コメント。円弧 G2 / G3 は**扱わない**(黙って直線にせず ValueError ——
スライサで直線に展開して出力すること)。層は ``layer_from="tag"`` なら ``;LAYER:n`` のコメント、``"z"`` なら押し出し
を伴う Z の増加で切る。``"auto"`` はタグがあればタグ、無ければ Z。座標が一度も与えられないまま押し出す行は
ValueError(方言の穴を黙って 0 で埋めない)。

>>> t = gcode_read("part.gcode")
>>> t["e"].sum()                                       # 押し出したフィラメントの総長 [mm]

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[gcode_write](gcode_write.md) · [gcode_extrusion_volume](gcode_extrusion_volume.md) · [gcode_time_estimate](gcode_time_estimate.md) · [gcode_layer_image](gcode_layer_image.md) · [contours_to_gcode](../slice/contours_to_gcode.md)

## 同カテゴリ(`gcode`)

[gcode_write](gcode_write.md) · [gcode_extrusion_volume](gcode_extrusion_volume.md) · [gcode_time_estimate](gcode_time_estimate.md) · [gcode_layer_image](gcode_layer_image.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
