---
op: beverloo_fit
dim: drive
category: granular
in: signal × signal × scalar × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# beverloo_fit — DRIVE `granular` op

- **データ種**: `signal × signal × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.beverloo_fit(D0, W, d: 'float', bulk_density: 'float', k: 'float' = 1.4, g: 'float' = 9.80665) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.beverloo_fit(D0, W, d: 'float', bulk_density: 'float', k: 'float' = 1.4, g: 'float' = 9.80665) -> 'dict'`、台帳から引くなら `opsdrive.get("beverloo_fit")`)

## 使い方

排出率の列 ``W_i(D0_i)`` に ``log W = log(C ρ_b √g) + n log(D₀ − k d)`` を最小二乗で当て、指数 ``n``
と係数 ``C`` を返す(真値 n = 2.5、C ≈ 0.58)。返り: ``n``, ``C``, ``rms_log``(対数残差)。
**Raises** ``ValueError``: 点が 3 未満 / ``D0 ≤ k d`` の点がある / W ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md) · [spoon_tilt_critical](spoon_tilt_critical.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
