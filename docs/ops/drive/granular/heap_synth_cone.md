---
op: heap_synth_cone
dim: drive
category: granular
in: scalar × scalar
out: table
examples: [poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# heap_synth_cone — DRIVE `granular` op

- **データ種**: `scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.heap_synth_cone(phi_deg: 'float', radius_px: 'float', pitch: 'float' = 0.001, *, toe_round_px: 'float' = 0.0, apex_blunt_px: 'float' = 0.0, ground_tilt_deg: 'float' = 0.0, margin_px: 'int' = 12, supersample: 'int' = 8, noise: 'float' = 0.0, seed: 'int | None' = None) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.heap_synth_cone(phi_deg: 'float', radius_px: 'float', pitch: 'float' = 0.001, *, toe_round_px: 'float' = 0.0, apex_blunt_px: 'float' = 0.0, ground_tilt_deg: 'float' = 0.0, margin_px: 'int' = 12, supersample: 'int' = 8, noise: 'float' = 0.0, seed: 'int | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("heap_synth_cone")`)

## 使い方

既知の安息角の円錐の山を合成する(側面像 = 反エイリアスの被覆率、高さ図 = セル中心の高さ)。

- ``radius_px``: 裾までの半径 [px] (丸み無しのとき)。高さ ``H = R tan φ``。
- ``ground_tilt_deg``: **基準面の傾き**(せん断型: ``z' = z + x tan β``)。高さ図の基準面(datum)
  が傾いているときの罠(平らでない地面で安息角が足し算される —— 既存 PoC `poc_stockpile_volume`
  と同じ門)。カメラのロール(回転型)とは 2 次でなく **1 次で違う**(β = 5 度・φ = 30 度で
  1.4 度、``atan(tan φ + tan β)`` 対 ``φ + β``)ので別物として扱う。
- ``noise``: 被覆率に足す一様雑音の振幅(縁の揺らぎの代わり)。
- 返り: ``side``(被覆率 ``(rows, cols)``)、``heightmap`` [m]、``ground``(基準面 [m]、同形)、
  ``truth``(phi_deg, R_px, H_px, toe_px, V(数値回転積分 [m³]), V_cone(閉形式)、ground_tilt_deg)、
  ``pitch``。側面像の列 ``x`` の粉の高さ(被覆率の列和)はちょうど ``c(x)`` [px] になる(副画素)。
**Raises** ``ValueError``: 範囲外・円弧の重なり。

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
