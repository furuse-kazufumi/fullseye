---
op: stopping_distance_grade
dim: drive
category: long
in: scalar × scalar × scalar
out: scalar
examples: [poc_driving_longitudinal, poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# stopping_distance_grade — DRIVE `long` op

- **データ種**: `scalar × scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.stopping_distance_grade(v: 'float', reaction: 'float', brake: 'float', theta: 'float' = 0.0, c_rr: 'float' = 0.0, k: 'float' = 0.0, g: 'float' = 9.80665) -> 'float'` (実装を直接呼ぶなら `import drivelong; drivelong.stopping_distance_grade(v: 'float', reaction: 'float', brake: 'float', theta: 'float' = 0.0, c_rr: 'float' = 0.0, k: 'float' = 0.0, g: 'float' = 9.80665) -> 'float'`、台帳から引くなら `opsdrive.get("stopping_distance_grade")`)

## 使い方

停止距離の閉形式 = 空走 v ρ + 制動距離 (1/(2k)) ln(1 + k v²/A)、A = brake + g sin θ + c_rr g cos θ(k = 0 で v²/(2A))。

θ > 0 が上り(止まりやすい)、θ < 0 が下り。ρ の間は速さを保つ。A ≤ 0(下りで制動が坂に負ける)なら止まらない → ``inf``。
平地・c_rr = k = 0 で ``rsssafety.rss_stopping_distance(v, ρ, 0, brake)`` と同じ式。

**Raises** ``ValueError``: v < 0、非有限、|θ| ≥ 45°。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`
- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [stop_line_plan](stop_line_plan.md) · [hill_hold_brake_min](hill_hold_brake_min.md) · [hill_start_rollback](hill_start_rollback.md) · [hill_start_command](hill_start_command.md) · [julian_day](../env/julian_day.md) · [sun_at](../env/sun_at.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
