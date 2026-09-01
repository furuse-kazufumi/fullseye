---
op: csi_signal_simulate
dim: interferometry
category: simulate
in: 
out: sweep
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_signal_simulate — INTERFEROMETRY `simulate` op

- **データ種**: `` → `sweep`
- **呼び出し**: `import interferometry; interferometry.csi_signal_simulate(surface_um=6.0, z_start_um=0.0, z_step_um=0.05, n_planes=241, wavelength_um=0.6, envelope_fwhm_um=2.8, envelope_sigma_um=None, bias=0.5, amplitude=0.4, reflectivity=1.0, noise=0.0, seed=0)` (または `opsinterferometry.get("csi_signal_simulate")`)

## 使い方

Synthesise the z-scan interferogram of one pixel over a known surface height.

The coherence-scanning forward model, and the reason every other operator here
has an exact answer to be checked against::

    I(z) = bias + amplitude*reflectivity * exp(-(z-z0)^2 / 2 sigma^2)
                                         * cos(4*pi*(z-z0)/wavelength)

with ``z0 = surface_um``. The **4** is the double pass — light goes down to the
surface and back, so one fringe is ``wavelength/2`` of *height*, not a whole
wavelength. Getting that factor wrong is a clean 2x in every height this
module produces, which is why it is written out here rather than hidden in a
constant.

surface_um:           the true surface height ``z0``, in the scan's own
                      coordinate. Need not land on a scan plane — the
                      sub-step case is the interesting one and the tests use
                      it deliberately.
z_start_um/z_step_um/n_planes: the scan grid,
                      ``z_k = z_start_um + k*z_step_um``.
wavelength_um:        mean wavelength of the source.
envelope_fwhm_um:     the FWHM of the envelope **along the scan axis**. Give
                      this *or* ``envelope_sigma_um``, never both. It is
                      **half** the source coherence length, because the
                      double pass makes OPD = 2z;
                      :func:`csi_design` returns both under separate names
                      for exactly that reason.
bias/amplitude:       the intensity pedestal ``a`` and fringe amplitude ``b``.
reflectivity:         per-pixel scale on the fringe amplitude (>= 0). It
                      scales the envelope and therefore
                      :func:`csi_contrast_map`, and — this is the honest part
                      — it does **not** move the envelope peak, so it does not
                      bias :func:`csi_peak_position`. A *spatially varying*
                      reflectivity biases nothing either; what does bias the
                      centroid is where the peak sits in the window, and that
                      is documented on :func:`csi_peak_position`.
noise:                additive Gaussian sigma (0 = the exact model).
seed:                 integer seed for that noise (no ``None``).

Returns a 1-D float64 array of ``n_planes`` intensities.

Ground truth: with ``noise=0`` and the surface centred in the scan, the
``"gaussian"`` estimator of :func:`csi_peak_position` returns *surface_um* to
1.43e-07 um over sub-step offsets, and to 2.9e-14 um when the envelope is
given analytically instead of through the Hilbert transform (both pinned in
the tests).

**Raises** ``ValueError``: a non-real / non-finite / string / bool parameter,
a non-positive ``z_step_um`` / ``wavelength_um`` / envelope width, a negative
``bias`` / ``amplitude`` / ``reflectivity`` / ``noise``, ``n_planes`` outside
``[3, MAX_SCAN_POINTS]``, a ``z_step_um`` at or past the ``wavelength_um/4``
Nyquist ceiling, and a *surface_um* outside the scan range (which is the case
a real instrument reports as "no surface found", not as a height).

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

[csi_stack_simulate](csi_stack_simulate.md) · [chromatic_confocal_simulate](chromatic_confocal_simulate.md)

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
