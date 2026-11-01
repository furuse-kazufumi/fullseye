---
op: table_write_csv
dim: fileio
category: table
in: table
out: text
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# table_write_csv — FILEIO `table` op

- **データ種**: `table` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_write_csv(table, *, units, meta)` (実装を直接呼ぶなら `import fileio; fileio.table_write_csv(table, *, units, meta)`、台帳から引くなら `opsfileio.get("table_write_csv")`)

## 使い方

単位と由来を持つ表を、pandas / MATLAB でも読める CSV 文字列にする(``text``)。

``table`` は ``{列名: 1-D 配列}``。``units`` は全列の単位を同じキーで持つ辞書、``meta`` は
``source``(出所)、``generated_at``(ISO 8601)、``coordinate_meaning``(座標の意味)を必ず持つ。
1 行目は列名、2 行目は ``# units:``、続く ``# key: value`` 行はメタデータ、その後がデータ。
``pandas.read_csv(StringIO(text), comment="#")`` で列名と値を読み、MATLAB ではコメント行を除外して
``readtable`` で読める。浮動小数は Python の ``repr`` で丸めず、列長不一致・単位欠落・無限値は拒否する。

呼び出し例: ``table_write_csv({"x": [1.0]}, units={"x": "mm"},
meta={"source": "caliper", "generated_at": "2026-10-31T12:00:00+09:00",
"coordinate_meaning": "x is right-handed"})``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`text` を入力に取れる)

[table_read_csv](table_read_csv.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_read_obj](../mesh/mesh_read_obj.md) · [mesh_read_off](../mesh/mesh_read_off.md) · [points_read_xyz](../points/points_read_xyz.md) · [e57_read](../e57/e57_read.md) · [archive_probe](../archive/archive_probe.md)

## 同カテゴリ(`table`)

[table_read_csv](table_read_csv.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
