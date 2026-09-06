---
op: fuse
dim: 3d
category: tsdf_fusion
in: depth
out: sdf
examples: [tsdf_fusion_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fuse — 3D `tsdf_fusion` op

- **データ種**: `depth` → `sdf`
- **呼び出し**: `import tsdf_fusion; tsdf_fusion.fuse(depths: 'Sequence[np.ndarray]', Ks: 'Sequence', Rs: 'Sequence', ts: 'Sequence', bounds: 'Bounds', res: 'int', trunc: 'float') -> 'Tuple[np.ndarray, np.ndarray]'` (または `ops3d.get("fuse")`)

## 使い方

深度列を new_volume + integrate で 1 つの TSDF volume に融合。返り値 (tsdf, weight)。

各フレームの (K,R,t) は world→camera。多視点で同じ表面を観測すると重みが積算され、
単フレームでは見えない(自己遮蔽の)面が別視点で埋まる。

- ``depths``: (H,W) 深度画像のリスト(カメラ Z 深度。0 以下・非有限の画素は未観測扱い)。
  サイズはフレームごとに異なってよい。
- ``Ks`` / ``Rs`` / ``ts``: 各フレームの (3,3) 内部行列・(3,3) 回転・(3,) 並進(``X_cam = R X + t``)。
- ``bounds``: ``((xmin,xmax),(ymin,ymax),(zmin,zmax))`` の world 領域(各軸 max > min)。
- ``res``: 一辺の voxel 数(正の int)。volume は ``res×res×res``、軸順は (x,y,z) の ``indexing='ij'``。
- ``trunc``: 切り詰め距離(world 単位、正の有限値)。voxel サイズの数倍が目安で、小さすぎると
  表面の両側に観測が乗らず、大きすぎると薄い構造の表裏が混ざる。

返り値: ``tsdf`` (res,res,res) float32(未観測 +1.0、表面手前が正・奥が負、[-1,1])と ``weight``
(res,res,res) float32(観測回数)。表面点は ``extract_surface_points(tsdf, weight, bounds, res)``
で取り出す。fail-closed: フレーム 0 枚、リスト長の不一致、退化 bounds、非正の ``res`` /
``trunc`` は ``ValueError``。統合の詳細(遮蔽領域を更新しない規則)は ``integrate`` を参照。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [tsdf_fusion_demo](../../../../examples_3d/tsdf_fusion_demo.py) — `py -3.11 examples_3d/tsdf_fusion_demo.py`

## 型が繋がる次の op(`sdf` を入力に取れる)

[sdf_to_occupancy](../transform/sdf_to_occupancy.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [integrate](integrate.md) · [extract_surface_points](extract_surface_points.md) · [query_distance](../occupancy/query_distance.md) · [sdf_union](../sdf_csg/sdf_union.md) · [sdf_intersect](../sdf_csg/sdf_intersect.md) · [sdf_subtract](../sdf_csg/sdf_subtract.md)

## 同カテゴリ(`tsdf_fusion`)

[integrate](integrate.md) · [extract_surface_points](extract_surface_points.md)

---
*Provenance: tsdf_fusion.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
