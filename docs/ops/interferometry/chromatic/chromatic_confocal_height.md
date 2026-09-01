---
op: chromatic_confocal_height
dim: interferometry
category: chromatic
in: sweep
out: measurement
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# chromatic_confocal_height — INTERFEROMETRY `chromatic` op

- **データ種**: `sweep` → `measurement`
- **呼び出し**: `import interferometry; interferometry.chromatic_confocal_height(spectrum, wavelength_start_nm=500.0, wavelength_step_nm=0.5, dispersion_um_per_nm=0.2, reference_wavelength_nm=600.0, mode='gaussian', subtract_background=True, min_visibility=0.3, min_peak_bins=2.0, max_carrier_fraction=0.1)` (または `opsinterferometry.get("chromatic_confocal_height")`)

## 使い方

Surface height from one confocal return spectrum — the wavelength *is* the height.

The inverse of :func:`chromatic_confocal_simulate`. Find the peak wavelength
of the spectrum, then::

    height = (lambda_peak - reference_wavelength_nm) * dispersion_um_per_nm

No scan, no moving parts, one spectrum per point — which is why this family
reaches sampling rates a z scan cannot, and why it is limited to the axial
range the objective's chromatic spread covers.

The four *mode* estimators are :data:`ESTIMATORS`, identical to
:func:`csi_peak_position`'s and sharing its implementation. ``"gaussian"`` is
exact for a Gaussian confocal response (measured 0.0e+00 to 3.6e-15 um),
*including when the peak is narrower than one bin and when it sits two bins
from the band edge* — the logarithm of a sampled Gaussian is a parabola
whatever its width, and the fit is local. That exactness is a property of
noiseless data only, which is what *min_peak_bins* is about.

spectrum:             1-D non-negative intensities across the spectrometer.
wavelength_start_nm / wavelength_step_nm: the spectrometer axis.
dispersion_um_per_nm: the axial chromatic calibration constant.
reference_wavelength_nm: the wavelength that focuses at height 0.
subtract_background:  subtract the spectrum's median before locating the peak.
                      On by default because a pedestal drags the ``centroid``
                      estimator toward the middle of the band exactly as it
                      drags the CSI centroid toward the middle of the scan.
min_visibility:       refuse a spectrum whose peak prominence
                      ``(max-median)/max`` is below this — a flat spectrum has
                      no focused wavelength and its argmax is noise.
min_peak_bins:        refuse a peak whose full width at half maximum spans
                      fewer than this many bins. Undersampling does not break
                      the noiseless algebra, but it destroys its noise
                      rejection. Measured at 1 % noise (1000 peak counts,
                      sigma_n = 10, 100 trials), RMS error in locating the
                      peak against the number of bins across its FWHM:

                          0.5 bins -> 0.256 nm
                          1.0 bins -> 0.137 nm
                          2.0 bins -> 0.010 nm
                          4.0 bins -> 0.030 nm
                          8.0 bins -> 0.118 nm

                      Two bins is the optimum and a half-bin peak is **25x**
                      worse, from a spectrum that looks perfectly healthy —
                      hence the default of 2. Note the curve turns around
                      again: a very *broad* peak is also bad, because the
                      three-point fit then sits where the curvature is tiny
                      and noise dominates it. "More samples is better" is
                      false here and this operator does not claim it. Set to
                      0 to disable the check if you know your data is
                      clean.
max_carrier_fraction: refuse a spectrum whose dominant alternating component
                      sits above this fraction of the Nyquist frequency. A
                      confocal response is one smooth peak and all of its AC
                      content is at low frequency (measured: dominant bin at
                      0.010 of Nyquist for a 4 nm peak, 0.010 for a 1 nm peak,
                      0.015 with 5 % noise). A **z-scan interferogram** put in
                      here instead sits at 0.333 — its fringe carrier — and
                      without this check its carrier's argmax would come back
                      as a focused wavelength and therefore as a plausible,
                      finite, wrong height. This is the guard that lets the
                      two 1-D families share one type pool safely. Pass 0 to
                      disable.

Returns the height as a float, in micrometres. It may be negative — a height
is signed, unlike a time-of-flight distance.

**Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite /
complex / masked *spectrum*, a *spectrum* over :data:`MAX_SCAN_POINTS`
elements (checked before the float64 promotion), any **negative** intensity
(a spectrometer cannot read negative light; clip explicitly if this is a
pre-subtracted spectrum), a non-positive step / dispersion / reference
wavelength, an unknown *mode*, a peak prominence below *min_visibility*, a
peak narrower than *min_peak_bins*, and a peak on the **first or last bin**
(the surface is outside the calibrated axial range, which is
``+-(band_nm/2) * dispersion_um_per_nm`` about the reference).

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`chromatic`)

—

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
