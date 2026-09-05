---
op: vector_to_shift
dim: reprconv
category: algebra
in: vector
out: shift
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# vector_to_shift — REPRCONV `algebra` op

- **データ種**: `vector` → `shift`
- **呼び出し**: `import reprconv; reprconv.vector_to_shift(vector)` (または `opsreprconv.get("vector_to_shift")`)

## 使い方

``vector (3,)`` → 整数シフト ``(dz, dy, dx)``。:func:`shift_to_vector` の逆向き。

**不可逆**(最近接整数へ丸める)。落ちる量は丸め残差そのもので、
``|v - round(v)| <= 0.5`` が各軸の上界。整数を渡した往復だけが bit 一致する。

Args:
    vector: (3,)。
Returns:
    3-tuple の int。
Raises:
    ValueError: (3,) でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`shift` を入力に取れる)

[shift_to_vector](shift_to_vector.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
