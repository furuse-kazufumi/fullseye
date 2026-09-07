---
op: mesh_area
dim: 3d
category: mesh_process
in: mesh
out: measurement
examples: [dl_mesh_curvature, mesh_props]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# mesh_area — 3D `mesh_process` op

- **データ種**: `mesh` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_area(mesh) -> 'float'` (実装を直接呼ぶなら `import mesh_props; mesh_props.mesh_area(mesh) -> 'float'`、台帳から引くなら `ops3d.get("mesh_area")`)

## 使い方

三角形メッシュの**表面積**(全三角形面積の総和)。→ float。

面積 = Σ 0.5·|cross(v1−v0, v2−v0)|。頂点数に定数を掛ける素朴な近似ではなく、実際の面の
大きさを積算するので、メッシュのスケール・形状に正しく追随する。

Args:
    mesh: (vertices (N,3), faces (M,3)) のタプル。

Returns:
    表面積(非負の float)。

Raises:
    ValueError: mesh が (vertices, faces) の 2 要素でない、形状不正、非有限座標、非整数・
    範囲外の index、空、または 3 頂点のどれかが同じ index の三角形があるとき。

注意: ``face_normals`` と違い、座標がほぼ一直線に並んだ退化三角形(面積 0)は拒否せず 0 として
加算する。重複面や表裏 2 枚張りの面はそのまま 2 回数えられる。単位は座標の単位の 2 乗。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dl_mesh_curvature](../../../../examples_3d/dl_mesh_curvature.py) — `py -3.11 examples_3d/dl_mesh_curvature.py`
- [mesh_props](../../../../examples_3d/mesh_props.py) — `py -3.11 examples_3d/mesh_props.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [vertex_curvature](vertex_curvature.md) · [face_areas](face_areas.md) · [mesh_volume](mesh_volume.md)

---
*Provenance: mesh_props.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
