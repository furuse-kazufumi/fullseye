---
op: occupancy_grid
dim: 3d
category: occupancy
in: points
out: voxel
examples: [occupancy_esdf]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# occupancy_grid — 3D `occupancy` op

- **データ種**: `points` → `voxel`
- **呼び出し**: `import occupancy; occupancy.occupancy_grid(points, bounds, res)` (または `ops3d.get("occupancy_grid")`)

## 使い方

点群 (N,3) → 3-D 占有ボクセル格子 (res,res,res) bool(点の落ちた voxel を占有)。

``bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax))`` が格子の張る体積、``res`` は各軸の
ボクセル数(立方 res³)。ボクセルは半開区間 [lo+i/res*span, lo+(i+1)/res*span) で、
上端 (frac==1) の点は最終ボクセルに含める。**bounds 外の点は落とす**(端セルへ
clamp すると境界に幻の障害物が積もるため)。match3d.points_to_voxel が密度(float)
を作るのに対し、これは planning 用の占有(bool)を作る点が固有。

Raises ValueError for res<=0, non-(N,3) points, or degenerate bounds.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [occupancy_esdf](../../../../examples_3d/occupancy_esdf.py) — `py -3.11 examples_3d/occupancy_esdf.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`occupancy`)

[esdf](esdf.md) · [inflate](inflate.md) · [query_distance](query_distance.md)

---
*Provenance: occupancy.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
