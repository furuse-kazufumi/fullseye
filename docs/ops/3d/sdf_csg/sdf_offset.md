---
op: sdf_offset
dim: 3d
category: sdf_csg
in: sdf
out: sdf
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# sdf_offset — 3D `sdf_csg` op

- **データ種**: `sdf` → `sdf`
- **呼び出し**: `import sdf_ops; sdf_ops.sdf_offset(sdf, r)` (または `ops3d.get("sdf_offset")`)

## 使い方

SDF のゼロ等値面を距離 ``r`` だけ法線方向へ動かす = ``sdf - r``(r>0 膨張, r<0 収縮)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md) · [sdf_smooth_union](sdf_smooth_union.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
