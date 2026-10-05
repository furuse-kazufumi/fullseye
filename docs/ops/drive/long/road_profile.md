---
op: road_profile
dim: drive
category: long
in: table
out: table
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# road_profile — DRIVE `long` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.road_profile(profile_xz, l0: 'float' = 0.0) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelong; drivelong.road_profile(profile_xz, l0: 'float' = 0.0) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("road_profile")`)

## 使い方

水平距離と高さの折線 (x, z)(drivecourse.course_slope の ``profile`` と同じ形)を、**路面に沿った弧長 l** の縦断にする。

返り値 = ``{"l" (n,), "x" (n,), "z" (n,), "sin" (n−1,), "cos" (n−1,)}``。l は ``l0`` から始まる折れ点の弧長。
区間 i の勾配角 θ_i は sin = Δz/Δl、cos = Δx/Δl(両端の外は平ら: θ = 0、z は端の値)。

**Raises** ``ValueError``: 2 点未満、非有限、x が狭義単調増加でない、勾配が 45° 以上。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
