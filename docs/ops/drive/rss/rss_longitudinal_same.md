---
op: rss_longitudinal_same
dim: drive
category: rss
in: table
out: scalar
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# rss_longitudinal_same — DRIVE `rss` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.rss_longitudinal_same(v_rear: 'float', v_front: 'float', p: 'dict', p_front: 'Optional[dict]' = None) -> 'float'` (実装を直接呼ぶなら `import rsssafety; rsssafety.rss_longitudinal_same(v_rear: 'float', v_front: 'float', p: 'dict', p_front: 'Optional[dict]' = None) -> 'float'`、台帳から引くなら `opsdrive.get("rss_longitudinal_same")`)

## 使い方

同方向(論文 Lemma 2 / lib ``calculateSafeLongitudinalDistanceSameDirection``)の最小安全距離 [m]。

``d_min = [ v_r ρ + ½ a ρ² + (v_r + a ρ)²/(2 b_min) − v_f²/(2 b_max) ]_+ + min_distance``。
後続車 c_r のパラメータが ``p``(ρ, accel_max, brake_min, v_max_accel, min_distance)、先行車 c_f の
``brake_max`` は ``p_front``(None なら ``p``)から取る。v_rear, v_front ≥ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [road_eval](../long/road_eval.md) · [long_simulate](../long/long_simulate.md)

## 同カテゴリ(`rss`)

[rss_params](rss_params.md) · [rss_stopping_distance](rss_stopping_distance.md) · [rss_longitudinal_opposite](rss_longitudinal_opposite.md) · [rss_lateral](rss_lateral.md) · [rss_longitudinal_check](rss_longitudinal_check.md) · [rss_lateral_check](rss_lateral_check.md) · [rss_worst_case_gap](rss_worst_case_gap.md) · [rss_worst_case_gap_opposite](rss_worst_case_gap_opposite.md)

---
*Provenance: rsssafety.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
