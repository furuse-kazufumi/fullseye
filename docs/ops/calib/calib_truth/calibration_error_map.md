---
op: calibration_error_map
dim: calib
category: calib_truth
in: table
out: table
gpu: なし
examples: [poc_calibration_truth_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# calibration_error_map — CALIB `calib_truth` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.calibration_error_map(calibration, K_true, dist_true, image_shape, step=16, depth=None, remove_rotation=True)` (実装を直接呼ぶなら `import calib_lm; calib_lm.calibration_error_map(calibration, K_true, dist_true, image_shape, step=16, depth=None, remove_rotation=True)`、台帳から引くなら `opscalib.get("calibration_error_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

真の K・歪みと推定値を比べ、画像のどこで再投影の誤差(px)と 3D の誤差(mm)が大きいかの地図を返す(``table``)。

Map, over the image, how far the estimated camera misplaces a point compared with the true camera —
possible only when the truth is known (a simulated calibration). For each grid pixel p the ray of the
TRUE camera through p is reprojected with the ESTIMATED camera; the map is |p̂ − p| in pixels (the
error any reprojection-based measurement inherits there). With ``depth`` Z (mm), the 3-D map is the
lateral distance between the points the two cameras back-project from p at depth Z.

``remove_rotation``(既定 True): 推定のカメラを最もよく合う小さな回転で回してから比べる。主点のずれの大部分は
カメラの向きのずれと見分けがつかず、どんな使い方でも外部の姿勢に吸収されるので、残るのが「内部パラメータと歪み
でしか直せない」誤差になる。回した角度は ``rotation_removed_deg``、回す前の地図は ``raw_*`` に残す。
閉形式の門(``remove_rotation=False``): 推定 = 真値 → 0、cx だけ δ ずれ(歪みなし)→ どこでも δ px、
3D は δ·Z/fx。``image_shape`` (H, W)、``step`` は格子の間隔(画素)。

返す ``dict``: ``rows``・``cols``(格子の中心)、``reproj_error_px``(地図)、``dx_px``・``dy_px``(成分、列・行)、
``max_px``・``rms_px``・``max_at``(row, col)、``raw_rms_px``・``raw_max_px``(回す前)、``rotation_removed_deg``、
``error_3d_mm``・``max_3d_mm``(``depth`` があれば)、``depth``。

**Raises** ``ValueError``: 校正の表が不正、K が正でない、``image_shape``・``step``・``depth`` の範囲外。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_calibration_truth_map](../../../../examples/poc_calibration_truth_map.py) — `py -3.11 examples/poc_calibration_truth_map.py`

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_uncertainty_map](calibration_uncertainty_map.md) · [calibration_next_pose](calibration_next_pose.md)

## 同カテゴリ(`calib_truth`)

[calibration_uncertainty_map](calibration_uncertainty_map.md) · [calibration_next_pose](calibration_next_pose.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
