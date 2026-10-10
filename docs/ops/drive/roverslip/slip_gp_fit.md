---
op: slip_gp_fit
dim: drive
category: roverslip
in: signal × signal
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# slip_gp_fit — DRIVE `roverslip` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.slip_gp_fit(slopes, slips, length_scales=None, noise_levels=None) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.slip_gp_fit(slopes, slips, length_scales=None, noise_levels=None) -> 'dict'`、台帳から引くなら `opsdrive.get("slip_gp_fit")`)

## 使い方

斜面の角 → 滑り率のガウス過程(RBF の核 + 一様な観測雑音)。超パラメータは対数周辺尤度の格子探索。

y は平均を引いて標準偏差で割ってから当てはめる(信号の分散 σ_f² = 1 に固定、ℓ と雑音 σ_n を探す)。
``length_scales`` の既定は角の範囲の 0.05〜2 倍の 16 段(対数)、``noise_levels`` は 0.01〜1(正規化した y の単位)の
16 段。返り値は予測に使う dict(``kind = "gp"``、``x``・``alpha``・``L``・``ell``・``noise``・``y_mean``・``y_scale``・
``log_marginal_likelihood``)。雑音が角によって変わる(異分散)データでは、帯は全体の平均の幅になる(門の罠)。

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
