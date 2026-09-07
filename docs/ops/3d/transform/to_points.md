---
op: to_points
dim: 3d
category: transform
in: voxel × points × mesh × depth × gaussians
out: points
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# to_points — 3D `transform` op

- **データ種**: `voxel × points × mesh × depth × gaussians` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.to_points(data, kind, samples=20000, **kw)` (実装を直接呼ぶなら `import fuse3d; fuse3d.to_points(data, kind, samples=20000, **kw)`、台帳から引くなら `ops3d.get("to_points")`)

## 使い方

任意の 3D 構造 → 点群(共通表現)。全5構造を 1 本の入口へ統合。

kind: "points"(N,3)/ "mesh"=(vertices,faces)/ "depth"=depth+{fx,fy,cx,cy[,stride]}/
      "voxel"=密度 grid+{iso}/ "3dgs"=means(N,3)。

``kind`` ごとの変換(実装どおり):
- ``"points"`` / ``"3dgs"``: ``np.asarray(data, float)`` を返すだけ(形の検査は
  しない。``(N, 3)`` を渡すのは呼び手の責任)。
- ``"mesh"``: ``data = (vertices, faces)``。``match3d.mesh_to_points`` で面積重みの
  一様サンプリングを ``samples`` 点(既定 20000、seed 固定 = 決定的)。
- ``"depth"``: ``data`` は深度マップ ``(H, W)``、``kw`` に ``fx, fy, cx, cy`` が
  **必須**(無ければ ``KeyError``)、``stride`` は任意(既定 1、間引き)。
  ``match3d.depth_to_points`` のピンホール逆投影で、``depth > 0`` の画素だけを
  ``(x, y, z)`` 点にする(カメラ座標、x = 列方向、y = 行方向、z = 深度)。
- ``"voxel"``: 密度 grid ``(D, H, W)`` を ``kw["iso"]``(既定 0.5)で閾値し、
  ``np.argwhere`` の **整数 index 座標** ``(z, y, x)`` を float にした点群。
  物理座標には直さない(spacing は掛けない)。

返り値: ``(N, 3)`` float64。``kind`` が上記以外なら ``ValueError``。
``samples`` は ``"mesh"`` 以外では無視される。

注意: ``"voxel"`` の座標は配列 index 順 ``(z, y, x)``、``"depth"`` はカメラ座標
``(x, y, z)`` と、種別ごとに軸の意味が違う。異種を ``register_cross`` /
``fuse_to_voxel`` で混ぜるときは、この差を呼び手が揃えておくこと。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [estimate_point_normals](estimate_point_normals.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md) · [icp_point2plane](../refine/icp_point2plane.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md)

---
*Provenance: fuse3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
