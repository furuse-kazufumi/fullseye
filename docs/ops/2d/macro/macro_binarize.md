---
op: macro_binarize
dim: 2d
category: macro
in: image
out: image
examples: [gallery2d_physics_alife_3d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# macro_binarize — 2D `macro` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "macro_binarize", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

![macro_binarize: input → output](../../_fig/macro_binarize.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

*つまみ a は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![macro_binarize: other inputs](../../_fig/macro_binarize.inputs.jpg)

*カラー (H,W,3) の入力は載せていない: この op は色チャネルを 3 本目の空間軸として扱う(色を跨ぐ)ため。チャネルごとに分けて呼ぶこと。*

## 使い方

進化探索が発見した固定パイプライン: ``bilateral(a=0.06,b=0.89)`` → ``unsharp(a=0.51,b=0.34)`` → ``bilateral(a=0.04,b=0.24)`` → ``lowpass(a=0.75,b=0.59)`` → ``gopen(a=0.38,b=1.00)`` → ``unsharp(a=0.78,b=0.68)``（平滑化とアンシャープマスクを交互に重ね、ローパスとグレースケールオープニングで整えてから再度シャープ化する 6 段）。

``a``, ``b`` は凍結済みで未使用。binarize 課題（IoU）でロック済みホールドアウト 0.75、手作りベースライン 0.62 を上回るが、train 0.91 / holdout0.95 に対し locked_holdout は 0.75 まで落ちる —— 分割ごとの差を隠さず書く（feedback_benchmark_honest_disclosure）。HALCON に対応する単一オペレータは無い。

## 詳しい使い方ガイド

- [gallery2d_physics_alife_3d ファミリ ガイド](../guides/gallery2d_physics_alife_3d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
macro_binarize 0.50 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_physics_alife_3d](../../../../examples/gallery2d_physics_alife_3d.py) — `py -3.11 examples/gallery2d_physics_alife_3d.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](../smoothing/gaussian.md) · [mean_box](../smoothing/mean_box.md) · [bilateral](../smoothing/bilateral.md) · [unsharp](../smoothing/unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`macro`)

[macro_denoise](macro_denoise.md) · [macro_edge](macro_edge.md) · [macro_vol_denoise](macro_vol_denoise.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
