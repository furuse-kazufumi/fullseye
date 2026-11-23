---
op: stop_line_detect
dim: drive
category: lane
in: labels × table
out: table
gpu: なし
examples: [lane_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# stop_line_detect — DRIVE `lane` op

- **データ種**: `labels × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stop_line_detect(labels, lane_model)` (実装を直接呼ぶなら `import laneops; laneops.stop_line_detect(labels, lane_model)`、台帳から引くなら `opsdrive.get("stop_line_detect")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

車線にほぼ直交する十分に広い白線を停止線として検出し、横断歩道を棄却する。

白画素を車線内へ切り、連結片を世界座標へ写す。同じ前方距離の遮蔽片を結合し、
車線接線への直交角、幅、厚さで判定する。似た横線が反復する集合は横断歩道候補に
するが、先頭が停止線か、遮蔽・端切れ・影で1〜2本しか見えないかを幾何だけでは
決められない。そこで候補を捨てず``ambiguous=True``かつ低確信度で返す。BEV対応と
経路の全区間を入口で検査する。摩耗した実線と横断歩道が接触して1成分になる場合は対象外。

Parameters
----------
labels : (H, W) labels
    :func:`color_rule_mask`のlabelを俯瞰へ写したもの。1だけを白として使う。
lane_model : table
    ``path``(世界xy), ``lane_width`` と ``pixel_to_world``(俯瞰画素col,row→世界xy)。

Returns
-------
table
    ``found``、``ambiguous``、経路始点からの``distance``[m]、``width``[m]、``confidence``、候補と横断歩道棄却数。

English: find wide white components nearly perpendicular to the lane tangent and
merge fragments split by occlusion. Repeated stripes are crosswalk evidence, but
geometry alone cannot tell whether their first stripe is an adjacent stop line or
whether one/two stripes are a partial crosswalk. Those cases remain an
``ambiguous`` low-confidence candidate rather than a definitive assertion. It
validates every path segment and an affine nonsingular BEV mapping first. Distance
is arc length from path[0].

呼び出し例::

    import numpy as np
    import laneops
    labels = np.zeros((201, 81), np.int16); labels[100:104, 8:73] = 1
    H = np.array([[.05,0.,-2.],[0.,-.05,10.],[0.,0.,1.]])
    lane = {"path":np.c_[np.zeros(101), np.linspace(0.,10.,101)], "lane_width":3.5, "pixel_to_world":H}
    out = laneops.stop_line_detect(labels, lane)
    assert out["found"] and abs(out["distance"] - 5.0) < 0.11

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lane_ops_tour](../../../../examples/lane_ops_tour.py) — `py -3.11 examples/lane_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lane`)

[color_rule_mask](color_rule_mask.md) · [plane_topview_color](plane_topview_color.md) · [lane_boundary_fit](lane_boundary_fit.md) · [lane_center_path](lane_center_path.md)

---
*Provenance: laneops.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
