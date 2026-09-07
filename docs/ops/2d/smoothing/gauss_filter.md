---
op: gauss_filter
dim: 2d
category: smoothing
in: image
out: image
halcon: gauss_filter
examples: [gallery2d_smoothing_rank, poc_cell_counting, poc_document_scan, poc_focus_stacking, poc_gear_tooth_metrology, poc_pv_thermal_survey, poc_sea_ice_concentration, poc_solar_limb_darkening, poc_vessel_network, poc_white_balance]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# gauss_filter — 2D `smoothing` op

- **データ種**: `image` → `image`
- **呼び出し**: `fullseye.apply(img, "gauss_filter", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)
- **HALCON 相当**: `gauss_filter`(意味・パラメータは HALCON リファレンスが参考になる)

![gauss_filter: input → output](../../_fig/gauss_filter.png)

*図は合成の入力 128×128 で実際に走らせた出力。左が入力、右が出力。点群は上から見た散布(明るさ = z)、1-D 列は折れ線、体積は z 方向の最大値投影、動画は中央フレーム、複素画像は振幅、絵にならない返り値は値そのもの。*

**つまみ a を振る**(0.1 / 0.5 / 0.9、もう一方は既定):

![gauss_filter: knob a sweep](../../_fig/gauss_filter.a.jpg)

*つまみ b は出力を変えない(実測: 0.1 / 0.5 / 0.9 で同一)。*

**別の画像でも**(合成シーン / 写真 / 硬貨。上段が入力、下段がその出力。つまみは既定):

![gauss_filter: other inputs](../../_fig/gauss_filter.inputs.jpg)

*カラー (H,W,3) の入力は載せていない: この op は色チャネルを 3 本目の空間軸として扱う(色を跨ぐ)ため。チャネルごとに分けて呼ぶこと。*

## 使い方

ガウシアンぼかし(``scipy.ndimage.gaussian_filter``、シグマ ``0.3+2.7*a``)
による平滑化。HALCON の ``gauss_filter``（Smooth using discrete Gauss
functions.）の代役 ―― HALCON は離散ガウス核(整数演算)、こちらは連続ガウス核
の scipy 実装で、近似ではあるが結果は非常に近い。

``a`` がシグマを 0.3〜3.0 の範囲で振る。``b`` は未使用。実装は
``gauss_image`` と同一。

## 詳しい使い方ガイド

- [gallery2d_smoothing_rank ファミリ ガイド](../guides/gallery2d_smoothing_rank.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## Studio で試す

下のプログラムは実際に走ることを確かめてある(図と同じ入力)。Studio のヘルプではこのブロックがボタンになり、その場で読み込んで実行できる。

```program
gauss_filter 0.35 0.50
```

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_smoothing_rank](../../../../examples/gallery2d_smoothing_rank.py) — `py -3.11 examples/gallery2d_smoothing_rank.py`
- [poc_cell_counting](../../../../examples/poc_cell_counting.py) — `py -3.11 examples/poc_cell_counting.py`
- [poc_document_scan](../../../../examples/poc_document_scan.py) — `py -3.11 examples/poc_document_scan.py`
- [poc_focus_stacking](../../../../examples/poc_focus_stacking.py) — `py -3.11 examples/poc_focus_stacking.py`
- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`
- [poc_pv_thermal_survey](../../../../examples/poc_pv_thermal_survey.py) — `py -3.11 examples/poc_pv_thermal_survey.py`
- [poc_sea_ice_concentration](../../../../examples/poc_sea_ice_concentration.py) — `py -3.11 examples/poc_sea_ice_concentration.py`
- [poc_solar_limb_darkening](../../../../examples/poc_solar_limb_darkening.py) — `py -3.11 examples/poc_solar_limb_darkening.py`
- [poc_vessel_network](../../../../examples/poc_vessel_network.py) — `py -3.11 examples/poc_vessel_network.py`
- [poc_white_balance](../../../../examples/poc_white_balance.py) — `py -3.11 examples/poc_white_balance.py`

## 型が繋がる次の op(`image` を入力に取れる)

[identity](../misc/identity.md) · [gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [unsharp](unsharp.md) · [median](../rank/median.md) · [min_filter](../rank/min_filter.md) · [max_filter](../rank/max_filter.md)

## 同カテゴリ(`smoothing`)

[gaussian](gaussian.md) · [mean_box](mean_box.md) · [bilateral](bilateral.md) · [unsharp](unsharp.md) · [sk_tv](sk_tv.md) · [sk_wavelet](sk_wavelet.md) · [sk_rolling_ball](sk_rolling_ball.md) · [sk_nlm](sk_nlm.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
