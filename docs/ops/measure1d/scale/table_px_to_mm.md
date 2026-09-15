---
op: table_px_to_mm
dim: measure1d
category: scale
in: table
out: table
examples: [example_inner_diameter_mm, example_scratch_width]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# table_px_to_mm — MEASURE1D `scale` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.table_px_to_mm(table, mm_per_px, keys=('width', 'radius', 'dist', 'rms', 'ra', 'rb', 'l1', 'l2'))` (実装を直接呼ぶなら `import measuring1d; measuring1d.table_px_to_mm(table, mm_per_px, keys=('width', 'radius', 'dist', 'rms', 'ra', 'rb', 'l1', 'l2'))`、台帳から引くなら `opsmeasure1d.get("table_px_to_mm")`)

## 使い方

計測結果の表(``measure_pairs`` / ``apply_metrology_model`` の返り)に mm 列を足す。

``keys`` にある数値の列 ``k`` ごとに ``k_mm = k * mm_per_px`` を **追加**する
(px の列は残す。消すと来歴が切れる)。``apply_metrology_model`` の各行は
``params`` dict の中に ``radius`` / ``l1`` … を持つので、そこも見る。
入力は list[dict] か dict 1 個。**浅い複製**を返し、入力は変えない。

- 数値でない列・無い列は黙って飛ばす(換算できたかは ``k_mm`` の有無で分かる)。
- ``mm_per_px`` は有限で正(``mm_per_px_from_reference`` の値)。
- ``rms`` は当てはめ残差 [px] なので mm にしておくと公差と直接比べられる。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_inner_diameter_mm](../../../../examples/example_inner_diameter_mm.py) — `py -3.11 examples/example_inner_diameter_mm.py`
- [example_scratch_width](../../../../examples/example_scratch_width.py) — `py -3.11 examples/example_scratch_width.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`scale`)

[mm_per_px_from_reference](mm_per_px_from_reference.md) · [pixel_to_world](pixel_to_world.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
