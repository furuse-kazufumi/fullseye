---
op: gait_step_events
dim: drive
category: locomotion
in: any × scalar × scalar × scalar
out: table
gpu: なし
examples: [walking_ops_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# gait_step_events — DRIVE `locomotion` op

- **データ種**: `any × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gait_step_events(foot_xyz, dt, plant_z, swing_z, min_swing_s: 'float' = 0.1, min_stance_s: 'float' = 0.1, clearance_min: 'float' = 0.02, advance_min: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import locomotion; locomotion.gait_step_events(foot_xyz, dt, plant_z, swing_z, min_swing_s: 'float' = 0.1, min_stance_s: 'float' = 0.1, clearance_min: 'float' = 0.02, advance_min: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsdrive.get("gait_step_events")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Extract walking steps (liftoff -> swing -> touchdown) from foot trajectories, with hysteresis.

足の軌跡から「一歩」を取り出す。足の高さにヒステリシスを掛けて着地 / 遊脚を決め
(``z < plant_z`` で着地、``z > swing_z`` で遊脚、その間は直前の状態を保つ = 接地の
ばたつきを一歩に数えない)、離地 → 遊脚 → 着地の 1 周期のうち次をすべて満たすものだけを
一歩と認める:

* 遊脚の長さ ≥ ``min_swing_s`` [s]、着地後の立脚 ≥ ``min_stance_s`` [s] (最後の一歩は
  記録の終わりまで立脚していれば足りる)
* 遊脚中の足の最高点 − 直前の立脚の始まりの高さ ≥ ``clearance_min`` [m] (すり足を落とす)
* 着地点の水平の前進(直前の立脚の始まり = 前の足場から着地点への変位の、進行方向への
  成分)≥ ``advance_min`` [m] (引きずりを落とす)。ヒステリシスの帯の中ではまだ「着地」と
  読むので、離地のコマの位置から測ると遊脚の出だしの分だけ短く出る —— だから前の足場から
  測る。進行方向は全足の最初と最後の位置の平均の差(動いていなければ +x)。

``foot_xyz`` は (T, F, 3) の世界座標 [m] (z が上)、``dt`` はコマの間隔 [s]。
``plant_z`` < ``swing_z`` は地面からの高さの閾値 [m] (既定値を置かない: 足の形・
センサで違う)。
返り値 ``{"steps": [{foot, liftoff, touchdown, t_touchdown, xy, advance, clearance,
swing_s}], "per_foot": [n_steps …], "rejected": [{foot, touchdown, reason}],
"alternating": bool, "direction": (2,)}``。``steps`` は着地のコマ順。``alternating`` は
足が 2 本以上で、続く一歩がいつも別の足のとき True。

★同じコマで 2 本以上の足が着地したら ``ValueError`` で拒否する: 両足の同時着地は歩行の
一歩ではなく(跳躍・両足着地)、交互かどうかの順序も決まらない(onocollo の
``alternation_ok`` が min_sep で落としていた穴を、ここでは入口で止める)。
空の入力(``foot_xyz`` が 0 要素)は ValueError で拒否する。

English: hysteresis step detector (plant below ``plant_z``, swing above ``swing_z``);
a step needs enough swing time, stance dwell, clearance and forward advance. Two feet
touching down in the same frame raise ``ValueError``. Adapted from onocollo
``evolve/musculo.py`` ``detect_steps`` / ``alternation_ok`` (Apache-2.0, same author).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [walking_ops_tour](../../../../examples/walking_ops_tour.py) — `py -3.11 examples/walking_ops_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`locomotion`)

[contact_points](contact_points.md) · [com_from_silhouette](com_from_silhouette.md) · [support_polygon](support_polygon.md) · [com_support_margin](com_support_margin.md) · [gait_phase](gait_phase.md) · [support_line_margin](support_line_margin.md) · [lipm_capture_point](lipm_capture_point.md) · [capture_margin](capture_margin.md)

---
*Provenance: locomotion.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
