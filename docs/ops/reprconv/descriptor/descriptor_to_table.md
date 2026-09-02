---
op: descriptor_to_table
dim: reprconv
category: descriptor
in: descriptor
out: table
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# descriptor_to_table — REPRCONV `descriptor` op

- **データ種**: `descriptor` → `table`
- **呼び出し**: `import reprconv; reprconv.descriptor_to_table(descriptor)` (または `opsreprconv.get("descriptor_to_table")`)

## 使い方

記述子 → 要約 ``table``。**一方向**。

次元・ノルム・エネルギー集中(正規化した二乗和の上位 10% が占める割合)を
出す。記述子が「実質何次元使っているか」を見るためのもので、次元だけ多くて
ほぼ全部 0 という失敗を可視化する。

Args:
    descriptor: (n,) または (m, n)。
Returns:
    dict(``shape`` / ``n`` / ``l2`` / ``mean`` / ``std`` / ``min`` /
    ``max`` / ``top10pct_energy`` / ``nonzero_fraction``)。
Raises:
    ValueError: 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`descriptor`)

[descriptor_to_matrix](descriptor_to_matrix.md) · [matrix_to_descriptor](matrix_to_descriptor.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
