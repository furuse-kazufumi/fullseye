---
op: world_gradient_illumination
dim: segmentation
category: world
in: 
out: table
examples: [poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# world_gradient_illumination — SEGMENTATION `world` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.world_gradient_illumination(seed: 'int' = 0, *, size=(160, 220), n_objects: 'int' = 8, gradient=(0.45, 0.2), i0: 'float' = 0.3, reflectance: 'float' = 0.35, noise: 'float' = 0.03) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.world_gradient_illumination(seed: 'int' = 0, *, size=(160, 220), n_objects: 'int' = 8, gradient=(0.45, 0.2), i0: 'float' = 0.3, reflectance: 'float' = 0.35, noise: 'float' = 0.03) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("world_gradient_illumination")`)

## 使い方

照明の勾配 + 雑音の上の暗い物体の世界(大域閾値が壊れ、局所閾値・フラットフィールドで切れる)。

I(x, y) = i0 + g_x x/(W−1) + g_y y/(H−1)(i0 + g_x + g_y ≤ 1)、画像 = I · R + 雑音。R = 背景 1、物体 ``reflectance``。
物体は円(半径 8〜14)と整数辺の矩形(14〜28)、互いに離す。
返り値: ``image``、``labels``(1..n)、``illumination``、``reflectance_map``、``truth`` = {``n_objects``、``objects``(kind, params)、
``areas``(πr² / w h)、``i0``、``gradient``、``reflectance``、``noise``}。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [segmentation_scoring_and_worlds](../guides/segmentation_scoring_and_worlds.md) — 分割の採点と真値つき合成世界 — どの物差しがどの壊れ方に盲目か

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`world`)

[world_blobs_touching](world_blobs_touching.md) · [world_grains_voronoi](world_grains_voronoi.md) · [world_parts_with_shadow](world_parts_with_shadow.md) · [world_texture_regions](world_texture_regions.md) · [world_thin_structures](world_thin_structures.md) · [lens_area](lens_area.md) · [voronoi_cells](voronoi_cells.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
