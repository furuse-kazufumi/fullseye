---
op: turn_maneuver_check
dim: drive
category: lateral
in: table
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# turn_maneuver_check — DRIVE `lateral` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.turn_maneuver_check(trajectory: 'dict', *, kind: 'str', x_entry: 'float', edge_y: 'float', center_y: 'float' = 0.0, corner_center=None, corner_radius: 'float' = 0.0, intersection_center=None, approach: 'float' = 30.0, keep_tol: 'float' = 0.5, side_tol: 'float' = 1.5, inside_tol: 'float' = 3.0, jokou: 'float' = 2.7777777777777777, clearance: 'float' = 0.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.turn_maneuver_check(trajectory: 'dict', *, kind: 'str', x_entry: 'float', edge_y: 'float', center_y: 'float' = 0.0, corner_center=None, corner_radius: 'float' = 0.0, intersection_center=None, approach: 'float' = 30.0, keep_tol: 'float' = 0.5, side_tol: 'float' = 1.5, inside_tol: 'float' = 3.0, jokou: 'float' = 2.7777777777777777, clearance: 'float' = 0.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("turn_maneuver_check")`)

## 使い方

左折・右折の通り方の判定(道交法 34 条 1・2 項 / 教則 5-7-2)。数値の幅はすべて仮定(``SOURCES``)。

道は +x へ進む(左 = +y)。車道の左端 y = ``edge_y``、中央線 y = ``center_y``、交差点の手前の縁 x = ``x_entry``。
``trajectory``: ``t``, ``front`` (N, 2)(前車軸の中心)、``rear`` (N, 2)(後車軸の中心)、``speed`` (N,)、``width``(車幅)、
``track``(輪距)、``front_overhang``・``rear_overhang``(車軸から車体の端まで)。

判定:
  * 寄る(あらかじめ): x_entry − approach ≤ 前端 < x_entry の間、左折は車体の左側と左端の距離が [0, keep_tol]
    (0 未満 = 路肩・路側帯へはみ出す)、右折は車体の右側と中央線の距離が [0, keep_tol] (0 未満 = 中央線をまたぐ)。
  * 徐行: 前端が x_entry を越えてから曲がり終える(向きが ±80° を超える)までの速さ ≤ ``jokou``。
  * 左折の「側端に沿って」: 曲がる間(向き 10°〜80°)の後輪の内側と隅切りの円(中心 ``corner_center``・半径
    ``corner_radius``)の距離が [``clearance``, ``side_tol``]。clearance を下回る = 内輪差で隅の人・自転車の場所に入る。
  * 右折の「交差点の中心のすぐ内側」: 前車軸の中心の軌跡が交差点の中心 ``intersection_center`` を **右(旋回の内側)に
    見ずに** 通り(中心が軌跡の外側 = 左)、最も近いときの距離 ≤ ``inside_tol``。
返り値: ``ok``, ``violations``(理由の文字列のリスト)、``metrics``(dict)。

**Raises** ``ValueError``: kind が "left" / "right" 以外、必要な値の欠け、形の誤り。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
