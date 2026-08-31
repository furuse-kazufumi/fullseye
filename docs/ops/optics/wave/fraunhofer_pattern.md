---
op: fraunhofer_pattern
dim: optics
category: wave
in: image2d
out: image2d
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# fraunhofer_pattern — OPTICS `wave` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import optics; optics.fraunhofer_pattern(aperture, wavelength_um=0.55, distance_mm=100.0, pixel_pitch_um=10.0)` (または `opsoptics.get("fraunhofer_pattern")`)

## 使い方

Far-field (Fraunhofer) diffraction intensity of an aperture.

In the far field the diffracted amplitude is the Fourier transform of the
aperture transmittance, so the intensity is
``|FFT{aperture}|^2`` (fftshifted, DC at the centre) normalised to a peak of
exactly 1.0.

Returns a float64 image with the same shape as *aperture*.

**The output plane is sampled differently from the input plane** — this is
the trap in every FFT diffraction routine. The observation-plane pitch is
``lambda*z/(N_pixels*input_pitch)``; with the defaults
(``0.55 um``, ``100 mm``, ``10 um``) and a 64-pixel aperture that is
``0.55*100000/(64*10) = 85.9 um`` per pixel. The value is not returned as
an image cannot carry it; compute it from the formula when you need
absolute positions.

A ``RuntimeWarning`` is emitted when the Fresnel number
``N_F = a^2/(lambda*z)`` (with ``a`` the aperture's support radius) is not
below 1 — i.e. when you are asking for a far-field pattern at a distance
where the near field still dominates. The result is still returned, because
the Fourier relation is exactly what was asked for; the warning says the
*physics*, not the arithmetic, is out of range.

Ground truth it reproduces (measured): a rectangular slit ``w`` pixels wide
in an ``N``-pixel array puts its diffraction zeros exactly on the DFT bins
``k*N/w``; a 4-pixel-wide slit in a 64-pixel array has **exactly** 0.0 at
bins +/-16 and +/-32 from DC (the DFT of a boxcar vanishes there to the
last bit, not merely to rounding); the pattern of a centred symmetric
aperture is symmetric to 2.2e-16.

**Raises** ``ValueError``: *aperture* is not 2-D / smaller than 2x2 / over
the size cap / complex / masked / non-finite; a negative transmittance
(that is not an aperture); an **opaque** aperture (everything zero — an
opaque screen diffracts nothing and the normalisation would be 0/0);
non-positive or non-finite *wavelength_um* / *distance_mm* /
*pixel_pitch_um*.

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

[psf_to_mtf](../imaging/psf_to_mtf.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [gaussian_beam](gaussian_beam.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
