---
op: dlt_pose
dim: 3d
category: pose_estimation
in: points × keypoints
out: pose
examples: [pnp_pose_outliers, pose_estimation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dlt_pose — 3D `pose_estimation` op

- **データ種**: `points × keypoints` → `pose`
- **呼び出し**: `import pnp3d; pnp3d.dlt_pose(points_3d, points_2d, K)` (または `ops3d.get("dlt_pose")`)

## 使い方

DLT で 3D-2D 対応からカメラ姿勢を復元(K 既知)。→ (R (3,3), t (3,))。6 点以上必要。

:func:`pnp_pose` の (R, t) 部分(正規化 DLT + 平面 PnP 分岐 + LM 精密化)。再投影
RMS も要るなら :func:`pnp_pose` を使う。共平面入力(チェッカーボード等)は平面 PnP へ
自動で振り分ける(旧実装は fail-closed で拒否していたが、正しく解けるので解く)。

手順(モジュール関数 ``pnp3d.pnp_pose`` を ``refine=True`` で呼ぶ):
- 画素を ``K⁻¹`` で正規化画像座標へ、3D 点は Hartley 正規化(重心を原点、平均距離 √3)して DLT(12 未知数の SVD)を解く。
- 共平面度(共分散の最小/最大固有値比の平方根)が 0.05 未満なら平面 PnP(ホモグラフィ分解)も候補に加え、厳密に平面(3 番目の広がりが 0)なら DLT を省く。
- 各候補を再投影誤差の Levenberg-Marquardt(最大 30 反復)で精密化し、前方点(深度 > 0)の割合が最大、同点なら再投影 RMS が最小の候補を採る。

返り値: ``R`` (3,3) 回転(det=+1)、``t`` (3,)(世界座標と同じ単位)。規約 ``Xc = R X + t``、``x ≅ K Xc``。

Raises ``ValueError``: ``points_2d`` が (N,2) でない(画像を渡した場合は名指しで拒否)/ ``points_3d`` が (N,3) でない / 非有限 / 6 点未満 / 点数不一致 / 全点が一直線か一点。

注意: 外れ値には無防備(全点を等しく使う)。誤対応があるなら ``pnp_ransac``。決定論的(乱数なし)。評価は ``reprojection_error``、GT との比較は ``pose_error``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pnp_pose_outliers](../../../../examples_3d/pnp_pose_outliers.py) — `py -3.11 examples_3d/pnp_pose_outliers.py`
- [pose_estimation](../../../../examples_3d/pose_estimation.py) — `py -3.11 examples_3d/pose_estimation.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`pose_estimation`)

[pnp_ransac](pnp_ransac.md) · [reprojection_error](reprojection_error.md)

---
*Provenance: pnp3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
