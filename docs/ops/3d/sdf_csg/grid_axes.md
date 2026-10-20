---
op: grid_axes
dim: 3d
category: sdf_csg
in: 
out: coordgrid
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# grid_axes — 3D `sdf_csg` op

- **データ種**: `なし` → `coordgrid`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.grid_axes(bounds, res)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.grid_axes(bounds, res)`、台帳から引くなら `ops3d.get("grid_axes")`)

## 使い方

Return three 1-D voxel-centre axes for memory-efficient primitive evaluation.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`coordgrid` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
