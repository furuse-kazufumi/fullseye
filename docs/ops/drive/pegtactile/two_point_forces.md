---
op: two_point_forces
dim: drive
category: pegtactile
in: table × signal × signal × signal × signal × signal
out: table
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# two_point_forces — DRIVE `pegtactile` op

- **データ種**: `table × signal × signal × signal × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.two_point_forces(kp, F, M_g, g, tip, axis, mu_grid=None) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.two_point_forces(kp, F, M_g, g, tip, axis, mu_grid=None) -> 'dict'`、台帳から引くなら `opsdrive.get("two_point_forces")`)

## 使い方

二点接触(Whitney)のレンチを 2 つの接触力と壁の摩擦 μ に分解する(平面、両点が下へ滑る Coulomb の仮定)。

傾きの面(軸の水平成分 e)で、先端の縁は −e 側の壁(法線 = 水平、摩擦 = 上向き)、胴は +e 側の最狭部の縁(法線 = 軸に垂直、摩擦 =
軸の上向き)。各 μ で (f_n1, f_n2) は 3 式(F_e, F_z, M)の最小二乗、残差最小の μ を放物線で詰める(既定の格子 0〜1.5、301 点)。
返り ``mu``・``fn_tip``・``fn_mouth``・``resid``(N)・``p_tip``・``p_mouth``。
**Raises** ValueError: 軸が鉛直すぎて傾きの面が決まらない、ベクトルが有限の 3 成分でない、μ の格子が 3 点未満。

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
