---
op: pupil_psf
dim: optics
category: wave
in: image2d
out: image2d
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# pupil_psf — OPTICS `wave` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.pupil_psf(pupil, defocus_waves=0.0, wavelength_um=0.55, f_number=5.6, oversample=4, pixel_pitch_um=None, opd_waves=None)` (実装を直接呼ぶなら `import optics; optics.pupil_psf(pupil, defocus_waves=0.0, wavelength_um=0.55, f_number=5.6, oversample=4, pixel_pitch_um=None, opd_waves=None)`、台帳から引くなら `opsoptics.get("pupil_psf")`)

## 使い方

Diffraction PSF of an **arbitrary pupil shape** with defocus (sums to 1).

*pupil* is a square ``(n, n)`` amplitude transmittance (0 = opaque, 1 =
clear; a binary mask is the usual case) drawn on a grid whose **full width
is the pupil's clear diameter** ``D`` — so a circle filling the grid is a
conventional round stop, a W-shaped band or an off-axis hole inside the
grid is just a different mask, and ``f_number = f / D`` refers to that
full width in every case. The wavefront over the grid is
``W(rho) = defocus_waves * rho^2 (+ opd_waves)`` with ``rho`` the radius
from the grid centre normalised to ``1`` at the grid half-width (the Seidel
defocus ``W20``; :func:`defocus_from_shift` converts an axial shift to it),
and the PSF is the Fraunhofer intensity of the pupil function

    ``PSF = | FFT{ pupil * exp(i 2 pi W) } |^2``

on a zero-padded ``M x M`` grid, ``M = n * oversample`` (rounded up to
even), centred on sample ``M//2`` and normalised to unit sum. The image
plane sample spacing is

    ``dx = lambda * N * n / M  ~= lambda * N / oversample``  [um]

— with *pixel_pitch_um* the fine PSF is **area-integrated** onto detector
pixels of that pitch (odd ``(K, K)``, centred on a pixel, unit sum), which
is what an image convolution needs; the pitch must not be finer than
``dx``. Without it the fine PSF is returned and ``dx`` is yours to compute
from the formula (an image cannot carry it).

Returns a float64 ``image2d``.

Ground truth it reproduces (measured, ``tests/test_optics.py``):

  * a circle filling a 64-sample grid, ``oversample = 16``: the first dark
    ring at ``1.2197 lambda N`` within 0.5 % of the Airy value (three
    wavelength / f-number pairs), and the same ring at the same
    *micrometre* radius within 5 % after binning to a pixel pitch of
    ``lambda N / 8`` (2.1 % measured — the parabolic minimum on a 9.8-pixel
    ring, not the binning) — so the pitch bookkeeping is right in physical
    units, not only in samples; the binned spot is centro-symmetric to
    1e-17 and correlates with :func:`airy_pattern` sampled at the same
    pitch at 0.99999 (0.9999 at ``lambda N / 4``, 0.9997 at ``lambda N / 3``);
  * pure defocus of a circular pupil: the on-axis intensity relative to the
    unaberrated peak is the closed-form ``[sin(pi W20)/(pi W20)]^2``
    (``0.405`` at half a wave, ``0`` at one wave — the dark centre of the
    one-wave defocused Airy spot), within 1 %;
  * ``defocus_waves = 0`` and a clear circular pupil is the Airy pattern of
    :func:`airy_pattern` to the sampling of the disc edge;
  * **the sign identity**: for a real pupil, ``-W`` is the complex
    conjugate of ``+W``, so ``PSF(-W)(x) = PSF(+W)(-x)`` exactly. The test
    pins it on a W-shaped band: the two PSFs are mirror images through the
    centre to 1e-12, and they are *not* equal to each other (the W pupil
    is asymmetric, so the direction of defocus is visible in the blur),
    while for the circle they are equal (a symmetric pupil cannot tell
    the sign). Rotating the W pupil by 90/180/270 degrees rotates the PSF
    the same way (checked, so the asymmetry is the pupil's, not the grid's).

**Raises** ``ValueError``: *pupil* is not 2-D, not square, smaller than 2x2,
over the size cap, complex, masked or non-finite; negative transmittance;
an all-opaque pupil (nothing to diffract, the normalisation would be
0/0); *opd_waves* not the same shape as *pupil*; non-finite
*defocus_waves*; non-positive or non-finite *wavelength_um* /
*f_number* / *pixel_pitch_um*; *oversample* outside ``[1, 64]``; an FFT
side over :data:`MAX_PUPIL_FFT`; **an aliased phase** — more than
:data:`MAX_WAVES_PER_SAMPLE` waves between neighbouring pupil samples (the
message says how many samples the grid needs); a pixel pitch finer than
the fine sample spacing (raise *oversample*).

Scalar Fraunhofer optics: no polarisation, no high-NA obliquity, no
pupil apodisation by the lens itself. The defocus term is the paraxial
``rho^2`` (see :func:`defocus_from_shift`). A pupil that reaches the grid
edge is fine (the zero padding is the field stop); a pupil *larger* than
the grid cannot be expressed — widen the grid and lower ``f_number``.

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

[fraunhofer_pattern](fraunhofer_pattern.md) · [pupil_blur](pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [polarization_demosaic](../polarization/polarization_demosaic.md) · [polarization_demosaic_color](../polarization/polarization_demosaic_color.md) · [illumination_uniformity](../illumination/illumination_uniformity.md) · [render_through_lens](../imaging_sim/render_through_lens.md) · [surface_defect](../scene/surface_defect.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [fourier_plane_filter](fourier_plane_filter.md) · [four_f_filter](four_f_filter.md) · [gaussian_beam](gaussian_beam.md) · [defocus_from_shift](defocus_from_shift.md) · [pupil_blur](pupil_blur.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
