---
op: pixel_to_world
dim: measure1d
category: scale
in: measurement
out: measurement
examples: [example_inner_diameter_mm]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# pixel_to_world — MEASURE1D `scale` op

- **データ種**: `measurement` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.pixel_to_world(value_px, mm_per_px)` (実装を直接呼ぶなら `import measuring1d; measuring1d.pixel_to_world(value_px, mm_per_px)`、台帳から引くなら `opsmeasure1d.get("pixel_to_world")`)

## 使い方

画素で測った長さ 1 個を実寸 mm にする(``value_px * mm_per_px``)。

``mm_per_px`` は ``mm_per_px_from_reference`` で**実測**したものを渡す。
``value_px`` は 0 や負でもよい(差分・偏りをそのまま換算できる)が、有限で
あること。``mm_per_px`` は有限で正。どちらも違えば ``ValueError``。
返り値は float(``measurement`` 型)。面積は mm/px を 2 乗して自分で掛ける
(この op は長さだけ)。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_inner_diameter_mm](../../../../examples/example_inner_diameter_mm.py) — `py -3.11 examples/example_inner_diameter_mm.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[mm_per_px_from_reference](mm_per_px_from_reference.md)

## 同カテゴリ(`scale`)

[mm_per_px_from_reference](mm_per_px_from_reference.md) · [table_px_to_mm](table_px_to_mm.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
