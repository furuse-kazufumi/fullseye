---
op: ground_shift_track
dim: drive
category: roverslip
in: any
out: table
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# ground_shift_track — DRIVE `roverslip` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ground_shift_track(frames, pixel_size: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import roverslip; roverslip.ground_shift_track(frames, pixel_size: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("ground_shift_track")`)

## 使い方

地面を見下ろすカメラのコマ列から、隣り合うコマの並進を、窓つきの相互相関(整数)と
並進の Lucas–Kanade(副画素)で測り、累積する。

``frames`` は (T, H, W) の配列か同じ形の 2-D 配列の列(T ≥ 2)。``pixel_size`` は地面での画素の大きさ [m]。
返り値 ``{"step": (T−1, 2) の (drow, dcol) [m]、"position": (T, 2) の累積 [m]、"peak": (T−1,) 合わせた後の正規化相関}``。
``step`` は **像の中で模様が動いた量**(カメラ・車体の移動はその逆向き —— 前に進むと地面は後ろへ流れる)。
1 コマの移動は像の 1/4 程度まで(相関は周期的なので、半分を越えると折り返す)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [bekker_wheel_sinkage](bekker_wheel_sinkage.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
