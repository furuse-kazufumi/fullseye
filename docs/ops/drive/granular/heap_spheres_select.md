---
op: heap_spheres_select
dim: drive
category: granular
in: matrix × scalar × scalar × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# heap_spheres_select — DRIVE `granular` op

- **データ種**: `matrix × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.heap_spheres_select(pos, radius: 'float', floor_height: 'float', bin_radius: 'float', keep_min: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.heap_spheres_select(pos, radius: 'float', floor_height: 'float', bin_radius: 'float', keep_min: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("heap_spheres_select")`)

## 使い方

山に属する球だけを選ぶ: ビンの底板より下(``z < floor_height − r``)で、ビン半径の 3 倍の内側。
ビンに残った球(平底の滞留層)と転がって逃げた球は山ではない。返り: ``pos``(選んだ中心)、``n_in_bin``、
``n_runaway``、``radius_95``(山の半径の目安)。**Raises** ``ValueError``: 残りが ``keep_min`` 未満(山になって
いない —— 滑らかな台で 1,200 個中 600 個が逃げたときに黙って測らないため)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
