---
op: camera_calibration_lm
dim: calib
category: calibrate
in: keypoints
out: table
gpu: なし
examples: [poc_calibration_truth_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# camera_calibration_lm — CALIB `calibrate` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_calibration_lm(object_points, image_points_list, dist_model='k1k2p1p2k3', image_shape=None)` (実装を直接呼ぶなら `import calib_lm; calib_lm.camera_calibration_lm(object_points, image_points_list, dist_model='k1k2p1p2k3', image_shape=None)`、台帳から引くなら `opscalib.get("camera_calibration_lm")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Zhang 法の初期値から内部パラメータ・歪み・全姿勢を LM で同時に最適化し、共分散とともに返す(``table``)。

Monocular calibration: Zhang's closed form (``calib.camera_calibration``) gives the start, then a
Levenberg-Marquardt refinement minimises the reprojection error over fx, fy, cx, cy, the distortion
coefficients of ``dist_model`` and every board pose jointly (Zhang 2000, §3.3; the Brown-Conrady model
with OpenCV's coefficient order). The Jacobian is analytic; poses are updated on the left by a small
rotation vector. Skew is fixed at 0.

``object_points``: 板の点 (N, 2) の (x, y)(:func:`checkerboard_points` など)。
``image_points_list``: 視点ごとの (N, 2) の **(row, col)**。``dist_model``: ``"none"``・``"k1"``・``"k1k2"``・
``"k1k2p1p2"``・``"k1k2p1p2k3"``(既定 = OpenCV の既定と同じ 5 係数)。
``image_shape``: Zhang の閉形式が退化したとき(全部が正面平行など)の初期値に使う。

返す ``dict``: ``K`` (3x3)、``fx``・``fy``・``cx``・``cy``、``dist`` [k1, k2, p1, p2, k3]、``poses``(板 → カメラ
の 4x4 の list)、``rvecs``・``tvecs``、``reproj_rms``(全体)、``per_view_rms``、``residuals``(視点ごとの (N,2)
(row, col))、``sigma_px``(残差から推定した角の雑音)、``covariance``(fx, fy, cx, cy, k1, k2, p1, p2, k3 の
9x9 の周辺共分散、固定の係数は 0)、``param_std``(名前 → 標準偏差)、``param_names``、``init``(Zhang の値)、
``iterations``・``converged``、``dist_model``、``object_points``、``image_shape``。
★再投影誤差が小さいことは配置が良いことを意味しない(``camera_calibration`` のノートの実測)。配置の良し悪しは
``param_std`` と :func:`calibration_uncertainty_map` で見る。

**Raises** ``ValueError``: 視点が 3 未満、点の数が合わない・4 未満・非有限、未知の ``dist_model``、
初期値が作れない、LM の途中で板が背後へ回る。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_calibration_truth_map](../../../../examples/poc_calibration_truth_map.py) — `py -3.11 examples/poc_calibration_truth_map.py`

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_error_map](../calib_truth/calibration_error_map.md) · [calibration_uncertainty_map](../calib_truth/calibration_uncertainty_map.md) · [calibration_next_pose](../calib_truth/calibration_next_pose.md)

## 同カテゴリ(`calibrate`)

[camera_calibration](camera_calibration.md) · [find_marks_and_pose](find_marks_and_pose.md) · [hand_eye_calibration](hand_eye_calibration.md) · [stereo_calibration_lm](stereo_calibration_lm.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
