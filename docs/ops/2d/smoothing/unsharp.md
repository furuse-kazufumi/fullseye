---
op: unsharp
dim: 2d
category: smoothing
in: image
out: image
halcon: emphasize
examples: [gallery2d_smoothing_rank, poc_camera_shake_deblur, poc_real_deblur_honesty, poc_superresolution_limits]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# unsharp — 2D `smoothing` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "unsharp", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `emphasize`(意味・パラメータは HALCON リファレンスが参考になる)

![unsharp: input → output](../../_fig/unsharp.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![unsharp: knob a sweep](../../_fig/unsharp.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![unsharp: knob b sweep](../../_fig/unsharp.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![unsharp: other inputs](../../_fig/unsharp.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Unsharp mask. ★出口で [0,1] に clip する(2026-09-02)。

``v + k*(v - blur)`` は定義上オーバーシュートする(実測 min=-0.1499 /
max=+1.1499)。`_apply` は段間で同じ clip を掛けるので **パイプライン結果は
ビット不変**だが、`fullseye.apply` を単発で呼ぶ経路だけは生値が出ていて、
`image` の [0,1] 契約を破ったまま保存すると黒/白に潰れていた。GPU 側
(`accel._unsharp`)も同じ clip を持つ。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
unsharp 0.35 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`
- [poc_camera_shake_deblur](../../../../examples/poc_camera_shake_deblur.py) — `py -3.11 examples/poc_camera_shake_deblur.py`
- [poc_real_deblur_honesty](../../../../examples/poc_real_deblur_honesty.py) — `py -3.11 examples/poc_real_deblur_honesty.py`
- [poc_superresolution_limits](../../../../examples/poc_superresolution_limits.py) — `py -3.11 examples/poc_superresolution_limits.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md) · [percentile](../rank/percentile.md)

## 同カテゴリ(`smoothing`)

[gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [sk_tv](sk_tv.md) · [sk_wavelet](sk_wavelet.md) · [sk_rolling_ball](sk_rolling_ball.md) · [sk_nlm](sk_nlm.md) · [sk_tv_bregman](sk_tv_bregman.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
