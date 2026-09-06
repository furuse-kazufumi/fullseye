---
op: medial_axis_points
dim: 3d
category: medial
in: voxel
out: points
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# medial_axis_points — 3D `medial` op

- **データ種**: `voxel` → `points`
- **呼び出し**: `import medial; medial.medial_axis_points(vol, min_radius=0.0)` (または `ops3d.get("medial_axis_points")`)

## 使い方

medial voxel の座標と局所半径(= その点の EDT 値)を点群化。返り値 (points, radius)。

太い部分は面状、細い部分は線状に分布する medial 点を (M,3) の座標(z,y,x)と、それぞれの
局所半径 (M,) として返す。半径最大の点は形状の最も「内側」= 中心を指す。

Args:
    vol: バイナリ voxel(bool / 0-1 の 3D)。
    min_radius: この半径以下の点を除外(ノイズ抑制)。

Returns:
    points (float64, (M,3)): medial voxel 座標(z, y, x)。
    radius (float64, (M,)): 各点の EDT 値(= 局所内接半径)。

手順: ``distance_ridge(vol, min_radius)`` で得た ``ridge_mask`` の ``np.argwhere``
(配列 index、行は z-major の辞書順で決定的)と、その位置の ``edt`` 値を返す。
座標は voxel index で spacing は掛けない(物理座標が要るなら呼び手で
``points * (sz, sy, sx)``、半径も同様に等方 spacing を掛ける)。

引数と検証: ``vol`` は 3-D(非ゼロ = 前景)。3-D でない・空・NaN/Inf は
``ValueError``、``min_radius < 0`` も ``ValueError``。``radius`` は
``> min_radius`` の点だけ(境界 voxel は EDT が 1 以下なので ``min_radius=1`` で
外殻ノイズをほぼ落とせる)。

端の挙動: 前景が無い、または全点が ``min_radius`` 以下なら ``points`` は ``(0, 3)``、
``radius`` は ``(0,)`` の空配列(エラーにしない)。

使いどころ: ``medial_match`` の半径分布、点群 op(``smallest_sphere3`` /
``fit_line3`` 等)への橋渡し、``np.argmax(radius)`` で最大内接球の中心を取る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [topology_signature](topology_signature.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
