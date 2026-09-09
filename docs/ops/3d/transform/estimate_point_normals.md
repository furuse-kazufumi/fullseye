---
op: estimate_point_normals
dim: 3d
category: transform
in: points
out: normals
examples: [fpfh_correspondence]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# estimate_point_normals — 3D `transform` op

- **データ種**: `points` → `normals`
- **呼び出し**: `import fullseye as fs; fs.ledger.estimate_point_normals(points, k=16, viewpoint=None)` (実装を直接呼ぶなら `import match3d; match3d.estimate_point_normals(points, k=16, viewpoint=None)`、台帳から引くなら `ops3d.get("estimate_point_normals")`)

## 使い方

点群 (N,3) → 単位法線(局所 k 近傍共分散の最小固有ベクトル=PCA)。

FPFH/SHOT/点-面 ICP が要る法線を raw 点群から生成。向きの規約は 2 面:
**viewpoint=None(既定)= 重心から外向き**(閉じた物体の全周点群向け)/
**viewpoint 指定 = 視点(センサ)向き**(Hoppe 1992 / PCL 規約。単一視点スキャンの
可視面はセンサ側を向くのが物理的に正しい。`pointcloud.estimate_normals` と同規約)。
旧版(〜2026-08-30)は viewpoint 指定でも「視点から遠ざける」符号で、単一視点
スキャンという本来用途で全点が裏返っていた。返り値 normals (N,3)。

手順: ``cKDTree`` で各点の ``k`` 近傍(自分自身を含む。``k > N`` なら N に切り詰め)を取り、
その共分散の最小固有ベクトルを法線にする。返り値 ``(N,3)`` float64 の単位ベクトル。
``viewpoint`` は 3 次元の座標(センサ位置)。点数が 3 未満・近傍が同一直線上だと法線は
不定のまま返る(検証は無い)。``k`` が小さいとノイズに弱く、大きいと角が丸まる。
後段: ``icp_point2plane`` の ``dst_normals``、``render_shaded`` 用の法線、``normals_to_egi``。
``pointcloud.estimate_normals``(台帳 ``estimate_normals``)と同じ規約。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fpfh_correspondence](../../../../examples_3d/fpfh_correspondence.py) — `py -3.11 examples_3d/fpfh_correspondence.py`

## 型が繋がる次の op(`normals` を入力に取れる)

[icp_point2plane](../refine/icp_point2plane.md) · [compute_fpfh](../feature_register/compute_fpfh.md) · [shot_descriptor](../feature_register/shot_descriptor.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [reflect](../optics/reflect.md) · [refract](../optics/refract.md) · [normal_consistency](../metrics/normal_consistency.md) · [ransac_cylinder](../robust_fit/ransac_cylinder.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
