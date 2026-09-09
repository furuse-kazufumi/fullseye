---
op: depth_to_points
dim: 3d
category: transform
in: depth
out: points
examples: [structured_light_scan, transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# depth_to_points — 3D `transform` op

- **データ種**: `depth` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.depth_to_points(depth, fx, fy, cx, cy, stride=1)` (実装を直接呼ぶなら `import match3d; match3d.depth_to_points(depth, fx, fy, cx, cy, stride=1)`、台帳から引くなら `ops3d.get("depth_to_points")`)

## 使い方

深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。

画素 (行 v, 列 u) の深度 z から ``X = (u − cx)·z/fx``、``Y = (v − cy)·z/fy``、``Z = z`` を作る。
返り値は ``(N,3)`` float64、列は **(X, Y, Z) のカメラ座標**(深度と同じ単位)。z が 0 以下の
画素は捨てるので N は画素数以下(無効深度は 0 で表す規約)。

- ``fx, fy, cx, cy``: 画素単位の焦点距離と主点。``project_points`` の K と同じ規約。
- ``stride``: 行・列とも ``stride`` 画素おきに間引く。u, v は間引き後の index に ``stride``
を掛けた **元画像の画素座標**で計算するので、間引いても幾何は変わらない。
- 入力検証は無い(2-D でなければ添字で失敗)。NaN 深度は ``z > 0`` が偽で捨てられる。
- 点は行優先の順に並ぶが、行・列の情報は残らない。格子構造を保ちたいなら
``depth_to_organized_points``。
後段: ``points_to_voxel`` / ``estimate_point_normals`` / ``icp_point2plane``。
逆写像は ``project_points``、TSDF 化は ``tsdf_from_depth``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light_scan](../../../../examples_3d/structured_light_scan.py) — `py -3.11 examples_3d/structured_light_scan.py`
- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [estimate_point_normals](estimate_point_normals.md) · [to_points](to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
