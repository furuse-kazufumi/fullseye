---
op: diabolo_axis_from_image
dim: drive
category: diabolo
in: rgb × table × table
out: table
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# diabolo_axis_from_image — DRIVE `diabolo` op

- **データ種**: `rgb × table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_axis_from_image(img, cam: 'dict', params: 'dict', *, refine: 'bool' = True, iters: 'int' = 15) -> 'dict'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_axis_from_image(img, cam: 'dict', params: 'dict', *, refine: 'bool' = True, iters: 'int' = 15) -> 'dict'`、台帳から引くなら `opsdrive.get("diabolo_axis_from_image")`)

## 使い方

1 コマから手前のカップの縁の中心 ``center_rim`` と軸 ``axis``(カメラ側を向く)を出す。ディアボロの中心 ``center`` =
center_rim − (L/2) axis。学習なし。

初期値(弱透視): 縁の楕円の長半径 → 深度、短 / 長 = cos θ、底の板の中心のずれ = (L/2 − z_h) sin θ、θ = atan2(sin, cos)
(acos の床を避ける)、ずれの向き = 軸の像の向き。仕上げ: 縁の円(半径 R、中心 C)と底の板(半径 r_h、中心 C − (L/2 − z_h) a)の
厳密な透視投影の多角形モーメント(面積・重心・2 次)を、マスクのモーメントに Gauss–Newton で合わせる(5 自由度、8 残差)。
残差 ``residual_px`` が 0.15 px を超えたら ``ok = False``(底の板が壁に隠れた等。視線から 45° で 2.8 px、38° まで ≤ 0.02 px)。

返り ``{"center", "center_rim", "axis", "axis_init", "tilt_init_deg", "a_px", "b_px", "residual_px", "ok", "seg"}``。
**Raises** ``ValueError``: 画像の形、カップの内側か底の板が見えない(推定不能)。

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
