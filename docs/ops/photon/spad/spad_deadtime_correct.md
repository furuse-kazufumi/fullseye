---
op: spad_deadtime_correct
dim: photon
category: spad
in: countrate
out: countrate
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# spad_deadtime_correct — PHOTON `spad` op

- **データ種**: `countrate` → `countrate`
- **呼び出し**: `import photoncount; photoncount.spad_deadtime_correct(measured_hz, dead_time_ns=50.0)` (または `opsphoton.get("spad_deadtime_correct")`)

## 使い方

Recover the true photon rate from a dead-time-distorted measured rate.

The exact inverse of the **non-paralysable** law of
:func:`spad_deadtime_apply`::

    n = m / (1 - m*tau)

A round trip ``apply -> correct`` is exact to machine precision (measured max
elementwise relative error 6.0e-16 over 2000 rates spanning 1e3 to 5e7 Hz at
``tau = 50 ns``, where the measured rate reaches 71.4% of the 20 MHz
saturation rate).

**There is deliberately no paralysable inverse.** ``m = n*exp(-n*tau)`` is not
injective — every measured rate below the maximum ``1/(e*tau)`` corresponds to
*two* true rates, one below and one above ``1/tau`` — so returning one of them
would be a fabrication dressed as a correction. Resolve the branch with an
independent measurement (e.g. an attenuator step) and invert it yourself.

*measured_hz* is a 1-D array of measured rates in counts per second;
*dead_time_ns* the dead time in nanoseconds (default 50, the same
placeholder :func:`spad_deadtime_apply` uses — replace it with the
datasheet value). Returns the corrected true rates as a float64 1-D array.

**Raises** ``ValueError``: negative, non-finite or non-1-D *measured_hz*, a
non-positive *dead_time_ns*, and — instead of returning ``inf`` or a negative
rate — any measured rate at or above the saturation rate ``1/tau``, which no
non-paralysable detector can ever produce.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`countrate` を入力に取れる)

[spad_deadtime_apply](spad_deadtime_apply.md)

## 同カテゴリ(`spad`)

[spad_deadtime_apply](spad_deadtime_apply.md) · [tcspc_coates_correct](tcspc_coates_correct.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
