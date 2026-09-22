---
op: stipple_points_from_image
dim: printpath
category: stroke
in: image2d
out: pairs
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# stipple_points_from_image — PRINTPATH `stroke` op

- **データ種**: `image2d` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.stipple_points_from_image(image, n_points, iterations=30, gamma=1.0, floor=0.02, seed=0, metric='euclidean')` (実装を直接呼ぶなら `import printpath; printpath.stipple_points_from_image(image, n_points, iterations=30, gamma=1.0, floor=0.02, seed=0, metric='euclidean')`、台帳から引くなら `opsprintpath.get("stipple_points_from_image")`)

## 使い方

濃淡を**点の密度**に写す(重みつき Lloyd = 重心ボロノイ)。→ ``pairs``

暗いところに点が密に集まる。返るのは ``(n_points, 2)`` の **(row, col)**。

引数:
    image: 明るさ ``[0, 1]`` の 2-D(または色。輝度に落とす)。
    n_points: 点の数。
    iterations: Lloyd の反復回数。
    gamma: 重みを ``darkness ** gamma`` にする(1 = 暗さそのまま)。
    floor: 重みの下限。**0 にしない** —— 真っ白な領域の重みが厳密に 0 だと
        そこへ入った点が動けず(重心が 0/0)、位置が入力に依らなくなる。
    seed: 初期配置の乱数。
    metric: いまは ``"euclidean"`` のみ。

返り値のほかに、収束の様子は :func:`stipple_points_from_image` を
``iterations`` を変えて呼び比べれば測れる(Lloyd のエネルギーは単調減少する)。

★**真っ白な画像でも点は等間隔に散る**(密度が一定なら重心ボロノイは均等)。
そこが「濃淡を読めている」ことの対照群になる。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[stipple_energy](stipple_energy.md) · [stroke_tour_closed](stroke_tour_closed.md) · [mst_length](mst_length.md) · [stroke_resample_closed](stroke_resample_closed.md) · [stroke_tone_error](stroke_tone_error.md)

## 同カテゴリ(`stroke`)

[stipple_energy](stipple_energy.md) · [stroke_tour_closed](stroke_tour_closed.md) · [mst_length](mst_length.md) · [stroke_resample_closed](stroke_resample_closed.md) · [stroke_tone_error](stroke_tone_error.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
