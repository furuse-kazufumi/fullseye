---
op: spoon_tilt_critical
dim: drive
category: granular
in: scalar × scalar × scalar
out: scalar
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# spoon_tilt_critical — DRIVE `granular` op

- **データ種**: `scalar × scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.spoon_tilt_critical(phi_deg: 'float', L: 'float', h0: 'float', lip: 'str' = 'wall') -> 'float'` (実装を直接呼ぶなら `import granular; granular.spoon_tilt_critical(phi_deg: 'float', L: 'float', h0: 'float', lip: 'str' = 'wall') -> 'float'`、台帳から引くなら `opsdrive.get("spoon_tilt_critical")`)

## 使い方

スプーンから粉がこぼれ始める傾き θ_c [度] (2 次元断面、準静的、壁摩擦なし —— **自分の導出**)。

模型: 床の長さ ``L``(唇から奥壁まで、奥壁は床に垂直)、水平で深さ ``h0`` に平らに盛った粉。唇を下げて床を θ 傾ける。
粉の自由表面は水平から φ(安息角)までしか立てないので、唇を通る斜面は**床から見て φ − θ**。

* ``lip="wall"``(既定: 口に縁があり、初めは口まで平らに満ちている、初めの面積 ``L h0``): 保持できる断面は
  ``A(θ) = ½ L² tan(φ − θ)``(床と表面の楔)。``L h0`` を超えて保持できなくなる傾きが ``θ_c = φ − atan(2 h0 / L)``(atan2 で)。
  盛りが多いほど早くこぼれ、``h0 → 0`` で ``θ_c → φ``、θ = φ で全部出る。``2 h0 / L ≥ tan φ`` なら水平でも既に保持できない(0 を返す)。
* ``lip="open"``(口に壁の無い器): 前面は初めから安息角の斜面なので **θ = 0⁺ からこぼれる** —— 常に 0 を返す。

★2026-10-05 まで ``wall`` の楔の傾きを ``tan φ − tan θ`` と書いていた(小角の近似、``θ_c = atan(tan φ − 2 h0 / L)``)。
θ = 10 度・φ = 30 度で楔の傾きが 10 % 大きく、L 50 mm・h0 5 mm で θ_c が 20.67 度(厳密 18.69 度)と出ていた。
**Raises** ``ValueError``: φ が (0, 90) の外、L / h0 が ≤ 0、``lip`` が wall / open 以外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
