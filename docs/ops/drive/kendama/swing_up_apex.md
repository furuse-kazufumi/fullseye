---
op: swing_up_apex
dim: drive
category: kendama
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# swing_up_apex — DRIVE `kendama` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.swing_up_apex(kp: 'dict', *, lift: 'float' = 0.265, T_lift: 'float' = 0.15, kind: 'str' = 'bang', g: 'float' = None) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.swing_up_apex(kp: 'dict', *, lift: 'float' = 0.265, T_lift: 'float' = 0.15, kind: 'str' = 'bang', g: 'float' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("swing_up_apex")`)

## 使い方

:func:`swing_up_plan` で真下に吊った玉(支点の L 下、静止)がどこまで昇るかの閉形式。
減速の加速度 a > g なら減速に入った瞬間(bang: T/2、trap: 2T/3)に弛み、そのときの手元の高さ z_s と速さ v_s で自由落下
→ 頂点 z = tie_z + z_s − L + v_s²/(2g)(手元の出発点から測った玉の中心、L = ひもの有効長、tie_z = 支点の手元からの高さ)。
a ≤ g なら弛まず、玉は支点の L 下で止まる。返り値 ``{"accel", "flies", "slack_t", "z_slack", "v_slack", "apex",
"apex_above_handle", "apex_above_cup"}``(apex_above_handle = apex − lift、apex_above_cup = それから大皿の縁の高さを引いた量:
皿に届くには ≥ h_c、皿の窓に入るには h_c ≤ … ≤ h_c + 1.5 r_b)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
