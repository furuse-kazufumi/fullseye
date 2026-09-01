---
op: csi_height_map
dim: interferometry
category: surface
in: zscan
out: depth
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_height_map — INTERFEROMETRY `surface` op

- **データ種**: `zscan` → `depth`
- **呼び出し**: `import interferometry; interferometry.csi_height_map(stack, z_step_um=0.05, z_start_um=0.0, wavelength_um=0.6, mode='gaussian', remove_bias=True, min_visibility=0.3, max_edge_envelope=0.05, carrier_tolerance=2.0, on_invalid='raise', fill_value=nan)` (または `opsinterferometry.get("csi_height_map")`)

## 使い方

Height map from a ``(Z, H, W)`` coherence-scanning stack — the CSI inversion.

The per-pixel :func:`csi_peak_position`, vectorised. **The scan axis is
first**; see :func:`csi_stack_simulate` for why that is checked rather than
inferred.

A pixel is *invalid* when any of three things is true, and all three are the
same trap in different shapes — each would otherwise yield a finite, plausible,
wrong height:

  1. its envelope prominence is below *min_visibility* — no fringes ever
     formed there (a hole, a dark or specular-dropout pixel, a facet tilted
     out of the aperture);
  2. its envelope peaks on the first or last plane — the surface is at or past
     the end of the scan;
  3. its envelope is still above *max_edge_envelope* of its peak at the ends
     of the scan — most of the coherence peak is outside the scan even though
     the argmax is on an interior plane. This is the one that has no natural
     alarm: measured, a surface at 0.500 um with an edge level of 0.639 reads
     **0.119 um** and nothing else about the result looks wrong. See
     :func:`_edge_level`.

What happens then is a decision, not a default:

  * ``on_invalid="raise"`` (**the default**) — raise, naming how many pixels
    failed which of the three checks. Fail-closed: a height map with silently
    wrong pixels in it is worse than no height map.
  * ``on_invalid="fill"`` — write *fill_value* (default NaN) at those pixels
    and return. Opt in to this when you intend to mask afterwards; a NaN
    height poisons every downstream reduction, which is precisely why it is
    not the default.

There is deliberately no third option that quietly reports the boundary plane.

Returns a float64 ``(H, W)`` height map, in the units of *z_start_um* /
*z_step_um*.

Ground truth (measured, 32x32 pixels, 241 planes x 0.05 um, 0.60 um
wavelength, 2.83 um envelope FWHM). On a tilted plane spanning **5.0-7.0 um**,
i.e. comfortably inside a 0-12 um scan, the RMS height error is 1.42e-02 um
for ``"peak"``, 3.81e-05 um for ``"centroid"``, 4.02e-06 um for
``"parabolic"`` and 2.08e-06 um for ``"gaussian"``. Widen the same plane to
**2.0-10.0 um** — pixels now within 2 um of the ends of the scan — and the
errors become 1.91e-02 / 5.98e-02 / 7.06e-03 / 7.06e-03 um: the local fits
lose three decades and the centroid loses four, entirely to envelope
truncation at the scan ends. Accuracy here is a property of the *scan layout*,
not of the estimator, and this is the number to look at when a real
measurement disappoints.

On that same surface, phase-shifting interferometry via :mod:`fringe` is exact
below a lambda/4 = 0.15 um step and wrong by exact multiples of
lambda/2 = 0.30 um above it.

**Raises** ``ValueError``: a non-3-D stack, fewer than 3 planes, an empty
spatial extent, a stack over :data:`MAX_STACK_ELEMENTS` (checked before the
float64 promotion), a non-finite / complex / masked stack, an unknown *mode*
or *on_invalid*, a *min_visibility* / *max_edge_envelope* outside ``[0, 1]``,
a *z_step_um* at or past the ``wavelength_um/4`` Nyquist ceiling, a
non-numeric *fill_value*, and — under the default ``on_invalid="raise"`` —
any invalid pixel.

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[csi_stack_simulate](../simulate/csi_stack_simulate.md)

## 同カテゴリ(`surface`)

[csi_contrast_map](csi_contrast_map.md)

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
