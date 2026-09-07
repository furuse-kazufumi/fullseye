---
op: sdf_offset
dim: 3d
category: sdf_csg
in: sdf
out: sdf
examples: [sfm_recon]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# sdf_offset — 3D `sdf_csg` op

- **データ種**: `sdf` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.sdf_offset(sdf, r)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.sdf_offset(sdf, r)`、台帳から引くなら `ops3d.get("sdf_offset")`)

## 使い方

SDF のゼロ等値面を距離 ``r`` だけ法線方向へ動かす = ``sdf - r``(r>0 膨張, r<0 収縮)。

新しいゼロ集合は旧 ``sdf == r`` の等値面。全点で距離が一様に ``r`` シフトするので、距離場
としての性質(勾配ノルム 1)は保たれる。プリミティブの厚み付け(丸めた殻)や配管の
クリアランス確保に使う。

計算: ``np.asarray(sdf, float64) - float(r)``。``r`` はスカラのみ(配列を渡すと
``float()`` で ``TypeError``)。単位は ``sdf`` の距離単位と同じ。``r = 0`` は恒等。
shape・NaN・inf の検査はしない(``inf - r = inf`` で契約どおり伝播)。

幾何的意味: 厳密な SDF に対しては Minkowski 和(``r > 0`` で半径 ``r`` の球で
膨張、``r < 0`` で収縮)に一致する。``sphere_sdf(g, c, R)`` に ``r`` を掛けると
``sphere_sdf(g, c, R + r)`` と厳密に等しい。``box_sdf`` の膨張では角が丸くなる
(ユークリッド膨張なので、箱が大きくなるのではなく角 R = r の丸箱になる)。

注意:
- 収縮(``r < 0``)で ``|r|`` が最小内接半径を超えると形は消える(全要素が正)。
  エラーにはならない。
- ``sdf_union`` / ``sdf_intersect`` の**内側**は真の距離の下界なので、合成後に
  ``r < 0`` で収縮すると、重なり領域で実際より多く削れることがある。
- 厚さ ``t`` の殻: ``sdf_subtract(sdf, sdf_offset(sdf, -t))``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [sfm_recon](../../../../examples_3d/sfm_recon.py) — `py -3.11 examples_3d/sfm_recon.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](sdf_union.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_union](sdf_union.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
