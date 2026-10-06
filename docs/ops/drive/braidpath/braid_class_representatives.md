---
op: braid_class_representatives
dim: drive
category: braidpath
in: any
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# braid_class_representatives — DRIVE `braidpath` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.braid_class_representatives(plans, obstacles=None, costs=None, angle=0.1, jitter='auto')` (実装を直接呼ぶなら `import braidpath; braidpath.braid_class_representatives(plans, obstacles=None, costs=None, angle=0.1, jitter='auto')`、台帳から引くなら `opsdrive.get("braid_class_representatives")`)

## 使い方

複数の計画(どの計画器の出力でもよい)をホモトピー類に分け、類ごとに費用の最も小さい計画を代表に選ぶ。

計画は (K, T, 2) の軌道か、格子の経路の列か、計画器の dict(``paths``、失敗した ``None`` は飛ばして数える)。
全部の計画の始点と終点がそろっている必要がある(類は端を止めた変形の類)。費用は ``costs`` か、なければ軌道の
長さの和。

Returns: dict ``classes``(費用の安い順の list、各要素 dict: ``key``・``word``(代表の語)・``best``(計画の番号)・
``cost``・``count``・``members``)、``n_plans``、``n_failed``、``n_classes``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
