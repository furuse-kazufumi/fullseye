---
op: diabolo_spin_from_markers
dim: drive
category: diabolo
in: signal × signal × scalar × scalar
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# diabolo_spin_from_markers — DRIVE `diabolo` op

- **データ種**: `signal × signal × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_spin_from_markers(phases, smears, dt: 'float', exposure: 'float', *, use_smear: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_spin_from_markers(phases, smears, dt: 'float', exposure: 'float', *, use_smear: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_spin_from_markers")`)

## 使い方

コマごとの位相 ψ_k(mod 2π)とぶれの弧の幅 → 回転の速さ ω、単位 rad/s(軸のまわり、右ねじ)。

隣のコマの差を (−π, π] に包むと |ω| dt < π までしか読めない(ナイキストで折り返す、車輪の錯視)。``use_smear`` なら
弧の幅 / 露光 = |ω| の粗い値で 2π k の枝を選ぶ(折り返さない粗い値 × 折り返す精しい値)。枝の間隔 2π/dt に対して弧の幅の
誤差が半分より小さいことを前提にする。返り ``{"omega", "omega_wrapped", "omega_smear", "branch"}``。
**Raises** ``ValueError``: 位相が 2 コマ未満、長さが違う、dt ≤ 0、露光 < 0、有限でない値。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
