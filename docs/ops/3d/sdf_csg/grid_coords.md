---
op: grid_coords
dim: 3d
category: sdf_csg
in: 
out: coordgrid
examples: [gear_metrology, molecule_atom_count, procedural_hand, render_beauty, sdf_csg, sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# grid_coords — 3D `sdf_csg` op

- **データ種**: `なし` → `coordgrid`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import sdf_ops; sdf_ops.grid_coords(bounds, res)` (または `ops3d.get("grid_coords")`)
- **台帳経由の戻り値**: `fullseye.ledger.grid_coords(...)` は**宣言 out 型 `coordgrid` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.grid_coords.raw(...)`、または `sdf_ops.grid_coords` を直接呼ぶ。

## 使い方

CSG 評価用のボクセル中心座標グリッドを作る(occupancy と同じ格子規約)。

``bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax))``、``res`` は各軸のボクセル数(スカラ=立方
or 長さ3)。voxel ``i`` の中心は world ``lo + (i+0.5)/res * span``(``occupancy.query_distance``
の ``c=(q-lo)/span*res-0.5`` と整合 = 中心アライン)。返り値は
``coords`` shape ``(nx,ny,nz,3)`` と ``extent=(xmin,xmax,ymin,ymax,zmin,zmax)``。

こうして作った座標に ``sphere_sdf``/``box_sdf`` を評価し CSG 合成すれば、``recon3d`` の
marching cubes や ``occupancy`` のゼロ交差抽出へそのまま渡せる。

Raises ValueError for degenerate bounds or res<=0。

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

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md)

## 同カテゴリ(`sdf_csg`)

[sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
