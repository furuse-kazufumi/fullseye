---
op: sdf_subtract
dim: 3d
category: sdf_csg
in: sdf × sdf
out: sdf
examples: [sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# sdf_subtract — 3D `sdf_csg` op

- **データ種**: `sdf × sdf` → `sdf`
- **呼び出し**: `import sdf_ops; sdf_ops.sdf_subtract(a, b)` (または `ops3d.get("sdf_subtract")`)

## 使い方

差集合 A\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_smooth_union](sdf_smooth_union.md)

## 同カテゴリ(`sdf_csg`)

[sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_smooth_union](sdf_smooth_union.md) · [sdf_offset](sdf_offset.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
