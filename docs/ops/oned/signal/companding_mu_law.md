---
op: companding_mu_law
dim: oned
category: signal
in: signal
out: signal
examples: [gallery2d_gray_arith]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# companding_mu_law — ONED `signal` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.companding_mu_law(x, mu=255.0, bits=8)` (実装を直接呼ぶなら `import dsp; dsp.companding_mu_law(x, mu=255.0, bits=8)`、台帳から引くなら `ops1d.get("companding_mu_law")`)

## 使い方

mu-law companding — the G.711 curve, used here on any 1-D signal.

Compress with ``F(v) = sign(v) * ln(1 + mu|v|) / ln(1 + mu)`` on the signal
scaled to ``[-1, 1]``, quantise uniformly, expand back. The steps end up fine
near zero and coarse near full scale, which is the right allocation when the
interesting part of the signal is small compared with its peaks — speech,
vibration, anything with a large crest factor.

**This is where mu-law comes from**: the image operator
``companding_mu_law`` is the same curve applied to intensity. Reporting both
keeps the family honest about which dimension the technique was designed for.

**Applicability — it is the crest factor that decides.** Measured on a sine
of amplitude *A* with one sample pinned at full scale, so the crest factor is
exactly ``1/A`` (mean square error relative to a uniform quantiser):

    crest 50    4 bit 0.011   6 bit 0.014     (about 90x better)
    crest 20    4 bit 0.122   6 bit 0.101
    crest 6.7   4 bit 0.613   6 bit 0.616
    crest 2.0   4 bit 4.22    6 bit 6.03      (several times WORSE)

So the rule is **crest factor above roughly 7** — speech, vibration, impact.
Below that, a plain uniform quantiser wins and mu-law actively hurts.
★Note the peak is a **single sample**: on random signals of the same family
the advantage swung between 0.55 and 0.87 purely with the seed, because the
largest excursion sets the scale. Measure the crest factor of *your* signal,
do not assume it from the distribution.

Other limits: ``mu`` near 0 degenerates to uniform quantisation (that is how
you check the curve is doing anything), and the curve is fixed — unlike a
Lloyd-Max codebook fitted to the signal — which is the point when values must
stay comparable across recordings.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery2d_gray_arith](../../../../examples/gallery2d_gray_arith.py) — `py -3.11 examples/gallery2d_gray_arith.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[create_funct_1d_array](../function/create_funct_1d_array.md) · [create_funct_1d_pairs](../function/create_funct_1d_pairs.md) · [smooth_funct_1d_gauss](../function/smooth_funct_1d_gauss.md) · [smooth_funct_1d_mean](../function/smooth_funct_1d_mean.md) · [derivate_funct_1d](../function/derivate_funct_1d.md) · [integrate_funct_1d](../function/integrate_funct_1d.md) · [zero_crossings_funct_1d](../function/zero_crossings_funct_1d.md) · [local_min_max_funct_1d](../function/local_min_max_funct_1d.md)

## 同カテゴリ(`signal`)

[lowpass](lowpass.md) · [highpass](highpass.md) · [bandpass](bandpass.md) · [envelope](envelope.md) · [rms](rms.md) · [local_std](local_std.md) · [quantize](quantize.md) · [resample](resample.md)

---
*Provenance: dsp.py — ONED operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
