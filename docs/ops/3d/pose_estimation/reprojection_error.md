---
op: reprojection_error
dim: 3d
category: pose_estimation
in: points × keypoints
out: measurement
examples: [pnp_pose_outliers, pose_estimation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# reprojection_error — 3D `pose_estimation` op

- **データ種**: `points × keypoints` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.reprojection_error(points_3d, points_2d, K, R, t)` (実装を直接呼ぶなら `import pnp3d; pnp3d.reprojection_error(points_3d, points_2d, K, R, t)`、台帳から引くなら `ops3d.get("reprojection_error")`)

## 使い方

再投影誤差(RMS ピクセル)。姿勢の当てはまり評価。→ scalar。

Raises ValueError: points_2d が (N,2) でない / 点数不一致 / 非有限。

計算: 各 3D 点を ``x = K (R X + t)`` で投影して ``u = x0/x2``, ``v = x1/x2`` を取り、観測 2D 点とのユークリッド距離 d_i [px] の RMS ``sqrt(mean(d_i²))`` を返す。

- ``points_3d`` (N,3)、``points_2d`` (N,2)(画素座標、``project_points`` と同じ規約)、``K`` (3,3)、``R`` (3,3)、``t`` (3,)。R, t は world → camera(``Xc = R X + t``)。
- 深度 ``x2`` が負の点(カメラ後方)もそのまま割って投影するので、誤った姿勢では前後反転した点が「近く」に見えることがある。``x2 = 0`` は除算で inf/NaN になり検査しない。
- 単位は画素。対応が正しく K が合っていれば画素ノイズ程度(サブピクセル)。
- 典型: ``dlt_pose`` / ``pnp_ransac`` の結果を評価する。``pnp_ransac`` の ``info["rms"]`` は同じ量(inlier 集合上)。GT 姿勢との比較は ``pose_error``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [pnp_pose_outliers](../../../../examples_3d/pnp_pose_outliers.py) — `py -3.11 examples_3d/pnp_pose_outliers.py`
- [pose_estimation](../../../../examples_3d/pose_estimation.py) — `py -3.11 examples_3d/pose_estimation.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`pose_estimation`)

[dlt_pose](dlt_pose.md) · [pnp_ransac](pnp_ransac.md)

---
*Provenance: pnp3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
