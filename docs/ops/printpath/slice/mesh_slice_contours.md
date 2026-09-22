---
op: mesh_slice_contours
dim: printpath
category: slice
in: mesh
out: table
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# mesh_slice_contours — PRINTPATH `slice` op

- **データ種**: `mesh` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_slice_contours(mesh: 'Any', z: 'float', tol: 'float' = 1e-06) -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import printpath; printpath.mesh_slice_contours(mesh: 'Any', z: 'float', tol: 'float' = 1e-06) -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsprintpath.get("mesh_slice_contours")`)

## 使い方

三角形メッシュを平面 ``z`` で切った**輪郭の表** ``table``: 列 ``ring``(輪の番号)、``x``、``y``(mm)。

各三角形と平面の交差を線分にし、三角形の法線で向きを付けて(外輪郭は反時計回り、穴は時計回り)、端点を
突き合わせて閉じた輪(閉じなければ開いた鎖)に繋ぐ(古典のスライサ)。輪の符号つき面積で中身と穴が分かる。
頂点がちょうど平面に乗るときは ``tol`` だけ持ち上げて退化を避ける。平面が形に触れなければ ValueError
(空の層は「無い」と言う)。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[gcode_write](../gcode/gcode_write.md) · [gcode_extrusion_volume](../gcode/gcode_extrusion_volume.md) · [gcode_time_estimate](../gcode/gcode_time_estimate.md) · [gcode_layer_image](../gcode/gcode_layer_image.md) · [contours_to_gcode](contours_to_gcode.md)

## 同カテゴリ(`slice`)

[mesh_slice_stack](mesh_slice_stack.md) · [contours_to_gcode](contours_to_gcode.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
