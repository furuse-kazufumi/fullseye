---
op: world_texture_regions
dim: segmentation
category: world
in: 
out: table
examples: [poc_graph_hierarchy_segmentation, poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# world_texture_regions — SEGMENTATION `world` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.world_texture_regions(seed: 'int' = 0, *, size=(192, 192), n_regions: 'int' = 3, mean: 'float' = 0.5, noise: 'float' = 0.03) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.world_texture_regions(seed: 'int' = 0, *, size=(192, 192), n_regions: 'int' = 3, mean: 'float' = 0.5, noise: 'float' = 0.03) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("world_texture_regions")`)

## 使い方

平均が同じで分散・周期だけ違う 2〜4 領域の世界(閾値では切れない)。真値 = 領域ラベル(1..n、背景なし)。

領域 = 離した種の最近傍(ボロノイ)。模様は順に: 小さい雑音(σ = noise)、大きい雑音(σ = 4 noise)、縞(周期 P₁・向き θ₁、
振幅 0.2)+ 雑音、縞(周期 P₂・向き θ₂)+ 雑音。どれも零平均で ``mean`` に足す(クリップは ±0.45 で対称 = 平均を保つ)。
返り値: ``image``、``labels``、``truth`` = {``n_regions``、``mean``、``seeds``、``specs``(kind, std(理論)、period、angle(度)、amp)}。

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

[world_blobs_touching](world_blobs_touching.md) · [world_grains_voronoi](world_grains_voronoi.md) · [world_parts_with_shadow](world_parts_with_shadow.md) · [world_gradient_illumination](world_gradient_illumination.md) · [world_thin_structures](world_thin_structures.md) · [lens_area](lens_area.md) · [voronoi_cells](voronoi_cells.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
