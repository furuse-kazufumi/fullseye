---
op: read_3mf
dim: printpath
category: format
in: text
out: mesh
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# read_3mf — PRINTPATH `format` op

- **データ種**: `text` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.read_3mf(path: 'str') -> 'tuple[np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import printpath; printpath.read_3mf(path: 'str') -> 'tuple[np.ndarray, np.ndarray]'`、台帳から引くなら `opsprintpath.get("read_3mf")`)

## 使い方

3MF(zip の中の ``3D/3dmodel.model``、3MF Core Specification)を三角形メッシュ ``mesh`` = (V, F) に読む。

複数の ``<object>`` は頂点を連結して 1 つのメッシュに(``<build>`` の変換行列は 3×4 の ``transform`` を適用)。
単位は ``<model unit>``(既定 millimeter、inch / centimeter / meter / micron は mm に換算)。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_slice_contours](../slice/mesh_slice_contours.md) · [mesh_slice_stack](../slice/mesh_slice_stack.md) · [write_3mf](write_3mf.md)

## 同カテゴリ(`format`)

[write_3mf](write_3mf.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
