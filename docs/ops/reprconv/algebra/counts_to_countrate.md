---
op: counts_to_countrate
dim: reprconv
category: algebra
in: counts
out: countrate
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# counts_to_countrate — REPRCONV `algebra` op

- **データ種**: `counts` → `countrate`
- **呼び出し**: `import reprconv; reprconv.counts_to_countrate(counts, gate_s=0.001)` (または `opsreprconv.get("counts_to_countrate")`)

## 使い方

計数 → 計数レート ``[Hz]``。:func:`countrate_to_counts` の逆。

Args:
    counts: (N,) の非負計数。
    gate_s: 積算窓 [s]。> 0。
Returns:
    (N,) float64 の非負レート [Hz]。
Raises:
    ValueError: 負の計数 / gate_s <= 0 / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`countrate` を入力に取れる)

[countrate_to_counts](countrate_to_counts.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
