---
op: spheroid_closest
dim: drive
category: diabolo
in: signal × table
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# spheroid_closest — DRIVE `diabolo` op

- **データ種**: `signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.spheroid_closest(x, sph: 'dict') -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.spheroid_closest(x, sph: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("spheroid_closest")`)

## 使い方

点 x → 回転楕円体の面の最近点 ``point``・符号つき距離 ``s``(内側 > 0、論文の s の定義)・外向きの単位法線 ``normal``
(最近点での勾配の向き)。

最近点は子午面の楕円への Eberly の二分法。★公開実装は中心から放射方向に縮めて戻し(最近点ではない、楕円体の外 5 mm の点で
最大 2.2 mm 違う)、法線を (x/b, y/a, z/b) で近似する(勾配なら 2 乗、軸の上以外では最大 12.2° ずれる)。ここでは本文の
「最も近い点へ動かす」と真の法線で書く。**Raises** ``ValueError``: x が有限の 3-vector でない、sph が楕円体の dict でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md) · [string_tension_from_sag](string_tension_from_sag.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
