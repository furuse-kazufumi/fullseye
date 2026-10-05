---
op: heap_volume_cone
dim: drive
category: granular
in: scalar × scalar
out: table
examples: [poc_granular_heap_repose, poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# heap_volume_cone — DRIVE `granular` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.heap_volume_cone(R: 'float | None' = None, H: 'float | None' = None, phi_deg: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.heap_volume_cone(R: 'float | None' = None, H: 'float | None' = None, phi_deg: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("heap_volume_cone")`)

## 使い方

円錐の山の閉形式 —— ``R``・``H``・``phi_deg`` のうち **ちょうど 2 つ** を与えると残りと体積を返す。

``V = (π/3) R² H``、``H = R tan φ``。返り: ``R``, ``H``, ``phi_deg``, ``V`` [m³]、``A``(底面積 πR²)。
**Raises** ``ValueError``: 与えた数が 2 つでない、または ≤ 0 / 非有限 / 角が (0, 90) の外。
3 つ全部渡されたときも拒否する(矛盾した 3 つ組を黙って片方で上書きしない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`
- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md) · [spoon_tilt_critical](spoon_tilt_critical.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
