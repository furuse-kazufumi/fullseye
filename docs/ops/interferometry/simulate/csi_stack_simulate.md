---
op: csi_stack_simulate
dim: interferometry
category: simulate
in: depth
out: zscan
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_stack_simulate — INTERFEROMETRY `simulate` op

- **データ種**: `depth` → `zscan`
- **呼び出し**: `import interferometry; interferometry.csi_stack_simulate(height_um, z_start_um=0.0, z_step_um=0.05, n_planes=241, wavelength_um=0.6, envelope_fwhm_um=2.8, envelope_sigma_um=None, bias=0.5, amplitude=0.4, reflectivity=None, noise=0.0, seed=0)` (または `opsinterferometry.get("csi_stack_simulate")`)

## 使い方

Synthesise the ``(Z, H, W)`` scan stack an interference microscope records.

The per-pixel version of :func:`csi_signal_simulate`: every pixel of the
*height_um* map gets its own coherence envelope centred on its own height, on
a shared scan grid. **The scan axis is FIRST** — a stack is what a camera
streams while the objective moves, one frame per plane — which is the same
layout as a ``video`` ``(T, H, W)`` and *not* the ``(H, W, T)`` of a
:func:`photoncount.dtof_cube_simulate` histogram cube.

That resemblance to ``video`` is not cosmetic and it is measured, not assumed:
handing a translating-grating clip to :func:`csi_height_map` does **not**
raise, it returns a height map (see the type note in :mod:`opsinterferometry`
for the numbers). The registry therefore declares a separate ``zscan`` type.

height_um:     2-D ``(H, W)`` map of true surface heights, in the scan's own
               coordinate. Every height must lie inside the scan range.
reflectivity:  optional ``(H, W)`` map of per-pixel fringe-amplitude scale
               (>= 0). ``None`` = uniform 1. A pixel with reflectivity 0 has
               no fringes at all and :func:`csi_height_map` will refuse it
               rather than report the first plane.
(the remaining parameters are :func:`csi_signal_simulate`'s, applied to every
pixel; ``noise`` is sampled once for the whole stack from *seed*.)

Returns a float64 ``(n_planes, H, W)`` stack.

Ground truth: with ``noise=0``, ``csi_height_map(stack, ..., mode="gaussian")``
returns *height_um* with an RMS error of **2.08e-06 um** over a tilted plane
spanning 5.0-7.0 um of a 0-12 um scan, and the per-pixel result is bit-for-bit
identical to running :func:`csi_peak_position` on each column separately
(both pinned in the tests). Widening the same plane to 2.0-10.0 um degrades
that to 7.06e-03 um — envelope truncation at the scan ends, not the
estimator.

**Raises** ``ValueError``: everything :func:`csi_signal_simulate` raises, plus
a non-2-D / empty *height_um*, a *reflectivity* that is negative or a
different shape, any height outside the scan range, and a stack over
:data:`MAX_STACK_ELEMENTS` (``n_planes*H*W`` grows fast — 241 planes of
256x256 is 1.9x the cap). The element cap is applied **before** the float64
promotion of *height_um*, not after.

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`zscan` を入力に取れる)

[csi_height_map](../surface/csi_height_map.md) · [csi_contrast_map](../surface/csi_contrast_map.md)

## 同カテゴリ(`simulate`)

[csi_signal_simulate](csi_signal_simulate.md) · [chromatic_confocal_simulate](chromatic_confocal_simulate.md)

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
