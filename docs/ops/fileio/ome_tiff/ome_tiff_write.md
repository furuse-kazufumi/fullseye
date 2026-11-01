---
op: ome_tiff_write
dim: fileio
category: ome_tiff
in: any
out: any
examples: [fileio_scientific_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# ome_tiff_write — FILEIO `ome_tiff` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.ome_tiff_write(stack, *, meta)` (実装を直接呼ぶなら `import fileio; fileio.ome_tiff_write(stack, *, meta)`、台帳から引くなら `opsfileio.get("ome_tiff_write")`)

## 使い方

TCZYX 多次元配列と物理サイズ・チャネル名を OME-TIFF の ``bytes`` にする。

``meta['axes']`` は TCZYX の部分列で YX 終端。X/Y(および Z 軸があれば Z)の
``physical_size_*`` と ``*_unit``、C 軸があれば ``channel_names`` を必須とする。
呼び出し例: ``ome_tiff_write(stack, meta={"axes": "CZYX", ...})``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_scientific_roundtrip](../../../../examples/fileio_scientific_roundtrip.py) — `py -3.11 examples/fileio_scientific_roundtrip.py`

## 型が繋がる次の op(`any` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [table_read_csv](../table/table_read_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_write_stl](../mesh/mesh_write_stl.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_write_obj](../mesh/mesh_write_obj.md) · [mesh_read_obj](../mesh/mesh_read_obj.md)

## 同カテゴリ(`ome_tiff`)

[ome_tiff_read](ome_tiff_read.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
