---
op: nrrd_write
dim: fileio
category: nrrd
in: any
out: any
examples: [fileio_scientific_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# nrrd_write — FILEIO `nrrd` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.nrrd_write(array, *, meta, encoding)` (実装を直接呼ぶなら `import fileio; fileio.nrrd_write(array, *, meta, encoding)`、台帳から引くなら `opsfileio.get("nrrd_write")`)

## 使い方

多次元配列と ``space directions`` を raw/gzip NRRD の ``bytes`` にする。

``meta`` は各配列軸の方向ベクトル(非空間軸は ``None``)、``space_origin``、
``space_unit``(``mm`` / ``um`` / ``angstrom``)を持つ。``encoding`` は ``raw`` または
``gzip`` を明示する。呼び出し例: ``nrrd_write(vol, meta=geometry, encoding="gzip")``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_scientific_roundtrip](../../../../examples/fileio_scientific_roundtrip.py) — `py -3.11 examples/fileio_scientific_roundtrip.py`

## 型が繋がる次の op(`any` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [table_read_csv](../table/table_read_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_write_stl](../mesh/mesh_write_stl.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_write_obj](../mesh/mesh_write_obj.md) · [mesh_read_obj](../mesh/mesh_read_obj.md)

## 同カテゴリ(`nrrd`)

[nrrd_read](nrrd_read.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
