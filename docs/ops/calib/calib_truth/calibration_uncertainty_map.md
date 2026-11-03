---
op: calibration_uncertainty_map
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

# calibration_uncertainty_map — CALIB `calib_truth` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.calibration_uncertainty_map(calibration, image_shape, step=16, depth=None, remove_rotation=True)` (実装を直接呼ぶなら `import calib_lm; calib_lm.calibration_uncertainty_map(calibration, image_shape, step=16, depth=None, remove_rotation=True)`、台帳から引くなら `opscalib.get("calibration_uncertainty_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

校正の推定の共分散を画像の上へ写し、各画素の予測の不確かさ(px、奥行き Z なら mm)の地図を返す(``table``)。

Propagate the marginal covariance of the intrinsics and distortion (from :func:`camera_calibration_lm`)
to every grid pixel: a point fixed in the camera frame that the estimate places at p would be
reprojected with a standard deviation ``sqrt(trace(J C Jᵀ))`` (px, radial), J the 2x9 Jacobian of the
projection with respect to (fx, fy, cx, cy, k1, k2, p1, p2, k3). Needs no ground truth — this is the
map a real calibration can show too; the simulation checks that it is honest (Monte Carlo gate).
With ``depth`` Z (mm) the map is also given in mm (std · Z / f, small-angle).

``remove_rotation``(既定 True)は :func:`calibration_error_map` と同じ意味: カメラの向きのずれと見分けの
つかない成分(主点のずれの大部分)を除く。両方を同じ設定で使うと、モンテカルロの誤差の地図と比べられる。
★姿勢の不確かさは周辺化で含まれる(9x9 は全変数の共分散からの周辺)。画像の端ほど大きくなるのは、
板が写っていない所を歪みの多項式が外挿するから。★線形の予測なので、外挿が大きい所では当たらない:
6 視点・σ = 0.2 px で k3 まで自由にすると、隅の予測 160 px に対しモンテカルロの実測は 55 px
(k1k2p1p2 なら全体の平均で 6.42 / 6.39 px と合う。tests の実測)。

返す ``dict``: ``rows``・``cols``、``std_px``(地図)、``mean_px``・``max_px``・``max_at``、``std_mm``(``depth``)。

**Raises** ``ValueError``: 共分散が無い・非有限、引数の範囲外。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_calibration_truth_map](../../../../examples/poc_calibration_truth_map.py) — `py -3.11 examples/poc_calibration_truth_map.py`

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_error_map](calibration_error_map.md) · [calibration_next_pose](calibration_next_pose.md)

## 同カテゴリ(`calib_truth`)

[calibration_error_map](calibration_error_map.md) · [calibration_next_pose](calibration_next_pose.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
