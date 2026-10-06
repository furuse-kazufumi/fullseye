---
op: cr_synthetic
dim: drive
category: commonroad
in: 
out: any
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cr_synthetic — DRIVE `commonroad` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_synthetic(kind: 'str' = 'tjunction', *, dt: 'float' = 0.1, speed_limit: 'float' = 13.89, v0: 'float' = 8.0) -> 'str'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_synthetic(kind: 'str' = 'tjunction', *, dt: 'float' = 0.1, speed_limit: 'float' = 13.89, v0: 'float' = 8.0) -> 'str'`、台帳から引くなら `opsdrive.get("cr_synthetic")`)

## 使い方

テスト・CI 用の最小 CommonRoad 2020a XML を文字列で返す。

``tjunction``: lanelet 100(直線 40 m, +x)→ 101(左 90° 円弧、中心線半径 12 m)→ 102(直線 40 m, +y)、対向 lanelet 200
(100 の左隣、−x 向き)に対向車 1 台(8 m/s、矩形 4.5 × 1.8)、標識 274(speed_limit m/s)は 3 本すべてに、stopLine は 100 の
終端(交差点の手前)、planning problem = (5, 0) から v0 でゴール lanelet 102・time_step [100, 200]・速度 [0, 15]。
``straight``: 101 も直線(3 本で 120 m)。``blocked``: straight の 101 の中央に静止障害物(衝突の門用)。
車線幅 3.5 m。中心線の長さ = 40 + 6π(≒ 18.85、円弧は 16 分割の折線) + 40(tjunction)/ 120(straight)。

**Raises** ``ValueError``: kind が :data:`SYNTHETIC_KINDS` 以外、dt / speed_limit / v0 が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`commonroad`)

[cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
