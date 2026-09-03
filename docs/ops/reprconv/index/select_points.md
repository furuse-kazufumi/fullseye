---
op: select_points
dim: reprconv
category: index
in: points × indices
out: points
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# select_points — REPRCONV `index` op

- **データ種**: `points × indices` → `points`
- **呼び出し**: `import reprconv; reprconv.select_points(points, indices)` (または `opsreprconv.get("select_points")`)

## 使い方

点群 ``(N,3)`` と添字 ``(M,)`` → 部分点群 ``(M,3)``。``indices`` の消費側。

``indices`` を産む op は 6 つあるのに(``iss_keypoints`` /
``farthest_point_sampling`` / ``alpha_shape_boundary`` / ``find_peaks`` /
``zero_crossings_funct_1d`` / ``cad_visible_faces``)、**添字を食う単入力 op が
1 つも無かった** —— 添字は「元の集合とセットで初めて意味を持つ」ので、
単入力では原理的に作れない。よってこれは 2 入力にしてある。

Args:
    points: (N, 3)。
    indices: (M,) の非負整数、N 未満。
Returns:
    (M, 3) float64。
Raises:
    ValueError: 範囲外の添字 / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_zyx_to_keypoints_uv](../keypoint/points_zyx_to_keypoints_uv.md) · [points_to_position](../keypoint/points_to_position.md) · [flow_apply](../flow/flow_apply.md) · [points_to_gaussians](../gaussians/points_to_gaussians.md)

## 同カテゴリ(`index`)

[indices_to_labels](indices_to_labels.md) · [labels_to_indices](labels_to_indices.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
