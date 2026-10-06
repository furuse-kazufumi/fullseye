---
op: two_point_depth
dim: drive
category: pegsim
in: table
out: scalar
examples: [poc_peg_insertion_tactile, poc_pegsim_insertion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# two_point_depth — DRIVE `pegsim` op

- **データ種**: `table` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.two_point_depth(kp, theta: 'float', model: 'str' = 'exact') -> 'float'` (実装を直接呼ぶなら `import pegsim; pegsim.two_point_depth(kp, theta: 'float', model: 'str' = 'exact') -> 'float'`、台帳から引くなら `opsdrive.get("two_point_depth")`)

## 使い方

傾き θ [rad] で二点接触が始まる挿入深さ l₂ [m] (最狭部から先端中心まで)。3 つの模型を名前で選ぶ。

``"exact"``: 3-D の円柱で厳密 l₂ = (2R − r(cos θ + sec θ)) / tan θ(導出 (1′))。``"small_angle"``: l₂ = 2c_r / sin θ
(OCW p.9 の l/d = c/θ を半径 clearance で書いたもの)。``"rectangle"``: 2-D の長方形近似 (D − d/cos θ)/tan θ(縁の点の
高さ r sin θ を無視するので θ = 6° で 0.5 mm 浅く出る —— 間違いの量を測るために残す)。
**Raises** ``ValueError``: θ ≤ 0、θ ≥ θ_m_exact(入口にすら入らない)、未知の model。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`
- [poc_pegsim_insertion](../../../../examples/poc_pegsim_insertion.py) — `py -3.11 examples/poc_pegsim_insertion.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`pegsim`)

[peg_params](peg_params.md) · [whitney_clearance](whitney_clearance.md) · [wedging_check](wedging_check.md) · [jamming_diagram](jamming_diagram.md) · [chamfer_capture](chamfer_capture.md) · [contact_state_predict](contact_state_predict.md) · [circle_fit_known_radius](circle_fit_known_radius.md) · [cylinder_fit_known_radius](cylinder_fit_known_radius.md)

---
*Provenance: pegsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
