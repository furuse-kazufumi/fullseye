---
op: height_width_ratio
dim: 2d
category: features
in: region
out: feature
halcon: height_width_ratio
examples: [gallery2d_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# height_width_ratio — 2D `features` op

- **データ種**: `region` → `feature`
- **呼び出し**: `fullseye.apply(img, "height_width_ratio", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `height_width_ratio`(意味・パラメータは HALCON リファレンスが参考になる)

![height_width_ratio: input → output](../../_fig/height_width_ratio.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**段階**(前置きの op → この op。左から順):

![height_width_ratio: stages](../../_fig/height_width_ratio.chain.jpg)

## 使い方

軸平行の外接矩形の縦横比 ``高さ / 幅``。上限は無く、縦長なら 1 を超える
(160x4 なら 40.0)。HALCON の ``height_width_ratio``（Compute the width,
height, and aspect ratio of the surrounding rectangle parallel to the
coordinate axes.）が返す 3 値のうち **Ratio と同じ量**(Height と Width は
画素の長さなので返していない —— docs/KNOWN_ISSUES.md §51)。

★2026-09-26 まで ``min(1, 高さ/幅)`` で切っていたので、**縦長の対象が全部
1.0** になっていた(60x20 で 1.0、真値 3.0)。横長は正しく出るので、
**向きが変わった瞬間に情報が消える**。飽和は説明文に「仕様」として書かれて
いたが、値域 [0,1] は feature の契約ではなく、潰す理由が無かった ――
``docs/hardening/features-saturated-at-one.md``。

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
height_width_ratio 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_features](../../../../examples/gallery2d_features.py) — `py -3.11 examples/gallery2d_features.py`

## 型が繋がる次の op(`feature` を入力に取れる)

[identity](../misc/identity.md) · [feature_to_img](../bridge/feature_to_img.md)

## 同カテゴリ(`features`)

[effective_bit_depth](effective_bit_depth.md) · [blob_count](blob_count.md) · [area_frac](area_frac.md) · [count_contours](count_contours.md) · [total_length](total_length.md) · [vol_count](vol_count.md) · [sk_euler](sk_euler.md) · [sk_entropy_feat](sk_entropy_feat.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
