---
op: rescale_img
dim: 2d
category: geometry
in: image
out: image
halcon: zoom_image_factor
examples: [gallery2d_geometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# rescale_img — 2D `geometry` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "rescale_img", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `zoom_image_factor`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Isotropic centre-preserving rescale by ``s = 0.7 + 0.6·a``, canvas kept.

    ``b`` = **補間の次数** — ``(0, 1, 3, 3)[min(3, int(4b))]``(0 = 最近傍、
    1 = 双一次、3 = 三次スプライン)。``b=0.5`` は 3 次で、``b`` が死んでいた頃の
    既定(``ndimage`` の order=3)と **ビット一致**する。

    ★2026-09-02: それまで ``rescale_img`` / ``zoom_image_factor`` /
    ``zoom_image_size`` は **3 つとも同じ実装**(実測: 相互の最大差 0.0 と
    4.9e-14)で、3 つとも ``b`` を使っていなかった。3 つの役割を分けた:

    * ``rescale_img``      — 等方倍率 1 つ + **補間次数**(この関数)
    * ``zoom_image_factor``— 縦横 **2 つの倍率**(HALCON の ScaleHeight/ScaleWidth)
    * ``zoom_image_size``  — **目標サイズ**指定(出力 shape が変わる)

    HALCON 名も実態に合わせて ``zoom_image_size`` → ``zoom_image_factor`` へ
    付け替えた(この op はサイズではなく倍率で駆動するため)。

## 詳しい使い方ガイド

- [gallery2d_geometry ファミリ ガイド](../guides/gallery2d_geometry.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_geometry](../../../../examples/gallery2d_geometry.py) — `py -3.11 examples/gallery2d_geometry.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`geometry`)

[rotate_img](rotate_img.md) · [affine_warp](affine_warp.md) · [sk_swirl](sk_swirl.md) · [mirror_image](mirror_image.md) · [transpose_region](transpose_region.md) · [rotate_image](rotate_image.md) · [zoom_image_factor](zoom_image_factor.md) · [zoom_image_size](zoom_image_size.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
