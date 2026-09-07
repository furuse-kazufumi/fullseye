---
op: torus_sdf
dim: 3d
category: sdf_csg
in: coordgrid
out: sdf
examples: [sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# torus_sdf — 3D `sdf_csg` op

- **データ種**: `coordgrid` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.torus_sdf(grid, center, axis, major_radius, minor_radius)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.torus_sdf(grid, center, axis, major_radius, minor_radius)`、台帳から引くなら `ops3d.get("torus_sdf")`)

## 使い方

トーラス(ドーナツ)の**厳密**な符号付き距離場(内側負・外側正)。

``sdf(p) = ‖(r - major_radius, t)‖ - minor_radius``(``r`` は軸からの半径、``t`` は
軸方向の距離)。芯線が半径 ``major_radius`` の円で、その周りに半径 ``minor_radius``
の管が付いた形なので、**フィレット(隅の丸み)の解析形**としてそのまま使える。

引数と検証(``ValueError``):
- ``grid`` / ``center`` / ``axis``: :func:`cylinder_sdf` と同じ(軸はドーナツの穴の向き)。
- ``major_radius``: 芯線の半径(負は拒否)。
- ``minor_radius``: 管の半径(負は拒否)。``minor_radius >= major_radius`` だと穴が
  潰れた形になるが、距離場としては正しいので**拒否しない**。

返り値: ``grid.shape[:-1]`` の float64。

使いどころ: ``sdf_subtract`` で内隅にフィレットを削り出す / ``sdf_union`` で O リング溝の
形を作る。角を丸めるだけなら ``sdf_smooth_union`` のほうが手軽だが、あちらは丸みの
半径が形状に依存する —— **半径を設計値として持ちたいときはこちら**。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
