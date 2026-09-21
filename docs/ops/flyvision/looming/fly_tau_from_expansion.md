---
op: fly_tau_from_expansion
dim: flyvision
category: looming
in: signal
out: signal
examples: [poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_tau_from_expansion — FLYVISION `looming` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_tau_from_expansion(theta_signal, dt_s, shape='sphere')` (実装を直接呼ぶなら `import flyvision; flyvision.fly_tau_from_expansion(theta_signal, dt_s, shape='sphere')`、台帳から引くなら `opsflyvision.get("fly_tau_from_expansion")`)

## 使い方

Time-to-contact from optical expansion — the tau margin.

From the subtended angle and its rate::

    shape="disk":   tau = sin(theta) / theta'
    shape="sphere": tau = 2*tan(theta/2) / theta'

``theta_signal`` is the full subtended angle over time, radians.

★ The two object models differ by 33% at a 60-degree subtense (``sin 60 = 0.866``
vs ``2 tan 30 = 1.155``); using the wrong one silently mis-times a landing, so
the model is a required, named choice rather than a default guess.

theta_signal: the full subtended angle per sample, radians.
dt_s:  the sample interval, seconds.
shape: ``"disk"`` (a frontal circular disk) or ``"sphere"``.

Returns a 1-D float64 array of the time-to-contact per sample, seconds.
Non-expanding samples (``theta' <= 0``) return ``NaN`` — a documented
non-finite, because a contracting or static angle has no time-to-contact and
inventing one would be a plausible-wrong number. (The registry op
``tb_fly_tau_from_expansion`` must return a finite signal, so it replaces those
NaN by the signal fallback without recording a fallback event —
``backend_safe.NONFINITE_BY_DESIGN``; call this function directly to keep the NaN.)

Ground truth: for the model's own object geometry (``theta = 2 asin(l/d)`` for a
sphere, ``theta = 2 atan(l/d)`` for a disk) approaching at speed ``|v|``, the
returned tau equals the true distance-over-speed ``d/|v|`` (pinned in the
tests).

**Raises** ``ValueError``: a non-1-D / empty / too-short (< 3) / non-finite
*theta_signal*, a signal over :data:`MAX_SIGNAL_POINTS`, a non-positive *dt_s*,
and an unknown *shape*. A non-expanding angle is **not** an error — it is the
documented ``NaN`` return above.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fly_hex_quantize](../sample/fly_hex_quantize.md) · [fly_emd_response](../motion/fly_emd_response.md) · [fly_lgmd_eta](fly_lgmd_eta.md) · [fly_dsi](../tuning/fly_dsi.md)

## 同カテゴリ(`looming`)

[fly_lgmd_eta](fly_lgmd_eta.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
