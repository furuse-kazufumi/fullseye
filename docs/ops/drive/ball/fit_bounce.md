---
op: fit_bounce
dim: drive
category: ball
in: table
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fit_bounce — DRIVE `ball` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_bounce(v_in, omega_in, v_out, omega_out, normal, bp: 'dict') -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.fit_bounce(v_in, omega_in, v_out, omega_out, normal, bp: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("fit_bounce")`)

## 使い方

跳ねの前後の (v, ω) から (e, μ) を閉形式で戻す(同定)。e = −v_n'/v_n。接線力積 J_t = m(v_t' − v_t) の大きさと
J_n = m(v_n' − v_n) の比が μ —— 滑ったままの領域なら等号、途中で転がりに移った(grip)領域なら **下界**(μ ≥ |J_t|/J_n)。
どちらかは、跳ねた後の接触点の滑り速度が 0 か(grip)で判る。返り値 ``{"e", "mu", "mu_is_lower_bound", "regime", "J_n", "J_t"}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
