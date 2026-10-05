---
op: diabolo_dynamics_step
dim: drive
category: diabolo
in: table × matrix × matrix × scalar × table
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# diabolo_dynamics_step — DRIVE `diabolo` op

- **データ種**: `table × matrix × matrix × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_dynamics_step(state: 'dict', sticks_prev, sticks_now, dt: 'float', params: 'dict', *, plane_rule: 'str' = 'paper', rotation: 'str' = 'paper', flying_rule: 'str' = 'paper') -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_dynamics_step(state: 'dict', sticks_prev, sticks_now, dt: 'float', params: 'dict', *, plane_rule: 'str' = 'paper', rotation: 'str' = 'paper', flying_rule: 'str' = 'paper') -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_dynamics_step")`)

## 使い方

論文の解析模型を 1 ステップ進める(ディアボロ = 質点 + 補助の回転楕円体 + 重力)。

``state`` = ``{"x", "v", "omega", "mode"}``(mode は :data:`DIABOLO_STATES`)。棒の組 = matrix (2, 3)。手順(本文の 1–4):
前進 Euler で x += v dt、v += g dt → 新しい楕円体 → 状態遷移 → 糸に乗っていて外に出たら最近点へ戻し、v_pull(変位/dt の
内向き法線成分)を v_origin + v_edge で頭打ち(式 3)、張りつめの近く(間隔 > l − 5 cm)では面の規則(式 4)、外向きの法線速度を
消す(本文は明記せず、公開実装に合わせた)→ 回転(式 2: ω_t = ω_{t−1} + μ Δ_string、Δ_string = d_R の増分、μ = μ_acc / μ_dec)。
減衰係数は全部 1(公開実装の既定)。

選べる形(公開実装との比較用): ``plane_rule`` = "paper"(式 4: n_plane = x̂ × (x_L − x_R) の向きだけ残す)/ "code"(前後の
成分だけ消す); ``rotation`` = "paper"(式 2、刻みに依らない望遠鏡和)/ "code"(Δω = k (Δd_R/dt − ω r)、k = 0.01。刻みを半分に
すると ω が 2 倍になる); ``flying_rule`` = "paper"(図: s > c_F)/ "code"(棒を結ぶ面より上)。

返り ``{"x", "v", "omega", "mode", "s", "pulled", "v_pull_raw"}``。**Raises** ``ValueError``: 選択肢の綴り、知らない mode、
dt ≤ 0、state の鍵の欠け、棒の組の形。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md) · [string_tension_from_sag](string_tension_from_sag.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
