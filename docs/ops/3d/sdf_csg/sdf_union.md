---
op: sdf_union
dim: 3d
category: sdf_csg
in: sdf × sdf
out: sdf
examples: [gear_metrology, render_beauty, sdf_csg]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# sdf_union — 3D `sdf_csg` op

- **データ種**: `sdf × sdf` → `sdf`
- **呼び出し**: `import fullseye as fs; fs.ledger.sdf_union(a, b)` (実装を直接呼ぶなら `import sdf_ops; sdf_ops.sdf_union(a, b)`、台帳から引くなら `ops3d.get("sdf_union")`)

## 使い方

2 SDF の和集合 A∪B = 要素ごとの min(a, b)(内側=負がどちらかにあれば内側)。

ゼロ等値面は両形状の境界の和集合に厳密一致。外側では厳密な SDF(最近表面までの距離)、
内側は保守的下界。``a``/``b`` はブロードキャスト整合すればよい。

計算: ``np.minimum(np.asarray(a, float64), np.asarray(b, float64))``。それ以外の
検査はしない — shape がブロードキャストできなければ numpy の ``ValueError``、
NaN は要素ごとに伝播する(``np.minimum`` は NaN を返す)。``±inf`` は厳密に伝播
(``min(a, +inf) = a``:``esdf`` の「全自由なら +inf」契約と相互運用できる)。

入力: 同一グリッド上で評価した 2 つの SDF(``sphere_sdf`` / ``box_sdf`` /
``esdf`` の出力など、内側負・外側正)。形は ``grid_coords`` の
``(nx, ny, nz)`` でも ``(N,)`` の点列でもよい。距離の単位は入力と同じ。

返り値: ブロードキャスト後の shape の float64。ゼロ交差(``<= 0``)が A∪B の
占有。

注意: 内側の値は「どちらか近い方の表面までの距離」の下界であり、重なり領域では
真の距離より小さめ(絶対値が大きめ)に出る。CSG の標準的性質で、等値面抽出
(marching cubes)や ``sdf_offset`` の膨張には影響しない。継ぎ目を丸めたい場合は
``sdf_smooth_union``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gear_metrology](../../../../examples_3d/gear_metrology.py) — `py -3.11 examples_3d/gear_metrology.py`
- [render_beauty](../../../../examples_3d/render_beauty.py) — `py -3.11 examples_3d/render_beauty.py`
- [sdf_csg](../../../../examples_3d/sdf_csg.py) — `py -3.11 examples_3d/sdf_csg.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](../tsdf_fusion/integrate.md) · [extract_surface_points](../tsdf_fusion/extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_intersect](sdf_intersect.md) · [sdf_subtract](sdf_subtract.md) · [sdf_smooth_union](sdf_smooth_union.md)

## 同カテゴリ(`sdf_csg`)

[grid_coords](grid_coords.md) · [sphere_sdf](sphere_sdf.md) · [box_sdf](box_sdf.md) · [plane_sdf](plane_sdf.md) · [cylinder_sdf](cylinder_sdf.md) · [torus_sdf](torus_sdf.md) · [capsule_sdf](capsule_sdf.md) · [sdf_intersect](sdf_intersect.md)

---
*Provenance: sdf_ops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
