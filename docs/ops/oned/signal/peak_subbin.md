---
op: peak_subbin
dim: oned
category: signal
in: signal × indices
out: measurement
examples: [poc_web_roll_periodicity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# peak_subbin — ONED `signal` op

- **データ種**: `signal × indices` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.peak_subbin(x, idx=None, mode='parabola')` (実装を直接呼ぶなら `import dsp; dsp.peak_subbin(x, idx=None, mode='parabola')`、台帳から引くなら `ops1d.get("peak_subbin")`)

## 使い方

Peak position **between** samples — the vertex of a fit through 3 points.

:func:`find_peaks` returns integer indices, so the position of a spectral
line or a correlation peak is quantised to the bin grid no matter how
finely the peak itself is resolved. This refines each index to a float by
fitting the sample and its two neighbours.

*mode* picks what is fitted:

``"parabola"``
    ``a x^2 + b x + c`` through the three raw values. The classic estimator;
    exact for a genuinely parabolic top and cheap.
``"gauss"``
    the same parabola through ``log`` of the three values, which is exact for
    a Gaussian peak. **Requires all three values positive** — a magnitude
    spectrum qualifies, a signed correlation does not. Non-positive
    neighbourhoods raise ``ValueError`` rather than silently returning the
    integer index, because "the refinement quietly did nothing" is the
    failure this operator exists to remove.

Measured on a Gaussian of width 1.7 bins centred at 40.37: the integer
argmax gives 40 (error 0.37 bins), ``parabola`` gives 40.3553 (error
**0.0147**) and ``gauss`` gives 40.3700 (error 0, to machine precision).
**The parabola is biased on a Gaussian, and the bias grows as the peak gets
narrower** — the same measurement at widths 6.0 / 3.0 / 1.7 / 1.0 bins errs
by 0.0012 / 0.0047 / 0.0147 / 0.0434. That is the whole reason ``gauss``
exists: for a spectral line the log-parabola is not an approximation, it is
the exact model.

The refinement is still an assumption about shape, not a measurement of it.
On a triangular peak, whose top is not smooth, ``parabola`` errs by 0.0857
bins where the integer index errs by 0.30 — better, but three times worse
than on the Gaussian it was designed for.

**The shift is not clamped.** A vertex more than half a sample away from the
index means the index was not a local maximum in the first place, and that is
information: clamping it to +/-0.5 would return a plausible number for a bin
that has no peak in it. Run :func:`find_peaks` first, or clamp deliberately
at the call site when evaluating bins that are not maxima (a harmonic comb,
for instance).

A peak sitting on the first or last sample has no neighbour on one side and
keeps its integer position (there is nothing to interpolate against); the
returned array says so by being exactly equal to the input index there.

Parameters
----------
x : array_like
    The 1-D signal the peaks were found in.
idx : int, sequence of int, or None
    Peak indices. ``None`` means "the argmax", so ``peak_subbin(mag)`` is the
    one-liner for a single line.
mode : {"parabola", "gauss"}

Returns
-------
float or ndarray
    Refined position(s) in samples. Scalar in, scalar out.

See also
--------
find_peaks : which indices to refine.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_web_roll_periodicity](../../../../examples/poc_web_roll_periodicity.py) — `py -3.11 examples/poc_web_roll_periodicity.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [resample](resample.md) · [spectrum](spectrum.md) · [spectrogram](spectrogram.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
