---
op: edt_jfa
dim: 3d
category: feature
in: voxel
out: sdf
gpu: true
examples: [diff_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# edt_jfa — 3D `feature` op

- **データ種**: `voxel` → `sdf`
- **呼び出し**: `import match3d; match3d.edt_jfa(seed_bool, device='cpu')` (または `ops3d.get("edt_jfa")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D ユークリッド距離変換 = Jump Flooding Algorithm(GPU)。各 voxel → 最近 seed 距離。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [diff_features](../../../../examples_3d/diff_features.py) — `py -3.11 examples_3d/diff_features.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
