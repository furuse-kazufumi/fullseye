---
op: xsitk_signed_maurer_dist
dim: 2d
category: extra
in: region
out: image
examples: [gallery2d_color_artistic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# xsitk_signed_maurer_dist — 2D `extra` op

- **データ種**: `region` → `image`
- **呼び出し**: `fullseye.apply(img, "xsitk_signed_maurer_dist", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

型契約は `region → image`。挙動の言語説明は下記のファミリ使い方ガイドと実行可能サンプルを参照(ここでは推測を書かない)。

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

## 同カテゴリ(`extra`)

[xsitk_curvature_flow](xsitk_curvature_flow.md) · [xsitk_minmax_curv_flow](xsitk_minmax_curv_flow.md) · [xsitk_curv_aniso_diff](xsitk_curv_aniso_diff.md) · [xsitk_laplacian_sharpen](xsitk_laplacian_sharpen.md) · [xsitk_grayscale_fillhole](xsitk_grayscale_fillhole.md) · [xsitk_grayscale_grindpeak](xsitk_grayscale_grindpeak.md) · [xsitk_opening_by_recon](xsitk_opening_by_recon.md) · [xsitk_closing_by_recon](xsitk_closing_by_recon.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
