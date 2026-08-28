---
op: fuse
dim: 3d
category: tsdf_fusion
in: depth
out: sdf
examples: [tsdf_fusion_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fuse — 3D `tsdf_fusion` op

- **データ種**: `depth` → `sdf`
- **呼び出し**: `import tsdf_fusion; tsdf_fusion.fuse(depths: 'Sequence[np.ndarray]', Ks: 'Sequence', Rs: 'Sequence', ts: 'Sequence', bounds: 'Bounds', res: 'int', trunc: 'float') -> 'Tuple[np.ndarray, np.ndarray]'` (または `ops3d.get("fuse")`)

## 使い方

深度列を new_volume + integrate で 1 つの TSDF volume に融合。返り値 (tsdf, weight)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [tsdf_fusion_demo](../../../../examples_3d/tsdf_fusion_demo.py) — `py -3.11 examples_3d/tsdf_fusion_demo.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](integrate.md) · [extract_surface_points](extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`tsdf_fusion`)

[integrate](integrate.md) · [extract_surface_points](extract_surface_points.md)

---
*Provenance: tsdf_fusion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
