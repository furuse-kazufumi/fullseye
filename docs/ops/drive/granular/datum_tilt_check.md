---
op: datum_tilt_check
dim: drive
category: granular
in: table
out: table
examples: [poc_geodetic_height_frames, poc_granular_heap_repose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# datum_tilt_check — DRIVE `granular` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.datum_tilt_check(result, warn_deg: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import granular; granular.datum_tilt_check(result, warn_deg: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("datum_tilt_check")`)

## 使い方

:func:`repose_angle_silhouette` の返り(左右の斜面角と地面の傾き)から **基準面が傾いていないか** を判定する。

平らでない地面(datum)の傾き β は安息角に足し算される(既存の体積 PoC と同じ罠)。せん断型(``z' = z + x tan β``)
なら左右の斜面は ``atan(tan φ ± tan β)``、カメラのロール(回転型)なら ``φ ± β`` —— **どちらも左右差 ≈ 2β** なので、
左右差が ``warn_deg`` を超えたら警報。2 つの模型は 1 次で違う(β = 5 度・φ = 30 度で左の斜面が 33.62 対 35.00 度、
実測)ので、両方の補正値を返し、どちらを使うかは地面の由来(高さ図の datum か、カメラの傾きか)で決める:
``phi_shear_deg``(tan の引き算、``ground_deg`` を使う)、``phi_roll_deg``(角の引き算 = 左右の平均そのもの)、
``beta_shear_deg``(左右の tan 差から読んだ β = atan((tan L − tan R)/2))、``beta_roll_deg``(= 左右差 / 2)。
**Raises** ``ValueError``: 欄が無い / 角が範囲外 / ``warn_deg ≤ 0``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`
- [poc_granular_heap_repose](../../../../examples/poc_granular_heap_repose.py) — `py -3.11 examples/poc_granular_heap_repose.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`granular`)

[heap_volume_cone](heap_volume_cone.md) · [heap_mass](heap_mass.md) · [heap_volume_heightmap](heap_volume_heightmap.md) · [beverloo_rate](beverloo_rate.md) · [beverloo_fit](beverloo_fit.md) · [discharge_synth](discharge_synth.md) · [dispense_mass_from_video](dispense_mass_from_video.md) · [hopper_discharge_rate](hopper_discharge_rate.md)

---
*Provenance: granular.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
