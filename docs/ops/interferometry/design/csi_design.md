---
op: csi_design
dim: interferometry
category: design
in: 
out: table
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_design — INTERFEROMETRY `design` op

- **データ種**: `` → `table`
- **呼び出し**: `import interferometry; interferometry.csi_design(wavelength_um=0.6, bandwidth_um=0.1, z_range_um=12.0, width_px=640, height_px=480, min_visibility=0.3, step_divisor=8.0)` (または `opsinterferometry.get("csi_design")`)

## 使い方

The axial limits of a coherence-scanning setup, from the source spectrum.

The counterpart of :mod:`visiondesign` for the *vertical* axis: closed-form
answers to the questions asked before any hardware is bought — how localised
is the coherence peak, how finely must the scan step, how many planes is that,
and how much memory does the stack need.

Returned dict:

  * ``coherence_length_um`` — ``(4 ln2 / pi) * lambda^2 / delta_lambda``, the
    FWHM of ``|gamma(OPD)|`` for a Gaussian source (Born & Wolf 7.5.8). This
    is a property of the **optical path difference**. Verified in the tests
    against a direct numerical Fourier transform of the Gaussian source
    spectrum, at three (lambda, delta_lambda) settings, agreeing to 6
    significant figures.
  * ``envelope_fwhm_um`` — **half** of that: the width of the envelope along
    the **scan axis**, because the double pass makes ``OPD = 2z``. This is the
    one to hand to :func:`csi_signal_simulate` /
    :func:`csi_stack_simulate`, and the two are reported separately precisely
    because collapsing them into one name called "coherence length" is a clean
    factor-of-two error in every height the module produces. (It was one
    during development, and the numerical check above is what caught it.)
  * ``envelope_sigma_um`` — ``envelope_fwhm_um`` as a Gaussian sigma.
  * ``fringe_period_um`` — ``lambda/2``. The double pass halves it, and this
    is the number that makes phase-shifting ambiguous above ``lambda/4``.
  * ``max_z_step_um`` — ``lambda/4``. The Nyquist ceiling on the scan step;
    :func:`csi_peak_position` and :func:`csi_height_map` refuse at or above
    it.
  * ``recommended_z_step_um`` — ``lambda/step_divisor`` (default lambda/8, the
    usual 90-degree-per-plane choice), reported only if it is below the
    ceiling.
  * ``capture_range_um`` — the height interval over which the fringe contrast
    stays above *min_visibility* of its peak,
    ``2*sigma*sqrt(2 ln(1/min_visibility))``. Outside it a surface produces
    fringes too faint to locate, whatever the scan range is.
  * ``planes_per_envelope`` — how many scan planes fall inside
    ``envelope_fwhm_um`` at the recommended step. Below ~4 the three-point
    estimators have nothing to fit.
  * ``n_planes`` / ``stack_elements`` / ``stack_megabytes`` — the scan you are
    about to run and the float64 stack it produces, plus
    ``stack_within_cap`` against :data:`MAX_STACK_ELEMENTS`. This is the
    number people discover after waiting for the scan.
  * ``phase_unambiguous_step_um`` — ``lambda/4``, the largest surface step
    phase-shifting interferometry can measure without a fringe-order error.
    It is here so the two families can be compared in one place: coherence
    scanning has **no** such limit inside the scan range, and that is the
    entire reason to pay for the scan.

What this deliberately does **not** return is a vertical *repeatability* — a
"resolution" in nanometres. That number depends on the signal-to-noise ratio
and on which of :data:`ESTIMATORS` you use, the estimators do not even rank
the same way with and without noise, and an attempt to verify the textbook
"two surfaces closer than the coherence length are unresolved" criterion
against this module's own forward model **failed**: two reflectors 0.4
coherence lengths apart still produce two envelope maxima, because the two
interferograms interfere with each other and the envelope of a sum is not the
sum of the envelopes. Rather than assert a formula that its own tests
contradict, this operator returns only quantities it can verify, and the
measured estimator table lives in the module docstring.

**Raises** ``ValueError``: non-real / non-finite / string / bool parameters, a
non-positive wavelength / bandwidth / range, a *bandwidth_um* at or above
*wavelength_um* (a source whose spectrum reaches zero frequency is not a
quasi-monochromatic source and the coherence-length formula does not apply to
it), a *min_visibility* outside ``(0, 1)``, a *step_divisor* below 4 (which
would recommend a step at or past its own Nyquist ceiling), and pixel counts
outside ``[1, 65536]``.

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`design`)

—

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
