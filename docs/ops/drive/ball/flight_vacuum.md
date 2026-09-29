---
op: flight_vacuum
dim: drive
category: ball
in: signal
out: points
examples: [poc_ball_bounce]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# flight_vacuum — DRIVE `ball` op

- **データ種**: `signal` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.flight_vacuum(p0, v0, t, g: 'float' = 9.81) -> 'np.ndarray'` (実装を直接呼ぶなら `import ballistics; ballistics.flight_vacuum(p0, v0, t, g: 'float' = 9.81) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("flight_vacuum")`)

## 使い方

真空の放物線(閉形式): p(t) = p₀ + v₀ t − ½ g t² ẑ。``t`` はスカラか (N,)、返り値 (3,) か (N, 3)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`

## 型が繋がる次の op(`points` を入力に取れる)

[course_contains](../course/course_contains.md) · [ray_plane_range](../lidar/ray_plane_range.md) · [ray_box_ranges](../lidar/ray_box_ranges.md) · [course_distance](../terrain/course_distance.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md) · [fit_parabola](fit_parabola.md) · [flight_fit](flight_fit.md) · [fit_aero](fit_aero.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md) · [bounce](bounce.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
