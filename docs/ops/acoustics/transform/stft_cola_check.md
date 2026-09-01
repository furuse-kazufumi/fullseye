---
op: stft_cola_check
dim: acoustics
category: transform
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# stft_cola_check — ACOUSTICS `transform` op

- **データ種**: `` → `table`
- **呼び出し**: `import acoustics; acoustics.stft_cola_check(window='hann', win=256, hop=None)` (または `opsacoustics.get("stft_cola_check")`)

## 使い方

Does this (window, hop) pair satisfy COLA, and how exactly?

COLA — the analysis windows summing to a constant over the hop lattice — is
what lets plain overlap-add work without a division. It is *not* required by
:func:`istft`, which is weighted, but it is required by anything that
overlap-adds modified frames without renormalising, and getting it wrong
produces a periodic amplitude ripple at ``rate/hop`` Hz that looks like
tremolo rather than like a bug.

Returns a dict: ``cola`` (bool), ``constant`` (the mean of the overlap sum),
``max_deviation`` (absolute), ``relative_deviation``, ``nola`` (bool),
``min_squared_sum``, plus the geometry.

Measured (periodic windows, ``relative_deviation`` of the plain sum):

========  ====  ====  ==================  ========  ====
window    win   hop   relative_deviation  constant  COLA
========  ====  ====  ==================  ========  ====
hann      256   128   4.44e-16            1.00      yes
hann      256   64    2.22e-16            2.00      yes
hann      256   85    1.48e-03            1.506     no
hamming   256   128   2.06e-16            1.08      yes
blackman  256   128   1.91e-01            0.84      no
blackman  256   64    3.97e-16            1.68      yes
boxcar    256   128   0.00e+00            2.00      yes
========  ====  ====  ==================  ========  ====

The two blackman rows are the useful ones: the same window is COLA at
hop = win/4 and 19 % off at hop = win/2, so "which window" is not the
question — the pair is. The boxcar row was worth measuring rather than
assuming: a rectangular window at 50 % overlap sums to exactly 2 and is
COLA, which is the opposite of the usual intuition about it. Note also that
the constant is not 1 in general — an overlap-add that does not divide by it
is off by a *gain*, which is the failure that looks like a working system.

**Raises** ``ValueError``: unknown / all-zero window, ``hop`` outside
``[1, win]``, ``win`` outside ``[2, MAX_WINDOW]``.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[istft](istft.md)

## 同カテゴリ(`transform`)

[stft](stft.md) · [istft](istft.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
