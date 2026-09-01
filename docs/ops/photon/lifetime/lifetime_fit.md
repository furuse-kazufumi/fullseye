---
op: lifetime_fit
dim: photon
category: lifetime
in: counts
out: table
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# lifetime_fit — PHOTON `lifetime` op

- **データ種**: `counts` → `table`
- **呼び出し**: `import photoncount; photoncount.lifetime_fit(decay, bin_ps=100.0, background=None, min_counts=1.0, start_bin=None)` (または `opsphoton.get("lifetime_fit")`)

## 使い方

Mono-exponential fluorescence lifetime from a TCSPC decay histogram.

Fits ``I(t) = A*exp(-t/tau) + b`` by a **Poisson-weighted log-linear least
squares**: the background is removed, the logarithm of the remaining counts
is linear in ``t`` with slope ``-1/tau``, and each bin is weighted by its own
counts because ``var(ln N) ~ 1/N`` — which is exactly the Poisson error bar
:func:`photon_uncertainty` reports.

The fit starts at the **peak** bin by default (or at *start_bin* if given):
the rising edge before the peak is the instrument response convolved with the
decay, not the decay, and including it flattens the log slope and so biases
the lifetime **long**. Measured on a 2000 ps decay blurred by a 600 ps IRF
(256 bins x 100 ps): starting at the peak (bin 4) gives 2008.0 ps (+0.40%),
forcing ``start_bin=0`` gives 2100.7 ps (+5.0%) — a 12x worse bias from four
extra bins. Only bins with more than *min_counts* counts after background
removal take part (the
logarithm of 0 is ``-inf``, and single-count tail bins carry almost no
information but huge log-scatter).

*background* is the flat pedestal per bin; ``None`` (default) estimates it as
the median of the **last decile** of bins, which for a decay is tail. Pass
``0.0`` to state that the data are already background free.

Returns a dict: ``lifetime_ps`` · ``amplitude`` (the fitted ``A`` at ``t=0``
of the fit window, in counts per bin) · ``background`` (the level used) ·
``start_bin`` · ``n_bins_used`` · ``r_squared`` (of the weighted log fit).

Ground truth: on a **noiseless** exponential the recovery is exact —
``lifetime_ps`` came back as 2000.000000000 ps for ``tau = 2000 ps`` (256
bins x 100 ps), a measured relative error of 0.0, with ``r_squared`` 1.0.
*That stays true when the histogram is built by integrating the exponential
over each bin* rather than sampling it, because bin integration multiplies
every bin by the same constant and so cannot change the slope.

With Poisson noise the log-linear estimator is **biased high**, and the size
of the bias is worth knowing: at 20000 total photons, seed 0,
``min_counts=1`` gives 2058.8 ps (+2.9%) from 133 bins, and raising
``min_counts`` to 10 gives 2047.3 ps (+2.4%) from 94 bins. Averaged over
seeds 0-19 at ``min_counts=10`` the mean is 2014.3 ps (**+0.72% systematic
bias**) with a 18.2 ps (0.9%) seed-to-seed spread — so seed 0 is a
2-sigma-high draw, and the bias, not the scatter, is the thing to remember.
It comes from ``E[ln N] < ln E[N]`` in the sparse tail; a full Poisson MLE
would remove it and is not what this op does.

**Raises** ``ValueError``: negative, non-finite or non-1-D *decay*, a
non-positive *bin_ps*, a negative *background* / *min_counts*, a *start_bin*
outside the histogram, fewer than 2 usable bins after the background and
threshold cuts (a straight line needs two points), a degenerate fit (all
usable bins at the same time), and — instead of returning a negative
lifetime — a fitted slope that is zero or positive, i.e. a profile that does
not decay.

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

## 同カテゴリ(`lifetime`)

[lifetime_phasor](lifetime_phasor.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
