---
op: sight_stop_speed
dim: drive
category: env
in: scalar × scalar × scalar
out: scalar
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# sight_stop_speed — DRIVE `env` op

- **データ種**: `scalar × scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.sight_stop_speed(sight: 'float', reaction: 'float', brake: 'float', theta: 'float' = 0.0, c_rr: 'float' = 0.0, k: 'float' = 0.0, g: 'float' = 9.80665) -> 'float'` (実装を直接呼ぶなら `import driveenv; driveenv.sight_stop_speed(sight: 'float', reaction: 'float', brake: 'float', theta: 'float' = 0.0, c_rr: 'float' = 0.0, k: 'float' = 0.0, g: 'float' = 9.80665) -> 'float'`、台帳から引くなら `opsdrive.get("sight_stop_speed")`)

## 使い方

見える距離 ``sight`` の中で止まれる最大の速さ v*: drivelong.stopping_distance_grade(v*) = sight。

k = 0 では v ρ + v²/(2A) = D の正の根 v* = A (√(ρ² + 2D/A) − ρ)(A = brake + g sin θ + c_rr g cos θ)。
k > 0 は停止距離が v に単調なので二分法(1e-12)。A ≤ 0(下りで制動が負ける)なら 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
