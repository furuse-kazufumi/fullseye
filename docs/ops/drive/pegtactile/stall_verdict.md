---
op: stall_verdict
dim: drive
category: pegtactile
in: table × scalar × any
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# stall_verdict — DRIVE `pegtactile` op

- **データ種**: `table × scalar × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stall_verdict(kp, theta: 'float', mu_hat) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.stall_verdict(kp, theta: 'float', mu_hat) -> 'dict'`、台帳から引くなら `opsdrive.get("stall_verdict")`)

## 使い方

二点接触で止まった時の Whitney の判定(OCW p.28): θ > c/μ̂ ならくさび(力を抜いても抜けない側)、以下ならかじり(力の向きで
解ける)。c = (R − r)/R。μ̂ は同じ挿入の滑りの区間で触覚から読んだ値(:func:`friction_from_single_contact`)、None か ≤ 0 なら
推測せず ``"unknown"``。返り ``verdict``("wedging" / "jamming" / "unknown")・``theta_limit``。**Raises** ValueError: θ が有限でないか負。

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
