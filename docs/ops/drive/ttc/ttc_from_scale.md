---
op: ttc_from_scale
dim: drive
category: ttc
in: 
out: scalar
examples: [poc_ttc_rss]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# ttc_from_scale — DRIVE `ttc` op

- **データ種**: `なし` → `scalar`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ttc_from_scale(w0: 'float', w1: 'float', dt: 'float') -> 'float'` (実装を直接呼ぶなら `import drivettc; drivettc.ttc_from_scale(w0: 'float', w1: 'float', dt: 'float') -> 'float'`、台帳から引くなら `opsdrive.get("ttc_from_scale")`)

## 使い方

見かけの大きさの変化から τ(秒、最初のコマの時刻で): ``τ₀ = Δt · w₁ / (w₁ − w₀)``。

像の幅は奥行きに反比例(``w ∝ 1/Z``)なので ``w₀/w₁ = Z₁/Z₀`` → ``τ₀ = Z₀ Δt / (Z₀ − Z₁) = Δt / (1 − w₀/w₁)``。
Lee の ``θ/θ̇`` を前進差分にした ``Δt · w₀ / (w₁ − w₀)`` は 2 コマ目の τ で、ちょうど Δt 小さい。
大きくならなければ(``w₁ ≤ w₀``)``inf``。幅は正でなければ ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_range](ttc_from_range.md) · [label_extent](label_extent.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
