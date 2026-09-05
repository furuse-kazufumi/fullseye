---
op: grid_coords
dim: 3d
category: sdf_csg
in: 
out: coordgrid
examples: [gear_metrology, molecule_atom_count, procedural_hand, render_beauty, sdf_csg, sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# grid_coords — 3D `sdf_csg` op

- **データ種**: `なし` → `coordgrid`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import sdf_ops; sdf_ops.grid_coords(bounds, res)` (または `ops3d.get("grid_coords")`)

## 使い方

CSG 評価用のボクセル中心座標グリッドを作る(occupancy と同じ格子規約)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gear_metrology](../../../../examples_3d/gear_metrology.py) — `py -3.11 examples_3d/gear_metrology.py`
- [molecule_atom_count](../../../../examples_3d/molecule_atom_count.py) — `py -3.11 examples_3d/molecule_atom_count.py`
- [procedural_hand](../../../../examples_3d/procedural_hand.py) — `py -3.11 examples_3d/procedural_hand.py`
- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`
- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`coordgrid` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md)

## 同カテゴリ(`sdf_csg`)

[sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md) · [sdf_smooth_union](sdf_smooth_union.md) · [sdf_offset](sdf_offset.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
