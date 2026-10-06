---
op: diabolo_simulate
dim: drive
category: diabolo
in: signal × signal × any × scalar × scalar × table
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# diabolo_simulate — DRIVE `diabolo` op

- **データ種**: `signal × signal × any × scalar × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_simulate(x0, v0, sticks, t_end: 'float', dt: 'float', params: 'dict', *, model: 'str' = 'paper', omega0: 'float' = 0.0, mode0: 'str' = 'on_string', gvec=None, topology: 'bool' = True, plane_rule: 'str' = 'paper', rotation: 'str' = 'paper', flying_rule: 'str' = 'paper') -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_simulate(x0, v0, sticks, t_end: 'float', dt: 'float', params: 'dict', *, model: 'str' = 'paper', omega0: 'float' = 0.0, mode0: 'str' = 'on_string', gvec=None, topology: 'bool' = True, plane_rule: 'str' = 'paper', rotation: 'str' = 'paper', flying_rule: 'str' = 'paper') -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_simulate")`)

## 使い方

棒の動き ``sticks`` のもとでディアボロを ``t_end`` まで刻み ``dt`` で進める。

``sticks`` = 名前(``"fixed"`` / ``"linear_accel"`` / ``"swing"`` / ``"throw"`` / ``"vertical_axis"``)、``{"kind": 名前, 引数…}``、
呼べる物 t ↦ (2, 3)、固定の (2, 3)。``model`` = "paper"(論文の解析模型、:func:`diabolo_dynamics_step`)/ "exact"(伸びない糸の
片側拘束を RATTLE で、張力つき。棒の速度は中心差分)。``topology`` は exact だけに効く(True = 棒を結ぶ面より上では糸が効かない)。

返り ``{"t", "x", "v", "omega", "mode", "tension", "energy", "sticks"}``(energy は J、tension は exact のときだけ、paper は NaN)。
**Raises** ``ValueError``: model の綴り、t_end < 0 / dt ≤ 0、刻みが多すぎる(> 2,000,000)、棒の動きの指定、params。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md) · [string_tension_from_sag](string_tension_from_sag.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
