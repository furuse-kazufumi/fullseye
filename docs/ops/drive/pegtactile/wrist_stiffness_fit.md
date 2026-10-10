---
op: wrist_stiffness_fit
dim: drive
category: pegtactile
in: signal × signal
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# wrist_stiffness_fit — DRIVE `pegtactile` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.wrist_stiffness_fit(dx, F, min_span: 'float' = 2e-05) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.wrist_stiffness_fit(dx, F, min_span: 'float' = 2e-05) -> 'dict'`、台帳から引くなら `opsdrive.get("wrist_stiffness_fit")`)

## 使い方

手首のたわみ Δx(手首カメラ)と、ペグが受ける接触力の同じ成分 F から k = Σ FΔx / ΣΔx²(原点を通る最小二乗、準静的な釣り合い
F_contact + F_spring ≈ 0 ⇒ F_contact = kΔx)。回転(角と モーメント)にも同じ式で使える。返り ``k``・``r2``・``rms_N``・``n``・``span``。
**Raises** ValueError: 点が 3 未満、形が違う、有限でない、Δx の幅が ``min_span`` 未満(悪条件: 動いていないばねの k は決まらない)。

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
