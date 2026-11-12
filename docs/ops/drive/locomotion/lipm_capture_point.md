---
op: lipm_capture_point
dim: drive
category: locomotion
in: points × points × scalar
out: points
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# lipm_capture_point — DRIVE `locomotion` op

- **データ種**: `points × points × scalar` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.lipm_capture_point(com, com_vel, com_height, gravity: 'float' = 9.81)` (実装を直接呼ぶなら `import locomotion; locomotion.lipm_capture_point(com, com_vel, com_height, gravity: 'float' = 9.81)`、台帳から引くなら `opsdrive.get("lipm_capture_point")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Instantaneous capture point of the linear inverted pendulum, ``xi = c + c_dot / omega``.

線形倒立振子(LIPM)の捕捉点 ξ = c + ċ/ω、ω = √(g / z_c)(Kajita ほか 2001、
Pratt ほか 2006、Koolen ほか 2012)。足圧中心 p を ξ に置けば重心は p の真上で止まり、
p が ξ から離れていると ξ は ``ξ̇ = ω (ξ - p)`` で指数的に離れていく。

* ``com`` / ``com_vel``: 重心の位置と速度。(3,) か (T, 3) の世界座標 [m]、[m/s]
  (x, y が地面、z が上)。(2,) / (T, 2) の地面の点でもよい。形は 2 つで揃える。
* ``com_height``: LIPM の一定の重心高さ z_c [m] (地面から)。正の有限値。既定値は置かない
  (ロボットごとに違い、間違うと ω が √ で狂う)。
* ``gravity``: 重力加速度 [m/s²]。
* 返り値: ``com`` と同じ形。x, y が捕捉点、3 列のときの z は ``com_z - com_height``
  (振子の支点 = 地面の高さ)。

照合: 解析解 ``x(t) = x0 cosh ωt + (v0/ω) sinh ωt`` から ``ξ(t) = (x0 + v0/ω) e^{ωt}``
(tests/test_locomotion_ops_2026_11_06.py)。
空の入力(``com`` が 0 要素)は ValueError で拒否する。

English: xi = c + c_dot / omega with omega = sqrt(g / z_c); same shape as ``com``; for
3-column input the z of the result is the pendulum pivot height ``com_z - com_height``.
The source of the law is onocollo ``scripts/evis_video/capture_point_train.py``
(Apache-2.0, same author); this is a fresh numpy implementation.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[course_contains](../course/course_contains.md) · [ray_plane_range](../lidar/ray_plane_range.md) · [ray_box_ranges](../lidar/ray_box_ranges.md) · [course_distance](../terrain/course_distance.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [capture_margin](capture_margin.md) · [gait_step_events](gait_step_events.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
