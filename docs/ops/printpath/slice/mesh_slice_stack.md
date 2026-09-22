---
op: mesh_slice_stack
dim: printpath
category: slice
in: mesh
out: voxel
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# mesh_slice_stack — PRINTPATH `slice` op

- **データ種**: `mesh` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_slice_stack(mesh: 'Any', layer_mm: 'float' = 0.2, px_per_mm: 'float' = 10.0, bounds=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import printpath; printpath.mesh_slice_stack(mesh: 'Any', layer_mm: 'float' = 0.2, px_per_mm: 'float' = 10.0, bounds=None) -> 'np.ndarray'`、台帳から引くなら `opsprintpath.get("mesh_slice_stack")`)

## 使い方

メッシュを ``layer_mm`` 刻みで切った**層マスクの積み** ``voxel`` (Z, Y, X)(0 / 1、Z は下から)。

各層は ``mesh_slice_contours`` の輪郭を **nonzero winding** で塗る(外向き法線の輪は中身、内向き法線 = 穴の輪は
引く。穴だけが残る層は空)。メッシュの面の向きが揃っていることが前提(STL / 3MF の規約)。``bounds`` は x–y の
範囲(mm)、無ければメッシュ全体 + 2 mm。形に触れない層(上下の端)は 0 のまま。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

—

## 同カテゴリ(`slice`)

[mesh_slice_contours](mesh_slice_contours.md) · [contours_to_gcode](contours_to_gcode.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
