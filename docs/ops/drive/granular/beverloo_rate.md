---
op: beverloo_rate
dim: drive
category: granular
in: scalar × scalar × scalar
out: scalar
examples: [poc_granular_heap_repose, poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# beverloo_rate — DRIVE `granular` op

- **データ種**: `scalar × scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.beverloo_rate(D0: 'float', d: 'float', bulk_density: 'float', C: 'float' = 0.58, k: 'float' = 1.4, g: 'float' = 9.80665) -> 'float'` (実装を直接呼ぶなら `import granular; granular.beverloo_rate(D0: 'float', d: 'float', bulk_density: 'float', C: 'float' = 0.58, k: 'float' = 1.4, g: 'float' = 9.80665) -> 'float'`、台帳から引くなら `opsdrive.get("beverloo_rate")`)

## 使い方

Beverloo の排出則 ``W = C ρ_b √g (D₀ − k d)^{5/2}`` [kg/s] (Beverloo ほか 1961; 係数 C ≈ 0.58、
k ≈ 1.4 は Nedderman 1992 の整理)。``D0`` = 円孔の直径 [m]、``d`` = 粒径 [m]、``bulk_density`` = かさ密度。

**Raises** ``ValueError``: ``D0 ≤ k d``(有効開口が無い。式は負の底を 5/2 乗できないし、現実には
詰まる)/ いずれかが ≤ 0 / 非有限。``D0/d < 6`` 程度では間欠流・詰まりが起きる(式の適用外)が、
それはここでは拒否せず、返りの検査は呼び手に委ねる(閾は材料依存)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`
- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md) · [spoon_tilt_critical](spoon_tilt_critical.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
