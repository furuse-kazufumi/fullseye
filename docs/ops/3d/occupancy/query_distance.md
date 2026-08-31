---
op: query_distance
dim: 3d
category: occupancy
in: sdf × points
out: measurement
examples: [occupancy_esdf]
author: Kazufumi Furuse
license: Apache-2.0
version: 0  # fullseye lib version this note was generated for
---

# query_distance — 3D `occupancy` op

- **データ種**: `sdf × points` → `measurement`
- **呼び出し**: `import occupancy; occupancy.query_distance(esdf_grid, bounds, res, query_points, mode='trilinear')` (または `ops3d.get("query_distance")`)

## 使い方

任意 world 座標 (M,3) での ESDF 値 (M,) を返す(``mode``='trilinear' 補間 or 'nearest')。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [occupancy_esdf](../../../../examples_3d/occupancy_esdf.py) — `py -3.11 examples_3d/occupancy_esdf.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`occupancy`)

[occupancy_grid](occupancy_grid.md) · [esdf](esdf.md) · [inflate](inflate.md)

---
*Provenance: occupancy.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
