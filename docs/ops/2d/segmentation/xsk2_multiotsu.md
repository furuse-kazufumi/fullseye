---
op: xsk2_multiotsu
dim: 2d
category: segmentation
in: image
out: image
examples: [gallery2d_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# xsk2_multiotsu — 2D `segmentation` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "xsk2_multiotsu", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

大津の判別分析法（Otsu's method）を多値に拡張した多値大津法で階調を
量子化する。``skimage.filters.threshold_multiotsu`` を使う。

a はクラス数を 3 または 4 に切り替える（``3 + int(a > 0.5)``）。
**5 クラス以上は実装していない**——多値大津はしきい値の全探索コストが
``bins ** (classes - 1)`` で増えるため、実測（128x128）で 3 クラス
0.0008 秒に対し 5 クラスは 2.435 秒（3239 倍）かかり、進化ループ 1 世代
だけで実行が止まって見えるほど遅い（画像サイズにはほぼ依らない）。
4 クラスなら 0.025 秒に収まる。b は未使用。しきい値で量子化した後
``(cls-1)`` で割って [0,1] に正規化する。

## 詳しい使い方ガイド

- [gallery2d_segmentation ファミリ ガイド](../guides/gallery2d_segmentation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_segmentation](../../../../examples/gallery2d_segmentation.py) — `py -3.11 examples/gallery2d_segmentation.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`segmentation`)

[threshold](threshold.md) · [otsu](otsu.md) · [canny](canny.md) · [adaptive_gauss_thresh](adaptive_gauss_thresh.md) · [sk_otsu](sk_otsu.md) · [sk_li](sk_li.md) · [sk_yen](sk_yen.md) · [sk_sauvola](sk_sauvola.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
