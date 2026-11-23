---
op: plane_topview_color
dim: drive
category: lane
in: rgbimage × matrix × matrix × signal
out: table
gpu: なし
examples: [lane_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# plane_topview_color — DRIVE `lane` op

- **データ種**: `rgbimage × matrix × matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plane_topview_color(image, K, R, t, *, z=0.0, centre=(0.0, 0.0), extent=30.0, res=0.05, fill=(0.0, 0.0, 0.0))` (実装を直接呼ぶなら `import laneops; laneops.plane_topview_color(image, K, R, t, *, z=0.0, centre=(0.0, 0.0), extent=30.0, res=0.05, fill=(0.0, 0.0, 0.0))`、台帳から引くなら `opsdrive.get("plane_topview_color")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

地面平面をRGBのまま俯瞰へ写し、有効maskと画素↔世界座標を返す。

投影格子は既存 :func:`plane_topview` と共通の ``calib`` 核を使う。列=世界+x、
行=世界−y、画素中心は整数。レンズ歪みは補正済みを前提とし、地面を単一平面
z=``z``とみなすため、坂・縁石・車体は正しい位置にならない。

Parameters
----------
image : (H, W, 3) rgbimage
    0..1 RGB。色を輝度へ落とさない。
K, R, t : matrix, matrix, signal
    ``X_camera = R @ X_world + t``の内部/外部パラメータ。
z, centre, extent, res
    平面の高さ、出力中心(x,y)、一辺[m]、1画素[m]。

Returns
-------
table
    ``rgb``, ``valid``, ``world_x/y``, ``image_row/col``, ``pixel_to_world`` と逆行列。

English: bilinearly rectify RGB onto a world z-plane while retaining a validity
mask and both pixel/world correspondences. It assumes an already-undistorted image
and a single plane; non-planar road objects are not metrically valid.

呼び出し例::

    import numpy as np
    import laneops
    rgb = np.zeros((8, 8, 3)); rgb[..., 1] = 1.0
    K = np.array([[4., 0., 3.5], [0., 4., 3.5], [0., 0., 1.]])
    R = np.diag([1., -1., -1.]); C = np.array([0., 0., 4.])
    out = laneops.plane_topview_color(rgb, K, R, -R @ C, extent=4., res=.5)
    assert out["rgb"].shape == (8, 8, 3) and np.all(out["rgb"][out["valid"], 1] == 1.0)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lane_ops_tour](../../../../examples/lane_ops_tour.py) — `py -3.11 examples/lane_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lane`)

[color_rule_mask](color_rule_mask.md) · [lane_boundary_fit](lane_boundary_fit.md) · [lane_center_path](lane_center_path.md) · [stop_line_detect](stop_line_detect.md)

---
*Provenance: laneops.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
