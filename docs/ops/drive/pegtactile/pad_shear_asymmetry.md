---
op: pad_shear_asymmetry
dim: drive
category: pegtactile
in: signal × signal
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# pad_shear_asymmetry — DRIVE `pegtactile` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pad_shear_asymmetry(qR, qL) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.pad_shear_asymmetry(qR, qL) -> 'dict'`、台帳から引くなら `opsdrive.get("pad_shear_asymmetry")`)

## 使い方

2 パッドの膜のせん断を共通成分(= 軸方向の力、F_z/2 の向き)と差分(= 偶力、M/(2w))に分ける: 共通 = (q_R + q_L)/2、
差分 = (q_R − q_L)/2。``ratio_v`` = |差分_v| / (|共通_v| + |差分_v|)(0 = 同じ向き、1 = 純粋な偶力)、``opposite_v`` = v 成分の
符号が左右で逆か。**Raises** ValueError: 有限の 2 成分でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md) · [contact_candidates](contact_candidates.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
