---
op: pegsym_scene_mjcf
dim: drive
category: pegsym
in: matrix × matrix
out: any
examples: [poc_peg_symmetry_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pegsym_scene_mjcf — DRIVE `pegsym` op

- **データ種**: `matrix × matrix` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.pegsym_scene_mjcf(peg_vertices, hole_vertices, chamfer: 'float' = 0.0005, hole_depth: 'float' = 0.02, peg_length: 'float' = 0.04, mu: 'float' = 0.3, k_trans: 'float' = 600.0, k_rot: 'float' = 1.5, k_yaw: 'float' = 0.01, timestep: 'float' = 0.0005, image_size=(480, 480), fovy_deg: 'float' = 40.0, station=(0.1, 0.0), offsamples: 'int' = 4) -> 'str'` (実装を直接呼ぶなら `import pegsym; pegsym.pegsym_scene_mjcf(peg_vertices, hole_vertices, chamfer: 'float' = 0.0005, hole_depth: 'float' = 0.02, peg_length: 'float' = 0.04, mu: 'float' = 0.3, k_trans: 'float' = 600.0, k_rot: 'float' = 1.5, k_yaw: 'float' = 0.01, timestep: 'float' = 0.0005, image_size=(480, 480), fovy_deg: 'float' = 40.0, station=(0.1, 0.0), offsamples: 'int' = 4) -> 'str'`、台帳から引くなら `opsdrive.get("pegsym_scene_mjcf")`)

## 使い方

多角形ペグの場面の MJCF 文字列(mujoco 不要): 穴 = 辺ごとに壁の箱(最狭部より下)・45° の面取りの板・明るい襟(口の面 z = 0)、
ペグ = 凸メッシュの角柱(断面 ``peg_vertices``、ペグ系、軸が原点)。搬送台は x・y・z のスライドと yaw のヒンジ(位置制御)、
その先に 6 自由度のばねの手首(傾き ``k_rot``・ねじり ``k_yaw`` [N m/rad] は別。把持はねじりに柔らかい)。カメラは
手首(搬送台の 30 mm 横、真下向き)と、穴から ``station`` [m] の上向きカメラ(床の面、ペグの端面を下から見る)、
図のための斜め上の固定カメラ ``side``。
箱は自分の辺の外側の半平面にだけあるので、角を越えて伸ばしても穴の中に入らない(凸の穴ならどの形でも同じ作り方)。
**Raises** ValueError: 多角形が凸でない、面取り < 0、穴の深さ ≤ 面取り、摩擦 < 0、剛性 ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_symmetry_search](../../../../examples/poc_peg_symmetry_search.py) — `py -3.11 examples/poc_peg_symmetry_search.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`pegsym`)

[polygon_peg](polygon_peg.md) · [polygon_offset](polygon_offset.md) · [polygon_fit_check](polygon_fit_check.md) · [rotation_window](rotation_window.md) · [polygon_two_point_depth](polygon_two_point_depth.md) · [polygon_coverage_image](polygon_coverage_image.md) · [plane_topview](plane_topview.md) · [polygon_yaw_read](polygon_yaw_read.md)

---
*Provenance: pegsym.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
