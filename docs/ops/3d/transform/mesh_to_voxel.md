---
op: mesh_to_voxel
dim: 3d
category: transform
in: mesh
out: voxel
gpu: true
examples: [transforms_repr]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mesh_to_voxel — 3D `transform` op

- **データ種**: `mesh` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_to_voxel(vertices, faces, size, bounds=None, samples=40000, device='cpu', smooth=0.8)` (実装を直接呼ぶなら `import match3d; match3d.mesh_to_voxel(vertices, faces, size, bounds=None, samples=40000, device='cpu', smooth=0.8)`、台帳から引くなら `ops3d.get("mesh_to_voxel")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

mesh(頂点+面)→ 密度 voxel。面上を一様サンプリング → splat(mesh 行を全手法へ接続)。

三角形上の一様点は barycentric(sqrt トリック)。占有 voxel が要るなら閾値化する。

手順: 各三角形の面積に比例して ``samples`` 個の面を選び(``default_rng(0)`` の固定 seed
→ 毎回同じ点)、面内一様な barycentric 点を作って ``points_to_voxel`` に渡す(``smooth``
既定 0.8 voxel)。``faces`` は (F,3) の頂点 index、``vertices`` は (V,3)。
退化面(面積 0)しか無い mesh は確率が NaN になり ``rng.choice`` が ValueError を出す。
``bounds=None`` ならサンプル点の min/max(mesh の bbox とほぼ一致するが、サンプル次第で
僅かに内側)。``bounds`` の検証・範囲外 clip は ``points_to_voxel`` と同じ。
返り値 ``(size, size, size)`` float64 の点密度(占有ではない。占有が要るなら閾値で
2 値化)。軸順は頂点座標の列順。seed を変えたい・点群も欲しいときは ``mesh_to_points`` で
点群を作ってから ``points_to_voxel`` へ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [transforms_repr](../../../../examples_3d/transforms_repr.py) — `py -3.11 examples_3d/transforms_repr.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [signed_distance_field](signed_distance_field.md) · [to_points](to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`transform`)

[points_to_voxel](points_to_voxel.md) · [gaussians_to_voxel](gaussians_to_voxel.md) · [mesh_to_points](mesh_to_points.md) · [depth_to_points](depth_to_points.md) · [voxel_to_mips](voxel_to_mips.md) · [voxel_to_mesh](voxel_to_mesh.md) · [tsdf_from_depth](tsdf_from_depth.md) · [signed_distance_field](signed_distance_field.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
