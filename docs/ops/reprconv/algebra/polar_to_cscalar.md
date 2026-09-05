---
op: polar_to_cscalar
dim: reprconv
category: algebra
in: pairs
out: cscalar
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# polar_to_cscalar — REPRCONV `algebra` op

- **データ種**: `pairs` → `cscalar`
- **呼び出し**: `import reprconv; reprconv.polar_to_cscalar(pairs)` (または `opsreprconv.get("polar_to_cscalar")`)

## 使い方

極形式 ``pairs (1,2) = [r, theta[度]]`` → 複素スカラ。:func:`cscalar_to_polar` の逆。

Args:
    pairs: (1, 2)。r >= 0。
Returns:
    complex。
Raises:
    ValueError: 形状が (1,2) でない / r < 0 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`cscalar` を入力に取れる)

[cscalar_to_polar](cscalar_to_polar.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
