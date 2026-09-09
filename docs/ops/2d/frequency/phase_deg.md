---
op: phase_deg
dim: 2d
category: frequency
in: image
out: image
halcon: phase_deg
examples: [gallery2d_texture_freq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# phase_deg — 2D `frequency` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "phase_deg", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `phase_deg`(意味・パラメータは HALCON リファレンスが参考になる)

![phase_deg: input → output](../../_fig/phase_deg.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*出力は viridis 風の疑似カラー(暗い紫 = 小、黄 = 大)。距離・位相・向き・深度のような「量の場」を読むため。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![phase_deg: other inputs](../../_fig/phase_deg.inputs.jpg)

*カラー (H,W,3) の入力は載せていない: この op は色チャネルを 3 本目の空間軸として扱う(色を跨ぐ)ため。チャネルごとに分けて呼ぶこと。*

## 使い方

複素画像の位相角マップ。``np.angle(F)``（-π〜π）を ``(angle+π)/(2π)`` で [0,1] に線形写像する。a, b は未使用。

名称は「度（degree）」を示唆するが、実装は phase_rad と同じ ``_sh_freq`` の ``fft_phase`` 分岐を共有しており、度数法への変換は行っていない —— 返るのは [0,1] に正規化された角度で、実際の度数（0-360°）ではない。HALCON の ``phase_deg``（複素画像の位相を度単位で返す演算）の代役としては単位が違う近似である点に注意。

## 詳しい使い方ガイド

- [gallery2d_texture_freq ファミリ ガイド](../guides/gallery2d_texture_freq.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
phase_deg 0.40 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_texture_freq](../../../../examples/gallery2d_texture_freq.py) — `py -3.11 examples/gallery2d_texture_freq.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`frequency`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [sk_butterworth](sk_butterworth.md) · [fft_image](fft_image.md) · [power_real](power_real.md) · [power_byte](power_byte.md) · [phase_rad](phase_rad.md) · [highpass_image](highpass_image.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
