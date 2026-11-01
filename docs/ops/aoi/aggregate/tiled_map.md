---
op: tiled_map
dim: aoi
category: aggregate
in: image2d
out: table
examples: [aoi_frontend_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# tiled_map — AOI `aggregate` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tiled_map(image, tile=16, stat='mean', overlap=0, drop_partial=False)` (実装を直接呼ぶなら `import aoi; aoi.tiled_map(image, tile=16, stat='mean', overlap=0, drop_partial=False)`、台帳から引くなら `opsaoi.get("tiled_map")`)

## 使い方

画像をタイルに割り、タイルごとの量を小さな地図にする。→ dict。

``tile`` 画素角のタイルを ``tile - overlap`` 画素ずつずらして敷き、各タイルの中の量
(:data:`TILE_STATS`)を 1 つずつ計算して ``(h, w)`` の地図にする。AOI では、明るさの
むら・ざらつき・欠陥の密度を「どのあたりが怪しいか」の粗い地図にして、次の段
(閾値・:mod:`spc` の管理図)へ渡すのに使う。

**半端なタイルを黙って捨てない。** 画像の辺が ``tile`` で割り切れないとき、縁のタイルは
小さくなる。既定(``drop_partial=False``)ではそれも計算に入れ、``partial_tiles`` に
件数を出す。``drop_partial=True`` にすると縁を落とすが、そのときも ``dropped_tiles`` と
``covered_fraction`` に**何をどれだけ捨てたか**が出る —— どちらを選んでも、捨てたことが
返り値に残る。

**分解可能な量なら検算できる。** ``overlap=0`` なら、タイルは画像を重なりなく覆う。
``stat="mean"`` の地図を ``counts`` で重み付けして平均すると、**全画素の平均に一致する**
(門で 1e-15 の水準を固定してある)。``"std"`` や ``"median"`` にこの性質は無い ——
タイルごとの標準偏差を平均しても全体の標準偏差にはならないので、地図を「まとめ直す」
使い方をするなら ``"mean"`` / ``"sum"`` / ``"count"`` に限ること。

``tile`` が画像より大きいときは、タイルは 1 枚(= 画像全体)で ``partial_tiles=1``。
``drop_partial=True`` だと残るタイルが 1 枚も無くなるので ``ValueError`` にする
(空の地図を返すと、後段が「異常なし」と読む)。

Args:
    image: ``(H, W)``。
    tile: タイルの一辺[px]。1 以上。
    stat: :data:`TILE_STATS` のどれか。
    overlap: 隣のタイルと重ねる画素数。``0 <= overlap < tile``。
    drop_partial: 縁の半端なタイルを落とすか。

Returns:
    dict。``map``(``(h, w)`` float64)、``counts``(``(h, w)`` int、タイルごとの画素数)、
    ``rows`` / ``cols``(各タイルの左上の座標)、``tile`` / ``overlap`` / ``stat``、
    ``partial_tiles``(小さいタイルの数)、``dropped_tiles``(落とした数)、
    ``covered_fraction``(残したタイルが覆う画素の割合。``overlap>0`` では重なるので
    1 を超えうる)、``shape``(元の画像の形)。

Raises:
    ValueError: 2-D でない / 非有限 / ``stat`` が未知 / ``overlap`` が範囲外 /
        ``drop_partial=True`` でタイルが 1 枚も残らない。

## 詳しい使い方ガイド

- [aoi_frontend ファミリ ガイド](../guides/aoi_frontend.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [aoi_frontend_tour](../../../../examples/aoi_frontend_tour.py) — `py -3.11 examples/aoi_frontend_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[symmetry_difference_map](../symmetry/symmetry_difference_map.md) · [symmetry_score](../symmetry/symmetry_score.md)

## 同カテゴリ(`aggregate`)

—

---
*Provenance: aoi.py — AOI operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
