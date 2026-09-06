---
op: pc_lod_chain
dim: 3d
category: resolution
in: points
out: table
examples: [mesh_resolution_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# pc_lod_chain — 3D `resolution` op

- **データ種**: `points` → `table`
- **呼び出し**: `import meshres; meshres.pc_lod_chain(points, spacing, levels=3, seed=0)` (または `ops3d.get("pc_lod_chain")`)

## 使い方

Poisson-disk levels at doubling spacings (``table``).

Level 0 is the input; level *k* keeps no two points closer than
``spacing × 2^(k−1)``. Returns ``levels`` (list of clouds), ``spacings``,
``counts``.

手順: level 0 = 入力点群(検証後の float64 コピー)。level ``k``(1..``levels``)は
**直前の level** に ``pc_poisson_disk(prev, spacing * 2**(k-1), seed=seed + k - 1)``
を掛けたもの(累積的に間引くので、粗い level の点は必ず細かい level にも含まれる
= 入れ子)。点は動かさない(格子平均のような重心移動はしない)。

引数: ``points`` ``(N, 3)``(有限、``MAX_POINTS`` 以下)、``spacing > 0``(level 1
の最小点間距離、座標と同じ単位)、``levels`` は 1..16 の整数、``seed`` は
Poisson-disk の訪問順の乱数種(固定なら決定的)。

返り値(dict): ``levels``(``levels + 1`` 個の ``(n_k, 3)`` 配列のリスト)、
``spacings``(``[0.0, spacing, 2*spacing, ...]``、level 0 は 0)、``counts``
(各 level の点数)、``n_levels``(``levels + 1``)。

検証(``ValueError``): 点群の形・非有限・点数超過 / ``spacing`` が非正 /
``levels`` が整数でない・範囲外。

注意: 各 level の点数は ``~ 面積 / spacing_k^2`` の目安で 4 分の 1 ずつ減るが、
疎な領域(元の点間隔が ``spacing_k`` より大きい)は間引かれず残る。何を落としたかは
``pc_thinning_report(points, levels[k])`` で数える。メッシュの LOD は
``mesh_lod_chain``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [mesh_resolution_demo](../../../../examples_3d/mesh_resolution_demo.py) — `py -3.11 examples_3d/mesh_resolution_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](mesh_select_lod.md)

## 同カテゴリ(`resolution`)

[mesh_edge_stats](mesh_edge_stats.md) · [mesh_detail_map](mesh_detail_map.md) · [mesh_split_long_edges](mesh_split_long_edges.md) · [mesh_isotropic_remesh](mesh_isotropic_remesh.md) · [mesh_sample_points](mesh_sample_points.md) · [mesh_lod_chain](mesh_lod_chain.md) · [mesh_select_lod](mesh_select_lod.md) · [mesh_reduction_report](mesh_reduction_report.md)

---
*Provenance: meshres.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
