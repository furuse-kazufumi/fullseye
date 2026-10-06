---
op: ks_step
dim: drive
category: commonroad
in: any × any
out: any
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ks_step — DRIVE `commonroad` op

- **データ種**: `any × any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.ks_step(state, u, dt: 'float', params=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.ks_step(state, u, dt: 'float', params=None) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("ks_step")`)

## 使い方

運動学単線(KS)モデルを区分一定入力 u = (δ̇, a) で dt だけ RK4 で進める。参照点 = 後軸中心。

state = (x_rear, y_rear, δ, v, ψ)。式: ẋ = v cos ψ、ẏ = v sin ψ、δ̇ = u₀、v̇ = u₁、ψ̇ = v / l_wb · tan δ
(commonroad-vehicle-models ``vehicle_dynamics_ks``、入力の飽和 ``steering_constraints`` / ``acceleration_constraints`` も同じ)。

門: δ = 0 で x = x₀ + v t(1e-9)、一定 δ で半径 l_wb / tan δ の円(1 周で始点へ 1e-6)、commonroad-io があれば
``vehicle_dynamics_ks`` の odeint と 1 step で 1e-6 一致。

**Raises** ``ValueError``: state が (5,) でない・非有限、u が (2,) でない、dt ≤ 0、params が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
