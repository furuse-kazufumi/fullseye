---
op: e57_write
dim: fileio
category: e57
in: table
out: any
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# e57_write — FILEIO `e57` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.e57_write(table)` (実装を直接呼ぶなら `import fileio; fileio.e57_write(table)`、台帳から引くなら `opsfileio.get("e57_write")`)

## 使い方

座標・強度・色・pose を持つ点群 ``table`` を ASTM E57 の ``bytes`` に書く。

``pye57`` は optional。未導入なら導入コマンドを含む ``ImportError`` で閉じる。
呼び出し例: ``payload = e57_write({'points': points, 'pose': pose})``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`any` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [table_read_csv](../table/table_read_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_write_stl](../mesh/mesh_write_stl.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_write_obj](../mesh/mesh_write_obj.md) · [mesh_read_obj](../mesh/mesh_read_obj.md)

## 同カテゴリ(`e57`)

[e57_read](e57_read.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
