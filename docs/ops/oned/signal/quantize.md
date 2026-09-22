---
op: quantize
dim: oned
category: signal
in: signal
out: signal
examples: [poc_cold_chain_excursion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# quantize — ONED `signal` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.quantize(x, bits=8, mode='round', dither=None, seed=0)` (実装を直接呼ぶなら `import dsp; dsp.quantize(x, bits=8, mode='round', dither=None, seed=0)`、台帳から引くなら `ops1d.get("quantize")`)

## 使い方

Scalar quantiser with the error model stated, plus optional dither.

*bits* sets the number of levels ``L = 2**bits`` over the signal's own
min..max range. *mode* is ``"round"`` (mid-tread, unbiased) or ``"truncate"``
(floor, the convention PIL's posterize and most fixed-point casts use).

**The two differ by more than a rounding convention.** With step
``Delta = range/(L-1)`` both have error variance ``Delta**2/12``, but
truncation also carries a mean of ``-Delta/2``, so its mean square error is

    truncate:  Delta**2/12 + (Delta/2)**2 = Delta**2/3
    round:     Delta**2/12

— a factor of **4**. Anything that measures a level (not just displays it)
must round.

*dither* adds noise **before** quantising so the error stops being a function
of the signal: ``"tpdf"`` (triangular, the audio standard — two uniform draws
summed, so the error's variance no longer depends on the sample value) or
``"rpdf"`` (one uniform draw). Dither raises the total error power but removes
the correlation that makes quantisation audible as distortion rather than as
hiss. ``seed`` fixes the draw so the op stays deterministic.

**Applicability.** (1) The range is taken from *this* signal, so two signals
quantised separately do not share a scale. (2) ``bits=1`` with no dither is a
comparator, not a quantiser — the error model does not apply. (3) The error
model assumes the signal moves by more than a step between samples; on a flat
stretch the error is a constant offset, not noise.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_cold_chain_excursion](../../../../examples/poc_cold_chain_excursion.py) — `py -3.11 examples/poc_cold_chain_excursion.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [local_std](local_std.md) · [companding_mu_law](companding_mu_law.md) · [resample](resample.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
