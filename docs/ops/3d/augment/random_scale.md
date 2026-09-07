---
op: random_scale
dim: 3d
category: augment
in: points
out: points
examples: [augment_pointcloud]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# random_scale — 3D `augment` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.random_scale(points, lo: 'float', hi: 'float', seed: 'int' = 0) -> 'Tuple[np.ndarray, float]'` (実装を直接呼ぶなら `import pcl_augment; pcl_augment.random_scale(points, lo: 'float', hi: 'float', seed: 'int' = 0) -> 'Tuple[np.ndarray, float]'`、台帳から引くなら `ops3d.get("random_scale")`)
- **台帳経由の戻り値**: `fullseye.ledger.random_scale(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.random_scale.raw(...)`、または `pcl_augment.random_scale` を直接呼ぶ。

## 使い方

一様スケール ``s ~ U(lo, hi)`` を原点まわりに適用し ``(scaled, s)`` を返す。

``scaled = points * s``。bbox 対角長はちょうど ``s`` 倍になる(``s > 0`` なので
``max``/``min`` が共に ``s`` 倍 → 対角 ``‖max-min‖`` も ``s`` 倍)。物体スケールの
ばらつき(距離/センサ倍率)を学習に注入する。``0 < lo <= hi`` を要求(fail-closed)。

``lo <= 0`` または ``hi < lo`` は ``ValueError``(``lo == hi`` は許され常に ``s = lo``)。
原点まわりの拡大なので、雲が原点から離れていれば重心も ``s`` 倍の位置へ動く(位置と
大きさが同時に変わる)。大きさだけ変えたいなら事前に重心を原点へ寄せる。``s`` は
Python float、返り値の点群は float64。``seed`` で決定論的。空入力は空を返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [augment_pointcloud](../../../../examples_3d/augment_pointcloud.py) — `py -3.11 examples_3d/augment_pointcloud.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`augment`)

[jitter](jitter.md) · [random_rotation](random_rotation.md) · [random_dropout](random_dropout.md) · [elastic_deform](elastic_deform.md) · [cutout](cutout.md)

---
*Provenance: pcl_augment.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
