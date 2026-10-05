---
op: world_grains_voronoi
dim: segmentation
category: world
in: 
out: table
examples: [poc_graph_hierarchy_segmentation, poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# world_grains_voronoi — SEGMENTATION `world` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.world_grains_voronoi(n: 'int' = 36, seed: 'int' = 0, *, size=(192, 192), jitter: 'float' = 0.8, boundary_width: 'float' = 1.5, noise: 'float' = 0.02) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.world_grains_voronoi(n: 'int' = 36, seed: 'int' = 0, *, size=(192, 192), jitter: 'float' = 0.8, boundary_width: 'float' = 1.5, noise: 'float' = 0.02) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("world_grains_voronoi")`)

## 使い方

ボロノイ結晶粒の世界: 格子の升から n 個を選んで ``jitter`` だけ揺らした種、ラベル = 最も近い種の番号(1..n)。

画像 = 粒ごとの明るさ(0.4〜0.75)× 粒界の暗い線(幅 ``boundary_width``、粒界までの距離の閉形式で描く)+ 雑音。
背景は無い(全画素がどれかの粒)。
返り値: ``image``、``labels``、``edge_distance``(各画素から粒界までの距離)、``truth`` = {``n``、``seeds`` (n, 2)、``areas``
(多角形、靴紐)、``edge_length_total``(内部の辺の長さの和)、``n_edges``、``polygons``、``boundary_width``、``total_area`` = H·W}。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`
- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`world`)

[world_blobs_touching](world_blobs_touching.md) · [world_parts_with_shadow](world_parts_with_shadow.md) · [world_texture_regions](world_texture_regions.md) · [world_gradient_illumination](world_gradient_illumination.md) · [world_thin_structures](world_thin_structures.md) · [lens_area](lens_area.md) · [voronoi_cells](voronoi_cells.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
