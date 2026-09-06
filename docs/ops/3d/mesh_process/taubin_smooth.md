---
op: taubin_smooth
dim: 3d
category: mesh_process
in: mesh
out: mesh
examples: [mesh_smooth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# taubin_smooth — 3D `mesh_process` op

- **データ種**: `mesh` → `mesh`
- **呼び出し**: `import mesh_smooth; mesh_smooth.taubin_smooth(mesh: 'Sequence', iters: 'int' = 10, lam: 'float' = 0.33, mu: 'float' = -0.34) -> 'Mesh'` (または `ops3d.get("taubin_smooth")`)

## 使い方

Taubin λ|μ フィルタによる **非収縮** 平滑化。→ (verts, faces)。

各反復で「正の ``lam`` で寄せる段」→「負の ``mu`` で押し戻す段」を続けて掛ける。
``|mu| > lam`` とすることで低周波(全体形状)を通し高周波(ノイズ)だけを減衰させる
帯域通過フィルタになり、Laplacian の収縮アーティファクトを打ち消す(球の平均半径が
ほぼ保たれる)。既定 ``lam=0.33, mu=-0.34`` は Taubin (1995) の推奨に近い。

Args:
    mesh: (verts (N,3), faces (M,3)[, ...]) のシーケンス。faces は不変。
    iters: λ|μ ペアの反復回数(正の整数)。
    lam: 寄せ段の係数、``0 < lam < 1``。
    mu: 押し戻し段の係数、``mu < 0`` かつ ``|mu| > lam``(収縮を打ち消す条件)。

Returns:
    (verts (N,3) float64, faces (M,3) int64)。faces は入力を保持。

Raises:
    ValueError: メッシュ形状不正・面範囲外・iters/lam/mu が不正(fail-closed)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_smooth](../../../../examples_3d/mesh_smooth.py) — `py -3.11 examples_3d/mesh_smooth.py`

## 型が繋がる次の op(`mesh` を入力に取れる)

[mesh_to_voxel](../transform/mesh_to_voxel.md) · [mesh_to_points](../transform/mesh_to_points.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [ambient_occlusion](../render/ambient_occlusion.md) · [cast_shadow](../render/cast_shadow.md) · [supersample_mesh](../render/supersample_mesh.md) · [render_beauty](../render/render_beauty.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [vertex_curvature](vertex_curvature.md)

---
*Provenance: mesh_smooth.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
