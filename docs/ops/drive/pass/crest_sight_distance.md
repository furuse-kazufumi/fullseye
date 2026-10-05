---
op: crest_sight_distance
dim: drive
category: pass
in: 
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# crest_sight_distance — DRIVE `pass` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.crest_sight_distance(*, radius: 'Optional[float]' = None, grade_in: 'Optional[float]' = None, grade_out: 'Optional[float]' = None, length: 'Optional[float]' = None, eye_height: 'float' = 1.2, object_height: 'float' = 0.1) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.crest_sight_distance(*, radius: 'Optional[float]' = None, grade_in: 'Optional[float]' = None, grade_out: 'Optional[float]' = None, length: 'Optional[float]' = None, eye_height: 'float' = 1.2, object_height: 'float' = 0.1) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("crest_sight_distance")`)

## 使い方

凸形縦断曲線(放物線)を越える最小の視距(閉形式)。場面 S065・S081(上り坂の頂上付近)。

``radius`` だけなら長さ無限の曲線(視距が曲線の中に収まる): S = √(2R)(√h₁ + √h₂)。``grade_in`` / ``grade_out``
(比、上りが正)と ``length`` = 曲線の水平の長さ L なら A = grade_in − grade_out(> 0)、R = L/A で、
S ≤ L なら上の式、S > L なら S = L/2 + (√h₁ + √h₂)²/A。h₁ = ``eye_height``、h₂ = ``object_height``
(既定 1.2 m・0.1 m = 道路構造令 2 条 24 号。対向車を見るなら h₂ = 車の高さ)。
返り値: ``sight``、``radius``、``within_curve``(S ≤ L)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
