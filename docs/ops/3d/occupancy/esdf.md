---
op: esdf
dim: 3d
category: occupancy
in: voxel
out: sdf
examples: [occupancy_esdf]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# esdf — 3D `occupancy` op

- **データ種**: `voxel` → `sdf`
- **呼び出し**: `import occupancy; occupancy.esdf(occupancy, voxel_size=1.0)` (または `ops3d.get("esdf")`)

## 使い方

占有格子 → Euclidean 符号付き距離場 (ESDF)(外=+ 最近占有まで, 内=- 最近自由まで)。

``scipy.ndimage.distance_transform_edt`` を自由側(外)と占有側(内)に別々にかけ、
``d_out - d_in`` で符号を付ける。``voxel_size`` はボクセル辺長(等方スカラ or 異方
長さ3。EDT の ``sampling`` に渡す)で、返る距離は world 単位。全自由なら +inf、全占有
なら -inf(honest: 最近対辺が存在しない)。ゼロ交差は占有/自由ボクセル**中心の中間**に
落ちるため、境界セル中心の |ESDF| は約 1 ボクセル(下流テストの許容根拠)。

Raises ValueError for voxel_size<=0.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [occupancy_esdf](../../../../examples_3d/occupancy_esdf.py) — `py -3.11 examples_3d/occupancy_esdf.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`occupancy`)

[occupancy_grid](occupancy_grid.md) · [inflate](inflate.md) · [query_distance](query_distance.md)

---
*Provenance: occupancy.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
