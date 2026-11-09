---
op: gen_radial_distortion_map
dim: calib
category: plane
in: 
out: table
halcon: gen_radial_distortion_map
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# gen_radial_distortion_map — CALIB `plane` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gen_radial_distortion_map(cam_par, kappa, shape)` (実装を直接呼ぶなら `import calib; calib.gen_radial_distortion_map(cam_par, kappa, shape)`、台帳から引くなら `opscalib.get("gen_radial_distortion_map")`)
- **HALCON 相当**: `gen_radial_distortion_map`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

半径歪みの逆マップ(row_map, col_map)を生成(gen_radial_distortion_map)。

出力の画素 (row, col) → 入力の座標。模型は**一次の多項式**: 主点からの画素 ``(x, y)``、
``r^2 = x^2 + y^2`` に対し ``入力 = 主点 + (x, y) * (1 + kappa r^2)``(``kappa`` の単位は
1/画素²、``cam_par`` の fx/fy は使わない)。
★除算模型(``mvimage.distort_division`` / ``undistort_division``、``u = d / (1 + kappa |d|^2)``)
の厳密な逆ではなく、その一次近似にあたる。同じ ``kappa`` を両方に使うと黙って食い違う:
640x480・主点 (320, 240) で ``kappa = -5e-7`` なら最大 4.28 px、``-2e-6`` なら最大 46.73 px
(2026-11-09 実測)。除算模型の厳密な歪み除去には ``mvimage.change_radial_distortion_image``
(``cam_out`` の ``kappa`` を 0)を使う。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](image_points_to_world_plane.md) · [contour_to_world_plane_xld](contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_error_map](../calib_truth/calibration_error_map.md) · [calibration_uncertainty_map](../calib_truth/calibration_uncertainty_map.md) · [calibration_next_pose](../calib_truth/calibration_next_pose.md)

## 同カテゴリ(`plane`)

[image_to_world_plane](image_to_world_plane.md) · [image_points_to_world_plane](image_points_to_world_plane.md) · [contour_to_world_plane_xld](contour_to_world_plane_xld.md) · [gen_image_to_world_plane_map](gen_image_to_world_plane_map.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
