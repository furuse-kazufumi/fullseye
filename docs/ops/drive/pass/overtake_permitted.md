---
op: overtake_permitted
dim: drive
category: pass
in: table
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# overtake_permitted — DRIVE `pass` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.overtake_permitted(*, maneuver_start: 'float', maneuver_end: 'float', zones_result: 'Optional[dict]' = None, lead_kind: 'str' = 'car', lead_overtaking: 'bool' = False, lead_keeping_right: 'bool' = False, side: 'str' = 'right', dist_oncoming: 'float' = inf, requirement: 'Optional[dict]' = None, being_overtaken: 'bool' = False) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.overtake_permitted(*, maneuver_start: 'float', maneuver_end: 'float', zones_result: 'Optional[dict]' = None, lead_kind: 'str' = 'car', lead_overtaking: 'bool' = False, lead_keeping_right: 'bool' = False, side: 'str' = 'right', dist_oncoming: 'float' = inf, requirement: 'Optional[dict]' = None, being_overtaken: 'bool' = False) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("overtake_permitted")`)

## 使い方

追越しを始めてよいか(条文と教則の判定)。場面 S077・S078・S079・S080・S081・S083。

``maneuver_start`` .. ``maneuver_end`` = 進路を変え始めてから前車の側方を通り終えるまでの自車の前端の位置。
理由(code, 根拠):
* ``no_passing_zone``(30 条): その区間が ``no_overtaking_zones`` の禁止区間と重なる(前車が ``EXEMPT_KINDS`` なら除く)。
* ``double_overtaking``(29 条): 前車が他の自動車を追い越そうとしている。
* ``wrong_side``(28 条 1・2 項): 前車が右折のため中央(右側端)に寄っている(``lead_keeping_right``)なら左、それ以外は右。
* ``oncoming_too_close``(28 条 4 項 + 閉形式): ``dist_oncoming`` < ``requirement["d_required"]``
  (``overtake_requirement`` の返り値)。
* ``being_overtaken``(教則 5-6-1(2)エ。**法の明文なし**、場面 S080): 後ろの車が自車を追い越そうとしている。
返り値: ``ok``、``reasons`` = [(code, 根拠)]、``required_side``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
