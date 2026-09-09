---
op: capsule_sdf
dim: 3d
category: sdf_csg
in: coordgrid
out: sdf
examples: [procedural_hand, sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# capsule_sdf — 3D `sdf_csg` op

- **データ種**: `coordgrid` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.capsule_sdf(grid, a, b, radius)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.capsule_sdf(grid, a, b, radius)`、台帳から引くなら `ops3d.get("capsule_sdf")`)

## 使い方

線分 ``a``–``b`` を半径 ``radius`` で太らせたカプセルの**厳密**な符号付き距離場。

``sdf(p) = ‖p - (a + clamp(((p-a)·(b-a))/‖b-a‖², 0, 1)·(b-a))‖ - radius``。
線分への最短距離そのものなので**全空間で勾配ノルム 1**(円柱と違い端が丸いぶん、
角が無く厳密)。リブ・配管・骨・ワイヤ・工具の掃引体積の近似に向く。

引数と検証(``ValueError``):
- ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``。
- ``a`` / ``b``: 芯線の端点(要素数 3)。``a == b`` なら球(``sphere_sdf`` と一致)。
- ``radius``: 太さ(負は拒否)。

返り値: ``grid.shape[:-1]`` の float64。

使いどころ: 工具の到達性を「工具の掃引体積が部品と交わらないか」で見るとき、工具を
カプセルで置いて ``sdf_intersect`` の最小値が正かを見る。骨梁・血管・繊維の合成にも。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [procedural_hand](../../../../examples_3d/procedural_hand.py) — `py -3.11 examples_3d/procedural_hand.py`
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
