---
op: dl_aniso_diffusion
dim: 2d
category: smoothing
in: image
out: image
halcon: anisotropic_diffusion
examples: [gallery2d_smoothing_rank]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# dl_aniso_diffusion — 2D `smoothing` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "dl_aniso_diffusion", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `anisotropic_diffusion`(意味・パラメータは HALCON リファレンスが参考になる)

![dl_aniso_diffusion: input → output](../../_fig/dl_aniso_diffusion.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![dl_aniso_diffusion: knob a sweep](../../_fig/dl_aniso_diffusion.a.jpg)

**つまみ b を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![dl_aniso_diffusion: knob b sweep](../../_fig/dl_aniso_diffusion.b.jpg)

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![dl_aniso_diffusion: other inputs](../../_fig/dl_aniso_diffusion.inputs.jpg)

*4 列目はカラー (H,W,3) の入力。この op は色を跨がずに扱える(色チャネルを 3 本目の空間軸として畳み込まない)。*

## 使い方

Perona-Malik 型の異方性拡散フィルタ（torch 実装、GPU があれば GPU 上で実行）。

上下左右 4 方向の差分にそれぞれ ``exp(-(差分/K)^2)`` の伝導度を掛けてから加算する
反復拡散で、勾配が大きい（エッジらしい）場所ほど拡散が弱まり、エッジを保ったまま
平滑化する。``a`` はエッジ検出しきい値 ``K`` を 0.02〜0.22 に振る（``K = 0.02 +
0.2*a``、大きいほどエッジを跨いで拡散しやすくなる）。``b`` は反復回数を 5〜20 回に
振る（``iters = 5 + int(b*15)``）。ステップ幅 ``lam=0.2`` は固定。ガウシアンぼかしと
異なりエッジをぼかさずにノイズだけ均せるのが利点。HALCON の
``anisotropic_diffusion``（画像の異方性拡散を行う）に相当するが、同じ結果になる
とは限らない近似実装。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
dl_aniso_diffusion 0.35 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [unsharp](unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`smoothing`)

[gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [unsharp](unsharp.md) · [sk_tv](sk_tv.md) · [sk_wavelet](sk_wavelet.md) · [sk_rolling_ball](sk_rolling_ball.md) · [sk_nlm](sk_nlm.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
