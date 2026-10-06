---
op: diabolo_scene_mjcf
dim: drive
category: diabolo
in: table
out: any
examples: [poc_diabolo_model_and_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# diabolo_scene_mjcf — DRIVE `diabolo` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.diabolo_scene_mjcf(params: 'dict', *, timestep: 'float' = 0.00025, solref=(0.0005, 1.0), wrap_axle: 'bool' = False) -> 'str'` (実装を直接呼ぶなら `import diabolo; diabolo.diabolo_scene_mjcf(params: 'dict', *, timestep: 'float' = 0.00025, solref=(0.0005, 1.0), wrap_axle: 'bool' = False) -> 'str'`、台帳から引くなら `opsdrive.get("diabolo_scene_mjcf")`)

## 使い方

第 2 実装の場面の MJCF 文字列(mujoco 不要): 空間テンドン 棒の先 → ディアボロ → 棒の先、長さの上限 = 糸(片側拘束 =
伸びた時だけ引く = 摩擦のない滑車の厳密模型と同じ物理を、柔らかい拘束と暗黙の速度更新という別の解法で解く)。棒の先は
mocap(各ステップで位置を書き込む)。ディアボロは自由関節の剛体(質量 = 論文の表 I、慣性は仮定。回転は糸と結合しない)。
``wrap_axle`` = True なら軸(半径 r)の円柱にテンドンを巻き付ける形(下側を通す、未検証)。
**Raises** ``ValueError``: params の形、timestep ≤ 0、solref が 2 つの正の数でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_diabolo_model_and_vision](../../../../examples/poc_diabolo_model_and_vision.py) — `py -3.11 examples/poc_diabolo_model_and_vision.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`diabolo`)

[diabolo_params](diabolo_params.md) · [diabolo_spheroid](diabolo_spheroid.md) · [spheroid_closest](spheroid_closest.md) · [diabolo_dynamics_step](diabolo_dynamics_step.md) · [diabolo_simulate](diabolo_simulate.md) · [diabolo_state_sequence](diabolo_state_sequence.md) · [diabolo_throw_catch_truth](diabolo_throw_catch_truth.md) · [string_tension_static](string_tension_static.md)

---
*Provenance: diabolo.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
