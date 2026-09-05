---
op: sk_frangi
dim: 2d
category: texture
in: image
out: image
halcon: lines_gauss
examples: [gallery2d_texture_freq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# sk_frangi — 2D `texture` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "sk_frangi", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `lines_gauss`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Frangi の管状構造検出フィルタ(vesselness filter)。血管・しわ・川のような細長い管状構造を、Hessian 行列の固有値比から検出する。

HALCON の `lines_gauss`(Detect lines and their width.)に相当(近似。線の幅や XLD 輪郭は返さず、応答強度の画像のみを返す)。2026-08-30 に a, b を配線した: a はスケール範囲(``sigmas=range(1, 2+round(a*4))`` —— 最大 σ を 1〜5 に振る。a=0.5 で旧来の固定範囲 ``range(1,4)`` とビット一致)、b は Frangi の blobness 感度 β を 0.15〜0.85 に振る(b=0.5 で skimage 既定の 0.5 と一致し、既定出力は変わらない)。既定で ``black_ridges=True``(明るい背景上の暗い管を検出する)ため、白い背景に黒い線が乗った画像でないと応答が弱く出る点に注意。

## 詳しい使い方ガイド

- [gallery2d_texture_freq ファミリ ガイド](../guides/gallery2d_texture_freq.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_texture_freq](../../../../examples/gallery2d_texture_freq.py) — `py -3.11 examples/gallery2d_texture_freq.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`texture`)

[std_filter](std_filter.md) · [gabor](gabor.md) · [sk_meijering](sk_meijering.md) · [sk_hessian](sk_hessian.md) · [sk_gabor](sk_gabor.md) · [sk_lbp](sk_lbp.md) · [sk_entropy](sk_entropy.md) · [sk_shape_index](sk_shape_index.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
