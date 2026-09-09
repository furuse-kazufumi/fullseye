---
op: mesh_edge_lengths
dim: 3d
category: terrain
in: mesh
out: signal
examples: [itokawa_regolith_hero]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# mesh_edge_lengths — 3D `terrain` op

- **データ種**: `mesh` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.mesh_edge_lengths(V, F, *, per: 'str' = 'vertex') -> 'np.ndarray'` (実装を直接呼ぶなら `import render3d; render3d.mesh_edge_lengths(V, F, *, per: 'str' = 'vertex') -> 'np.ndarray'`、台帳から引くなら `ops3d.get("mesh_edge_lengths")`)

## 使い方

Local edge length of a triangle mesh → ``(N,)`` per vertex (mean of incident edges),

``(M,)`` per face (mean of its 3 edges) or ``(E,)`` per unique edge.

This is the resolution map of the mesh in its own units: the shortest wavelength a
region can carry as *geometry* is about twice the local edge (Nyquist), which is what
:func:`mesh_subdivide` (``target_edge``) and :func:`displacement_band_weights` use.
Deterministic; fail-closed on degenerate meshes / unknown ``per``.

無向の一意な辺 ``(E,2)`` を取り、各辺の長さ(メッシュ単位、float64)を集計する。

- ``per='vertex'``: 頂点に接する辺長の平均 ``(N,)``。どの面にも属さない孤立頂点は
  辺を持たないので、無言で **全辺の平均値** が入る(ゼロにはならない)。
- ``per='face'``: 面の 3 辺の平均 ``(M,)``。
- ``per='edge'``: 一意辺そのものの長さ ``(E,)``。辺の並びは ``np.unique`` の辞書順
  (頂点 index の小さい順)で、``F`` の順とは対応しない。

``per`` が上記 3 つ以外、頂点/面が空、face index 範囲外、非有限座標は ``ValueError``。
``displacement_band_weights`` の ``local_edge`` や ``mesh_subdivide`` の
``target_edge`` を決める(例: 中央値の半分)ために使う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_regolith_hero](../../../../examples_3d/itokawa_regolith_hero.py) — `py -3.11 examples_3d/itokawa_regolith_hero.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`terrain`)

[mesh_displace_fbm](mesh_displace_fbm.md) · [terrain_region_mask](terrain_region_mask.md) · [mesh_scatter_boulders](mesh_scatter_boulders.md) · [mesh_subdivide](mesh_subdivide.md) · [displacement_band_weights](displacement_band_weights.md) · [mesh_displace_spectrum](mesh_displace_spectrum.md) · [bump_normals_fbm](bump_normals_fbm.md)

---
*Provenance: render3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
