---
op: face_areas
dim: 3d
category: mesh_process
in: mesh
out: signal
examples: [mesh_props]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# face_areas — 3D `mesh_process` op

- **データ種**: `mesh` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.face_areas(mesh) -> 'np.ndarray'` (実装を直接呼ぶなら `import mesh_props; mesh_props.face_areas(mesh) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("face_areas")`)

## 使い方

三角形メッシュの**面ごとの面積** → ``(M,)``。

面積 = ``0.5·|cross(v1−v0, v2−v0)|`` を面ごとに返す(``mesh_area`` はこの総和)。
面積は**重み**として使うためにある —— 「下を向いた面の面積」「公差外の面積」
「曲率の面積加重平均」はすべて面ごとの面積が要る量で、総和からは作れない。

Args:
    mesh: ``(vertices (N,3), faces (M,3))`` のタプル。

Returns:
    ``(M,)`` の float64(非負)。順序は ``faces`` の順で、``face_normals`` と同じ
    並びなので ``areas[normals[:, 2] < 0].sum()`` のように直接組み合わせられる。

Raises:
    ValueError: ``mesh`` が ``(vertices, faces)`` の 2 要素でない、形状不正、
    非有限座標、非整数・範囲外の index、空のとき。

注意: ``mesh_area`` と同じく、退化三角形(面積 0)は**拒否せず 0 を返す**
(``face_normals`` は法線が定義できないので拒否する —— 同じメッシュでも
こちらは通る)。重複面・表裏 2 枚張りはそれぞれ 1 面として数える。
単位は座標の単位の 2 乗。

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_props](../../../../examples_3d/mesh_props.py) — `py -3.11 examples_3d/mesh_props.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`mesh_process`)

[laplacian_smooth](laplacian_smooth.md) · [taubin_smooth](taubin_smooth.md) · [decimate_qem](decimate_qem.md) · [face_normals](face_normals.md) · [vertex_normals](vertex_normals.md) · [mesh_area](mesh_area.md) · [vertex_curvature](vertex_curvature.md) · [mesh_volume](mesh_volume.md)

---
*Provenance: mesh_props.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
