---
op: checkerboard_points
dim: calib
category: checkerboard
in: 
out: keypoints
gpu: なし
examples: [poc_calibration_truth_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# checkerboard_points — CALIB `checkerboard` op

- **データ種**: `なし` → `keypoints`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.checkerboard_points(pattern_size, square_size)` (実装を直接呼ぶなら `import calib_lm; calib_lm.checkerboard_points(pattern_size, square_size)`、台帳から引くなら `opscalib.get("checkerboard_points")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

チェッカー板の内側の角の板座標 (x, y) を行優先で返す(``keypoints``)。

Board coordinates (x, y) of the inner corners of a checkerboard with ``pattern_size = (cols, rows)``
inner corners and squares of ``square_size`` (mm), row-major: index ``r·cols + c`` is
``(c·square, r·square)``. The first corner is the origin (OpenCV's convention for
``findChessboardCorners``). The board has ``(cols + 1) x (rows + 1)`` squares.

**Raises** ``ValueError``: cols・rows が 2 未満・整数でない、``square_size`` が正でない。

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

[sim_checkerboard](sim_checkerboard.md) · [find_checkerboard_corners](find_checkerboard_corners.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
