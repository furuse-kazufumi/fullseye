---
op: lane_boundary_fit
dim: drive
category: lane
in: keypoints
out: table
gpu: なし
examples: [lane_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# lane_boundary_fit — DRIVE `lane` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lane_boundary_fit(points, *, side='unknown', ransac_threshold=0.18, ransac_iterations=300, initial_outlier_weight=0.25, seed=0)` (実装を直接呼ぶなら `import laneops; laneops.lane_boundary_fit(points, *, side='unknown', ransac_threshold=0.18, ransac_iterations=300, initial_outlier_weight=0.25, seed=0)`、台帳から引くなら `opsdrive.get("lane_boundary_fit")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

俯瞰の(x横,y前方)点から ``x=c0+c1*y+c2*y²`` の車線境界を頑健に当てはめる。

既存 :func:`ransac_line` を外れ値に強い初期直線として使い、その後Huber IRLSの
二次曲線へ拡張する。強いS字、yが折り返す境界、地面平面でない点には使えない。

Parameters
----------
points : (N, 2) keypoints
    世界座標 ``(x lateral, y forward)`` [m]。順序は問わない。
side : {"left", "right", "unknown"}
    後段が片側だけを車線中央へずらすための名前。
ransac_threshold, ransac_iterations, initial_outlier_weight, seed
    直線/最終inlierの距離[m]、反復数、初期RANSAC外れ値のIRLS重み、固定乱数seed。
    ``initial_outlier_weight=0.25``は初期inlierを4倍優先しつつ、曲線上で初期直線から
    外れた点を残すための固定値である。

Returns
-------
table
    正準の``normalised_coefficients``(b0,b1,b2), ``y_centre``, ``y_scale``、
    ``observed_y``、``inlier_mask``、残差、RMS、確信度。互換用の
    ``coefficients``(c0,c1,c2)は ``abs(y) <= 1e6 m`` の範囲だけ数値精度を契約する。

English: initialise with the existing 3-D ``ransac_line`` (z=0), then fit the
boundary x(y) with a Huber robust quadratic. Point order does not matter. It centres
and normalises y for rank, condition-number, least-squares work, and evaluation.
``normalised_coefficients``, ``y_centre``, and ``y_scale`` are the canonical output.
The legacy expanded world coefficients are numerically guaranteed only while
``abs(y) <= 1e6 m``. The final inlier design must have
rank 3, at least three distinct y values, and bounded condition number; otherwise it
returns ``valid=False`` instead of silently using a line. Hairpins where y is not
single-valued are outside the contract and fail closed.

呼び出し例::

    import numpy as np
    import laneops
    y = np.linspace(0., 20., 41); x = -1.75 + 0.002 * y*y
    fit = laneops.lane_boundary_fit(np.c_[x, y], side="left", seed=7)
    assert np.allclose(fit["coefficients"], [-1.75, 0., 0.002], atol=1e-10)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lane_ops_tour](../../../../examples/lane_ops_tour.py) — `py -3.11 examples/lane_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lane`)

[color_rule_mask](color_rule_mask.md) · [plane_topview_color](plane_topview_color.md) · [lane_center_path](lane_center_path.md) · [stop_line_detect](stop_line_detect.md)

---
*Provenance: laneops.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
