---
op: contact_state_from_wrench
dim: drive
category: pegtactile
in: table × signal × signal × signal × signal × signal
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# contact_state_from_wrench — DRIVE `pegtactile` op

- **データ種**: `table × signal × signal × signal × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_state_from_wrench(kp, F, M_g, g, tip, axis, f_air: 'float' = 0.05, tau: 'float' = 0.35, tol: 'float' = 8e-05, geometry: 'bool' = True, tol_l: 'float' = 5e-05) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.contact_state_from_wrench(kp, F, M_g, g, tip, axis, f_air: 'float' = 0.05, tau: 'float' = 0.35, tol: 'float' = 8e-05, geometry: 'bool' = True, tol_l: 'float' = 5e-05) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_state_from_wrench")`)

## 使い方

接触レンチ(ペグが穴から受ける F と把持点 g まわりの M、世界系)→ 接触状態(学習なしの規則)。

単一の点接触なら、その点まわりのモーメントは 0(点に偶力なし)。**幾何的に触れうる**候補点 c(:func:`contact_candidates`)ごとの
正規化残差 e(c) = |M_g − (c − g) × F| / (|F| r) の最小が ``tau`` 未満なら一点(先端の縁で深さ < W なら面取り)、どの候補でも説明
できず先端と胴の両方に有効な候補があれば二点、|F| < ``f_air`` なら無接触。``geometry`` なら Whitney の幾何を優先する: 傾き θ で
先端が最狭部から l₂(θ) − ``tol_l`` より深ければ両側に触れるしかない(二点を強制)。くさびの境目 θ = c/μ では先端の摩擦円錐の縁が
口の接触点を通り(口と先端を結ぶ線の傾き c/θ = μ)、二点のレンチが「口の一点」と区別できない —— レンチだけの規則の原理的な死角。
返り ``state``(:data:`CONTACT_STATES`)、``e_tip``・``e_mouth``、``where``("none" / "tip" / "mouth" / "tip+mouth" / "?")、
``c``(当たった点、一点のとき)、``Fmag``・``depth``・``forced``。**Raises** ValueError: ベクトルが有限の 3 成分でない、tau ≤ 0。

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
