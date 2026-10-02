---
op: dilemma_zone
dim: drive
category: decide
in: any
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# dilemma_zone — DRIVE `decide` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dilemma_zone(v, *, reaction: 'float', decel: 'float', amber: 'float', intersection_width: 'float', car_length: 'float', accel: 'float' = 0.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.dilemma_zone(v, *, reaction: 'float', decel: 'float', amber: 'float', intersection_width: 'float', car_length: 'float', accel: 'float' = 0.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("dilemma_zone")`)

## 使い方

黄信号のジレンマゾーン(Gazis, Herman, Maradudin 1960)。

速度 ``v`` で停止線の手前 x にいるとき黄が点いた:

    止まれる     ⇔ x ≥ x_c = v δ + v²/(2a)                         (δ = reaction、a = decel)
    抜けられる   ⇔ x ≤ x_0 = v τ + ½ a₁ (τ − δ)² − (w + L)          (τ = amber、a₁ = accel ≥ 0、w = 交差点の幅、L = 車長)

(a₁ = 0 が基本形。加速は反応の後から黄の終わりまで、と置いた形。τ ≤ δ なら加速項は 0。)
max(x_0, 0) < x < x_c が **ジレンマゾーン**(止まれず抜けられない。x < 0 は停止線を越えているので除く)、
x_c ≤ x ≤ x_0 が **選べる区間**(両方できる)。

日本の法令の読み: 教則 付表1(黄)は「停止位置に近く安全に止まれない場合はそのまま進行可」= **停止線を越えれば
よい**(交差点を黄のうちに抜ける義務ではない)。その読みでは ``intersection_width = car_length = 0`` として呼ぶ
(x_0 = vτ)。GHM の「交差点を抜ける」は全赤の時間が無い前提の厳しい読み。

返り値: ``x_stop_min`` = x_c、``x_clear_max`` = x_0、``dilemma``((lo, hi) か None)、``option``(同)、
``length``(ジレンマゾーンの長さ、無ければ 0)、``v_critical``(a₁ = 0 のとき x_c = x_0 になる速度の組。
実根が無ければ空 = どの速度でもジレンマが無い)。``v`` は 1 つの数(配列は ``np.vectorize`` などで)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [check_sequence_score](check_sequence_score.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
