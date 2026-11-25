---
op: color_rule_mask
dim: drive
category: lane
in: rgbimage × table
out: table
gpu: なし
examples: [lane_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# color_rule_mask — DRIVE `lane` op

- **データ種**: `rgbimage × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.color_rule_mask(image, rules=None)` (実装を直接呼ぶなら `import laneops; laneops.color_rule_mask(image, rules=None)`、台帳から引くなら `opsdrive.get("color_rule_mask")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

RGBを明示的なHSV規則で白線・黄線・不明に分け、maskと確信度を返す。

:func:`trans_from_rgb` の既存実装でRGB→HSVに変換する。白と黄のscoreを独立に
計算して最大scoreを採るため、``rules``をlistで渡した順序には依存しない。scoreが
``min_class_confidence``未満、または上位2色の差が``ambiguity_margin``以下なら
``unknown``に棄却する。影・逆光・濡れ路面に合わせた自動較正はしない。

Parameters
----------
image : (H, W, 3) rgbimage
    0..1の有限なRGB画像。
rules : table or None
    名前付きしきい値の上書き。``[{"name":"white", "min_value":...}, ...]``も可。

Returns
-------
table
    ``labels``(0 unknown, 1 white, 2 yellow)、各mask、``confidence``、色ごとのscore、HSV、使った規則。

English: classify finite RGB pixels as white, yellow or unknown with explicit HSV
thresholds after the existing ``trans_from_rgb`` conversion. Ambiguous pixels are
rejected. White additionally requires local value contrast, so a uniformly bright road
is not a white line; this is a fixed classical rule, not an illumination estimator.

呼び出し例::

    import numpy as np
    import laneops
    rgb = np.array([[[0.9, 0.9, 0.9], [0.9, 0.75, 0.05], [0.3, 0.3, 0.3]]])
    out = laneops.color_rule_mask(rgb, {})
    assert out["labels"].tolist() == [[1, 2, 0]]

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lane_ops_tour](../../../../examples/lane_ops_tour.py) — `py -3.11 examples/lane_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lane`)

[plane_topview_color](plane_topview_color.md) · [lane_boundary_fit](lane_boundary_fit.md) · [lane_center_path](lane_center_path.md) · [stop_line_detect](stop_line_detect.md)

---
*Provenance: laneops.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
