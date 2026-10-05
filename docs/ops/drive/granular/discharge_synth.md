---
op: discharge_synth
dim: drive
category: granular
in: scalar × scalar × scalar × scalar × scalar × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# discharge_synth — DRIVE `granular` op

- **データ種**: `scalar × scalar × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.discharge_synth(D0: 'float', d: 'float', bulk_density: 'float', phi_deg: 'float', pitch: 'float', duration: 'float', n_frames: 'int' = 8, grid: 'int' = 256, C: 'float' = 0.58, k: 'float' = 1.4, noise: 'float' = 0.0, seed: 'int | None' = None) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.discharge_synth(D0: 'float', d: 'float', bulk_density: 'float', phi_deg: 'float', pitch: 'float', duration: 'float', n_frames: 'int' = 8, grid: 'int' = 256, C: 'float' = 0.58, k: 'float' = 1.4, noise: 'float' = 0.0, seed: 'int | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("discharge_synth")`)

## 使い方

円孔 ``D0`` から Beverloo の率で落ちた粉が、下で安息角 φ の円錐に積もっていく高さ図の列を合成する。

``V(t) = W t / ρ_b``、``R(t) = (3 V / (π tan φ))^{1/3}``。返り: ``frames``(``n_frames`` 枚、``(grid, grid)``
[m])、``times`` [s]、``W``(真の率 [kg/s])、``masses``(真の質量列)。``noise`` = 高さ図に足す
ガウス雑音の σ [m] (距離センサの雑音の代わり; 地面も揺れるので体積は 0 で切られて偏る —— その偏りを
門で測る)。山が格子からはみ出すと ``ValueError``(体積を黙って切らない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md) · [spoon_tilt_critical](spoon_tilt_critical.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
