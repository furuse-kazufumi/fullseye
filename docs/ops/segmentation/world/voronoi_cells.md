---
op: voronoi_cells
dim: segmentation
category: world
in: points
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# voronoi_cells — SEGMENTATION `world` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.voronoi_cells(seeds, size) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.voronoi_cells(seeds, size) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("voronoi_cells")`)

## 使い方

矩形 [−0.5, W − 0.5] × [−0.5, H − 0.5] の中の種のボロノイ分割を多角形で返す(半平面の総当たり、O(n²))。

返り値: ``polygons``(多角形の列、各 (k, 2) [y, x])、``areas``(靴紐)、``edge_length_total``(内部の辺の長さの和)、
``n_edges``(内部の辺の数)、``perimeter_internal`` (n,)(各セルの内部の辺の長さ)。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`world`)

[world_blobs_touching](world_blobs_touching.md) · [world_grains_voronoi](world_grains_voronoi.md) · [world_parts_with_shadow](world_parts_with_shadow.md) · [world_texture_regions](world_texture_regions.md) · [world_gradient_illumination](world_gradient_illumination.md) · [world_thin_structures](world_thin_structures.md) · [lens_area](lens_area.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
