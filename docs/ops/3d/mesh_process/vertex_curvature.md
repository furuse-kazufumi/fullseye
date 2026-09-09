---
op: vertex_curvature
dim: 3d
category: mesh_process
in: mesh
out: curvature
examples: [dl_mesh_curvature, mesh_props]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vertex_curvature — 3D `mesh_process` op

- **データ種**: `mesh` → `curvature`
- **呼び出し**: `import fullseye as fs; fs.ledger.vertex_curvature(mesh) -> 'np.ndarray'` (実装を直接呼ぶなら `import mesh_props; mesh_props.vertex_curvature(mesh) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("vertex_curvature")`)

## 使い方

三角形メッシュの各頂点の**平均曲率の大きさ**(mean curvature magnitude)。→ (N,)。

Meyer et al. (2003) の離散 Laplace-Beltrami 作用素:

    K(x_i) = (1 / (2·A_mixed_i)) · Σ_{j∈1-ring} (cot α_ij + cot β_ij)·(x_i − x_j)

は平均曲率法線ベクトル K = 2·H·n に等しい(H=平均曲率, n=単位法線)。ここでは向きに依らない
**大きさ** H_i = |K(x_i)| / 2 を返す。α_ij, β_ij は辺 (i,j) に相対する 2 つの角、A_mixed は
Meyer の混合面積(非鈍角三角形は Voronoi 面積、鈍角三角形は面積の 1/2 か 1/4)で、素朴な
重心面積より曲率推定が正確になる。

半径 R の球(閉じた多様体)では全頂点で H ≈ 1/R(離散化誤差内)。平面の内部頂点では
H ≈ 0。**限界(honest)**: cotangent Laplace-Beltrami は閉多様体/内部頂点でのみ妥当で、
開いたメッシュの**境界頂点**(1-ring が閉じない)では値が発散的に不正確になる。閉じた
メッシュ、または開メッシュの内部頂点にのみ意味がある。

Args:
    mesh: (vertices (N,3), faces (M,3)) のタプル。

Returns:
    (N,) の平均曲率の大きさ(非負)。境界頂点の値は上記の理由で信頼できない。

Raises:
    ValueError: 形状不正・範囲外 index、または混合面積がゼロの頂点(退化)があるとき。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_curvature](../../../../examples_3d/dl_mesh_curvature.py) — `py -3.11 examples_3d/dl_mesh_curvature.py`
- [mesh_props](../../../../examples_3d/mesh_props.py) — `py -3.11 examples_3d/mesh_props.py`

## 型が繋がる次の op(`curvature` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [face_areas](face_areas.md) · [mesh_volume](mesh_volume.md)

---
*Provenance: mesh_props.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
