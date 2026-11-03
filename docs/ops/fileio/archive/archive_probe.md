---
op: archive_probe
dim: fileio
category: archive
in: any
out: text
examples: [archive_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# archive_probe — FILEIO `archive` op

- **データ種**: `any` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.archive_probe(data_or_path)` (実装を直接呼ぶなら `import fileio; fileio.archive_probe(data_or_path)`、台帳から引くなら `opsfileio.get("archive_probe")`)

## 使い方

書庫のマジックナンバーを検査し、形式名を返す。 / Probe archive magic and return its format name.

入力は ``bytes`` または既存ファイルの path。返り値は ``zip/tar/tar.gz/tar.bz2/tar.xz/7z/rar``
のいずれかで、拡張子だけでは判定しない。未知・切断・圧縮tarでないgzip等は明示して拒否する。
Example: ``fmt = archive_probe(payload)``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [archive_roundtrip](../../../../examples/archive_roundtrip.py) — `py -3.11 examples/archive_roundtrip.py`

## 型が繋がる次の op(`text` を入力に取れる)

[table_read_csv](../table/table_read_csv.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_read_obj](../mesh/mesh_read_obj.md) · [mesh_read_off](../mesh/mesh_read_off.md) · [points_read_xyz](../points/points_read_xyz.md) · [e57_read](../e57/e57_read.md) · [archive_list](archive_list.md)

## 同カテゴリ(`archive`)

[archive_list](archive_list.md) · [archive_extract](archive_extract.md) · [archive_create](archive_create.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
