---
op: regular_shape_classify
dim: drive
category: sign
in: contour
out: table
gpu: なし
examples: [poc_ginza_stage2_ops]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# regular_shape_classify — DRIVE `sign` op

- **データ種**: `contour` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.regular_shape_classify(contour, *, simplify_tolerance=0.012)` (実装を直接呼ぶなら `import roadsign; roadsign.regular_shape_classify(contour, *, simplify_tolerance=0.012)`、台帳から引くなら `opsdrive.get("regular_shape_classify")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

輪郭を頂点数と等周円形度で三角・八角・円・不明に分類する。

Parameters
----------
contour : contour
    ``{"shape": (H,W), "cs": [Nx2]}``。行・列順の閉じた輪郭を1本だけ受ける。
simplify_tolerance : float
    輪郭bbox対角に対するRDP許容距離の比。既定0.012。

Returns
-------
table
    ``label``、RDPの``vertex_count``/``vertices``、``circularity=4πA/P²``、
    面積、周長、確信度。欠け・凹み・閾値境界は ``unknown``。

English: simplify one ordered closed contour with scale-relative RDP, then combine
vertex count with isoperimetric circularity.  It recognises triangle, octagon, and
circle only; partial, concave, or threshold-boundary contours are rejected as unknown.
Rotation and uniform scale do not affect the features.

呼び出し例::

    import numpy as np
    import roadsign
    t = np.linspace(0., 2*np.pi, 65)
    c = np.c_[32 + 20*np.sin(t), 32 + 20*np.cos(t)]
    out = roadsign.regular_shape_classify({"shape":(65,65), "cs":[c]})
    assert out["label"] == "circle" and out["circularity"] > .99

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ginza_stage2_ops](../../../../examples/poc_ginza_stage2_ops.py) — `py -3.11 examples/poc_ginza_stage2_ops.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`sign`)

[road_sign_rule_classify](road_sign_rule_classify.md)

---
*Provenance: roadsign.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
