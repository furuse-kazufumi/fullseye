---
op: pnp_ransac
dim: 3d
category: pose_estimation
in: points × keypoints
out: pose
examples: [pnp_pose_outliers, pose_estimation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# pnp_ransac — 3D `pose_estimation` op

- **データ種**: `points × keypoints` → `pose`
- **呼び出し**: `import pnp3d; pnp3d.pnp_ransac(points_3d, points_2d, K, thresh=2.0, iters=300, seed=0)` (または `ops3d.get("pnp_ransac")`)

## 使い方

外れ値に頑健な PnP(RANSAC + 最終 DLT リフィット)。→ (R, t, inlier_mask, info)。

6 点の最小サンプルで DLT(精密化なし)→ 再投影誤差 < thresh の inlier 最大化 →
inlier 全体で :func:`pnp_pose`(精密化あり)リフィット。

Raises ValueError: points_2d が (N,2) でない / points_3d が (N,3) でない /
    点数不一致 / 6 点未満 / 非有限。

引数:
- ``thresh``: 再投影誤差のしきい値 [px] (ユークリッド距離、既定 2.0)。これ未満を inlier とする。
- ``iters``: 反復数(既定 300)。早期終了はせず必ずこの回数回す。各反復は 6 点を非復元抽出し初期姿勢だけを解く(縮退した標本は捨てて次へ)。
- ``seed``: ``numpy.random.default_rng(seed)`` に渡す。同じ入力と seed なら結果は再現する。

返り値: ``R`` (3,3)、``t`` (3,)(規約 ``Xc = R X + t``)、``inlier_mask`` bool (N,)、``info`` dict。
``info`` のキーは ``n_inliers`` / ``inlier_ratio`` / ``iters`` / ``rms``(最終姿勢の再投影 RMS [px]、inlier 集合上)。

- 最良標本の inlier が 6 未満のときは全点で解き直す fallback に入り、``info["fallback"] = True`` が付く。このとき ``inlier_mask`` は fallback 姿勢で数え直した実測値なので、``inlier_ratio`` が小さいまま返ることがある(合意を捏造しない)。fallback も失敗すれば ``ValueError``。
- inlier 数の比較は「より多い」だけを更新するので、同数なら先に見つかった標本が残る。
- 最終姿勢は inlier 全体でのリフィット(LM 精密化あり)。
- Raises ``ValueError``: 形状不正 / 6 点未満 / 点数不一致 / 非有限(``dlt_pose`` と同じ入口検査)。
- 評価は ``reprojection_error``、GT 比較は ``pose_error``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pnp_pose_outliers](../../../../examples_3d/pnp_pose_outliers.py) — `py -3.11 examples_3d/pnp_pose_outliers.py`
- [pose_estimation](../../../../examples_3d/pose_estimation.py) — `py -3.11 examples_3d/pose_estimation.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`pose_estimation`)

[dlt_pose](dlt_pose.md) · [reprojection_error](reprojection_error.md)

---
*Provenance: pnp3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
