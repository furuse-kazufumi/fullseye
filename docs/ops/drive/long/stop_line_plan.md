---
op: stop_line_plan
dim: drive
category: long
in: scalar × scalar
out: table
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# stop_line_plan — DRIVE `long` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stop_line_plan(v: 'float', dist_to_line: 'float', theta: 'float' = 0.0, params: 'Optional[dict]' = None, t0: 'float' = 0.0, margin: 'float' = 0.5, A1: 'float' = 1.5, A2: 'float' = 2.5, split: 'float' = 0.5) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivelong; drivelong.stop_line_plan(v: 'float', dist_to_line: 'float', theta: 'float' = 0.0, params: 'Optional[dict]' = None, t0: 'float' = 0.0, margin: 'float' = 0.5, A1: 'float' = 1.5, A2: 'float' = 2.5, split: 'float' = 0.5) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("stop_line_plan")`)

## 使い方

知覚した瞬間(時刻 t0、前端から停止線まで ``dist_to_line``、速さ v)から、停止線の ``margin`` 手前に止まる **2 段制動** の計画。

段: 反応(ρ、速さを保つ)→ [必要なら速さを保ったまま待つ(cruise)] → 1 段目(減速度の定数部分 A1、速さが split·v まで)
→ 2 段目(A2、止まるまで)→ 保持。制動を 2 段に分けるのは通達の「ブレーキを数回に分けて踏まない場合」(制動操作不良)に合わせる。
間に合わないときは 2 段目の減速度を閉形式で解き直し(ln の式、k > 0 でも厳密)、1 段目だけで足りない距離なら 1 段で止める
(stages = 1)。上限(min(a_brake_max, μ g cos θ))で頭打ちなら ``saturated`` = True、予測は頭打ちの値で出す。
坂は区間の中で一定の θ(停止の区間が坂の折れ点をまたがない)とする。

Returns
-------
dict : ``phases``(``(t_start, kind, drive, brake)`` の列、kind = react / cruise / brake1 / brake2)、``t_breaks``、
``stages``、``predicted_gap``(止まった前端から停止線まで。負 = 越えた)、``t_stop``、``saturated``、``theta``、
``d_react``, ``d_cruise``, ``d_brake``。

**Raises** ``ValueError``: v ≤ 0、非有限、split ∉ (0, 1)、A1・A2 ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [plan_command](plan_command.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
