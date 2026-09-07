---
op: sdf_subtract
dim: 3d
category: sdf_csg
in: sdf × sdf
out: sdf
examples: [sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sdf_subtract — 3D `sdf_csg` op

- **データ種**: `sdf × sdf` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.sdf_subtract(a, b)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.sdf_subtract(a, b)`、台帳から引くなら `ops3d.get("sdf_subtract")`)

## 使い方

差集合 A\B = max(a, -b)(A の内側 かつ B の外側 = ``-b`` の内側)。

``b`` の符号反転は「B の外を内、B の内を外」に反転する(相補集合)ので、A との積が
A から B をくり抜いた形になる。非可換: ``sdf_subtract(a,b) != sdf_subtract(b,a)``。

計算: ``np.maximum(np.asarray(a, float64), -np.asarray(b, float64))``。
``sdf_intersect(a, -b)`` と同じ。shape はブロードキャスト整合が必要(不整合なら
numpy の ``ValueError``)で、それ以外の検査はしない。NaN は伝播、``±inf`` も
厳密に伝播する(``b = +inf`` の点は ``-b = -inf`` なので ``a`` がそのまま残る =
「B が無限に遠い」点は A のまま)。

入力: 同一グリッド上の 2 つの SDF(内側負・外側正)。``a`` が残す形、``b`` が
くり抜く形。距離の単位は入力と同じ。

返り値: ブロードキャスト後の shape の float64。``<= 0`` が A\B の占有。

注意:
- B の内側で値は ``-b > 0``(B の表面までの距離)になるので、くり抜いた穴の内壁
  までの距離は外側では厳密、A の内側では下界(CSG の標準的性質)。
- B が A を完全に含むと全要素が正(空集合)。エラーにはならない。
- 穴あけ・ポケット加工・殻(``a`` と ``sdf_offset(a, -t)`` の差で厚さ ``t`` の
  殻)に使う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_smooth_union](sdf_smooth_union.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
