---
op: world_parts_with_shadow
dim: segmentation
category: world
in: 
out: table
examples: [poc_active_contours, poc_graph_hierarchy_segmentation, poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# world_parts_with_shadow — SEGMENTATION `world` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.world_parts_with_shadow(seed: 'int' = 0, *, size=(200, 260), n_parts: 'int' = 3, light_angle: 'float' = 35.0, shadow_length: 'float' = 9.0, noise: 'float' = 0.02) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.world_parts_with_shadow(seed: 'int' = 0, *, size=(200, 260), n_parts: 'int' = 3, light_angle: 'float' = 35.0, shadow_length: 'float' = 9.0, noise: 'float' = 0.02) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("world_parts_with_shadow")`)

## 使い方

工業部品(回転した矩形 + 円の穴)と、斜めの照明による影・面の明暗・ハイライトの世界。真値 = 部品(穴は背景、影は背景)。

光は ``light_angle``(度、画像の x 軸から y 軸へ)の向きに差す平行光。影 = 部品のマスクを光の向きに ``shadow_length``
だけずらした集合から部品を除いた画素(穴は光を通す)。部品の面は光に向く側が明るく、遠い側は影と同じくらい暗い
(閾値が欺かれる理由)。ハイライトは光に向く側の縁の近くのガウス。
返り値: ``image``、``labels``(部品 1..n)、``shadow``(bool)、``truth`` = {``n_parts``、``parts``(center, w, h, angle, holes)、
``areas``(w h − Σ π r²)、``shadow_offset`` (dy, dx)、``shadow_area``(測った画素数)、``light_angle``}。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_active_contours](../../../../examples/poc_active_contours.py) — `py -3.11 examples/poc_active_contours.py`
- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`
- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`world`)

[world_blobs_touching](world_blobs_touching.md) · [world_grains_voronoi](world_grains_voronoi.md) · [world_texture_regions](world_texture_regions.md) · [world_gradient_illumination](world_gradient_illumination.md) · [world_thin_structures](world_thin_structures.md) · [lens_area](lens_area.md) · [voronoi_cells](voronoi_cells.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
