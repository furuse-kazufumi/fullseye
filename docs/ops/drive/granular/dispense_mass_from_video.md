---
op: dispense_mass_from_video
dim: drive
category: granular
in: any × scalar × scalar × signal
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# dispense_mass_from_video — DRIVE `granular` op

- **データ種**: `any × scalar × scalar × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dispense_mass_from_video(frames, pitch: 'float', bulk_density: 'float', times, ground=None) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.dispense_mass_from_video(frames, pitch: 'float', bulk_density: 'float', times, ground=None) -> 'dict'`、台帳から引くなら `opsdrive.get("dispense_mass_from_video")`)

## 使い方

高さ図の列から出た質量と排出率 —— 各コマの山の体積 × ρ_b、時間に対する直線当て(最小二乗)。

返り: ``masses`` [kg]、``rate``(傾き [kg/s])、``total``(最後 − 最初)、``rms``(直線残差 [kg])。
**Raises** ``ValueError``: コマが 2 未満 / 時刻の数が合わない / 時刻が単調でない。
画像の体積分解能は ``pitch³ ρ_b`` の桁(1 mm・1500 kg/m³ で 1.5 mg/画素³ だが、縁の 1 画素の
不確かさが面積 × pitch で乗るので実際は g 級)。mg 級は秤に譲る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [hopper_discharge_rate](hopper_discharge_rate.md) · [spoon_tilt_critical](spoon_tilt_critical.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
