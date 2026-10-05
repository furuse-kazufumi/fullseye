---
op: spoon_tilt_dispense
dim: drive
category: granular
in: scalar × scalar × scalar × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# spoon_tilt_dispense — DRIVE `granular` op

- **データ種**: `scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spoon_tilt_dispense(theta_deg: 'float', phi_deg: 'float', L: 'float', h0: 'float', h_wall: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.spoon_tilt_dispense(theta_deg: 'float', phi_deg: 'float', L: 'float', h0: 'float', h_wall: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("spoon_tilt_dispense")`)

## 使い方

傾き θ で出た粉の割合(:func:`spoon_tilt_critical` と同じ 2 次元模型)。

保持断面 ``A(θ) = ∫₀ᴸ min((tan φ − tan θ) x, h_wall) dx``(``h_wall`` = 奥壁の高さ、None = 無限)、
出た割合 ``= 1 − min(A, L h0) / (L h0)``。θ ≤ θ_c で 0、θ ≥ φ で 1、間は単調。
返り: ``fraction``, ``retained_area``, ``theta_c_deg``。**Raises** ``ValueError``: 引数の範囲。

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
