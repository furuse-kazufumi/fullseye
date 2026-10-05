---
op: peg_wrench_to_pad_loads
dim: drive
category: pegtactile
in: signal × signal × table
out: table
examples: [poc_knife_tactile_toughness, poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# peg_wrench_to_pad_loads — DRIVE `pegtactile` op

- **データ種**: `signal × signal × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.peg_wrench_to_pad_loads(F_pad, M_pad, pad: 'dict') -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.peg_wrench_to_pad_loads(F_pad, M_pad, pad: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("peg_wrench_to_pad_loads")`)

## 使い方

2 つのパッドがペグに加えるレンチ(グリッパ系、把持点まわり)→ 各パッドの (法線力 P、膜が受けるせん断 q = (q_u, q_v))。

釣り合い(導出): パッド R(+x)はペグに −N_R x̂ と T_R、L(−x)は +N_L x̂ と T_L。F_x = N_L − N_R、F_y = T_Ry + T_Ly、
F_z = T_Rz + T_Lz、M_y = −w(T_Rz − T_Lz)、M_z = w(T_Ry − T_Ly)、M_x = ねじり(半分ずつ)。法線は把持力で N = G₀ ∓ F_x/2。
返り: ``R``・``L``(各 ``P``・``q``(膜が受ける = −T)・``slip_ratio`` = |q|/(μP)・``torsion``(膜が受けるねじり)・``torsion_ratio``
= |ねじり| / 全滑りトルク (3π/16)μPa)、``torsion``(ペグへのねじりの半分 M_x/2)、``ok``(両方 |q| < μP)、``min_margin``、
``torsion_ok``。滑り(|q| ≥ μP)とねじりの全滑りは**印**で返す(例外にしない: 合成は比例載荷・無滑りねじりの模型)。
**Raises** ValueError: 形が (3,) でない・有限でない、どちらかのパッドの法線力が 0 以下(パッドが離れる = この写像の外。fail-closed)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`
- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
