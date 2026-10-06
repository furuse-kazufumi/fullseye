---
op: foe_from_flow
dim: drive
category: ttc
in: image2d × image2d
out: table
examples: [poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# foe_from_flow — DRIVE `ttc` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.foe_from_flow(u, v, mask=None, *, min_speed: 'float' = 0.3, max_speed: 'float' = inf, iters: 'int' = 5, angle_scale: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import drivettc; drivettc.foe_from_flow(u, v, mask=None, *, min_speed: 'float' = 0.3, max_speed: 'float' = inf, iters: 'int' = 5, angle_scale: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsdrive.get("foe_from_flow")`)

## 使い方

光学流から拡大の中心(FoE)を推定する: ``{"foe": (col, row), "n", "residual"}``。

純平行移動の流れは FoE から放射状(Longuet-Higgins & Prazdny 1980)なので、各画素の流線(点 p_i を流れの向きに
通る直線)は全部 FoE を通る。FoE = Σ w_i·dist(F, 流線_i)² を最小にする点(2×2 の正規方程式)。重みは反復で
``1/|p_i − F|·1/(1 + (角度残差/angle_scale)²)``(Cauchy 風)。遠い画素の流線ほど向きの誤差が FoE の位置に
効くので距離で割り、外れ値(遮蔽・無地)を角度残差で落とす。15 巡目で「既知」にした FoE を流れから出す口(16 巡目)。
定理の門: 真の流れ(flow_from_depth_motion)を入れると :func:`foe_from_motion` と 1e-9 で一致。

``mask`` は使う画素(既定 = 有限で速さが [min_speed, max_speed] の画素)。有効画素が 3 未満、または正規方程式が
特異(流線が全部平行)なら ``ValueError``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [foe_from_motion](foe_from_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_scale](ttc_from_scale.md) · [ttc_from_range](ttc_from_range.md) · [label_extent](label_extent.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
