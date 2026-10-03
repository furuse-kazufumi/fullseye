---
op: veil_chroma_limit
dim: drive
category: env
in: any × scalar
out: scalar
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# veil_chroma_limit — DRIVE `env` op

- **データ種**: `any × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.veil_chroma_limit(color, luminance: 'float', tol: 'float' = 0.15) -> 'float'` (実装を直接呼ぶなら `import driveenv; driveenv.veil_chroma_limit(color, luminance: 'float', tol: 'float' = 0.15) -> 'float'`、台帳から引くなら `opsdrive.get("veil_chroma_limit")`)

## 使い方

色 ``color``(RGB の比)で輝度 ``luminance`` の灯火に白い光(光幕・霧の大気光)W を足したとき、色度の距離
|(c L + W·1)/|c L + W·1| − c/|c||(balltrack.ball_detect の chroma と同じ量)が ``tol`` に達する W* [cd/m²]。

距離は W に単調に増える(W → ∞ で灰色 (1,1,1)/√3 との距離に漸近)。漸近値が tol 以下なら ``inf``(どれだけ白を足しても
色は読める)。二分法で相対 1e-12。使い道: 逆光の閾値 θ* = √(10 E_glare / W*)(Stiles–Holladay)、霧の中で色が読める距離
d* = ln(1 + W*/L_h)/β(灯火 c L e^{−βd} + 大気光 L_h (1 − e^{−βd}) の色度は c L + L_h (e^{βd} − 1)·1 と同じ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [road_eval](../long/road_eval.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
