---
op: csi_peak_position
dim: interferometry
category: locate
in: sweep
out: measurement
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_peak_position — INTERFEROMETRY `locate` op

- **データ種**: `sweep` → `measurement`
- **呼び出し**: `import interferometry; interferometry.csi_peak_position(signal, z_step_um=0.05, z_start_um=0.0, wavelength_um=0.6, mode='gaussian', remove_bias=True, min_visibility=0.3, max_edge_envelope=0.05, carrier_tolerance=2.0)` (または `opsinterferometry.get("csi_peak_position")`)

## 使い方

Surface height from one z-scan: the position of the coherence envelope peak.

This is the operator the whole module is for. Unlike a phase, an envelope has
no period, so there is no fringe order to get wrong and no unwrapping to do —
the height is simply where the fringe contrast is greatest, and it is correct
for a surface step of any size that stays inside the scan.

*mode* picks the estimator. Measured on the reference scan (0.60 um
wavelength, 2.83 um envelope FWHM, 0.05 um step, surface centred, four
sub-step offsets), and then again with 1 % additive noise over 200 trials:

  * ``"peak"``      — the scan plane with the largest envelope. Noiseless
                      2.50e-02 um, which is exactly the step quantisation
                      ``z_step_um/2``. Noisy RMS 0.1395 um.
  * ``"centroid"``  — the centroid of the whole envelope. Noiseless
                      4.55e-07 um, and the **best estimator under noise**
                      (RMS 0.0219 um, 6.4x better than the local fits, because
                      it averages 241 planes instead of looking at 3 samples
                      around an argmax that noise moves). Its own failure is
                      *window bias*: it is pulled toward the centre of the
                      scan. Measured on a 12 um scan, a surface at 2 um reads
                      **+0.189 um** high with no noise at all and **+0.873 um**
                      high with a 2 % noise floor; at 10 um the same bias runs
                      the other way (-0.189 / -0.851). Centre the scan on the
                      surface, or use a local estimator.
  * ``"parabolic"`` — three-point parabola on the envelope. 4.21e-06 um
                      noiseless, 0.1403 um noisy.
  * ``"gaussian"``  — three-point parabola on the **log** of the envelope,
                      which is algebraically exact for a Gaussian envelope:
                      1.43e-07 um noiseless — and the floor there is the
                      Hilbert envelope's own 1.8e-07 error, not the fit, since
                      the same fit on the analytic envelope is exact to 3e-14
                      — and 0.1403 um noisy. The default.

There is no single best estimator here and this module does not pretend
otherwise: ``"gaussian"`` is 30x better than ``"parabolic"`` on clean data and
indistinguishable from it on noisy data, where ``"centroid"`` beats both by
6.4x — and ``"centroid"`` is the only one of the four whose bias grows with
how far the surface sits from the middle of the scan.

signal:            1-D scan intensities.
z_step_um:         spacing of the scan planes. Must be below the
                   ``wavelength_um/4`` Nyquist ceiling — see
                   :func:`csi_design`.
z_start_um:        height of plane 0.
wavelength_um:     mean wavelength, used only for the Nyquist check.
mode:              one of :data:`ESTIMATORS`.
remove_bias:       passed to :func:`csi_envelope`.
min_visibility:    refuse a scan whose envelope prominence
                   ``(max - median)/max`` is below this. A real interferogram
                   scores 0.958; the chain fuzzer's generic ``signal`` (a
                   sinusoid plus 10 % noise, no coherence envelope at all)
                   scores 0.241 and is refused; a constant scores 0.000. The
                   argmax of a flat envelope is a plane noise chose, not a
                   surface.
max_edge_envelope: refuse a scan whose envelope has not decayed by the ends,
                   ``max(env[0], env[-1]) / max(env) > this``. See
                   :func:`_edge_level` for the measured table this default of
                   0.05 comes from, and for the silent failure it exists to
                   catch — a surface at 0.500 um read as 0.119 um, from an
                   envelope peaking on an *interior* plane so that no
                   first-or-last-plane check fires. Pass 1.0 to disable the
                   check and accept that reading.
carrier_tolerance: refuse a scan whose fringe carrier is more than this
                   factor away from the ``2/wavelength_um`` the stated
                   wavelength implies. This is the **unit guard**, and it is
                   the only thing standing between a nanometre/micrometre
                   swap and a wrong answer: *wavelength_um* is otherwise used
                   only for the Nyquist ceiling, so writing 600 instead of
                   0.6 silently disables that ceiling while changing nothing
                   in the returned height (measured: the same 6.025 um either
                   way). The default factor of 2 is deliberately loose — the
                   measured ratio on real scans is 0.996 and stays there
                   under 10 % noise, a truncated envelope and a 0.3 um
                   envelope — because it exists to catch a factor of 1000,
                   not to re-derive the wavelength. Scans shorter than 16
                   planes skip it (the FFT cannot resolve the carrier: the
                   ratio is 0.667 at 9 planes). Pass 0 to disable.

Returns the height as a float, in the same units as *z_start_um* /
*z_step_um*.

**Raises** ``ValueError``: everything :func:`csi_envelope` raises, plus an
unknown *mode*, a non-positive *z_step_um* / *wavelength_um*, a *z_step_um* at
or past the Nyquist ceiling, an envelope prominence below *min_visibility*, an
envelope edge level above *max_edge_envelope*, and an envelope peaking on the
**first or last plane** (the surface is at or beyond the end of the scan).
Those last three are the same trap in three shapes: each would otherwise
return a height that is finite, plausible, and wrong.

Honest scope of the boundary check: it is a **backstop, not the workhorse**.
The analytic-signal magnitude of a finite record is suppressed at its own
endpoints, so a surface at ``z = 0.0`` — or at ``-3.0 um``, entirely outside
the scan — comes back with its envelope maximum on plane **1**, one plane
inside the boundary, and the first-or-last-plane test does not fire. It fires
for a genuinely monotone input (a ramp, an impulse on the first sample) and
for a dead pixel. Everything else is caught by *max_edge_envelope*, and the
tests pin both halves of that statement.

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

## 同カテゴリ(`locate`)

—

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
