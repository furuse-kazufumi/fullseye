---
op: road_sign_rule_classify
dim: drive
category: sign
in: rgbimage × contour × table
out: table
gpu: なし
examples: [poc_ginza_stage2_ops]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# road_sign_rule_classify — DRIVE `sign` op

- **データ種**: `rgbimage × contour × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.road_sign_rule_classify(image, contour, rules=None)` (実装を直接呼ぶなら `import roadsign; roadsign.road_sign_rule_classify(image, contour, rules=None)`、台帳から引くなら `opsdrive.get("road_sign_rule_classify")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

RGBと輪郭の形から日本式一時停止・最高速度候補・車両進入禁止を規則分類する。

Parameters
----------
image : (H, W, 3) rgbimage
    0..1の標識crop。輪郭と同じ画素座標。
contour : contour
    :func:`regular_shape_classify` と同じXLD輪郭。
rules : table or None
    HSVしきい値の名前付き上書き。既定値はモジュール定数として公開する。

Returns
-------
table
    ``label`` は ``stop_jp``、``speed_limit_candidate``、``no_entry``、``unknown``。
    形、赤/白/青の面積率、外周/内側配色、白帯の形、確信度、棄却理由も返す。

出典: e-Gov「道路標識、区画線及び道路標示に関する命令」別表第二、Law ID
``335M50004002003``、Revision ``335M50004002003_20260901_508M60000802003``
(2026-11-25確認)。一時停止(330-A)は赤い逆三角形、最高速度(323)は赤枠・白地・
青文字の円、車両進入禁止(303)は赤地・白横帯の円。図示寸法は順に一辺0.80 m、
直径0.60 m、直径0.60 m。

``speed_limit_candidate`` は速度標識らしい外形までで、数字も規制内容も確定しない。
数字認識には別の検証済みOCR/テンプレート照合が必要である。赤い八角形は日本の
一時停止ではないため ``unknown`` に棄却する。

English: combine the contour op with explicit HSV/layout rules for the three supported
Japanese appearances.  A circular red border is only a ``speed_limit_candidate``;
no numeric limit is inferred without a separate validated digit recogniser.  A red
octagon is deliberately rejected because Japanese stop sign 330-A is an inverted triangle.
The normative dimensions and colours above come from e-Gov Appended Table 2.

呼び出し例::

    import numpy as np
    import roadsign
    t = np.linspace(0., 2*np.pi, 65)
    c = np.c_[32 + 24*np.sin(t), 32 + 24*np.cos(t)]
    rgb = np.zeros((65,65,3)); rgb[...,0] = .8
    rgb[28:37, 14:51] = 1.
    out = roadsign.road_sign_rule_classify(rgb, {"shape":(65,65), "cs":[c]}, {})
    assert out["label"] == "no_entry"

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ginza_stage2_ops](../../../../examples/poc_ginza_stage2_ops.py) — `py -3.11 examples/poc_ginza_stage2_ops.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`sign`)

[regular_shape_classify](regular_shape_classify.md)

---
*Provenance: roadsign.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
