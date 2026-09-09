---
op: recover_pose
dim: 3d
category: two_view
in: image2d × image2d
out: pose
examples: [two_view_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# recover_pose — 3D `two_view` op

- **データ種**: `image2d × image2d` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.recover_pose(pts1, pts2, K1, K2=None, planar_tol=0.01)` (実装を直接呼ぶなら `import twoview; twoview.recover_pose(pts1, pts2, K1, K2=None, planar_tol=0.01)`、台帳から引くなら `ops3d.get("recover_pose")`)

## 使い方

対応点 + K から相対姿勢 (R,t) と 3D 構造を復元(cheirality で一意化)。→ (R, t_unit, points3d)。

t はスケール不定なので単位ベクトル。points3d は cam1 座標系(|t|=1 に対応するスケール)。

fail-closed: 平面(共平面 3D)/純回転シーンは本質行列分解の**退化配置**で、Sampson 残差 ~0 の
まま並進方向を誤って返す(見かけは完璧)。そうした入力は姿勢を復元できないため ValueError で
明示拒否する(ホモグラフィ分解を使うこと)。`planar_tol` はスケール不変な平面度しきい値
(`_planar_degeneracy_ratio` の戻り値がこれ未満なら退化と判定)。

手順:
- 入口検査(8 点以上、点数一致、(N,2) かつ有限)。
- 平面度: 正規化 DLT でホモグラフィ H を当て、対称転送残差の中央値を両画像の点の広がり(重心からの平均距離の和)で割った比を出す。これが ``planar_tol``(既定 1e-2)未満なら ``ValueError``。H が特異なら比 0 として同じく拒否。
- ``essential_8point`` → 4 候補 ``(R, ±t)`` へ分解 → 各候補で ``triangulate`` し、両カメラで深度 > 0 の点数が最大の候補を採る(同数なら先の候補)。

返り値: ``R`` (3,3)、``t`` (3,) 単位ベクトル、``points3d`` (N,3)。規約は cam1 = K1[I|0]、cam2 = K2[R|t] で ``X2 = R X1 + t``。``points3d`` は cam1 座標系で |t|=1 のスケール。視線が平行な対応は NaN 行になる。

- ``K2`` 省略時は ``K1`` を両画像に使う。
- 外れ値に無防備(RANSAC は行わない)。前段で誤対応を除く。
- 決定論的。GT 検証は ``pose_error``、残差は ``sampson_distance``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [two_view_pose](../../../../examples_3d/two_view_pose.py) — `py -3.11 examples_3d/two_view_pose.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`two_view`)

[fundamental_8point](fundamental_8point.md) · [essential_8point](essential_8point.md) · [triangulate](triangulate.md) · [sampson_distance](sampson_distance.md)

---
*Provenance: twoview.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
