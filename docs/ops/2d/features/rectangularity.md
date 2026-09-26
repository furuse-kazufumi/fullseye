---
op: rectangularity
dim: 2d
category: features
in: region
out: feature
halcon: rectangularity
examples: [gallery2d_features, shape_factors_closed_form]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# rectangularity — 2D `features` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "rectangularity", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `rectangularity`(意味・パラメータは HALCON リファレンスが参考になる)

![rectangularity: input → output](../../_fig/rectangularity.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![rectangularity: stages](../../_fig/rectangularity.chain.jpg)

## 使い方

矩形度。**同じ 1 次・2 次モーメントを持つ矩形**を作り、領域との差の面積を
その矩形の面積で正規化する(``1 - |領域 XOR 矩形| / |矩形|``)。矩形なら 1。
HALCON の ``rectangularity``（Shape factor for the rectangularity of a
region.）**と同じ定義**。

★2026-09-26 まで**軸平行の**外接矩形との比(``skimage`` の ``extent``)だった。
向きを見ないので、**同じ長方形を 30 度回しただけで 1.000 が 0.359 に落ちていた**
(HALCON は 0.998 のまま)。``docs/hardening/halcon-named-shape-factors.md``。

★正方形や円のように 2 次モーメントで向きが決まらない形では、「同じモーメントを
持つ矩形」が向きの数だけ在って定義が向きを決めない。ここでは重なりが最大に
なる向きを選ぶ —— そのまま任意の向きで当てると正方形が 0.651 になり、HALCON の
「矩形なら 1」と食い違う。HALCON もこの形では最大 10% 過小評価すると明記する。

``a``, ``b`` は未使用。

## 詳しい使い方ガイド

- [gallery2d_features ファミリ ガイド](../guides/gallery2d_features.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
threshold 0.50 0.50
rectangularity 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_features](../../../../examples/gallery2d_features.py) — `py -3.11 examples/gallery2d_features.py`
- [shape_factors_closed_form](../../../../examples/shape_factors_closed_form.py) — `py -3.11 examples/shape_factors_closed_form.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md) · [feature_to_img](../bridge/feature_to_img.md)

## 同カテゴリ(`features`)

[effective_bit_depth](effective_bit_depth.md) · [blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [vol_count](vol_count.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
