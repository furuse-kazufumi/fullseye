---
op: hx_gabor
dim: 2d
category: halcon_ext
in: image
out: image
halcon: convol_gabor
examples: [gallery2d_halcon_ext]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# hx_gabor — 2D `halcon_ext` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "hx_gabor", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `convol_gabor`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Gabor フィルタ(方位 theta=a*pi、周波数 freq=0.08+0.35b)。応答の大きさを返す。

    向きの規約は core の ``gabor`` と同じ: ``a=0`` (θ=0) が **縦縞**、``a=0.5``
    (θ=90°) が横縞に最も応答する。

    ★正規化(2026-09-02 の修正): **カーネルの L1 ノルムで割る固定スケール**。
    以前は ``_norm01``(その画像の min–max を [0,1] へ引き伸ばす)だったため、
    向きによる応答の大小が潰れるどころか **順序が逆転していた** —— 実測
    (96×96 の横縞、b=0.5): 横縞検出器 (a=0.5) の平均 0.34663 に対し、ほとんど
    反応しないはずの縦縞検出器 (a=0) が 0.58434 と **高く**出ていた(弱い応答ほど
    引き伸ばし率が大きいため)。``|v| <= 1`` なら ``|v * g| <= sum|g|`` なので
    L1 で割れば [0,1] を保ったまま向き・画像を跨いで比較できる。

## 詳しい使い方ガイド

- [gallery2d_halcon_ext ファミリ ガイド](../guides/gallery2d_halcon_ext.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_halcon_ext](../../../../examples/gallery2d_halcon_ext.py) — `py -3.11 examples/gallery2d_halcon_ext.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`halcon_ext`)

[hx_gen_circle](hx_gen_circle.md) · [hx_gen_ellipse](hx_gen_ellipse.md) · [hx_gen_rectangle2](hx_gen_rectangle2.md) · [hx_gen_checker_region](hx_gen_checker_region.md) · [hx_gen_grid_region](hx_gen_grid_region.md) · [hx_fit_surface1](hx_fit_surface1.md) · [hx_fit_surface2](hx_fit_surface2.md) · [hx_cooc_feature](hx_cooc_feature.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
