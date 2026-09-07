---
op: cylinder_sdf
dim: 3d
category: sdf_csg
in: coordgrid
out: sdf
examples: [sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# cylinder_sdf — 3D `sdf_csg` op

- **データ種**: `coordgrid` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.cylinder_sdf(grid, center, axis, radius, height)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.cylinder_sdf(grid, center, axis, radius, height)`、台帳から引くなら `ops3d.get("cylinder_sdf")`)

## 使い方

有限長の円柱(両端が平らな蓋)の**厳密**な符号付き距離場(内側負・外側正)。

軸方向の距離 ``t`` と軸からの半径 ``r`` に分け、``q = (r - radius, |t| - height/2)``
として ``outside = ‖max(q, 0)‖``、``inside = min(max(q), 0)``、``sdf = outside + inside``。
これは ``box_sdf`` と同じ Quilez 流の構成を「(半径, 軸)の 2-D 断面」に適用したもので、
側面・蓋・角(縁)のいずれに対しても真のユークリッド距離になる。

引数と検証(``ValueError``):
- ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``。
- ``center``: 円柱の**中心**(端面ではなく重心。要素数 3)。
- ``axis``: 軸の向き(要素数 3、零ベクトル・NaN は拒否。長さは自動正規化)。
- ``radius``: 半径 > 0 相当のスカラ(``0`` は軸線そのもの、負は拒否)。
- ``height``: 全長のスカラ(``center`` から ±height/2。負は拒否)。

返り値: ``grid.shape[:-1]`` の float64。

使いどころ: **貫通穴は ``sdf_subtract(part, cylinder_sdf(...))``**(``height`` を部品より
長くして端面の縁を残さない)。ボス・ピン・シャフトは ``sdf_union``。無限長の円柱が
要るなら ``height`` を十分大きく取る(端面が評価域の外に出れば側面だけが効く)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
