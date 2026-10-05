---
op: town_centerline
dim: drive
category: town
in: table
out: any
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# town_centerline — DRIVE `town` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_centerline(layout, step: 'float' = 0.5) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivetown; drivetown.town_centerline(layout, step: 'float' = 0.5) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("town_centerline")`)

## 使い方

継いだ中心線を弧長 ``step`` ごとに標本化する → ``(N, 4) = (s, x, y, yaw)``(終点は必ず含む)。

門: 直線部では隣接点の間隔が厳密に step、始点 = 最初の要素の entry、終点 = 最後の要素の exit。

**Raises** ``ValueError``: layout が town_chain の物でない、step が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_world](town_world.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
