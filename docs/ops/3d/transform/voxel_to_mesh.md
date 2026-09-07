---
op: voxel_to_mesh
dim: 3d
category: transform
in: voxel
out: mesh
examples: [mesh_smooth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# voxel_to_mesh — 3D `transform` op

- **データ種**: `voxel` → `mesh`
- **呼び出し**: `import match3d; match3d.voxel_to_mesh(vol, iso=0.5)` (または `ops3d.get("voxel_to_mesh")`)
- **台帳経由の戻り値**: `fullseye.ledger.voxel_to_mesh(...)` は**宣言 out 型 `mesh` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.voxel_to_mesh.raw(...)`、または `match3d.voxel_to_mesh` を直接呼ぶ。

## 使い方

voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。

``skimage.measure.marching_cubes(vol, level=iso)`` の薄い包み(spacing 指定なし = 1 voxel
単位)。``verts`` (V,3) float は **voxel index 座標**で、列は入力の軸順(``vol`` が (D,H,W)
なら (z,y,x))。``faces`` (F,3) int は verts への index、``normals`` (V,3) は skimage が
勾配から与える頂点法線。4 番目の返り値(values)は捨てる。

- ``iso``: 等値面のレベル。**入力の値域の外だと skimage が ValueError** を出す(全 0 の
volume で iso=0.5 など)。個数密度なら 0.5、SDF なら 0.0 を渡す。
- 境界に接する等値面は開いたまま(端で閉じない)。
- skimage は呼び出し時 import(未導入なら ImportError)。
後段: ``mesh_to_points`` で点群化、``mesh_area`` / ``mesh_edge_stats`` で計測。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_smooth](../../../../examples_3d/mesh_smooth.py) — `py -3.11 examples_3d/mesh_smooth.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [to_points](to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_voxel](mesh_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
