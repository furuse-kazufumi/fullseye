---
op: table_read_csv
dim: fileio
category: table
in: text
out: table
gpu: なし
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# table_read_csv — FILEIO `table` op

- **データ種**: `text` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_read_csv(text)` (実装を直接呼ぶなら `import fileio; fileio.table_read_csv(text)`、台帳から引くなら `opsfileio.get("table_read_csv")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

:func:`table_write_csv` の単位つき CSV を読み、列・単位・メタデータの ``table`` を返す。

返り値は ``{"columns": {列名: 1-D 配列}, "units": {...}, "meta": {...}}``。列名と単位の
個数、全データ行の列数、必須メタデータを検査し、途中までの表は返さない。数値列は float64
(空欄は NaN)、数値以外を含む列は文字列配列になる。入力は UTF-8 の ``str`` または ``bytes``。

呼び出し例: ``roundtrip = table_read_csv(table_write_csv(table, units=units, meta=meta))``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`table` を入力に取れる)

[table_write_csv](table_write_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [e57_write](../e57/e57_write.md) · [e57_read](../e57/e57_read.md)

## 同カテゴリ(`table`)

[table_write_csv](table_write_csv.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
