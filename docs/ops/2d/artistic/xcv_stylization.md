---
op: xcv_stylization
dim: 2d
category: artistic
in: image
out: image
examples: [gallery2d_color_artistic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# xcv_stylization — 2D `artistic` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "xcv_stylization", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

OpenCV の stylization(絵画風/カートゥーン風のノンフォトリアリスティック・
レンダリング)。

エッジ保存平滑化を使って細部を均しつつ主要な輪郭を残し、平坦な色面と
目立つ輪郭からなるイラスト調の画像を作る(内部で 3ch に変換して処理し、
結果をグレースケールへ戻す)。

``a`` が空間方向の平滑化範囲 ``sigma_s`` を 20〜120 で振る(大きいほど
広い範囲を均す)。``b`` が色(輝度)差の許容範囲 ``sigma_r`` を 0.1〜0.5
で振る(大きいほどエッジをまたいで均しやすくなり、平坦化が強まる)。

## 詳しい使い方ガイド

- [gallery2d_color_artistic ファミリ ガイド](../guides/gallery2d_color_artistic.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_color_artistic](../../../../examples/gallery2d_color_artistic.py) — `py -3.11 examples/gallery2d_color_artistic.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`artistic`)

[xcv_pencil_sketch](xcv_pencil_sketch.md) · [xpil_emboss](xpil_emboss.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
