---
op: ttc_from_range
dim: drive
category: ttc
in: 
out: scalar
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# ttc_from_range — DRIVE `ttc` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ttc_from_range(distance: 'float', closing_speed: 'float') -> 'float'` (実装を直接呼ぶなら `import drivettc; drivettc.ttc_from_range(distance: 'float', closing_speed: 'float') -> 'float'`、台帳から引くなら `opsdrive.get("ttc_from_range")`)

## 使い方

距離と閉じる速さから τ = d / v(秒)。世界の姿勢から出す真値(v ≤ 0 なら ``inf``、d < 0 は ``ValueError``)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_scale](ttc_from_scale.md) · [label_extent](label_extent.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
