---
op: fly_emd_response
dim: flyvision
category: motion
in: signal × signal
out: signal
examples: [poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# fly_emd_response — FLYVISION `motion` op

- **データ種**: `signal × signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_emd_response(signal_a, signal_b, tau_s=0.05, dt_s=0.001)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_emd_response(signal_a, signal_b, tau_s=0.05, dt_s=0.001)`、台帳から引くなら `opsflyvision.get("fly_emd_response")`)

## 使い方

Hassenstein-Reichardt correlator between two adjacent ommatidial signals.

The opponent elementary motion detector::

    R(t) = LP(a)(t) * b(t) - a(t) * LP(b)(t)

where ``LP`` is a first-order low-pass of time constant *tau_s*. Delaying one
channel and multiplying it against the other, then subtracting the mirror
pair, gives a signal whose sign is the direction of motion and whose
steady-state mean encodes the temporal frequency.

signal_a / signal_b: the two 1-D input time series (same length).
tau_s:  the low-pass time constant, seconds.
dt_s:   the sample interval, seconds.

Returns a 1-D float64 array ``R(t)`` of the same length.

Ground truth: for two sinusoids of temporal frequency ``f`` (``omega = 2 pi f``)
with a spatial phase ``psi = 2 pi dphi/lambda`` between them, the steady-state
mean is ``R_bar = dI^2 * sin(psi) * omega tau/(1 + (omega tau)^2)`` (to 5%),
which is zero at ``lambda = 2 dphi`` (``psi = pi``) and maximal at
``f = 1/(2 pi tau)`` independent of ``lambda`` (pinned in the tests).

**Raises** ``ValueError``: a non-1-D / empty / too-short (< 2) / non-finite
*signal_a* or *signal_b*, mismatched lengths, a signal over
:data:`MAX_SIGNAL_POINTS`, and a non-positive *tau_s* / *dt_s*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fly_lgmd_eta](../looming/fly_lgmd_eta.md) · [fly_tau_from_expansion](../looming/fly_tau_from_expansion.md) · [fly_dsi](../tuning/fly_dsi.md)

## 同カテゴリ(`motion`)

—

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
