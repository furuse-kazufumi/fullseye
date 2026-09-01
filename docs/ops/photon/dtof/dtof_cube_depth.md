---
op: dtof_cube_depth
dim: photon
category: dtof
in: histcube
out: depth
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# dtof_cube_depth — PHOTON `dtof` op

- **データ種**: `histcube` → `depth`
- **呼び出し**: `import photoncount; photoncount.dtof_cube_depth(cube, bin_ps=100.0, mode='peak', offset_ps=0.0, min_counts=1.0, empty_value=0.0, subtract_background=False)` (または `opsphoton.get("dtof_cube_depth")`)

## 使い方

Depth map from a ``(H, W, T)`` photon histogram cube — the dToF inversion.

The array version of :func:`dtof_depth`, with the same four *mode* estimators
and the same ``t_flight = t_measured - offset_ps`` sign convention. The time
axis is **last**: a ``(D, H, W)`` voxel volume passed in here would be read as
``W`` time bins and return a plausible-wrong depth map, so the shape is
checked and the error message says exactly that.

Pixels whose total counts are below *min_counts* — and, in the peak-based
modes, pixels whose histogram is exactly **flat** (no peak to find, so
``argmax`` would report bin 0 for every one of them) — are set to
*empty_value* (default 0.0, a value no real return can have since
``d > 0``). Set
``empty_value=float('nan')`` if you would rather propagate a NaN — that is an
opt-in, never the default, because a NaN depth map silently poisons every
downstream reduction.

Where a sub-bin *mode* cannot be applied to a pixel — the peak is in the
first or last bin, or the three samples are flat / non-positive for the log
fit — that pixel **falls back to the bin-centre (``"peak"``) estimate**. A
per-pixel exception would be useless on a megapixel cube; the fallback is
documented here and pinned in the tests, and it degrades to the coarser
estimator rather than to a wrong one.

Ground truth: on a noiseless simulated cube of a tilted plane from 1.0 to
3.0 m (32x32 pixels, 256 bins x 100 ps, 500 ps IRF) the RMS depth error is
4.39 mm for ``"peak"``, 3.2e-16 m for ``"centroid"``, 0.114 mm for
``"parabolic"`` and 1.6e-8 m for ``"gaussian"``. With Poisson noise (20
signal + 5 ambient photons per pixel, seed 0) the same four give 19.9 mm,
164.8 mm (background subtracted), 18.7 mm and 19.2 mm — at 20 photons the
estimator choice is worth about 6%, and the centroid is 8x worse than doing
nothing clever at all.

Returns a float64 ``(H, W)`` depth map in metres.

**Raises** ``ValueError``: a cube that is not 3-D / has fewer than 2 time
bins / holds negative counts / exceeds :data:`MAX_CUBE_ELEMENTS`, a
non-positive *bin_ps*, an unknown *mode*, a negative *min_counts*, a
non-finite *empty_value* other than NaN, and — instead of returning negative
distances — an *offset_ps* that exceeds the measured arrival time of any
valid pixel (a mis-signed or mis-scaled calibration delay).

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[dtof_cube_simulate](dtof_cube_simulate.md)

## 同カテゴリ(`dtof`)

[dtof_depth](dtof_depth.md) · [dtof_cube_simulate](dtof_cube_simulate.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
