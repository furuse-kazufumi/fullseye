---
op: tcspc_irf_convolve
dim: photon
category: tcspc
in: counts
out: counts
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# tcspc_irf_convolve — PHOTON `tcspc` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `import photoncount; photoncount.tcspc_irf_convolve(hist, bin_ps=100.0, irf_fwhm_ps=200.0, truncate=4.0)` (または `opsphoton.get("tcspc_irf_convolve")`)

## 使い方

Blur an arrival-time histogram by the instrument response (timing jitter).

The temporal analogue of a PSF convolution: a detector's timing uncertainty
(SPAD jitter + TDC quantisation + laser pulse width) smears every arrival
time by the instrument response function, here a Gaussian of full width at
half maximum *irf_fwhm_ps*. The kernel is the **exact bin integral** of that
Gaussian (erf differences), normalised to sum 1, truncated at
``+-truncate*sigma`` and forced to odd length so the convolution is centred.

Ground truth: convolving a unit spike in the middle of a 256-bin window with
``irf_fwhm_ps = 500`` at ``bin_ps = 50`` leaves the centroid **exactly**
where it was (measured shift 0.0 ps — the kernel is symmetric) and gives a
profile whose measured FWHM is 501.22 ps. That 0.24% excess over 500 is the
*measurement*, not the kernel: :func:`tcspc_stats` finds the half-maximum
crossings by linear interpolation between bins, which slightly overestimates
the width of a Gaussian.

Total counts are preserved *except* at the window edges, where
``mode='same'`` discards the tail that falls outside — measured loss exactly
0 for that centred spike, but a genuine loss for a pulse within a few sigma
of either end.

Returns a float64 1-D histogram of the same length as *hist*.

**Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, a
non-positive *bin_ps* / *irf_fwhm_ps* / *truncate*, an IRF sigma below
1e-3 bins (the kernel would be a delta and the op a no-op — say so instead
of pretending to blur), and a kernel that would be longer than the
:data:`MAX_BINS` cap.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`counts` を入力に取れる)

[tcspc_coates_correct](../spad/tcspc_coates_correct.md) · [tcspc_background_subtract](tcspc_background_subtract.md) · [tcspc_stats](tcspc_stats.md) · [dtof_depth](../dtof/dtof_depth.md) · [lifetime_fit](../lifetime/lifetime_fit.md) · [lifetime_phasor](../lifetime/lifetime_phasor.md)

## 同カテゴリ(`tcspc`)

[tcspc_simulate](tcspc_simulate.md) · [tcspc_background_subtract](tcspc_background_subtract.md) · [tcspc_stats](tcspc_stats.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
