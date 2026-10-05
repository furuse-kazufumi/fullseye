---
op: string_tension_from_sag
dim: drive
category: diabolo
in: signal × signal × signal × scalar
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# string_tension_from_sag — DRIVE `diabolo` op

- **データ種**: `signal × signal × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.string_tension_from_sag(p_left, p_right, p_diabolo, mass: 'float', *, accel=None, g: 'float' = 9.81) -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.string_tension_from_sag(p_left, p_right, p_diabolo, mass: 'float', *, accel=None, g: 'float' = 9.81) -> 'dict'`、台帳から引くなら `opsdrive.get("string_tension_from_sag")`)

## 使い方

糸の V 字(棒の先 2 点と軸の位置)から張力を出す(摩擦のない滑車 = 両側の張力が等しい)。

T (û_L + û_R) = m (a − g⃗) の最小二乗: T = m (a − g⃗)·n / |n|²、n = û_L + û_R(û は軸 → 棒の単位ベクトル)。静止(accel = None)
なら T = m g / (sin α_L + sin α_R)(α = 糸の水平からの角)と同じ。残差(釣り合いの破れ)も返す —— 大きければ「加速度の入れ忘れ /
摩擦 / 弾性」の警報。**Raises** ``ValueError``: 形、質量 ≤ 0、軸が棒と重なる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
