---
op: stereo_calibration_lm
dim: calib
category: calibrate
in: keypoints
out: table
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# stereo_calibration_lm — CALIB `calibrate` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stereo_calibration_lm(object_points, image_points_left, image_points_right, dist_model='k1k2p1p2k3', fix_intrinsics=False, calib_left=None, calib_right=None, image_shape=None)` (実装を直接呼ぶなら `import calib_lm; calib_lm.stereo_calibration_lm(object_points, image_points_left, image_points_right, dist_model='k1k2p1p2k3', fix_intrinsics=False, calib_left=None, calib_right=None, image_shape=None)`、台帳から引くなら `opscalib.get("stereo_calibration_lm")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

左右の内部・歪み・板の姿勢と右カメラの相対姿勢 (R, T) を LM で同時に最適化する(``table``)。

Joint stereo calibration: both cameras' intrinsics and distortion, the board poses in the left camera
and the right camera's pose relative to the left (X_right = R·X_left + T) are refined together by
Levenberg-Marquardt on the reprojection error in both images. Each camera starts from
:func:`camera_calibration_lm` (or ``calib_left`` / ``calib_right`` if given) and (R, T) from the
per-view relative poses (rotation by the chordal mean, translation by the mean).
``fix_intrinsics`` keeps both cameras' intrinsics and distortion fixed (OpenCV's CALIB_FIX_INTRINSIC).

返す ``dict``: ``K1``・``dist1``・``K2``・``dist2``・``R``・``T``・``E`` = [T]x R・``F`` = K2⁻ᵀ E K1⁻¹
(画素 (u = col, v = row) の同次座標どうし)、``baseline`` = |T|、``reproj_rms``(左右合わせて)、
``rms_left``・``rms_right``、``poses_left``、``sigma_px``、``rel_std``(R の回転ベクトルと T の標準偏差 6 個)、
``iterations``・``converged``。

**Raises** ``ValueError``: 左右の視点の数が違う・3 未満、点の数が合わない、単眼の校正の失敗。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_error_map](../calib_truth/calibration_error_map.md) · [calibration_uncertainty_map](../calib_truth/calibration_uncertainty_map.md) · [calibration_next_pose](../calib_truth/calibration_next_pose.md)

## 同カテゴリ(`calibrate`)

[camera_calibration](camera_calibration.md) · [find_marks_and_pose](find_marks_and_pose.md) · [hand_eye_calibration](hand_eye_calibration.md) · [camera_calibration_lm](camera_calibration_lm.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
