---
op: fit_cone
dim: 3d
category: robust_fit
in: points
out: primitive
examples: [fit_primitives_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fit_cone — 3D `robust_fit` op

- **データ種**: `points` → `primitive`
- **呼び出し**: `import fit_primitives_ext; fit_primitives_ext.fit_cone(points) -> 'dict'` (または `ops3d.get("fit_cone")`)

## 使い方

点群に無限円錐を当てはめ ``{apex, axis, half_angle, residual}`` を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_primitives_ext](../../../../examples_3d/fit_primitives_ext.py) — `py -3.11 examples_3d/fit_primitives_ext.py`

## 型が繋がる次の op(`primitive` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [angle_between_lines](../geometry/angle_between_lines.md) · [angle_between_planes](../geometry/angle_between_planes.md) · [angle_line_plane](../geometry/angle_line_plane.md) · [distance_point_plane](../geometry/distance_point_plane.md) · [distance_point_line](../geometry/distance_point_line.md) · [distance_line_line](../geometry/distance_line_line.md) · [intersect_line_plane](../geometry/intersect_line_plane.md)

## 同カテゴリ(`robust_fit`)

[ransac_plane](ransac_plane.md) · [ransac_sphere](ransac_sphere.md) · [ransac_line](ransac_line.md) · [ransac_cylinder](ransac_cylinder.md) · [fit_torus](fit_torus.md) · [fit_ellipsoid](fit_ellipsoid.md)

---
*Provenance: fit_primitives_ext.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
