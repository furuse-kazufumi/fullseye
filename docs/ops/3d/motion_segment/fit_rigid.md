---
op: fit_rigid
dim: 3d
category: motion_segment
in: points × points
out: pose
examples: [motion_scene]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# fit_rigid — 3D `motion_segment` op

- **データ種**: `points × points` → `pose`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_rigid(pts_from, pts_to)` (実装を直接呼ぶなら `import motion_seg3d; motion_seg3d.fit_rigid(pts_from, pts_to)`、台帳から引くなら `ops3d.get("fit_rigid")`)

## 使い方

対応点から閉形式 Kabsch で剛体変換 (R, t) を推定する(pts_from[i] -> pts_to[i])。

行 i どうしが対応する (N, 3) 2 点集合から、``|| (R·p + t) - q ||`` を最小化する
proper rotation(det = +1, 反射なし)と並進を返す。:func:`registration.kabsch` の
薄いラッパで、入力検証を付す(N >= 3 で回転が一意)。

Args:
    pts_from: (N, 3) 変換元(対応順)。
    pts_to: (N, 3) 変換先(対応順)。
Returns:
    (R, t): (3, 3) 回転行列, (3,) 並進ベクトル。
Raises:
    ValueError: 形状不一致 / (N, 3) でない / N < 3 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [motion_scene](../../../../examples_3d/motion_scene.py) — `py -3.11 examples_3d/motion_scene.py`

## 型が繋がる次の op(`pose` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [pose_error](../metrics/pose_error.md) · [bundle_adjust](../bundle_adjust/bundle_adjust.md) · [mean_reprojection_error](../bundle_adjust/mean_reprojection_error.md) · [optimize_pose_graph](../pose_graph/optimize_pose_graph.md) · [relative_pose](../pose_graph/relative_pose.md) · [mean_edge_error](../pose_graph/mean_edge_error.md) · [rotation_translation_error](../registration_metrics/rotation_translation_error.md)

## 同カテゴリ(`motion_segment`)

[segment_rigid_motions](segment_rigid_motions.md) · [estimate_flow](estimate_flow.md)

---
*Provenance: motion_seg3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
