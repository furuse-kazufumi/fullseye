---
op: sigma_clip_stack
dim: astrostack
category: stack
in: images
out: image2d
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# sigma_clip_stack — ASTROSTACK `stack` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import astrostack; astrostack.sigma_clip_stack(frames, mode='sigma_clip', kappa=3.0, iters=5, center='median', scale='mad')` (または `opsastrostack.get("sigma_clip_stack")`)

## 使い方

フレーム列を合成する(平均 / 中央値 / κ-σ クリップ)。採否マスクつき。

*mode*:

* ``"mean"`` —— 単純平均。雑音は ``sqrt(N)`` で下がるが、外れ値(宇宙線・
  人工衛星の航跡)は ``1/N`` しか薄まらず**必ず残る**。
* ``"median"`` —— 中央値。外れ値に強い代わりに、正規分布のとき雑音は
  平均の ``sqrt(pi/2) = 1.2533`` 倍しか下がらない(= 実効的に 36 % 枚数を
  捨てている)。
* ``"sigma_clip"`` —— 中央値を中心、``scale`` を尺度として
  ``|x - center| > kappa * scale`` を落とし、残りで平均を取る。これを
  ``iters`` 回。外れ値に強く、かつ生き残った画素は平均されるので雑音も
  ``sqrt(N_accepted)`` で下がる —— 実用の既定。

**破綻点は 50 %。** 中心を中央値、尺度を MAD で取る以上、汚染フレームが
半数を超えた画素では中央値そのものが汚染側に乗り、クリップは**正しい方**を
捨てる。これはこの実装の不具合ではなく中央値の定義そのもので、
``center="mean"`` にすればもっと早く(汚染 1 枚でも)壊れる。テストは
0〜60 % の汚染率で誤差を測り、**壊れる側もそのまま残してある**。

**``scale`` の既定が ``"mad"`` なのは実測の結果。** ``scale="std"`` は
「外れ値を見つけるための尺度を、その外れ値自身が膨らませる」ので、汚染が
増えるとむしろ**何も落とさなくなる** —— 24x24 の平坦場(真値 100、
σ=2)20 枚のうち 4 枚(20 %)に +500 の汚染を入れた実測では、
``scale="std"`` は棄却率 **0.0 %** で誤差 **+99.9975**(= 単純平均と
小数点以下まで完全に同じ)、``scale="mad"`` は棄却率 **22.0 %** で誤差
**-0.019**。破綻点は ``std`` が 10〜20 % の間、``mad`` がちょうど 50 % で、
5 倍近く違う。

Returns ``(stack, accepted)``:

* ``stack`` —— ``(H, W)`` float64。
* ``accepted`` —— ``(N, H, W)`` bool、``True`` = **採用**した画素。
  ``mode="mean"`` / ``"median"`` では全 ``True``(どちらもクリップしない
  ので、「採否」の概念が無いことを ``False`` が 1 つも無いことで示す)。

**Raises** ``ValueError``: *frames* が list / tuple でない / 枚数が 2 未満 /
形が揃っていない / *mode* が :data:`STACK_MODES` にない / *kappa* が非正 /
*center* が ``"median"`` / ``"mean"`` 以外 / *scale* が ``"std"`` /
``"mad"`` 以外の場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[frame_quality](../quality/frame_quality.md) · [noise_sigma](../quality/noise_sigma.md) · [cosmic_ray_reject](../cosmic/cosmic_ray_reject.md) · [star_detect](../photometry/star_detect.md) · [psf_fit](../photometry/psf_fit.md) · [aperture_photometry](../photometry/aperture_photometry.md) · [frame_align](../align/frame_align.md)

## 同カテゴリ(`stack`)

[drizzle_resample](drizzle_resample.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
