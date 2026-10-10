---
op: puck_detect
dim: drive
category: puck
in: image2d × table
out: any
examples: [poc_air_hockey_intercept]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# puck_detect — DRIVE `puck` op

- **データ種**: `image2d × table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.puck_detect(frame, cam: 'dict', *, mode: 'str' = 'dark', thresh: 'float' = 0.85, radius_tol: 'float' = 0.5, color=None, color_tol: 'float' = 0.25)` (実装を直接呼ぶなら `import puck; puck.puck_detect(frame, cam: 'dict', *, mode: 'str' = 'dark', thresh: 'float' = 0.85, radius_tol: 'float' = 0.5, color=None, color_tol: 'float' = 0.25)`、台帳から引くなら `opsdrive.get("puck_detect")`)

## 使い方

:func:`balltrack.ball_detect` の facade: 真上のコマから円盤を 1 つ取り、ホモグラフィで台の平面 (x, y) [m] に写す。

``mode`` = "dark"(白い台に暗いパック、合成)/ "color"・"chroma"(色で、MuJoCo の赤いパック)。``thresh`` は台の値
(0.92)の少し下に置く: ``ball_detect`` の重みは (thresh − 画素値) なので、しきい値が台に近いほど重み ∝ 被覆率で
重心が面積重心に一致する。中間の 0.5 では縁の画素が切れて位相依存の偏りが出る(実測 2026-10-04、r = 6.3 px:
thresh 0.5 → 最大 0.08 px / 0.7 → 0.03 / 0.85 → 0.005、雑音 σ 0.01 でも 0.014)。半径が期待
(puck_radius·px_per_m)の (1 ± radius_tol) 倍から外れる塊は捨てる。返り値 ``{"col","row","radius","fill","x","y"}`` か、
見つからなければ ``None``(fail-closed)。知らない ``mode`` は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_air_hockey_intercept](../../../../examples/poc_air_hockey_intercept.py) — `py -3.11 examples/poc_air_hockey_intercept.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`puck`)

[puck_table](puck_table.md) · [puck_wall_bounce](puck_wall_bounce.md) · [puck_slide_predict](puck_slide_predict.md) · [puck_state_at](puck_state_at.md) · [puck_crossing_point](puck_crossing_point.md) · [puck_mirror_path](puck_mirror_path.md) · [puck_stop_distance](puck_stop_distance.md) · [puck_camera](puck_camera.md)

---
*Provenance: puck.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
