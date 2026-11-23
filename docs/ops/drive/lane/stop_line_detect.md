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

停止線と日本式横断歩道を別々の型付き出力として検出する。

白画素を車線内へ切り、連結片を世界座標へ写す。同じ前方距離の遮蔽片を結合し、
車線接線への直交角、幅、厚さで停止線を判定する。日本式の横断歩道は、車の進行方向と
平行な細長い白線を道路幅方向に並べる様式なので、長手が接線方向・幅が道路幅方向に細い
片を横断歩道縞として数える。同一の8近傍成分に停止線と縦縞が接しても、まず各前方位置の
横方向の帯を取り出して停止線候補を残す。縞は別に横方向へ束ね、停止線とは別の横断歩道
表として手前/奥の弧長、幅、縞数、縞幅、白線間隔、確信度を返す。縞の間隔が法令の範囲外
なら横断歩道と断定しない。別様式の横断歩道はこのopの入力契約外である。

様式の一次情報: 道路標識、区画線及び道路標示に関する命令（昭和三十五年総理府・建設省令
第三号）別表第6の横断歩道(201)および停止線(203)、e-Gov法令検索
https://laws.e-gov.go.jp/law/335M50004002003 。
白線間隔は警察庁交通規制課長通達「白線の設置間隔を拡大した横断歩道等を設ける場合の
留意事項について」（令和6年7月26日、警規発第96号）で45--90 cm。
https://www.npa.go.jp/laws/notification/koutuu/kisei/kisei20240726_4.pdf 。BEVでは各端
を1画素までしか測れないため、判定域を ``[0.45-res, 0.90+res] m`` とする。

Parameters
----------
labels : (H, W) labels
    :func:`color_rule_mask`のlabelを俯瞰へ写したもの。1だけを白として使う。
lane_model : table
    ``path``(世界xy), ``lane_width`` と ``pixel_to_world``(俯瞰画素col,row→世界xy)。

Returns
-------
table
    停止線の``found``、``ambiguous``、経路始点からの``distance``[m]、``width``[m]、
    ``confidence``、候補に加え、別の型付き ``crosswalk`` 表と同じ値の
    ``crosswalk_found``、``crosswalk_near_distance``、``crosswalk_far_distance``、
    ``crosswalk_width``、``crosswalk_stripe_count``、``crosswalk_stripe_width``、
    ``crosswalk_stripe_spacing``、``crosswalk_confidence``を返す。

English: find wide white components nearly perpendicular to the lane tangent and
merge fragments split by occlusion. It returns a separate typed crosswalk table.
The supported Japanese crosswalk style is a set of long lane-parallel, laterally narrow stripes, per Road Sign, Road Marking
and Road Surface Marking Order, Appended Table 6, crosswalk (201) and stop line
(203), e-Gov https://laws.e-gov.go.jp/law/335M50004002003 . Its clear stripe gaps
must be 0.45--0.90 m per National Police Agency notification No. 96 (2024-07-26),
https://www.npa.go.jp/laws/notification/koutuu/kisei/kisei20240726_4.pdf , with one
BEV pixel tolerance at each bound. Other national styles are outside this op's contract. It
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
