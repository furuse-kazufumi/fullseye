---
op: grid_paths_to_xy
dim: drive
category: braidpath
in: any
out: any
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# grid_paths_to_xy — DRIVE `braidpath` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.grid_paths_to_xy(paths) -> 'np.ndarray'` (実装を直接呼ぶなら `import braidpath; braidpath.grid_paths_to_xy(paths) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("grid_paths_to_xy")`)

## 使い方

格子の経路(各台の (row, col) の列)を (K, T, 2) の [x, y] = [col, −row] にする(短い経路は最後の点で詰める)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
