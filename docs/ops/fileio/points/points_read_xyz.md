---
op: points_read_xyz
dim: fileio
category: points
in: text
out: points
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# points_read_xyz — FILEIO `points` op

- **データ種**: `text` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.points_read_xyz(data)` (実装を直接呼ぶなら `import fileio; fileio.points_read_xyz(data)`、台帳から引くなら `opsfileio.get("points_read_xyz")`)

## 使い方

空白区切りの XYZ テキストを読み、`(N,3)` の ``points`` を返す。

色列は受け付けるが points sort では返さない。列数不一致・非有限値は拒否する。呼び出し例:
``points = points_read_xyz(xyz_text)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`points` を入力に取れる)

[mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [points_write_xyz](points_write_xyz.md) · [e57_read](../e57/e57_read.md) · [astro_fits_write](../fits/astro_fits_write.md) · [astro_fits_read](../fits/astro_fits_read.md) · [em_mrc_write](../mrc/em_mrc_write.md) · [em_mrc_read](../mrc/em_mrc_read.md)

## 同カテゴリ(`points`)

[points_write_xyz](points_write_xyz.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
