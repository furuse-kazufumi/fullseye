---
op: register_cross
dim: 3d
category: fusion
in: any × any
out: pose
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# register_cross — 3D `fusion` op

- **データ種**: `any × any` → `pose`
- **呼び出し**: `import fuse3d; fuse3d.register_cross(src, src_kind, dst, dst_kind, method='fpfh', samples=15000, **kw)` (または `ops3d.get("register_cross")`)

## 使い方

異種構造間の剛体登録。両者を点群へ変換 → 登録器(fpfh=大回転/icp=要 coarse init)。

例: register_cross((verts,faces),"mesh", scan_pts,"points") で CAD↔スキャン整合。返り値 (R, t)。

手順: ``to_points(src, src_kind, samples, **kw)`` と ``to_points(dst, dst_kind,
samples, **kw)`` で両者を点群にし、``method`` で登録器を選ぶ。
- ``"fpfh"``(既定): ``feat_fpfh.register_fpfh(ps, pd)`` を既定パラメータで呼ぶ
  (FPFH 記述子 + RANSAC、初期姿勢不要、大回転・部分重なりに対応)。
- ``"icp"``: ``match3d.icp_point2point_3d(ps, pd, iters=50)``(最近傍対応 +
  Kabsch)。初期姿勢の引数は渡さないので、``src`` が ``dst`` に近い(粗く
  合っている)ことが前提。
- それ以外は ``ValueError``。

返り値: ``(R, t)`` — ``R`` は ``(3, 3)``、``t`` は ``(3,)`` の numpy 配列(torch tensor
は CPU の numpy に変換して返す)。慣習は ``dst ≈ src @ R.T + t``。

注意:
- ``**kw`` は **両方の** ``to_points`` に同じものが渡る(``"depth"`` の ``fx, fy, cx,
  cy`` や ``"voxel"`` の ``iso`` を片側だけに与えることはできない)。
- ``samples`` は ``"mesh"`` のサンプル数(既定 15000)。点群の個数・形は検査しない。
- 座標系の違い(``to_points`` 参照: voxel は ``(z, y, x)`` index、depth はカメラ
  ``(x, y, z)``)は吸収しない。
- 精度を締めるには fpfh の結果を初期値に ``icp_point2point_3d`` を直接呼ぶ。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`fusion`)

[fuse_to_voxel](fuse_to_voxel.md)

---
*Provenance: fuse3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
