---
op: mesh_write_obj
dim: fileio
category: mesh
in: mesh
out: text
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mesh_write_obj — FILEIO `mesh` op

- **データ種**: `mesh` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_write_obj(mesh)` (実装を直接呼ぶなら `import fileio; fileio.mesh_write_obj(mesh)`、台帳から引くなら `opsfileio.get("mesh_write_obj")`)

## 使い方

三角形 mesh を ``v`` / ``vn`` / ``f`` を持つ Wavefront OBJ 文字列に書く(``text``)。

面ごとの法線を ``vn`` として書く。material/texture は書かない。呼び出し例:
``text = mesh_write_obj((vertices, faces))``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`text` を入力に取れる)

[table_read_csv](../table/table_read_csv.md) · [mesh_read_obj](mesh_read_obj.md) · [mesh_read_off](mesh_read_off.md) · [points_read_xyz](../points/points_read_xyz.md)

## 同カテゴリ(`mesh`)

[mesh_write_ply](mesh_write_ply.md) · [mesh_read_ply](mesh_read_ply.md) · [mesh_write_stl](mesh_write_stl.md) · [mesh_read_stl](mesh_read_stl.md) · [mesh_read_obj](mesh_read_obj.md) · [mesh_write_off](mesh_write_off.md) · [mesh_read_off](mesh_read_off.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
