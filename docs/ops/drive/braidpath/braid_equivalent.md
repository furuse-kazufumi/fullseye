---
op: braid_equivalent
dim: drive
category: braidpath
in: signal × signal × scalar
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# braid_equivalent — DRIVE `braidpath` op

- **データ種**: `signal × signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.braid_equivalent(word_a, word_b, n_strands, method='dynnikov')` (実装を直接呼ぶなら `import braidpath; braidpath.braid_equivalent(word_a, word_b, n_strands, method='dynnikov')`、台帳から引くなら `opsdrive.get("braid_equivalent")`)

## 使い方

2 つの組紐語が同じ組紐か(関係式だけで移り合うか)。

method: ``"dynnikov"``(座標を比べる、速い)/ ``"handle"``(a b⁻¹ を取っ手簡約して空か)/ ``"artin"``(自由群の像を
比べる)/ ``"all"``(3 つとも計算し、食い違えば RuntimeError —— 実装の検査)。

Returns: dict ``equal``、``method``、``key_a`` / ``key_b``(Dynnikov の鍵)、``reduced_quotient``(a b⁻¹ の簡約、
handle / all のとき)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
