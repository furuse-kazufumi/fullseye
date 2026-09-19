---
op: fly_lgmd_eta
dim: flyvision
category: looming
in: signal
out: signal
examples: [poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_lgmd_eta — FLYVISION `looming` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_lgmd_eta(theta_signal, dt_s, alpha=4.7, delay_s=0.0)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_lgmd_eta(theta_signal, dt_s, alpha=4.7, delay_s=0.0)`、台帳から引くなら `opsflyvision.get("fly_lgmd_eta")`)

## 使い方

LGMD/eta looming response from an expanding subtended angle.

The multiplicative looming model::

    eta(t) = theta'(t - delay) * exp(-alpha * theta(t - delay))

where *theta_signal* is the object's full subtended angle over time, in
radians. The product of the angular expansion rate and an exponentially
decaying gain gives a response that peaks a fixed time before collision.

theta_signal: the full subtended angle per sample, radians.
dt_s:  the sample interval, seconds.
alpha: the gain-decay constant.
delay_s: a fixed neural delay, seconds.

Returns a 1-D float64 array ``eta(t)`` of the same length.

Ground truth: for an object of half-size ``l`` approaching at speed ``|v|``,
``eta`` peaks at a time-to-contact of ``alpha*l/|v| - delay_s`` (Gabbiani et
al. Eq. 5), where the subtended angle is exactly ``2*atan(1/alpha)`` (Eq. 6;
24.0 degrees for ``alpha = 4.7``) — both pinned in the tests.

**Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite
*theta_signal*, a signal over :data:`MAX_SIGNAL_POINTS`, a non-positive *dt_s*
/ *alpha*, and a negative *delay_s*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fly_emd_response](../motion/fly_emd_response.md) · [fly_tau_from_expansion](fly_tau_from_expansion.md) · [fly_dsi](../tuning/fly_dsi.md)

## 同カテゴリ(`looming`)

[fly_tau_from_expansion](fly_tau_from_expansion.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
