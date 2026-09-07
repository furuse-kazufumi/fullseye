---
op: sphere_sdf
dim: 3d
category: sdf_csg
in: coordgrid
out: sdf
examples: [annotate3d_figure, gear_metrology, molecule_atom_count, procedural_hand, render_beauty, sdf_csg, sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sphere_sdf — 3D `sdf_csg` op

- **データ種**: `coordgrid` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.sphere_sdf(grid, center, R)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.sphere_sdf(grid, center, R)`、台帳から引くなら `ops3d.get("sphere_sdf")`)

## 使い方

球の符号付き距離場: ``|p - center| - R``(内側負・外側正)。

``grid`` は最終軸が 3 の座標配列 (..., 3)(``grid_coords`` の出力や (N,3) 点群)。
``center`` は長さ3、``R>=0`` は半径。返り値の shape は ``grid.shape[:-1]``。厳密な SDF
(勾配ノルム 1)。``sdf_offset(sphere_sdf(g,c,R), r) == sphere_sdf(g,c,R+r)``。

Raises ValueError for R<0 or malformed grid/center。

計算: ``np.linalg.norm(grid - center, axis=-1) - R``。座標の単位はそのまま距離の
単位になる(``grid_coords`` の world 座標を渡せば world 単位)。座標の成分順は
``grid`` の最終軸の順(``grid_coords`` なら ``(x, y, z)``)で、``center`` も同じ順。

引数と検証(``ValueError``):
- ``grid``: 最終軸が 3 の float 配列 ``(..., 3)``(1-D の ``(3,)`` も可。0-D や
  最終軸が 3 以外は拒否)。
- ``center``: 要素数 3(``reshape(3)`` できなければ numpy の ``ValueError``)。
- ``R``: ``float()`` できるスカラ。回転行列などを渡した場合も ``ValueError``
  (この引数は半径であって姿勢ではない)。``R < 0`` は拒否、``R = 0`` は
  中心からの距離場そのもの。

返り値: ``grid.shape[:-1]`` の float64(``grid_coords`` の出力なら
``(nx, ny, nz)``)。中心で ``-R``、表面で 0、外側で正。

使いどころ: ``grid_coords`` で格子 → ``sphere_sdf`` / ``box_sdf`` → ``sdf_union`` /
``sdf_subtract`` で CSG → ``<= 0`` を占有として marching cubes(``voxel_to_mesh``
に ``-sdf`` を渡し ``iso=0`` 相当で等値面)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate3d_figure](../../../../examples_3d/annotate3d_figure.py) — `py -3.11 examples_3d/annotate3d_figure.py`
- [gear_metrology](../../../../examples_3d/gear_metrology.py) — `py -3.11 examples_3d/gear_metrology.py`
- [molecule_atom_count](../../../../examples_3d/molecule_atom_count.py) — `py -3.11 examples_3d/molecule_atom_count.py`
- [procedural_hand](../../../../examples_3d/procedural_hand.py) — `py -3.11 examples_3d/procedural_hand.py`
- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`
- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
