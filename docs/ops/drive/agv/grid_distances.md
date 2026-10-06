---
op: grid_distances
dim: drive
category: agv
in: image2d
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# grid_distances — DRIVE `agv` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.grid_distances(grid, goal)` (実装を直接呼ぶなら `import agvfleet; agvfleet.grid_distances(grid, goal)`、台帳から引くなら `opsdrive.get("grid_distances")`)

## 使い方

``goal`` までの格子上の最短手数(BFS、障害物は通れない)。届かないマスは ``inf``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`agv`)

[warehouse_grid](warehouse_grid.md) · [mapf_cbs](mapf_cbs.md) · [mapf_ecbs](mapf_ecbs.md) · [mapf_joint_astar](mapf_joint_astar.md) · [mapf_prioritized](mapf_prioritized.md) · [plan_conflicts](plan_conflicts.md) · [plan_cost](plan_cost.md) · [adg_build](adg_build.md)

---
*Provenance: agvfleet.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
