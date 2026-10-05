---
op: path_slip_risk
dim: drive
category: roverslip
in: matrix × image2d × scalar × table
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# path_slip_risk — DRIVE `roverslip` op

- **データ種**: `matrix × image2d × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.path_slip_risk(path, dtm, cell: 'float', model, alpha: 'float' = 0.9, speed: 'float' = 0.05, s_max: 'float' = 0.9) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.path_slip_risk(path, dtm, cell: 'float', model, alpha: 'float' = 0.9, speed: 'float' = 0.05, s_max: 'float' = 0.9) -> 'dict'`、台帳から引くなら `opsdrive.get("path_slip_risk")`)

## 使い方

経路を辺ごとに評価する: 傾き、平均の滑り、CVaR_α の滑り、``s_max`` を越える確率(ガウス過程は正規分布、
分位点回帰は分位点の曲線の内挿)、平均の滑りでの所要時間と CVaR での所要時間。

返り値 ``{"length" [m], "time_mean" [s], "time_cvar" [s], "max_pitch" [deg], "max_mean_slip", "max_cvar_slip",
"p_exceed_max": 辺ごとの越える確率の最大, "p_exceed_any": 辺が独立と置いた 1 − Π(1 − p), "pitch", "mean_slip",
"cvar_slip", "p_exceed"}``(後ろ 4 つは辺ごと)。下りの辺は −s で測る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
