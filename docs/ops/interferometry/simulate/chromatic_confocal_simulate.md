---
op: chromatic_confocal_simulate
dim: interferometry
category: simulate
in: 
out: sweep
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# chromatic_confocal_simulate — INTERFEROMETRY `simulate` op

- **データ種**: `` → `sweep`
- **呼び出し**: `import interferometry; interferometry.chromatic_confocal_simulate(surface_um=0.0, wavelength_start_nm=500.0, wavelength_step_nm=0.5, n_bins=401, dispersion_um_per_nm=0.2, reference_wavelength_nm=600.0, peak_fwhm_nm=4.0, peak_counts=1000.0, background=10.0, noise=0.0, seed=0)` (または `opsinterferometry.get("chromatic_confocal_simulate")`)

## 使い方

Synthesise the confocal return spectrum of a surface at a known height.

A chromatic objective is built to have axial colour on purpose: each
wavelength focuses at a different height, so only the wavelength focused *on
the surface* passes the confocal pinhole. The spectrometer therefore sees a
peak whose **wavelength is the height**::

    lambda_peak = reference_wavelength_nm
                + (surface_um - 0) / dispersion_um_per_nm

i.e. ``surface_um = (lambda_peak - reference_wavelength_nm) *
dispersion_um_per_nm``, which is what :func:`chromatic_confocal_height`
inverts. The peak is modelled as a Gaussian of FWHM *peak_fwhm_nm* on a flat
*background* pedestal.

surface_um:                 true height (0 = the reference wavelength focuses
                            exactly on it). May be negative — unlike a
                            time-of-flight distance, a height is signed.
wavelength_start_nm / wavelength_step_nm / n_bins: the spectrometer axis.
dispersion_um_per_nm:       the axial chromatic dispersion, height per
                            nanometre. This is the calibration constant and
                            the units are in the name for a reason: a
                            per-micrometre reading of it is a 1000x error in
                            the height.
peak_fwhm_nm:               spectral width of the confocal response.
peak_counts / background:   peak height above, and level of, the pedestal.
noise / seed:               additive Gaussian sigma and its integer seed.

Returns a 1-D float64 spectrum of ``n_bins`` non-negative intensities
(clipped at 0, because a spectrometer cannot read negative light — and the
clip is stated here rather than left as a surprise).

Ground truth: with ``noise=0`` the ``"gaussian"`` estimator recovers
*surface_um* **exactly** (measured 0.0e+00 to 3.6e-15 um over heights from
-15 to +18 um), at any peak width and even with the peak two bins from the
band edge, because the logarithm of a sampled Gaussian is exactly a parabola
and the three-point fit is *local* — there is no Hilbert transform here, so
the truncation failure that limits the coherence-scanning side does not exist
on this one (pinned in the tests).

**Raises** ``ValueError``: non-real / non-finite / string / bool parameters, a
non-positive step / width / dispersion, negative *peak_counts* /
*background* / *noise*, *n_bins* outside ``[3, MAX_SCAN_POINTS]``, and a
*surface_um* whose wavelength falls outside the spectrometer band (the
out-of-range case a real probe reports as "no surface").

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`sweep` を入力に取れる)

[csi_envelope](../envelope/csi_envelope.md) · [csi_peak_position](../locate/csi_peak_position.md) · [chromatic_confocal_height](../chromatic/chromatic_confocal_height.md)

## 同カテゴリ(`simulate`)

[csi_signal_simulate](csi_signal_simulate.md) · [csi_stack_simulate](csi_stack_simulate.md)

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
