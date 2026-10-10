---
op: toughness_from_pads
dim: drive
category: cuttouch
in: any × signal
out: table
examples: [poc_knife_tactile_toughness]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# toughness_from_pads — DRIVE `cuttouch` op

- **データ種**: `any × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.toughness_from_pads(loads, w_eff_mm, xi: 'float | None' = None, min_w_mm: 'float' = 2.0, readable_only: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import cuttouch; cuttouch.toughness_from_pads(loads, w_eff_mm, xi: 'float | None' = None, min_w_mm: 'float' = 2.0, readable_only: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("toughness_from_pads")`)

## 使い方

:func:`knife_load_from_pads` の列と切っている幅 w_eff [mm] (画像から、:func:`cutting.food_cut_width`)→ 靱性 R と当たり位置の要約。

R = 原点を通る最小二乗 ``V = R · w_eff · g(ξ)``、g = 1/(1+ξ²)(:func:`cutting.cut_force_fit`、摩擦は R に吸い込まれる)。ξ は
``xi`` を渡せばそれ(運動から)、省けば **触覚だけ** の ξ̂ = 中央値(H/V)(w_eff ≥ ``min_w_mm`` かつ読めるコマ)。``readable_only`` なら
``readable = False`` のコマは使わない(黙って混ぜない、数は ``n_unreadable`` に)。返り: ``R``・``rms_n``・``n``、``xi_used``・
``xi_tactile``(中央値)・``xi_tactile_iqr``、``Ly_median``・``Ly_mad``(読めるコマ)、``n_unreadable``、``model``。
**Raises** ValueError: 長さ違い、使えるコマが 3 未満、要素が knife_load_from_pads の返りでない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`cuttouch`)

[torsion_partial_slip](torsion_partial_slip.md) · [knife_load_from_pads](knife_load_from_pads.md)

---
*Provenance: cuttouch.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
