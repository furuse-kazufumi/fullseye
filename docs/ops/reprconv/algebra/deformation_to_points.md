---
op: deformation_to_points
dim: reprconv
category: algebra
in: deformation
out: points
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# deformation_to_points — REPRCONV `algebra` op

- **データ種**: `deformation` → `points`
- **呼び出し**: `import reprconv; reprconv.deformation_to_points(deformation)` (または `opsreprconv.get("deformation_to_points")`)

## 使い方

TPS 変形 ``deformation`` → 制御点 ``points (N,3)``。``deformation`` の出口。

``tps_fit`` が返す dict の ``ctrl`` を取り出す。「この歪みはどこに
固定されているか」を点群語彙で見るためのもので、**一方向**
(制御点だけからは重み ``w`` とアフィン項 ``a`` は復元できない)。

Args:
    deformation: ``ctrl`` を持つ dict(``tps_fit`` の返り)。
Returns:
    (N, 3) float64。
Raises:
    ValueError: dict でない / ``ctrl`` が無い / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](../keypoint/points_zyx_to_keypoints_uv.md) · [points_to_position](../keypoint/points_to_position.md) · [select_points](../index/select_points.md) · [flow_apply](../flow/flow_apply.md) · [points_to_gaussians](../gaussians/points_to_gaussians.md)

## 同カテゴリ(`algebra`)

[angle_to_matrix](angle_to_matrix.md) · [matrix_to_angle](matrix_to_angle.md) · [rot_scale_to_matrix](rot_scale_to_matrix.md) · [matrix_to_rot_scale](matrix_to_rot_scale.md) · [shift_to_vector](shift_to_vector.md) · [vector_to_shift](vector_to_shift.md) · [cscalar_to_polar](cscalar_to_polar.md) · [polar_to_cscalar](polar_to_cscalar.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
