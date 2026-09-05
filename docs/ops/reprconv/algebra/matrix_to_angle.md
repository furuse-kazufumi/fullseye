---
op: matrix_to_angle
dim: reprconv
category: algebra
in: matrix
out: angle
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# matrix_to_angle — REPRCONV `algebra` op

- **データ種**: `matrix` → `angle`
- **呼び出し**: `import reprconv; reprconv.matrix_to_angle(matrix)` (または `opsreprconv.get("matrix_to_angle")`)

## 使い方

z 軸まわりの回転行列 → 角度 **[度]**。:func:`angle_to_matrix` の逆。

``atan2(R[2,1], R[1,1])`` を度で返す(-180, 180]。往復は
(-180, 180] の範囲で **bit 一致に近い**(実測 max|Δ| = 2.8e-14 度)。

Args:
    matrix: (3, 3)。
Returns:
    float(度)。
Raises:
    ValueError: (3,3) でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`angle` を入力に取れる)

[angle_to_matrix](angle_to_matrix.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
