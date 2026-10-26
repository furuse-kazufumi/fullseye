---
op: polyhedron_clip_halfspace
dim: drive
category: polygrav
in: any × any × any
out: any
examples: [itokawa_gravity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# polyhedron_clip_halfspace — DRIVE `polygrav` op

- **データ種**: `any × any × any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.polyhedron_clip_halfspace(mesh, point, normal)` (実装を直接呼ぶなら `import polygrav; polygrav.polyhedron_clip_halfspace(mesh, point, normal)`、台帳から引くなら `opsdrive.get("polyhedron_clip_halfspace")`)

## 使い方

閉じたメッシュを平面で切り、``(x − point)·normal ≥ 0`` の側を閉じた立体として返す → (vertices, faces)。

切り口(平面上の多角形)は ``point`` からの扇の三角形で塞ぐ。切り口が非凸でも、``point`` が切り口の外でも、
扇の三角形は向き付きで重なって打ち消し合うので、面について線形な量(:func:`polyhedron_gravity` の重力・
``mesh_volume`` の体積・重心)はそのまま正しい(見た目の三角形は重なることがある)。
辺と平面の交点は辺ごとに 1 回だけ作るので、返りのメッシュは有向辺がちょうど打ち消す(閉じている)。
平面の上にちょうど乗る頂点は残す側に数える。

Parameters
----------
mesh : (vertices (N,3), faces (M,3))
    閉じた三角形メッシュ(外向きの巻き)。
point : (3,)
    平面上の 1 点(切り口の扇の中心にもなる)。
normal : (3,)
    残す側を向く平面の法線(正規化する)。

Returns
-------
(vertices (N',3), faces (M',3))
    残した側の閉じたメッシュ(使わない頂点は落とす)。切り口の三角形は末尾に並ぶ。

平面がメッシュに交わらない(全部が片側)ときは、残す側に全部あればそのまま、全部が反対側なら ``ValueError``。
メッシュが閉じていない・非有限・範囲外の索引も ``ValueError``。空の入力(``mesh`` の面が 0 個)は ValueError で拒否する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [itokawa_gravity_tour](../../../../examples/itokawa_gravity_tour.py) — `py -3.11 examples/itokawa_gravity_tour.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`polygrav`)

[polyhedron_gravity](polyhedron_gravity.md)

---
*Provenance: polygrav.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
