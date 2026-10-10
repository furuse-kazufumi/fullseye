---
op: social_force_step
dim: drive
category: traffic
in: points × points × points
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# social_force_step — DRIVE `traffic` op

- **データ種**: `points × points × points` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.social_force_step(pos, vel, goals, *, dt: 'float', v0, tau: 'float', A: 'float', B: 'float', radius, walls=None)` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.social_force_step(pos, vel, goals, *, dt: 'float', v0, tau: 'float', A: 'float', B: 'float', radius, walls=None)`、台帳から引くなら `opsdrive.get("social_force_step")`)

## 使い方

social force の 1 歩(単位質量あたり。Helbing & Molnár 1995 / Helbing, Farkas, Vicsek 2000 の形)。

    dv_i/dt = (v0_i e_i − v_i)/τ + Σ_j A exp((r_ij − d_ij)/B) n_ij + Σ_W A exp((r_i − d_iW)/B) n_iW

e_i = 目標への単位ベクトル(目標に 1e-9 m 以内なら 0)、r_ij = r_i + r_j、d_ij = |x_i − x_j|、
n_ij = (x_i − x_j)/d_ij。壁 W は線分 ((x0, y0), (x1, y1)) の列で、d_iW と n_iW は最近点から。

積分(指数積分): 斥力 F を刻みの間一定と置き、線形部分 (v_d − v)/τ(v_d = v0 e + τ F)を厳密に解く:
v' = v_d + (v − v_d) e^{−dt/τ}、x' = x + v_d dt + (v − v_d) τ (1 − e^{−dt/τ})。
1 人で斥力が無ければ v(t) = v0(1 − e^{−t/τ}) に **dt に依らず** 一致する(門)。斥力がある時は 1 次の誤差。

引数: ``pos``, ``vel``, ``goals`` は (N, 2)。``v0`` と ``radius`` はスカラーか (N,)。``walls`` は (M, 2, 2) か None。
戻り値: (pos', vel')。配置が鏡映・点対称なら結果も同じ対称性を保つ(式が対称なので。門で確かめる)。

**Raises** ``ValueError``: 形の不一致、非有限、τ・B・dt ≤ 0、A < 0、半径 < 0、2 人の位置が一致。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
