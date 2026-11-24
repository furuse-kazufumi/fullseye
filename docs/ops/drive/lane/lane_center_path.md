---
op: lane_center_path
dim: drive
category: lane
in: table × table
out: table
gpu: なし
examples: [lane_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# lane_center_path — DRIVE `lane` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lane_center_path(left, right, *, lane_width=3.5, samples=51, band_inset=0.2)` (実装を直接呼ぶなら `import laneops; laneops.lane_center_path(left, right, *, lane_width=3.5, samples=51, band_inset=0.2)`、台帳から引くなら `opsdrive.get("lane_center_path")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

左右境界から車線中央の経路と走行可能帯を返す。

両側があれば共通観測範囲で中点を取る。片側だけなら既知の``lane_width``の半分
だけ内側へずらし、確信度を``SINGLE_BOUNDARY_CONFIDENCE_SCALE``倍に下げる。

Parameters
----------
left, right : table or None
    :func:`lane_boundary_fit`の結果。欠測側はNoneか``{"valid":False}``。
lane_width, samples, band_inset
    既知の車線幅[m]、標本数、境界から走行帯を内側へ引く量[m]。両側がある場合も、
    観測した幅が既知幅と整合することを検査する。

Returns
-------
table
    ``path``(x,y)、``band_left/right``、閉じた``corridor_polygon``、幅、確信度、使用した側。

English: average two fitted boundaries after checking their observed width against
the supplied known lane width, or offset a single observed boundary by
half the known lane width with reduced confidence. Before a one-sided offset, it
rejects a curvature radius no larger than any constructed offset, and rejects a
cusp, tangent reversal, or self-intersection with ``valid=False``. It returns the
centre path and an inset drivable corridor; it does not check vehicle footprint or
obstacles.

呼び出し例::

    import numpy as np
    import laneops
    left = {"coefficients":np.array([-1.75,0.,0.]), "observed_y":np.array([0.,20.]), "confidence":1.}
    right = {"coefficients":np.array([1.75,0.,0.]), "observed_y":np.array([0.,20.]), "confidence":1.}
    out = laneops.lane_center_path(left, right)
    assert np.allclose(out["path"][:, 0], 0.) and np.allclose(out["lane_width_samples"], 3.5)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lane_ops_tour](../../../../examples/lane_ops_tour.py) — `py -3.11 examples/lane_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lane`)

[color_rule_mask](color_rule_mask.md) · [plane_topview_color](plane_topview_color.md) · [lane_boundary_fit](lane_boundary_fit.md) · [stop_line_detect](stop_line_detect.md)

---
*Provenance: laneops.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
