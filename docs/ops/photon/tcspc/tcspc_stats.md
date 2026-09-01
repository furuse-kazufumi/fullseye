---
op: tcspc_stats
dim: photon
category: tcspc
in: counts
out: table
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# tcspc_stats — PHOTON `tcspc` op

- **データ種**: `counts` → `table`
- **呼び出し**: `import photoncount; photoncount.tcspc_stats(hist, bin_ps=100.0)` (または `opsphoton.get("tcspc_stats")`)

## 使い方

Descriptors of an arrival-time histogram: peak, centroid, width, background.

Returns a dict: ``total_counts`` · ``peak_bin`` (int) · ``peak_counts`` ·
``peak_time_ps`` (the **centre** of the peak bin, ``(k + 0.5)*bin_ps``) ·
``centroid_ps`` (the first moment over the whole histogram, background
included — run :func:`tcspc_background_subtract` first if that matters) ·
``fwhm_ps`` (full width at half maximum *above the background*, by linear
interpolation of the two half-crossings around the peak) ·
``background_per_bin`` (the median bin, the same robust estimate
:func:`tcspc_background_subtract` uses) · ``signal_counts``
(``total - background*bins``) · ``sbr`` (signal-to-background ratio, or
``None`` when the background estimate is 0) · ``n_bins`` · ``window_ps``.

``fwhm_ps`` is ``None`` — never a fabricated number — when the profile does
not cross the half-maximum on both sides of the peak, which is exactly what a
monotone fluorescence decay does (its peak is bin 0). A ``None`` here means
"this histogram has no width in the FWHM sense", not "the measurement
failed".

Ground truth: for a noiseless Gaussian return of FWHM 500 ps, ``centroid_ps``
matches the analytic ``2d/c`` to 1.8e-12 ps. ``fwhm_ps`` comes back as 508.41
at 100 ps bins and 503.07 at 50 ps bins — the linear interpolation between
two bins on either flank systematically **overestimates** a Gaussian's width,
by 1.7% and 0.6% respectively, and the error shrinks with the bin width.
That bias is a property of the estimator; it is reported here rather than
hidden behind a "500" that only holds in the continuum limit.

**Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
non-positive *bin_ps*, and an all-zero histogram (no photon arrived, so
there is no arrival time; the centroid would be ``0/0``).

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`tcspc`)

[tcspc_simulate](tcspc_simulate.md) · [tcspc_irf_convolve](tcspc_irf_convolve.md) · [tcspc_background_subtract](tcspc_background_subtract.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
