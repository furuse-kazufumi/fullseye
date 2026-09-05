---
op: shift_to_vector
dim: reprconv
category: algebra
in: shift
out: vector
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# shift_to_vector — REPRCONV `algebra` op

- **データ種**: `shift` → `vector`
- **呼び出し**: `import reprconv; reprconv.shift_to_vector(shift)` (または `opsreprconv.get("shift_to_vector")`)

## 使い方

整数シフト ``(dz, dy, dx)`` → ``vector (3,)``。``shift`` の出口(**可逆**)。

``match_phase_3d`` は整数 3-tuple を返す。``vector`` へ載せると
``points`` 語彙へ繋がる(``vector -> points`` の既存 op がある)。

Args:
    shift: 長さ 3 の整数列 (dz, dy, dx)。
Returns:
    (3,) float64。
Raises:
    ValueError: 長さが 3 でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`vector` を入力に取れる)

[vector_to_shift](vector_to_shift.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
