---
op: psf_fit
dim: astrostack
category: photometry
in: image2d × keypoints
out: table
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# psf_fit — ASTROSTACK `photometry` op

- **データ種**: `image2d × keypoints` → `table`
- **呼び出し**: `import astrostack; astrostack.psf_fit(image, centers, model='gaussian', box=11, max_iter=200)` (または `opsastrostack.get("psf_fit")`)

## 使い方

星像に PSF を当てはめて中心と FWHM を出す。

*model* ``"gaussian"`` は**楕円**ガウシアン
``bkg + amp * exp(-((dr/sr)^2 + (dc/sc)^2)/2)`` の 6 パラメータ当てはめで、
真円度(``roundness = min(sr,sc)/max(sr,sc)``)が副産物として出る ——
追尾誤差や風で伸びた星像はここに出る。``"moffat"`` は円対称の
``bkg + amp * (1 + r^2/alpha^2)^(-beta)``(Moffat 1969)で、``beta`` も
自由パラメータ。最小二乗は :func:`scipy.optimize.least_squares`
(Trust Region Reflective)で、初期値は 2 次モーメントから作る決定的な値
—— 乱数を使わないので同じ入力なら同じ答え。

FWHM は当てはめたパラメータからの**閉形式**:
ガウシアンは ``2 sqrt(2 ln 2) * sqrt(sr*sc)``(幾何平均)、Moffat は
``2 alpha sqrt(2^(1/beta) - 1)``。

**画素の箱のぶんだけ、必ず太く出る。** ここが当てはめているのは*連続の*
ガウシアンだが、画像の各画素は連続分布を 1 画素の箱で積分した値である。
一様な幅 1 の箱の分散は ``1/12`` なので、返る sigma は真の sigma ではなく
``sqrt(sigma^2 + 1/12)`` になる —— これは推定の誤差ではなく**画像がそう
できている**ということ。実測はこの予測とよく合う::

    真の FWHM   予測 = 2.3548*sqrt(sigma^2+1/12)   実測(中央値)
      2.5              2.5908                        2.5930
      3.5              3.5654                        3.5625
      5.0              5.0460                        5.0145

真の sigma が欲しければ ``sqrt(sigma_fit^2 - 1/12)`` と引けばよいが、
**既定では引かない** —— 星の測定で普通に言う「FWHM」は画像上の見た目の
幅であり、黙って補正を入れると他の道具の値と合わなくなる。

Returns 各星 1 つの dict の ``list``(``table`` 語彙)。キーは
``row`` / ``col``(当てはめた中心)、``fwhm_px``、``amplitude``、
``background``、``roundness``、``rms``(残差 RMS)、``converged``(bool)、
``model``、そして model 依存の ``sigma_row_px`` / ``sigma_col_px``
または ``alpha_px`` / ``beta``。窓が画像からはみ出す星、当てはめが
収束しなかった星も**落とさずに** ``converged=False`` で返す
—— 黙って消すと「星が減った」ことに誰も気づけない。

**Raises** ``ValueError``: *model* が :data:`PSF_MODELS` にない /
*box* が 5 未満または偶数 / *centers* が ``(N, 2)`` でない場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`photometry`)

[star_detect](star_detect.md) · [aperture_photometry](aperture_photometry.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
