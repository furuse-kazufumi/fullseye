---
op: tcspc_background_subtract
dim: photon
category: tcspc
in: counts
out: counts
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# tcspc_background_subtract — PHOTON `tcspc` op

- **データ種**: `counts` → `counts`
- **呼び出し**: `import photoncount; photoncount.tcspc_background_subtract(hist, method='median', leading_bins=None, quantile=0.5, scale=1.0)` (または `opsphoton.get("tcspc_background_subtract")`)

## 使い方

Remove the ambient-light / dark-count floor from an arrival-time histogram.

Outdoors, most of what a dToF sensor counts is sunlight: a roughly uniform
pedestal under the return pulse. It biases the centroid toward the middle of
the window (a floor of ``b`` per bin pulls the first moment toward
``window/2``) and it inflates the apparent signal, so it is removed before
any depth or lifetime estimate.

The level is estimated by *method* and then **subtracted** (the sign trap:
the result is ``hist - level``, clipped at 0, never ``hist + level``):

  * ``"median"`` (default) — the median of every bin. Robust while the pulse
    occupies well under half the window, which is the normal dToF case.
  * ``"leading"`` — the mean of the first *leading_bins* bins, the classical
    choice when the pulse is known to arrive late (a far target).
  * ``"trailing"`` — the mean of the last *leading_bins* bins, for
    fluorescence decays where the tail is background.
  * ``"quantile"`` — the given *quantile* of all bins, for tuning by hand.

*leading_bins* defaults to ``None`` = ``min(8, len(hist))``, so the default
call works on a short histogram instead of raising over a constant nobody
chose (a fixed default of 8 made ``method="leading"`` fail on any histogram
with fewer than 8 bins).

*scale* multiplies the estimated level before subtraction (``scale=1.2`` for
a deliberately aggressive removal). Clipping at 0 means the result is a valid
non-negative histogram that the rest of this module will accept.

Ground truth: on a noiseless histogram with a known flat pedestal of 20
counts/bin under a 5000-photon pulse covering 5.1% of the window, the median
estimate recovers 20.000000 and the returned histogram equals the pedestal-
free pulse **exactly** (measured area error 0.0, pinned in the tests).

Returns a float64 1-D histogram of the same length as *hist*.

**Raises** ``ValueError``: negative, non-finite or non-1-D *hist*, an unknown
*method*, a *leading_bins* outside ``[1, len(hist)]``, a *quantile* outside
``[0, 1]``, and a negative *scale*.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`counts` を入力に取れる)

[tcspc_coates_correct](../spad/tcspc_coates_correct.md) · [tcspc_irf_convolve](tcspc_irf_convolve.md) · [tcspc_stats](tcspc_stats.md) · [dtof_depth](../dtof/dtof_depth.md) · [lifetime_fit](../lifetime/lifetime_fit.md) · [lifetime_phasor](../lifetime/lifetime_phasor.md)

## 同カテゴリ(`tcspc`)

[tcspc_simulate](tcspc_simulate.md) · [tcspc_irf_convolve](tcspc_irf_convolve.md) · [tcspc_stats](tcspc_stats.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
