---
op: random_rotation
dim: 3d
category: augment
in: points
out: points
examples: [augment_pointcloud, sh_descriptor_retrieval, shape_retrieval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# random_rotation — 3D `augment` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.random_rotation(points, seed: 'int' = 0, max_angle: 'Optional[float]' = None) -> 'Tuple[np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import pcl_augment; pcl_augment.random_rotation(points, seed: 'int' = 0, max_angle: 'Optional[float]' = None) -> 'Tuple[np.ndarray, np.ndarray]'`、台帳から引くなら `ops3d.get("random_rotation")`)
- **台帳経由の戻り値**: `fullseye.ledger.random_rotation(...)` は**宣言 out 型 `points` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.random_rotation.raw(...)`、または `pcl_augment.random_rotation` を直接呼ぶ。
  - 本体の返り: `(points, R)`

## 使い方

ランダム回転を適用し ``(rotated, R)`` を返す(視点変化の模倣)。

``R`` は正規直交・``det=+1``(``rotated = points @ R.T`` = 各点に ``R`` を左作用、
逆変換は ``rotated @ R``)。``max_angle=None`` なら Shoemake 法で一様ランダム回転、
``max_angle`` 指定(ラジアン, 期待 ``[0, π]``)なら軸を球面一様・角を ``[0, max_angle]``
一様に取り、回転角を制限する(``arccos((tr R -1)/2) ≤ max_angle`` を厳密に保証)。

``max_angle < 0`` は ``ValueError``、``max_angle=0`` は単位行列。単位はラジアン(度で
渡すと桁違いに大きくなる)。``max_angle=None`` の一様回転は上限 π までの大きな回転も
普通に出るので、視点変化の範囲を絞りたいときは ``max_angle`` を使う。回転は原点まわり
で、雲が原点から離れていれば重心も動く。``R`` の規約 ``rotated = points @ R.T`` は
``register_fpfh``・``register_shot`` が返す ``dst ≈ src @ R.T + t`` と同じ向きなので、
推定結果との角度誤差は ``arccos((tr(R_est·Rᵀ)-1)/2)`` で測れる。``seed`` で決定論的
(同 seed なら同じ ``R``)。返り値は float64 の ``(N,3)`` と ``(3,3)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [augment_pointcloud](../../../../examples_3d/augment_pointcloud.py) — `py -3.11 examples_3d/augment_pointcloud.py`
- [sh_descriptor_retrieval](../../../../examples_3d/sh_descriptor_retrieval.py) — `py -3.11 examples_3d/sh_descriptor_retrieval.py`
- [shape_retrieval](../../../../examples_3d/shape_retrieval.py) — `py -3.11 examples_3d/shape_retrieval.py`

## 型が繋がる次の op(`points` を入力に取れる)

[points_to_voxel](../transform/points_to_voxel.md) · [gaussians_to_voxel](../transform/gaussians_to_voxel.md) · [estimate_point_normals](../transform/estimate_point_normals.md) · [to_points](../transform/to_points.md) · [match_points_ncc](../match_localize/match_points_ncc.md) · [match_pca](../match_pose/match_pca.md) · [moment_axes](../match_pose/moment_axes.md) · [icp_point2point_3d](../refine/icp_point2point_3d.md)

## 同カテゴリ(`augment`)

[jitter](jitter.md) · [random_scale](random_scale.md) · [random_dropout](random_dropout.md) · [elastic_deform](elastic_deform.md) · [cutout](cutout.md)

---
*Provenance: pcl_augment.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
