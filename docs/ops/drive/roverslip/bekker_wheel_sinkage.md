---
op: bekker_wheel_sinkage
dim: drive
category: roverslip
in: scalar × table × any
out: scalar
examples: [poc_rover_slip_risk_path]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# bekker_wheel_sinkage — DRIVE `roverslip` op

- **データ種**: `scalar × table × any` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.bekker_wheel_sinkage(load, wheel, soil, form: 'str' = 'classic') -> 'float'` (実装を直接呼ぶなら `import roverslip; roverslip.bekker_wheel_sinkage(load, wheel, soil, form: 'str' = 'classic') -> 'float'`、台帳から引くなら `opsdrive.get("bekker_wheel_sinkage")`)

## 使い方

Bekker の剛な車輪の沈下の近似式 [m]。接地を放物線 ``z(x) = z₀ − x²/D`` で近似し、せん断は入れない。

``load`` は 1 輪の垂直荷重 [N]、D = 2r、``k = k_c/b + k_φ``。荷重は ``W = b k sqrt(D) z₀^(n+1/2) · I(n)``、
``I(n) = ∫₀¹ (1 − t²)ⁿ dt``。
``form = "classic"``: Bekker の教科書の式 ``z = [3W / ((3 − n) b k sqrt(D))]^(2/(2n+1))``。これは
``(1 − t²)ⁿ ≈ 1 − n t²`` と置いた ``I(n) ≈ (3 − n)/3`` で、**n = 1 でだけ厳密**(n = 1.9 では I を 21 % 大きく
見積もり、沈下を 17 % 深く出す —— 2026-10-06 の試作で数値積分と比べて見つけた)。
``form = "parabolic"``: 同じ放物線のまま ``I(n) = √π Γ(n+1) / (2 Γ(n + 3/2))`` を厳密に使う。小さな沈下
(z ≪ D)で :func:`wheel_sinkage` の数値積分(後側の接地なし、τ = 0)に収束する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_rover_slip_risk_path](../../../../examples/poc_rover_slip_risk_path.py) — `py -3.11 examples/poc_rover_slip_risk_path.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`roverslip`)

[bekker_pressure](bekker_pressure.md) · [wheel_forces](wheel_forces.md) · [wheel_sinkage](wheel_sinkage.md) · [wheel_traction_curve](wheel_traction_curve.md) · [slope_slip_curve](slope_slip_curve.md) · [ground_shift_track](ground_shift_track.md) · [odometry_slip](odometry_slip.md) · [slip_gp_fit](slip_gp_fit.md)

---
*Provenance: roverslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
