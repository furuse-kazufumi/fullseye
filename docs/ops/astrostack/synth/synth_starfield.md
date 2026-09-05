---
op: synth_starfield
dim: astrostack
category: synth
in: 
out: image2d
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# synth_starfield — ASTROSTACK `synth` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import astrostack; astrostack.synth_starfield(shape=(128, 128), n_stars=30, flux_min=400.0, flux_max=9000.0, fwhm_px=3.2, psf='gaussian', moffat_beta=2.5, sky=60.0, read_sigma=6.0, shift_row=0.0, shift_col=0.0, n_cosmic=0, cosmic_flux=4000.0, margin_px=6.0, seed=0, field_seed=None, noise=True)` (または `opsastrostack.get("synth_starfield")`)

## 使い方

既知の星野を 1 枚合成する —— **この族の正解の供給源**。

星は ``flux_min``〜``flux_max`` の対数一様分布から総フラックス(電子)を引き、
画像の縁から ``margin_px`` 以上内側に一様に置く。*psf* が ``"gaussian"`` の
ときは :func:`scipy.special.erf` による**画素の厳密な積分**なので、星 1 個の
総和は与えたフラックスに(画像の外へ出た分を除いて)厳密に一致する。
``"moffat"`` は Moffat, *A Theoretical Investigation of Focal Stellar Images*,
A&A 3, 455 (1969) の ``(1 + (r/alpha)^2)^(-beta)`` で、地上の**大気**が支配する
星像の標準モデル(回折限界の兄弟は :func:`optics.airy_pattern`)。

ノイズは 1 つの理論しか持たない ——
``Poisson(星 + sky)``(:func:`photoncount.photon_sample` を
``photons_per_unit=1.0`` で呼ぶ)に、**その後**で宇宙線を足し、**最後**に
加法ガウスの読み出しノイズ ``read_sigma`` を足す。順序は物理どおりで、
宇宙線は光子ではない(Poisson 標本化を通さない)。宇宙線の**位置**は
:func:`defectgen.defect_pits` の一様点過程に任せる —— 「稀で小さく鋭い、
位置がランダムな付着」は孔食と同じ確率幾何であって、二つ目のモデルを
書く理由が無い。

*shift_row* / *shift_col* は星野全体を副画素で動かす(ディザ)。合成した
真値の座標もその分だけ動くので、位置合わせと drizzle の検算に使える。

Returns ``(frame, truth)``:

* ``frame`` —— ``(H, W)`` float64、単位は**電子**。
* ``truth`` —— dict。``rows`` / ``cols`` ``(N,)`` は星の真の中心(整数座標が
  画素中心の規約)、``fluxes`` ``(N,)`` は真の総フラックス、``fwhm_px`` /
  ``sigma_px`` / ``alpha_px`` / ``beta`` は PSF、``sky`` / ``read_sigma`` は
  雑音、``cosmic_mask`` ``(H, W)`` bool は宇宙線の画素、``noiseless``
  ``(H, W)`` はノイズを載せる前の期待値(検算用)。

**seed は 2 本ある。** ``field_seed`` が**星野**(座標とフラックス)を、
``seed`` が**その回の観測**(ショットノイズ・読み出しノイズ・宇宙線の位置)を
決める。``field_seed=None`` なら ``seed`` と同じ値になる。分けてある理由は
実測で見つけた事故で、1 本にしていた最初の版では
:func:`synth_frame_series` がフレームごとに ``seed`` を変えた結果
**星野そのものが毎フレーム別物**になり、位置合わせが 1 対応しか見つけられず
(``frame_align`` が正しく fail-closed した)、フレーム間の宇宙線除去は
「全画素が外れ値」を返した。同じ空を撮り直すのと、別の空を撮るのは、
引数 1 つで取り違えられる —— だから型ではなく名前で分ける。
乱数はどちらも ``numpy.random.default_rng`` なので、同じ seed 対なら
どの機械でも同じフレーム。

Ground truth it reproduces(``tests/test_astrostack.py`` で固定):
``noise=False``、``sky=0``、``fwhm_px=3.0`` の 1 星フレーム(64x64、
フラックス 5000 e-)では、画像全体の総和と与えたフラックスの相対誤差が
**1.8e-16** —— float64 の丸め 1 回ぶんで、「ほぼ保存」ではなく保存。
半径 ``r`` の円形開口が拾う割合は ``1 - exp(-r^2/(2 sigma^2))`` で、
``r = 2 sigma`` なら 0.8647、``r = 3 sigma`` なら 0.98889。

**Raises** ``ValueError``: *shape* が小さすぎる / *n_stars* が非負整数でない /
``flux_min > flux_max`` / *psf* が :data:`PSF_MODELS` にない /
``moffat_beta <= 1``(積分が発散する)/ ``margin_px`` が画像より大きい /
*seed* が非負整数でない場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[frame_quality](../quality/frame_quality.md) · [noise_sigma](../quality/noise_sigma.md) · [cosmic_ray_reject](../cosmic/cosmic_ray_reject.md) · [star_detect](../photometry/star_detect.md) · [psf_fit](../photometry/psf_fit.md) · [aperture_photometry](../photometry/aperture_photometry.md) · [frame_align](../align/frame_align.md)

## 同カテゴリ(`synth`)

[synth_frame_series](synth_frame_series.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
