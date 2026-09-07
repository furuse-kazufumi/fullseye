---
op: alpha_shape_mesh
dim: 3d
category: reconstruct
in: points
out: mesh
examples: [alpha_shape_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# alpha_shape_mesh — 3D `reconstruct` op

- **データ種**: `points` → `mesh`
- **呼び出し**: `import fullseye as fs; fs.ledger.alpha_shape_mesh(points, alpha)` (実装を直接呼ぶなら `import recon3d; recon3d.alpha_shape_mesh(points, alpha)`、台帳から引くなら `ops3d.get("alpha_shape_mesh")`)

## 使い方

alpha shapes による**表面三角形メッシュ**(点群 → (vertices, faces))。

``alpha_shape_boundary`` と同じ境界三角形を、使用頂点だけに詰め直したメッシュとして返す。
voxel を介さず点群から直接張る表面。凹み/穴を保持できるのが marching cubes 系との差別化。

Parameters
----------
points : array_like (N,3)
alpha : float
    正の実数(半径しきい値 1/alpha)。

Returns
-------
vertices : numpy.ndarray (V,3) float64
    境界に使われた入力点(詰め直し済み)。
faces : numpy.ndarray (F,3) int64
    vertices を参照する三角形インデックス。境界が無ければ (0,3)/(0,3)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [alpha_shape_topology](../../../../examples_3d/alpha_shape_topology.py) — `py -3.11 examples_3d/alpha_shape_topology.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`reconstruct`)

[poisson_lite](poisson_lite.md) · [alpha_shape_boundary](alpha_shape_boundary.md) · [estimate_alpha](estimate_alpha.md)

---
*Provenance: recon3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
