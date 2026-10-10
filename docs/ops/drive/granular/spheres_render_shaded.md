---
op: spheres_render_shaded
dim: drive
category: granular
in: matrix × scalar × scalar × scalar × scalar
out: rgb
examples: [poc_granular_heap_repose, poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# spheres_render_shaded — DRIVE `granular` op

- **データ種**: `matrix × scalar × scalar × scalar × scalar` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.spheres_render_shaded(pos, radius: 'float', pitch: 'float', extent: 'float', height: 'float', light=(-0.4, -0.6, 0.7)) -> 'np.ndarray'` (実装を直接呼ぶなら `import granular; granular.spheres_render_shaded(pos, radius: 'float', pitch: 'float', extent: 'float', height: 'float', light=(-0.4, -0.6, 0.7)) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("spheres_render_shaded")`)

## 使い方

横からの正射影を陰影つきで描く(numpy の z バッファ、Lambert)。GIF 用。返り ``(rows, cols, 3)`` [0, 1]。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`
- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
