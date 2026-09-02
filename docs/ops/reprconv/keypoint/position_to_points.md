---
op: position_to_points
dim: reprconv
category: keypoint
in: position
out: points
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# position_to_points — REPRCONV `keypoint` op

- **データ種**: `position` → `points`
- **呼び出し**: `import reprconv; reprconv.position_to_points(position)` (または `opsreprconv.get("position_to_points")`)

## 使い方

位置 ``(z, y, x)`` → 1 点の点群 ``(1, 3)``。``position`` の出口(**可逆**)。

``position`` は ``volregion.vol_rle_centroid`` などが返す 3-tuple で、
順序は **(z, y, x)**(``vol_rle_centroid`` の docstring が明示している)。
点群も voxel 由来なら同じ順なので、そのまま 1 行の点群にできる。

Args:
    position: 長さ 3 の列 (z, y, x)。
Returns:
    (1, 3) float64。
Raises:
    ValueError: 長さが 3 でない / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [points_to_position](points_to_position.md) · [select_points](../index/select_points.md) · [flow_apply](../flow/flow_apply.md) · [points_to_gaussians](../gaussians/points_to_gaussians.md)

## 同カテゴリ(`keypoint`)

[keypoints_uv_to_points](keypoints_uv_to_points.md) · [points_zyx_to_keypoints_uv](points_zyx_to_keypoints_uv.md) · [keypoints_to_image2d](keypoints_to_image2d.md) · [keypoints_from_image2d](keypoints_from_image2d.md) · [points_to_position](points_to_position.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
