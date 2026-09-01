---
op: dtof_depth
dim: photon
category: dtof
in: counts
out: measurement
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# dtof_depth — PHOTON `dtof` op

- **データ種**: `counts` → `measurement`
- **呼び出し**: `import photoncount; photoncount.dtof_depth(hist, bin_ps=100.0, mode='peak', offset_ps=0.0, subtract_background=False)` (または `opsphoton.get("dtof_depth")`)

## 使い方

Distance from a photon arrival-time histogram: ``d = c*t/2``.

Direct time-of-flight. The light travels to the target and back, so the
one-way distance is **half** the round-trip time times the speed of light.
*bin_ps* is the width of one time bin (a 100 ps bin is 1.50 cm of depth).

Four estimators, from crudest to sharpest:

  * ``"peak"`` — the centre of the fullest bin. Quantised to the bin grid;
    the error is uniform in ``+-half`` a bin (``+-0.75 cm`` at 100 ps).
  * ``"centroid"`` — the first moment of the whole histogram. Exact for a
    symmetric pulse *with no background*, and badly biased toward the middle
    of the window with one — pass ``subtract_background=True``.
  * ``"parabolic"`` — a parabola through the peak bin and its two neighbours.
    Sub-bin, cheap, and biased for a Gaussian pulse.
  * ``"gaussian"`` — the same parabola fitted to the **log** of those three
    samples, which is the exact vertex for a Gaussian pulse.

Measured on a **noiseless** simulated return at 2.4371 m (256 bins x 100 ps,
500 ps IRF), absolute error: ``peak`` 1.29 mm, ``centroid`` 4.4e-16 m,
``parabolic`` 0.067 mm, ``gaussian`` 9.4e-9 m — three orders of magnitude
between the crudest and the sharpest.

With **Poisson noise** (200 signal + 200 ambient photons, seed 0) the same
four give 13.7 mm, 146.5 mm (with ``subtract_background=True``), 8.5 mm and
8.0 mm. Two honest readings of that: once shot noise dominates the sub-bin
estimators buy about 1.6x, not three orders of magnitude, and the centroid
**collapses** because a median-subtracted ambient floor still leaves noise
across the whole window that drags the first moment toward the centre. Use
``"gaussian"`` or ``"parabolic"`` on noisy data; use ``"centroid"`` only when
the background is genuinely gone.

*offset_ps* is a **system delay to remove**: ``t_flight = t_measured -
offset_ps``, so a positive offset makes the answer *closer*. Returns the
distance in metres as a float.

**Raises** ``ValueError``: negative, non-finite, non-1-D or all-zero *hist*,
a non-positive *bin_ps*, an unknown *mode*, a non-finite *offset_ps*, a
**flat** histogram in a peak-based mode (``argmax`` would silently pick bin 0
and report the first bin's depth), a peak in the first or last bin with a
sub-bin *mode* (there is no neighbour to fit to — use ``"peak"``), a
degenerate three-sample fit, and — instead of returning a negative distance —
an *offset_ps* larger than the measured arrival time.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`dtof`)

[dtof_cube_simulate](dtof_cube_simulate.md) · [dtof_cube_depth](dtof_cube_depth.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
