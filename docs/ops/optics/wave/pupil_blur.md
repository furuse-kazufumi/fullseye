---
op: pupil_blur
dim: optics
category: wave
in: image2d × image2d
out: image2d
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# pupil_blur — OPTICS `wave` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.pupil_blur(image, pupil, defocus_waves=0.0, wavelength_um=0.55, f_number=5.6, pixel_pitch_um=5.0, oversample=4, opd_waves=None)` (実装を直接呼ぶなら `import optics; optics.pupil_blur(image, pupil, defocus_waves=0.0, wavelength_um=0.55, f_number=5.6, pixel_pitch_um=5.0, oversample=4, opd_waves=None)`、台帳から引くなら `opsoptics.get("pupil_blur")`)

## 使い方

Blur an image with the PSF of a pupil shape at one wavelength band.

The forward imaging model of *one* spectral band: the PSF of
:func:`pupil_psf` (same pupil / defocus / wavelength / f-number
arguments), **binned to the image's pixel pitch** so the blur is in the
image's own units, convolved with the image (FFT, reflect-padded borders so
a flat field stays flat and nothing wraps around). Call it once per band
with that band's ``defocus_waves`` (from :func:`defocus_from_shift` and a
focal shift versus wavelength) and you have the polychromatic image of a
lens with longitudinal chromatic aberration seen through any pupil — the
ingredient of the "colour from chromatic blur" hypothesis for
single-photoreceptor eyes (Stubbs & Stubbs, *PNAS* 113:8206, 2016).

Returns a float64 ``image2d`` of the image's shape. Linear: no clipping,
no re-normalisation of the image (the PSF sums to 1, so a constant image
is returned unchanged to rounding).

Ground truth it reproduces (measured, ``tests/test_optics.py``): a constant
image is unchanged to 1e-12; a delta image returns the binned PSF itself
(the impulse response, to 1e-12 where the kernel fits); with
``defocus_waves = 0`` and a diffraction spot much smaller than the pixel
(``lambda N = 0.8 um`` on a 5 um pitch) a sharp edge is unchanged to
within 1 % — the *identity at focus*; the blurred image's total is the
input's total to 1e-9 (flux is conserved by the reflect padding).

**Raises** ``ValueError``: everything :func:`pupil_psf` raises, plus
*image* not 2-D / smaller than 2x2 / over the size cap / complex / masked
/ non-finite, and a non-finite result (an FFT overflow).

Shift-invariant: one PSF for the whole field. Field-dependent blur
(vignetting, off-axis aberration) is ``lensimage.render_through_lens``.

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [optics_imaging](../../../../examples/optics_imaging.py) — `py -3.11 examples/optics_imaging.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](fraunhofer_pattern.md) · [pupil_psf](pupil_psf.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [polarization_demosaic](../polarization/polarization_demosaic.md) · [polarization_demosaic_color](../polarization/polarization_demosaic_color.md) · [illumination_uniformity](../illumination/illumination_uniformity.md) · [render_through_lens](../imaging_sim/render_through_lens.md) · [surface_defect](../scene/surface_defect.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [fourier_plane_filter](fourier_plane_filter.md) · [four_f_filter](four_f_filter.md) · [gaussian_beam](gaussian_beam.md) · [defocus_from_shift](defocus_from_shift.md) · [pupil_psf](pupil_psf.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
