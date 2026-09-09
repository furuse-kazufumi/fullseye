---
op: boundary_vertices
dim: 3d
category: mesh_process
in: mesh
out: indices
examples: [mesh_decimate, mesh_props]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# boundary_vertices — 3D `mesh_process` op

- **データ種**: `mesh` → `indices`
- **呼び出し**: `import fullseye as fs; fs.ledger.boundary_vertices(mesh) -> 'np.ndarray'` (実装を直接呼ぶなら `import mesh_props; mesh_props.boundary_vertices(mesh) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("boundary_vertices")`)

## 使い方

開いた縁(境界)に乗っている**頂点の index** → ``(K,)``。

無向辺のうち**ちょうど 1 つの面にしか使われていない辺**(境界辺)の端点を集めて
返す。閉じた多様体なら空配列 —— つまり ``len(boundary_vertices(mesh)) == 0`` が
**水密性(watertight)の判定**になる。穴埋め・体積計算・曲率のどれも、境界の
有無で意味が変わるので、先にここを見る。

Args:
    mesh: ``(vertices (N,3), faces (M,3))`` のタプル。

Returns:
    昇順・重複なしの ``(K,)`` int64。境界が無ければ ``shape == (0,)``。

Raises:
    ValueError: ``mesh`` が ``(vertices, faces)`` の 2 要素でない、形状不正、
    非有限座標、非整数・範囲外の index、空のとき。

**限界(honest)**: 返るのは頂点の集合で、**縁のループ(周回順)ではない**。
穴が複数あっても 1 つの配列にまとまるので、穴ごとに分けたいなら連結成分を
自分で辿ることになる(ループ抽出の op はまだ無い)。3 つ以上の面が共有する
非多様体辺はここには出ない(``mesh_edge_stats`` の ``non_manifold_edges``)。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_decimate](../../../../examples_3d/mesh_decimate.py) — `py -3.11 examples_3d/mesh_decimate.py`
- [mesh_props](../../../../examples_3d/mesh_props.py) — `py -3.11 examples_3d/mesh_props.py`

## 型が繋がる次の op(`indices` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [vertex_curvature](vertex_curvature.md) · [face_areas](face_areas.md)

---
*Provenance: mesh_props.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
