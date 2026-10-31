---
op: mesh_read_ply
dim: fileio
category: mesh
in: file
out: table
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mesh_read_ply — FILEIO `mesh` op

- **データ種**: `file` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_read_ply(data)` (実装を直接呼ぶなら `import fileio; fileio.mesh_read_ply(data)`、台帳から引くなら `opsfileio.get("mesh_read_ply")`)

## 使い方

ASCII / binary PLY を読み、頂点・面・色・法線・スカラー属性の ``table`` を返す。

未知の頂点スカラーは ``attributes`` に保つ。未知の要素、面の未知プロパティ、未知の list
property は名前を示して拒否する。呼び出し例: ``table = mesh_read_ply(ply_bytes)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`table` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [mesh_write_ply](mesh_write_ply.md)

## 同カテゴリ(`mesh`)

[mesh_write_ply](mesh_write_ply.md) · [mesh_write_stl](mesh_write_stl.md) · [mesh_read_stl](mesh_read_stl.md) · [mesh_write_obj](mesh_write_obj.md) · [mesh_read_obj](mesh_read_obj.md) · [mesh_write_off](mesh_write_off.md) · [mesh_read_off](mesh_read_off.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
