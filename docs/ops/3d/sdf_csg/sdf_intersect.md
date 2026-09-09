---
op: sdf_intersect
dim: 3d
category: sdf_csg
in: sdf × sdf
out: sdf
examples: [gear_metrology, render_beauty, sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sdf_intersect — 3D `sdf_csg` op

- **データ種**: `sdf × sdf` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.sdf_intersect(a, b)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.sdf_intersect(a, b)`、台帳から引くなら `ops3d.get("sdf_intersect")`)

## 使い方

2 SDF の積集合 A∩B = 要素ごとの max(a, b)(両方の内側でのみ内側)。

ゼロ等値面は両境界の共通部分。外側で厳密 SDF、内側は保守的下界。

計算: ``np.maximum(np.asarray(a, float64), np.asarray(b, float64))``。要素ごとの
max なので、ある点が A∩B の内側(負)になるのは ``a < 0`` かつ ``b < 0`` のときだけ。
shape はブロードキャスト整合していればよく(不整合なら numpy の ``ValueError``)、
それ以外の検査はしない。NaN は伝播、``±inf`` は厳密に伝播(``max(a, -inf) = a``)。

入力: 同一グリッド上で評価した 2 つの SDF(``sphere_sdf`` / ``box_sdf`` /
``esdf`` の出力など、内側負・外側正)。距離の単位は入力と同じ。

返り値: ブロードキャスト後の shape の float64。``<= 0`` が A∩B の占有。

注意:
- **外側の値は真の距離より小さく出うる**: 交差の外側で、点が A の外かつ B の外の
  とき ``max(a, b)`` は「遠い方の表面まで」の距離で、A∩B の表面はそれより遠い
  ことがある(下界)。ゼロ等値面は厳密。
- 共通部分が無ければ全要素が正(占有 0)になり、エラーにはならない。
- 箱で球を切る・2 つの箱で角柱を作る、といった CSG の「切り出し」に使う。
  A から B を抜くのは ``sdf_subtract``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gear_metrology](../../../../examples_3d/gear_metrology.py) — `py -3.11 examples_3d/gear_metrology.py`
- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_subtract](sdf_subtract.md) · [sdf_smooth_union](sdf_smooth_union.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
