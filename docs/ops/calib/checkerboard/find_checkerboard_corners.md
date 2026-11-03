---
op: find_checkerboard_corners
dim: calib
category: checkerboard
in: image2d
out: keypoints
gpu: なし
examples: [poc_calibration_truth_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# find_checkerboard_corners — CALIB `checkerboard` op

- **データ種**: `image2d` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.find_checkerboard_corners(image, pattern_size, sigma=1.5, refine_window=None)` (実装を直接呼ぶなら `import calib_lm; calib_lm.find_checkerboard_corners(image, pattern_size, sigma=1.5, refine_window=None)`、台帳から引くなら `opscalib.get("find_checkerboard_corners")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

チェッカー板の画像から内側の角をサブピクセルで検出し、板の行優先の順で返す(``keypoints``)。

Detect the inner corners of a checkerboard with ``pattern_size = (cols, rows)`` inner corners, refine
them to sub-pixel accuracy and return them as (row, col) in the board's row-major order
(pairs with :func:`checkerboard_points`).

手順: (1) ガウスの 2 階微分(尺度 ``sigma``)で鞍点の強さ ``−det(Hessian)`` を出し、局所最大を候補に
(2) 各候補を Förstner の勾配直交の式(OpenCV の ``cornerSubPix`` と同じ原理: 窓の中の勾配 g が角へ向かう
ベクトルと直交 → ``Σ g gᵀ (p − q) = 0``)で反復して詰める(Förstner & Gülch 1987)
(3) 最寄りの近傍から格子の 2 方向を決め、局所の平行四辺形で予測しながら格子を伸ばす
(4) 埋まった格子が ``cols x rows``(または転置)でなければ拒否。
順の約束: 列の方向 = 長さ cols の軸。2 つの軸の向きは「画像で右手系(板を表から見る)」と
「最初の角が画像の左上に最も近い」で決める。★対称な板の 180 度の回転は区別しない —— 校正には効かない
(板の点の集合がその回転で自分に写るので、姿勢が 180 度回るだけ)。cols = rows の板では 90 度も区別しない。

返す ``(N, 2)``: (row, col)、N = cols·rows。

**Raises** ``ValueError``: 画像が 2 次元でない・非有限、角の数が合わない・格子が組めない(板が見えない・
ぼけすぎ・一部が画像の外)、引数の範囲外。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_calibration_truth_map](../../../../examples/poc_calibration_truth_map.py) — `py -3.11 examples/poc_calibration_truth_map.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[image_to_world_plane](../plane/image_to_world_plane.md) · [camera_calibration](../calibrate/camera_calibration.md) · [camera_calibration_lm](../calibrate/camera_calibration_lm.md) · [stereo_calibration_lm](../calibrate/stereo_calibration_lm.md) · [vector_to_rigid](../fit/vector_to_rigid.md) · [vector_to_similarity](../fit/vector_to_similarity.md) · [hom_vector_to_proj_hom_mat2d](../fit/hom_vector_to_proj_hom_mat2d.md)

## 同カテゴリ(`checkerboard`)

[checkerboard_points](checkerboard_points.md) · [sim_checkerboard](sim_checkerboard.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
