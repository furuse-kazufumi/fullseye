---
op: fly_lamina_filter
dim: flyvision
category: lamina
in: matrix
out: matrix
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_lamina_filter — FLYVISION `lamina` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_lamina_filter(movie, dt_s, tau_adapt_s=0.2, tau_lp_s=0.02, mode='divisive', floor=0.001)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_lamina_filter(movie, dt_s, tau_adapt_s=0.2, tau_lp_s=0.02, mode='divisive', floor=0.001)`、台帳から引くなら `opsflyvision.get("fly_lamina_filter")`)

## 使い方

Photoreceptor adaptation + the lamina's band-pass: intensities in, contrast out.

The first thing the optic lobe does to a picture is throw away its brightness.
A photoreceptor adapts to the running mean light level and the large monopolar
cells (L1/L2) report the *deviation* from it, so the same scene at dawn and at
noon arrives at the motion detectors as the same signal. Two closed-form
stages, in that order:

  1. **adaptation** — a first-order low-pass of time constant *tau_adapt_s*
     per ommatidium is the adaptation state ``a(t)``. ``mode="divisive"``
     returns the Weber contrast ``(x - a)/(a + eps)`` (``eps = floor *
     mean(x)``, so it scales with the picture and a dark ommatidium cannot
     divide by zero); ``mode="subtractive"`` returns ``x - a``, which is the
     same high-pass without the gain control.
  2. **membrane** — a first-order low-pass of time constant *tau_lp_s*, the
     cell's own bandwidth.

movie: ``(T, n)`` intensities, rows = time. ``mode="divisive"`` refuses a
negative entry (a negative light level is not a measurement) and an all-zero
movie (its contrast is 0/0, which would be fabricated rather than measured).
dt_s: sample interval, seconds. tau_adapt_s / tau_lp_s: the two time
constants, seconds. floor: the divisive guard, relative to the mean intensity.

Returns ``(T, n)`` float64 contrast.

Ground truth, both exact rather than approximate:

  * **Weber invariance.** In ``"divisive"`` mode, scaling the whole movie by
    any positive constant returns *the same array* — both ``a`` and ``eps``
    scale with it. That is the point of the stage and the tests pin it to
    machine precision.
  * **The transfer is the product of the two first-order filters.** With
    ``A = 1 - exp(-dt/tau_adapt)`` and ``B = 1 - exp(-dt/tau_lp)``, the
    steady-state gain at angular frequency ``w`` is
    ``|1 - H_A(w)| * |H_B(w)|`` where ``H(w) = C/(1 - (1-C) exp(-i w dt))`` —
    a band-pass that blocks DC exactly and is measured at four frequencies in
    the tests.

**Raises** ``ValueError``: a non-2-D / too-short / non-finite *movie*, a movie
over :data:`MAX_MOVIE_ELEMENTS`, a non-positive *dt_s* / *tau_adapt_s* /
*tau_lp_s*, a non-positive *floor*, an unknown *mode*, and (divisive only) a
negative or all-zero movie.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fly_onoff_split](fly_onoff_split.md) · [fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`lamina`)

[fly_onoff_split](fly_onoff_split.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
