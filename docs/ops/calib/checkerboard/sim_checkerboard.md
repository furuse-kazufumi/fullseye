---
op: sim_checkerboard
dim: calib
category: checkerboard
in: 
out: table
gpu: なし
examples: [poc_calibration_truth_map]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# sim_checkerboard — CALIB `checkerboard` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sim_checkerboard(pattern_size, square_size, K, dist, pose, image_shape, supersample=3, margin=1.0, blur_sigma=0.0, noise_sigma=0.0, seed=0, black=0.1, white=0.9, background=0.5)` (実装を直接呼ぶなら `import calib_lm; calib_lm.sim_checkerboard(pattern_size, square_size, K, dist, pose, image_shape, supersample=3, margin=1.0, blur_sigma=0.0, noise_sigma=0.0, seed=0, black=0.1, white=0.9, background=0.5)`、台帳から引くなら `opscalib.get("sim_checkerboard")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

既知の K・歪み・姿勢でチェッカー板の画像を合成し、角の真の画素とともに返す(``table``)。

Render a checkerboard seen through a camera with known intrinsics ``K`` (3x3 or {fx, fy, cx, cy}),
distortion ``dist`` ([k1, k2, p1, p2(, k3)], OpenCV order) and board pose ``pose`` (board -> camera
4x4), with the true pixel of every inner corner.

描画は**投影の式とは逆向きの経路**: 画素(``supersample`` x ``supersample`` の標本)ごとに歪みを固定点反復で
外し、視線を板の平面に当てて板の座標を求め、その色(黒・白・板の外の余白 ``margin`` マス分は白、その外は
``background``)を塗って平均する。真の角は板の点を前向きに投影した値。だから検出の誤差は「描画の標本化 +
検出器」の誤差で、式の写しにはならない。``blur_sigma``(画素)でガウスぼけ、``noise_sigma`` で正規雑音。

返す ``dict``: ``image`` (H, W) [0, 1]、``corners`` (N, 2) **(row, col)**、``object_points`` (N, 2) (x, y)、
``visible``(全部の角が画像の内側 2 画素以上にある)、``pattern_size``、``square_size``、``K``、``dist``、``pose``。

**Raises** ``ValueError``: 引数の形・範囲(K が正でない、姿勢が剛体でない、板が背後にある、
supersample が 1〜8 の外、色が [0, 1] の外)。

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

## 同カテゴリ(`checkerboard`)

[checkerboard_points](checkerboard_points.md) · [find_checkerboard_corners](find_checkerboard_corners.md)

---
*Provenance: calib_lm.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
