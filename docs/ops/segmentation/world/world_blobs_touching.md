---
op: world_blobs_touching
dim: segmentation
category: world
in: 
out: table
examples: [poc_active_contours, poc_graph_hierarchy_segmentation, poc_segmentation_gauntlet]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# world_blobs_touching — SEGMENTATION `world` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.world_blobs_touching(n: 'int' = 10, overlap: 'float' = 0.2, seed: 'int' = 0, *, size=(160, 160), radius: 'float' = 14.0, noise: 'float' = 0.03) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import segworld; segworld.world_blobs_touching(n: 'int' = 10, overlap: 'float' = 0.2, seed: 'int' = 0, *, size=(160, 160), radius: 'float' = 14.0, noise: 'float' = 0.03) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("world_blobs_touching")`)

## 使い方

重なり合う円(細胞・粒)の世界: 鎖状に置いた等しい半径の円、各円は前の円とだけ中心間 2r(1 − overlap) で重なる。

ラベル = 円の内側で最も近い中心(重なりは垂直二等分線で分ける)。画像 = 明るい内部 + 暗い縁 + 重なりはやや明るい
+ ぼかし + 雑音(細胞の見た目)。鎖がそれ以上伸ばせなければ新しい鎖を始める(その円は誰とも重ならない)。
返り値: ``image``、``labels``、``count_map``(各画素を覆う円の数)、``truth`` = {``n``、``centers`` (n, 2) [y, x]、``radius``、
``overlap``、``pairs`` (m, 2)(重なる組)、``lens_area`` (m,)(閉形式)、``areas`` (n,)(πr² − Σ レンズ/2)、``union_area``、
``overlap_measured``(2 つ以上に覆われた画素 / 和集合の画素)}。置けなければ ValueError。

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

[world_grains_voronoi](world_grains_voronoi.md) · [world_parts_with_shadow](world_parts_with_shadow.md) · [world_texture_regions](world_texture_regions.md) · [world_gradient_illumination](world_gradient_illumination.md) · [world_thin_structures](world_thin_structures.md) · [lens_area](lens_area.md) · [voronoi_cells](voronoi_cells.md)

---
*Provenance: segworld.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
