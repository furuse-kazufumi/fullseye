---
op: matrix_to_rot_scale
dim: reprconv
category: algebra
in: matrix
out: rot_scale
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# matrix_to_rot_scale — REPRCONV `algebra` op

- **データ種**: `matrix` → `rot_scale`
- **呼び出し**: `import reprconv; reprconv.matrix_to_rot_scale(matrix)` (または `opsreprconv.get("matrix_to_rot_scale")`)

## 使い方

2-D 相似変換 ``(2,2)`` → ``(角度[度], 倍率)``。:func:`rot_scale_to_matrix` の逆。

倍率は列ノルム、角度は ``atan2(m[1,0], m[0,0])``。
せん断を含む一般の (2,2) を渡しても例外は出ない(相似成分だけを読む)ので、
``residual`` が要るときは呼び出し側で ``m - rot_scale_to_matrix(...)`` を取ること。

Args:
    matrix: (2, 2)。
Returns:
    2-tuple の float ``(angle_deg, scale)``。
Raises:
    ValueError: (2,2) でない / 退化(倍率 0)/ 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rot_scale` を入力に取れる)

[rot_scale_to_matrix](rot_scale_to_matrix.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
