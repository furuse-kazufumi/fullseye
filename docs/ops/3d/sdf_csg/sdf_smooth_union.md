---
op: sdf_smooth_union
dim: 3d
category: sdf_csg
in: sdf × sdf
out: sdf
examples: [render_beauty]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sdf_smooth_union — 3D `sdf_csg` op

- **データ種**: `sdf × sdf` → `sdf`
- **呼び出し**: `import sdf_ops; sdf_ops.sdf_smooth_union(a, b, k)` (または `ops3d.get("sdf_smooth_union")`)

## 使い方

滑らかに丸めた和集合(polynomial smooth-min)。``k>0`` で継ぎ目を半径 ~k で丸める。

Inigo Quilez の二次多項式 smin:
    ``h = clip(0.5 + 0.5*(b-a)/k, 0, 1)``,  ``smin = mix(b,a,h) - k*h*(1-h)``。
性質: (1) 対称 ``smin(a,b)=smin(b,a)``、(2) ``smin <= min(a,b)``(継ぎ目でくぼむ)、
(3) **k→0 で min(a,b) に一致**(= 硬い ``sdf_union``)、(4) 1 次同次
``smin(s*a,s*b,s*k)=s*smin(a,b,k)``(スケール整合)。

``k`` は距離次元の丸め半径。硬い min が欲しければ ``sdf_union`` を使う。
``±inf`` を含む入力(``esdf`` の「全自由なら +inf」契約との相互運用)では、
ブレンド帯 ``|a-b|<k`` が退化するため厳密に ``min(a,b)`` を返す。
Raises ValueError for k<=0(0 除算を避けるため fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md) · [sdf_offset](sdf_offset.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
