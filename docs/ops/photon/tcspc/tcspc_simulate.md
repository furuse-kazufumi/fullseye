---
op: tcspc_simulate
dim: photon
category: tcspc
in: 
out: counts
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# tcspc_simulate — PHOTON `tcspc` op

- **データ種**: `` → `counts`
- **呼び出し**: `import photoncount; photoncount.tcspc_simulate(distance_m=3.0, bins=256, bin_ps=100.0, signal_photons=50.0, ambient_photons=20.0, irf_fwhm_ps=200.0, seed=0, noise=True)` (または `opsphoton.get("tcspc_simulate")`)

## 使い方

Synthesise a single-pixel photon arrival-time histogram with a known answer.

The generative model of a direct time-of-flight (dToF) / TCSPC measurement::

    lambda_k = signal_photons * P(pulse in bin k) + ambient_photons / bins
    N_k      ~ Poisson(lambda_k)

where the pulse is a Gaussian of full width at half maximum *irf_fwhm_ps*
centred at the round-trip time ``t0 = 2*distance_m/c``, and ``P(pulse in bin
k)`` is its **exact** integral over the bin (an erf difference, not a
midpoint sample) — so with ``noise=False`` the returned histogram is an
analytic ground truth, not an approximation of one. *ambient_photons* is the
total background (sunlight, dark counts) spread uniformly over the window.

``noise=False`` returns ``lambda_k`` itself (no sampling); ``noise=True``
draws one Poisson realisation from ``numpy.random.default_rng(seed)``.

Returns a float64 1-D histogram of length *bins*. The unambiguous range is
``c * bins * bin_ps / 2`` — 3.84 m at the defaults (256 bins x 100 ps), with
a bin resolution of 1.50 cm.

The pulse is **not** renormalised to the window: a target near the far edge
genuinely loses the tail of its pulse, exactly as a real sensor does, and the
total signal comes back slightly below *signal_photons*. Renormalising would
have made the truncated pulse asymmetric and biased its centroid.

**Raises** ``ValueError``: a non-positive *distance_m*, a *bins* outside
``[2, MAX_BINS]``, a non-positive *bin_ps* / *irf_fwhm_ps*, negative photon
budgets, a non-integer or negative *seed*, a non-bool *noise*, and — instead
of wrapping the pulse silently to a short distance — a *distance_m* whose
round-trip time falls outside the ``bins * bin_ps`` window.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`counts` を入力に取れる)

[tcspc_coates_correct](../spad/tcspc_coates_correct.md) · [tcspc_irf_convolve](tcspc_irf_convolve.md) · [tcspc_background_subtract](tcspc_background_subtract.md) · [tcspc_stats](tcspc_stats.md) · [dtof_depth](../dtof/dtof_depth.md) · [lifetime_fit](../lifetime/lifetime_fit.md) · [lifetime_phasor](../lifetime/lifetime_phasor.md)

## 同カテゴリ(`tcspc`)

[tcspc_irf_convolve](tcspc_irf_convolve.md) · [tcspc_background_subtract](tcspc_background_subtract.md) · [tcspc_stats](tcspc_stats.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
