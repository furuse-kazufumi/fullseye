---
op: archive_extract
dim: fileio
category: archive
in: any × text
out: any
examples: [archive_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# archive_extract — FILEIO `archive` op

- **データ種**: `any × text` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.archive_extract(data_or_path, dest, *, members=None, max_total_bytes=2147483648, max_members=100000)` (実装を直接呼ぶなら `import fileio; fileio.archive_extract(data_or_path, dest, *, members=None, max_total_bytes=2147483648, max_members=100000)`、台帳から引くなら `opsfileio.get("archive_extract")`)

## 使い方

書庫を空の ``dest`` へ安全に展開し、相対path一覧を返す。 / Safely extract into an empty destination.

zip-slip(絶対path・``..``・drive文字)、link、特殊ファイル、重複名、10万件超、既定2 GiB超、
1:1000超の圧縮率を拒否する。``dest`` は存在しないか空の実directoryに限り、検証済みの
一時directoryを最後に置換するため失敗時に半端な出力を残さない。
Example: ``paths = archive_extract(payload, out_dir, members=["data/a.bin"])``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [archive_roundtrip](../../../../examples/archive_roundtrip.py) — `py -3.11 examples/archive_roundtrip.py`

## 型が繋がる次の op(`any` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [table_read_csv](../table/table_read_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_write_stl](../mesh/mesh_write_stl.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_write_obj](../mesh/mesh_write_obj.md) · [mesh_read_obj](../mesh/mesh_read_obj.md)

## 同カテゴリ(`archive`)

[archive_probe](archive_probe.md) · [archive_list](archive_list.md) · [archive_create](archive_create.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
