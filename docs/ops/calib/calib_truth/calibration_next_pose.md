---
op: calibration_next_pose
dim: calib
category: calib_truth
in: table
out: table
gpu: なし
examples: [poc_calibration_truth_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# calibration_next_pose — CALIB `calib_truth` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.calibration_next_pose(calibration, candidate_poses, image_shape, step=32, sigma_px=None)` (実装を直接呼ぶなら `import calib_lm; calib_lm.calibration_next_pose(calibration, candidate_poses, image_shape, step=32, sigma_px=None)`、台帳から引くなら `opscalib.get("calibration_next_pose")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

候補の板の姿勢のうち、足すと校正の不確かさ(画像全体の平均)を最も減らす 1 枚を推薦する(``table``)。

Recommend the next calibration view. The information already gathered is rebuilt from the
calibration's own geometry (board, poses, current estimate — the Jacobian does not depend on the
measured points) as JᵀJ/σ²; each candidate pose (board -> camera 4x4) adds its own block (with its 6
pose unknowns). The score is the mean of :func:`calibration_uncertainty_map` after adding the
candidate; lower is better. Candidates whose board leaves the image or goes behind the camera get
``inf``. ``sigma_px`` overrides the corner noise (default: the calibration's ``sigma_px``).

★これは**予測**(線形化した共分散)。モンテカルロで「推薦を足した校正の実際の誤差 < 最下位を足した校正」を
門で確かめる(tests)。最適な実験計画の D 最適ではなく、画像の上の予測の不確かさの平均を直接減らす基準。
画像の上の予測の再投影誤差で次の姿勢を選ぶ考え方は AprilCal(Richardson, Strom & Olson, IROS 2013)と同じ系統
(あちらは最大値、こちらは平均)。★実測(tests の 6 候補): 候補どうしの差が小さいとき予測の順位と実際の順位は
入れ替わりうる。確かなのは「最下位を避ける」ほうで、門もそこを見る。

返す ``dict``: ``scores``(候補ごと、px)、``best_index``、``current_mean_px``、``improvement``(現在 − 最良)、
``visible``(候補ごと)、``param_std``(候補ごとの 9 変数の標準偏差)。

**Raises** ``ValueError``: 校正の表に姿勢・板・雑音が無い、候補が空・剛体でない、引数の範囲外。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_calibration_truth_map](../../../../examples/poc_calibration_truth_map.py) — `py -3.11 examples/poc_calibration_truth_map.py`

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_error_map](calibration_error_map.md) · [calibration_uncertainty_map](calibration_uncertainty_map.md)

## 同カテゴリ(`calib_truth`)

[calibration_error_map](calibration_error_map.md) · [calibration_uncertainty_map](calibration_uncertainty_map.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
