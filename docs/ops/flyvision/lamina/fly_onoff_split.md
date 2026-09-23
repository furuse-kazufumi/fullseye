---
op: fly_onoff_split
dim: flyvision
category: lamina
in: matrix
out: matrix
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fly_onoff_split — FLYVISION `lamina` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_onoff_split(movie, dt_s, tau_on_s=0.02, tau_off_s=0.02, rectify=True)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_onoff_split(movie, dt_s, tau_on_s=0.02, tau_off_s=0.02, rectify=True)`、台帳から引くなら `opsflyvision.get("fly_onoff_split")`)

## 使い方

Split a contrast movie into the ON and OFF channels the medulla carries.

Beyond the lamina the fly stops carrying one signed signal and carries two:
an ON channel (Mi1 / Tm3, brightening) and an OFF channel (Tm1 / Tm2,
darkening), each with its own relay dynamics. This op is that split, and it
keeps the rectification *optional* on purpose: the split was measured
downstream, in the motion response (Joesch et al., *Nature* 468:300, 2010),
while L1/L2 themselves respond linearly (Clark et al., *Neuron* 70:1165,
2011), so a pathway that rectifies at the lamina is making a claim the
recordings do not.

movie: ``(T, n)`` contrast, rows = time (the return of
:func:`fly_lamina_filter`). dt_s: sample interval, seconds.
tau_on_s / tau_off_s: the low-pass time constant of each channel, seconds.
rectify: ``True`` half-wave rectifies (``ON = max(c, 0)``,
``OFF = max(-c, 0)``, both >= 0); ``False`` passes the signed contrast into
the ON channel and its negation into the OFF channel, which is the linear
L1/L2 case and lets the rectification happen downstream instead.

Returns ``(T, 2n)`` float64: columns ``0..n-1`` are ON, ``n..2n-1`` are OFF,
the same ommatidium order in each half.

Ground truth (exact, with ``tau_on_s == tau_off_s`` so the two channels share
one filter):

  * ``ON - OFF`` is the low-passed input, whichever *rectify* you chose;
  * with ``rectify=True``, ``ON + OFF`` is the low-passed **absolute value**;
  * a movie that never goes negative leaves the OFF channel identically zero
    (and vice versa) — the split does not invent a dark event.

**Raises** ``ValueError``: a non-2-D / too-short / non-finite *movie*, a movie
over :data:`MAX_MOVIE_ELEMENTS`, and a non-positive *dt_s* / *tau_on_s* /
*tau_off_s*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fly_lamina_filter](fly_lamina_filter.md) · [fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`lamina`)

[fly_lamina_filter](fly_lamina_filter.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
