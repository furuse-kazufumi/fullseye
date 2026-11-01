---
op: points_write_xyz
dim: fileio
category: points
in: points
out: text
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# points_write_xyz — FILEIO `points` op

- **データ種**: `points` → `text`
- **呼び出し**: `import fullseye as fs; fs.ledger.points_write_xyz(points)` (実装を直接呼ぶなら `import fileio; fileio.points_write_xyz(points)`、台帳から引くなら `opsfileio.get("points_write_xyz")`)

## 使い方

有限な `(N,3)` 点群を17桁の XYZ テキストに書く(``text``)。

1行に ``x y z`` を1点ずつ書く。呼び出し例: ``text = points_write_xyz(points)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`text` を入力に取れる)

[table_read_csv](../table/table_read_csv.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [mesh_read_obj](../mesh/mesh_read_obj.md) · [mesh_read_off](../mesh/mesh_read_off.md) · [points_read_xyz](points_read_xyz.md) · [e57_read](../e57/e57_read.md) · [archive_probe](../archive/archive_probe.md)

## 同カテゴリ(`points`)

[points_read_xyz](points_read_xyz.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
