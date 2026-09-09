---
op: plane_sweep_depth
dim: 3d
category: plane_sweep_stereo
in: image2d × image2d
out: depth
examples: [plane_sweep_depth]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# plane_sweep_depth — 3D `plane_sweep_stereo` op

- **データ種**: `image2d × image2d` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.plane_sweep_depth(img_ref: 'np.ndarray', img_src: 'np.ndarray', K: 'np.ndarray', R: 'np.ndarray', t: 'np.ndarray', depth_candidates, window: 'int' = 1, normal=(0.0, 0.0, 1.0)) -> 'np.ndarray'` (実装を直接呼ぶなら `import plane_sweep; plane_sweep.plane_sweep_depth(img_ref: 'np.ndarray', img_src: 'np.ndarray', K: 'np.ndarray', R: 'np.ndarray', t: 'np.ndarray', depth_candidates, window: 'int' = 1, normal=(0.0, 0.0, 1.0)) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("plane_sweep_depth")`)

## 使い方

plane-sweep stereo で密な深度マップを推定。→ (H,W) depth。

各深度平面で src を ref へワープし、photo-consistency 最小の候補深度を画素ごとに選ぶ
(winner-take-all)。全候補で視野外の画素は NaN。fail-closed(空/非 2D/shape 不一致/非正深度)。

- ``img_ref`` / ``img_src``: 同形状の (H,W) グレースケール float。基準カメラは ``[I|0]``、source は
  ``P_src = K [R|t]``(``X_src = R X_ref + t``)。
- ``K``: 共通の (3,3) 内部行列(特異なら ``ValueError``)。
- ``depth_candidates``: 基準カメラ座標での正の有限な深度列(D 個)。返る深度は必ずこの中の
  どれかで、量子化誤差は候補間隔程度。候補は近距離を細かく(逆深度で等間隔)取るのが常道。
- ``window``: コストの box 集約サイズ(既定 1 = 画素ごとの絶対差)。2 以上で窓内 SAD を有効画素数で
  正規化した値になり、テクスチャの乏しい領域で安定するが段差はぼける。1 未満は ``ValueError``。
- ``normal``: 掃引平面の法線(既定 (0,0,1) = フロント平行)。

返り値は (H,W) float。全候補で src の視野外に写った画素(コスト ∞)は NaN。輝度が一定の領域では
全候補のコストが同点になり ``argmin`` が先頭候補を返すので、信頼度の無い深度が混じる。
コスト体 (D,H,W) そのものが要るときは同モジュールの ``cost_volume`` を使う。得られた深度は
``depth_to_points`` で点群化できる。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [plane_sweep_depth](../../../../examples_3d/plane_sweep_depth.py) — `py -3.11 examples_3d/plane_sweep_depth.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[depth_to_points](../transform/depth_to_points.md) · [tsdf_from_depth](../transform/tsdf_from_depth.md) · [to_points](../transform/to_points.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [depth_to_organized_points](../range_image/depth_to_organized_points.md) · [normals_from_depth](../range_image/normals_from_depth.md) · [occlusion_edges](../range_image/occlusion_edges.md) · [bearing_angle_image](../range_image/bearing_angle_image.md)

## 同カテゴリ(`plane_sweep_stereo`)

[warp_by_plane](warp_by_plane.md)

---
*Provenance: plane_sweep.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
