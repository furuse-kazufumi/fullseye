---
op: hopper_discharge_rate
dim: drive
category: granular
in: signal × signal × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# hopper_discharge_rate — DRIVE `granular` op

- **データ種**: `signal × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hopper_discharge_rate(mass_below, times, mass_total: 'float', *, lo: 'float' = 0.2, hi: 'float' = 0.8) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.hopper_discharge_rate(mass_below, times, mass_total: 'float', *, lo: 'float' = 0.2, hi: 'float' = 0.8) -> 'dict'`、台帳から引くなら `opsdrive.get("hopper_discharge_rate")`)

## 使い方

底板より下の質量の列 ``m(t)`` から排出率 [kg/s] —— 全質量の ``lo``〜``hi`` の帯だけを直線で当てる(立ち上がりと
止まり際を除く; Beverloo の定常流の仮定)。返り: ``rate``, ``n_frames``(帯のコマ数), ``t_range``, ``rms`` [kg]。
**Raises** ``ValueError``: 帯に 3 コマ未満(排出が速すぎてコマが無い —— 黙って 2 点の傾きを返さない)/ 時刻が単調でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [spoon_tilt_critical](spoon_tilt_critical.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
