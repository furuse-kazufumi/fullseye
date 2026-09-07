---
op: mesh_volume
dim: 3d
category: mesh_process
in: mesh
out: measurement
examples: [hull_bounds, mesh_props]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_volume — 3D `mesh_process` op

- **データ種**: `mesh` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_volume(mesh) -> 'float'` (実装を直接呼ぶなら `import mesh_props; mesh_props.mesh_volume(mesh) -> 'float'`、台帳から引くなら `ops3d.get("mesh_volume")`)

## 使い方

閉じた三角形メッシュが囲む**符号付き体積** → float。

発散定理(divergence theorem)で ``V = (1/6)·Σ v0 · (v1 × v2)``。面の巻き順が外向き
(右手系)なら正、内向きなら負になる —— **符号は向きの検査そのもの**で、負が
返ったら法線が裏返っている。

Args:
    mesh: ``(vertices (N,3), faces (M,3))`` のタプル。

Returns:
    符号付き体積(float、座標の単位の 3 乗)。

Raises:
    ValueError: ``mesh`` が ``(vertices, faces)`` の 2 要素でない、形状不正、
    非有限座標、非整数・範囲外の index、空のとき。

**限界(honest)**: 発散定理は**閉じた曲面でのみ**成り立つ。開いたメッシュ
(穴のあるスキャン)に対しても数値は返るが、それは「穴を原点へ向かって
塞いだ立体の体積」であって、欲しい量ではない。閉じているかどうかは
:func:`boundary_vertices` が空か、``mesh_edge_stats`` の ``boundary_edges`` が
0 かで**先に確かめること**。自己交差があるメッシュでは重なった領域が
符号つきで二重に数えられる(これも定理どおりの挙動で、検出はしない)。

Reference (public): 発散定理による多面体体積は標準的な公式。例えば
C. Zhang & T. Chen, "Efficient feature extraction for 2D/3D objects in mesh
representation", ICIP 2001。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hull_bounds](../../../../examples_3d/hull_bounds.py) — `py -3.11 examples_3d/hull_bounds.py`
- [mesh_props](../../../../examples_3d/mesh_props.py) — `py -3.11 examples_3d/mesh_props.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [vertex_curvature](vertex_curvature.md) · [face_areas](face_areas.md)

---
*Provenance: mesh_props.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
