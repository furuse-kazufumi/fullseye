---
op: topology_signature
dim: 3d
category: medial
in: voxel
out: table
examples: [medial_topology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# topology_signature — 3D `medial` op

- **データ種**: `voxel` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.topology_signature(skeleton)` (実装を直接呼ぶなら `import medial; medial.topology_signature(skeleton)`、台帳から引くなら `ops3d.get("topology_signature")`)

## 使い方

骨格の 26 近傍次数から位相記述子を作る。端点/分岐点/通常点/孤立点の個数を返す。

各骨格 voxel について 26 近傍にある骨格 voxel 数(次数)を数え、
    次数 1  = 端点(endpoint)
    次数 2  = 通常点(骨格の途中)
    次数>=3 = 分岐点(branch)
    次数 0  = 孤立点(isolated)
に分類する。個数は平行移動・回転(90 度)不変で、形状の位相を粗く要約する記述子になる。

注意(honest): 26 近傍の次数は、分岐近傍で対角隣接により過大に数えられることがある(離散
骨格の既知の性質)。端点数は各枝の末端で厳密だが、分岐点数はやや過大側に振れうる。

Args:
    skeleton: 骨格 voxel(bool / 0-1 の 3D)。

Returns:
    dict: endpoints, branches, normal, isolated, total(骨格 voxel 総数),
          degree_hist(次数 -> 個数)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [medial_topology](../../../../examples_3d/medial_topology.py) — `py -3.11 examples_3d/medial_topology.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`medial`)

[distance_ridge](distance_ridge.md) · [skeletonize_vol](skeletonize_vol.md) · [medial_axis_points](medial_axis_points.md) · [medial_match](medial_match.md) · [skeleton_junctions3d](skeleton_junctions3d.md) · [skeleton_endpoints3d](skeleton_endpoints3d.md) · [skeleton_prune3d](skeleton_prune3d.md) · [skeleton_branches3d](skeleton_branches3d.md)

---
*Provenance: medial.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
