---
op: ncd
dim: imgmetrics
category: compression
in: image2d × image2d
out: scalar
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# ncd — IMGMETRICS `compression` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import imgmetrics; imgmetrics.ncd(a, b, compressor='lzma', levels=None, data_range=None, symmetric=True)` (または `opsimgmetrics.get("ncd")`)

## 使い方

正規化圧縮距離(Li, Chen, Li, Ma & Vitányi, IEEE TIT 50(12), 2004)。

``NCD(x,y) = (C(xy) - min(C(x),C(y))) / max(C(x),C(y))``。
同じものなら 0 に近づき、無関係なら 1 に近づく ―― ただし **実際の圧縮器は
理想的な Kolmogorov 複雑度ではない**ので、同一入力でも厳密に 0 にはならない
(ヘッダぶんの下駄がある)。その下駄の実測値はテストに残してある。

**生の float 配列は受け付けない。** 圧縮器はバイト列の繰り返しを見るので、
値がごくわずか違うだけで float の仮数部が総取っ替えになり、**似ている 2 枚
でも共通のバイト列が消える**。実測(2026-09-02、``linspace`` の勾配と
それを +0.02 した絵、PSNR 34.0 dB = よく似ている):

* ``float64`` のまま:8 バイト語の共有率 **0.02 %** → **NCD 1.0959**
  (「まったく無関係」と読める値。しかも 1 を超える)
* 256 段に量子化:**NCD 0.1290**(正しく「よく似ている」)
* 本当に無関係な 2 枚:**NCD 0.9981**

つまり float のまま測ると**例外なく逆の結論**が出る。よって float には
``levels`` の明示を要求する(``levels=256`` なら ``data_range`` を 256 段に
量子化してから測る)。整数 dtype はそのまま測れる。

``symmetric=True``(既定)は **両向きを測って平均する**。圧縮器は前から順に
辞書を作るので ``C(xy) != C(yx)`` になり、素朴に実装すると「距離」を名乗り
ながら引数の順で値が変わる(実測: 縦縞と横縞で 0.571429 対 0.595238、
相対 4 %)。**一様乱数どうしでは差 0.000e+00 になるので、乱数で試している
限り気づけない** ―― 構造のある実データで初めて破れる型の欠陥。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`compression`)

[compressed_size](compressed_size.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
