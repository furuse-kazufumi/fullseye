---
op: archive_list
dim: fileio
category: archive
in: any
out: table
examples: [archive_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# archive_list — FILEIO `archive` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.archive_list(data_or_path)` (実装を直接呼ぶなら `import fileio; fileio.archive_list(data_or_path)`、台帳から引くなら `opsfileio.get("archive_list")`)

## 使い方

書庫を読み、名前・展開後/圧縮後サイズ・更新時刻・directoryフラグの一覧を返す。 / List archive metadata.

``bytes`` または path を受け、行は ``name/size/compressed_size/modified/is_dir`` を持つ。
zip と tar 系は標準ライブラリ、7z/rar は 7-Zip が見つかる場合だけ扱う。7-Zip 不在や
壊れた書庫では空一覧にせず例外にする。Example: ``rows = archive_list(zip_bytes)``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [archive_roundtrip](../../../../examples/archive_roundtrip.py) — `py -3.11 examples/archive_roundtrip.py`

## 型が繋がる次の op(`table` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [e57_write](../e57/e57_write.md) · [e57_read](../e57/e57_read.md) · [archive_probe](archive_probe.md)

## 同カテゴリ(`archive`)

[archive_probe](archive_probe.md) · [archive_extract](archive_extract.md) · [archive_create](archive_create.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
