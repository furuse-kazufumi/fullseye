---
op: local_std
dim: oned
category: signal
in: signal
out: signal
examples: [gallery2d_texture_freq]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# local_std — ONED `signal` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.local_std(x, window=9)` (実装を直接呼ぶなら `import dsp; dsp.local_std(x, window=9)`、台帳から引くなら `ops1d.get("local_std")`)

## 使い方

Rolling standard deviation with a stated error bound.

The 1-D counterpart of the image operator ``local_std`` (HALCON's
``deviation_image``): the variance is taken after subtracting the mean
(``E[x^2] - E[x]^2`` loses its significant digits on a signal that sits far
from zero), unbiased by ``n/(n-1)``, and the residual bias of the square root
removed by ``c4(n)``, so the estimate of ``sigma`` itself is unbiased.

*window* is the number of samples in the sliding window, **rounded up to the
next odd number** so the window can be centred (10 becomes 11). The error
bound below is computed from the window actually used, so the number quoted
stays true. The 2-D side does the same thing — ``_k(a)`` snaps the knob to
3/5/7/9 — and the typed bridge that exposes this op as ``tb_local_std``
scales the knob continuously, so an even value arrives whenever the knob
lands between two odd ones.
**The relative standard error of each estimate is ``1/sqrt(2(n-1))``** —
35 % for a 5-sample window, 11 % for 41. Quote it next to any noise figure:
a rolling sigma over 9 samples is +- 25 %, which is wider than most of the
changes people try to read off it.

Returns an array the same length as *x* (the ends are reflected).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_texture_freq](../../../../examples/gallery2d_texture_freq.py) — `py -3.11 examples/gallery2d_texture_freq.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [quantize](quantize.md) · [companding_mu_law](companding_mu_law.md) · [resample](resample.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
