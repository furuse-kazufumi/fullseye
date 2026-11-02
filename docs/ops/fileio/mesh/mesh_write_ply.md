---
op: mesh_write_ply
dim: fileio
category: mesh
in: table
out: any
gpu: なし
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mesh_write_ply — FILEIO `mesh` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_write_ply(table, *, binary)` (実装を直接呼ぶなら `import fileio; fileio.mesh_write_ply(table, *, binary)`、台帳から引くなら `opsfileio.get("mesh_write_ply")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

頂点・面・色・法線・任意スカラー属性を ASCII / little-endian PLY に書く(``text`` / ``bytes``)。

``table`` は ``vertices`` と任意の ``faces/colors/normals/attributes`` を持つ。``binary=False`` は
ASCII 文字列、``binary=True`` は binary_little_endian bytes。色は最近傍整数へ丸める。
呼び出し例: ``mesh_write_ply({"vertices": v, "faces": f}, binary=True)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`any` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [table_read_csv](../table/table_read_csv.md) · [mesh_read_ply](mesh_read_ply.md) · [mesh_write_stl](mesh_write_stl.md) · [mesh_read_stl](mesh_read_stl.md) · [mesh_write_obj](mesh_write_obj.md) · [mesh_read_obj](mesh_read_obj.md) · [mesh_write_off](mesh_write_off.md)

## 同カテゴリ(`mesh`)

[mesh_read_ply](mesh_read_ply.md) · [mesh_write_stl](mesh_write_stl.md) · [mesh_read_stl](mesh_read_stl.md) · [mesh_write_obj](mesh_write_obj.md) · [mesh_read_obj](mesh_read_obj.md) · [mesh_write_off](mesh_write_off.md) · [mesh_read_off](mesh_read_off.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
