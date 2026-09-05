---
op: histogram_match
dim: colortransport
category: matching
in: image2d × image2d
out: image2d
examples: [color_transport]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# histogram_match — COLORTRANSPORT `matching` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import colortransport; colortransport.histogram_match(src, ref, bins=None, ties='average')` (または `opscolortransport.get("histogram_match")`)

## 使い方

``src`` の値分布を ``ref`` に合わせる(1 次元の厳密な最適輸送)。

順位を保ったまま参照の分位点に置き換える。``bins`` を指定すると、その段数の
累積分布で近似する ―― 速いが**厳密ではなくなる**ので、既定は ``None``
(厳密)にしてある。

**同じ値の画素をどう扱うかで、絵の意味が変わる。** 単調写像なら「等しい入力
は等しい出力に写る」はずだが、素朴に順位で置き換えると**同値が引き裂かれる**。
実測(値 2 が 4 画素ある整数画像):出力は ``0.2222 / 0.3333 / 0.4444 /
0.5556`` の 4 つに分かれた。つまり**平坦だった領域に、元の絵に無い濃淡が
生える**。整数画像は同値だらけなので、これは例外ではなく常態。

* ``ties="average"``(既定)—— 同値の画素には、そこに割り当たった参照値の
  **平均**を与える。等しい入力は等しい出力に写り、単調性が保たれる。
  その代わり**出力の分布は参照と厳密には一致しなくなる**(同値の塊のぶん、
  分布が階段状に丸まる)。連続な入力(同値が無い)なら厳密一致のまま。
* ``ties="break"`` —— 順位そのままで引き裂く。**出力の分布は参照と厳密に
  一致する**が、平坦部に偽の濃淡が出る。分布を厳密に合わせることが目的で、
  絵として見ないと分かっているときだけ。

どちらを選んでも失うものがある(分布の厳密さ か 平坦部の平坦さ)ので、
**黙って片方に決めず引数にした**。

多チャネルの絵に**そのまま掛けるとチャネル間の相関を壊す**。
各軸の周辺分布は合うのに、色の組合せが元に無かったものになりうる。
相関ごと運びたいときは :func:`color_transfer` の ``method="gaussian"``。

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [color_transport](../../../../examples/color_transport.py) — `py -3.11 examples/color_transport.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[poisson_blend](../blend/poisson_blend.md)

## 同カテゴリ(`matching`)

[color_transfer](color_transfer.md) · [gaussian_transport_map](gaussian_transport_map.md)

---
*Provenance: colortransport.py — COLORTRANSPORT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
