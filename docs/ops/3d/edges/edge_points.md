---
op: edge_points
dim: 3d
category: edges
in: voxel
out: points
examples: [edges_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# edge_points — 3D `edges` op

- **データ種**: `voxel` → `points`
- **呼び出し**: `import edges3d; edges3d.edge_points(edge_mask) -> 'np.ndarray'` (または `ops3d.get("edge_points")`)

## 使い方

エッジ mask を (M,3) の座標点群にする(下流の chamfer / Hough 用)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [edges_3d](../../../../examples_3d/edges_3d.py) — `py -3.11 examples_3d/edges_3d.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`edges`)

[gradient3d](gradient3d.md) · [canny3d](canny3d.md) · [log_zero_crossings](log_zero_crossings.md) · [link_edges](link_edges.md)

---
*Provenance: edges3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
