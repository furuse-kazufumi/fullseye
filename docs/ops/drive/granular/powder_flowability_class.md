---
op: powder_flowability_class
dim: drive
category: granular
in: scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# powder_flowability_class — DRIVE `granular` op

- **データ種**: `scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.powder_flowability_class(phi_deg: 'float') -> 'dict'` (実装を直接呼ぶなら `import granular; granular.powder_flowability_class(phi_deg: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("powder_flowability_class")`)

## 使い方

安息角 → 流動性区分(USP <1174> Table 1、原典 Carr 1965)。

返り: ``cls``(excellent / good / fair / passable / poor / very poor / very, very poor)、``phi_int``(表を引いた
整数の度 = 四捨五入)、``tabulated``(表の下限 25 度以上か)、``band_upper_deg``(その区分の上限; 上限の無い最後の区分は None ——
返りに inf を入れない、JSON に載らないため)。表は整数の
度なので 30.5 は 31(good)、30.4 は 30(excellent)。**Raises** ``ValueError``: 角が (0, 90) の外。

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
