---
op: friction_from_single_contact
dim: drive
category: pegtactile
in: signal × text × any × signal
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# friction_from_single_contact — DRIVE `pegtactile` op

- **データ種**: `signal × text × any × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.friction_from_single_contact(F, where: 'str', c, axis, chamfer: 'bool' = False) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.friction_from_single_contact(F, where: 'str', c, axis, chamfer: 'bool' = False) -> 'dict'`、台帳から引くなら `opsdrive.get("friction_from_single_contact")`)

## 使い方

一点接触で滑っている間の接触力から壁の摩擦係数(滑りの間だけ Coulomb の限界に張り付く、固着中は下限)。
先端の縁が壁(``where="tip"``)なら法線 = 水平(穴の中心へ)、摩擦 = 鉛直 → μ̂ = |F_z|/|F_水平|。胴が最狭部の縁(``"mouth"``)なら
法線 = 軸に垂直、摩擦 = 軸方向 → μ̂ = |F·a|/|F_⊥|。``chamfer`` なら 45° の面取り面の上(法線 = (−r̂, 1)/√2、``c`` = 接触点が要る)。
``"none"`` は None。返り ``mu``(None 可)。**Raises** ValueError: where が語彙の外、F・axis が有限の 3 成分でない、面取りで c が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
