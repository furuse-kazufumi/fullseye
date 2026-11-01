---
op: mesh_read_off
dim: fileio
category: mesh
in: text
out: mesh
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mesh_read_off — FILEIO `mesh` op

- **データ種**: `text` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_read_off(data)` (実装を直接呼ぶなら `import fileio; fileio.mesh_read_off(data)`、台帳から引くなら `opsfileio.get("mesh_read_off")`)

## 使い方

Geomview OFF を読み、三角形 ``mesh`` `(vertices, faces)` を返す。

宣言した頂点・面数とデータ行数、全添字を検査する。呼び出し例: ``mesh = mesh_read_off(off_text)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_read_ply](mesh_read_ply.md) · [mesh_write_stl](mesh_write_stl.md) · [mesh_read_stl](mesh_read_stl.md) · [mesh_write_obj](mesh_write_obj.md) · [mesh_write_off](mesh_write_off.md) · [e57_read](../e57/e57_read.md) · [archive_probe](../archive/archive_probe.md) · [archive_list](../archive/archive_list.md)

## 同カテゴリ(`mesh`)

[mesh_write_ply](mesh_write_ply.md) · [mesh_read_ply](mesh_read_ply.md) · [mesh_write_stl](mesh_write_stl.md) · [mesh_read_stl](mesh_read_stl.md) · [mesh_write_obj](mesh_write_obj.md) · [mesh_read_obj](mesh_read_obj.md) · [mesh_write_off](mesh_write_off.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
