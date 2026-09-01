---
op: rot_scale_to_matrix
dim: reprconv
category: algebra
in: rot_scale
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rot_scale_to_matrix — REPRCONV `algebra` op

- **データ種**: `rot_scale` → `matrix`
- **呼び出し**: `import reprconv; reprconv.rot_scale_to_matrix(rot_scale)` (または `opsreprconv.get("rot_scale_to_matrix")`)

## 使い方

``(角度[度], 倍率)`` → 2-D 相似変換 ``matrix (2,2)``。``rot_scale`` の出口。

``match_logpolar_z`` が返す 2-tuple をそのまま行列にする。
:func:`matrix_to_rot_scale` と往復して実測 max|Δ| = 2.8e-14(角度は度、倍率は無次元)。

Args:
    rot_scale: 長さ 2 の列 ``(angle_deg, scale)``。scale > 0。
Returns:
    (2, 2) float64。
Raises:
    ValueError: 長さが 2 でない / scale <= 0 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[matrix_to_descriptor](../descriptor/matrix_to_descriptor.md) · [matrix_to_angle](matrix_to_angle.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md) · [countrate_to_counts](countrate_to_counts.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
