---
op: world_thin_structures
dim: segmentation
category: world
in: 
out: table
examples: [poc_active_contours, poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# world_thin_structures — SEGMENTATION `world` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.world_thin_structures(seed: 'int' = 0, *, size=(200, 200), n: 'int' = 6, widths: 'Sequence[float]' = (1.0, 2.0, 3.0), noise: 'float' = 0.03) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.world_thin_structures(seed: 'int' = 0, *, size=(200, 200), n: 'int' = 6, widths: 'Sequence[float]' = (1.0, 2.0, 3.0), noise: 'float' = 0.03) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("world_thin_structures")`)

## 使い方

幅 1〜3 px の線(直線)とひび(折れ線)の世界。真値 = 中心線と幅。ラベル = 構造の番号(1..n、互いに離す)。

構造 k は直線(2 点)と折れ線(7 点のランダムウォーク)を交互に、幅は ``widths`` を順に使う。画素は中心線からの距離
≤ w/2 なら構造。画像 = 明るい背景(0.82 + 緩い勾配)に、幅が細いほど薄い暗線(w = 1: 0.5、2: 0.38、3: 0.26)、
縁は距離で反エイリアス、わずかにぼかし + 雑音。
返り値: ``image``、``labels``、``distance``(各画素から最も近い中心線までの距離)、``truth`` = {``n``、``kinds``、``widths``、
``lengths``(Σ 線分)、``length_total``、``polylines``((m, 2) [y, x] の列)、``areas_stadium``(L w + π w²/4)}。

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
- [poc_segmentation_gauntlet](../../../../examples/poc_segmentation_gauntlet.py) — `py -3.11 examples/poc_segmentation_gauntlet.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`world`)

[world_blobs_touching](world_blobs_touching.md) · [world_grains_voronoi](world_grains_voronoi.md) · [world_parts_with_shadow](world_parts_with_shadow.md) · [world_texture_regions](world_texture_regions.md) · [world_gradient_illumination](world_gradient_illumination.md) · [lens_area](lens_area.md) · [voronoi_cells](voronoi_cells.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
