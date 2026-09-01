---
op: gabor
dim: 2d
category: texture
in: image
out: image
halcon: gen_gabor
examples: [gallery2d_texture_freq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# gabor — 2D `texture` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "gabor", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `gen_gabor`(意味・パラメータは HALCON リファレンスが参考になる)

## 使い方

Gabor energy |v * g| — an oriented band-pass texture response.

    - ``a`` — **向き** ``θ = π·a`` [rad]。カーネルの余弦は回転後の x 方向に走るので、
      ``a=0`` (θ=0) は **縦縞**(列方向に明暗が変わる模様)に最も強く応答し、
      ``a=0.5`` (θ=90°) は **横縞**に応答する。``a=1`` は θ=180° で a=0 と同じ向き。
    - ``b`` — 空間周波数 ``0.1 + 0.3·b`` [cycles/px]。

    ★正規化(2026-09-02 の修正): **カーネルの L1 ノルムで割る固定スケール**。
    以前は ``_norm`` = その画像での最大絶対値で割っていたため、**応答の大小そのもの
    が消えていた**。実測(96×96 の横縞、周波数 0.25): 生の畳み込みの平均振幅は
    θ=0° が 0.0165、θ=90° が 0.9077 で **54.9 倍**の差があるのに、``_norm`` を通すと
    平均は 0.3554 対 0.4790 = **1.35 倍**まで潰れていた —— 向きを見分けるための
    特徴量なのに識別力が消えていた(向きごとに別の除数で割っていたのだから当然)。
    ``|v| <= 1`` なら ``|v * g| <= sum|g|`` なので L1 で割れば値域 [0,1] を保ったまま
    **op を跨いで比較できる絶対スケール**になる。

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

[std_filter](std_filter.md) · [sk_frangi](sk_frangi.md) · [sk_meijering](sk_meijering.md) · [sk_hessian](sk_hessian.md) · [sk_gabor](sk_gabor.md) · [sk_lbp](sk_lbp.md) · [sk_entropy](sk_entropy.md) · [sk_shape_index](sk_shape_index.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
