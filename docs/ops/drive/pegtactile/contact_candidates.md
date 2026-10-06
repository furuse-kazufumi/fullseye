---
op: contact_candidates
dim: drive
category: pegtactile
in: table × signal × signal
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# contact_candidates — DRIVE `pegtactile` op

- **データ種**: `table × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.contact_candidates(kp, tip, axis, n_az: 'int' = 144, tol: 'float' = 8e-05) -> 'dict'` (実装を直接呼ぶなら `import pegtactile; pegtactile.contact_candidates(kp, tip, axis, n_az: 'int' = 144, tol: 'float' = 8e-05) -> 'dict'`、台帳から引くなら `opsdrive.get("contact_candidates")`)

## 使い方

単一接触の候補点(世界系)と、その点が**幾何的に触れうるか**の印。``tip_rim`` = 先端の縁の円(半径 r、軸に垂直)で、縁の点が
壁(最狭部より深い: 半径 ≥ R − tol)か面取り面(半径 ≥ R + (W − 深さ) − tol)に届くものだけ有効。``mouth`` = 穴の最狭部の縁の円
(半径 R、z = −W)で、胴の表面が通る(軸の直線からの距離が r ± tol、先端が最狭部より深い)ものだけ有効。
候補を絞らないと、二点接触の合力の作用線が「壁に触れていない側の先端の縁」を通る偶然を一点と読む(試作のくさびで実測)。
``tol`` は MuJoCo の柔らかい接触のめり込みと 36 角形の壁(頂点で +0.02 mm)ぶん。返り ``tip_rim``・``rim_ok``・``mouth``・
``mouth_ok``・``depth``。**Raises** ValueError: tip・axis が有限の 3 成分でない、n_az < 8、tol < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
