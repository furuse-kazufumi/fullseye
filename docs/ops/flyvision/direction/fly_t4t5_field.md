---
op: fly_t4t5_field
dim: flyvision
category: direction
in: matrix × table
out: matrix
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# fly_t4t5_field — FLYVISION `direction` op

- **データ種**: `matrix × table` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_t4t5_field(movie, lattice, dt_s, tau_s=0.25, k_e=5.0, k_d=5.0, k_s=10.0, dc=1.0, model='three_arm', tau_hr_s=0.05, reduce='mean')` (実装を直接呼ぶなら `import flyvision; flyvision.fly_t4t5_field(movie, lattice, dt_s, tau_s=0.25, k_e=5.0, k_d=5.0, k_s=10.0, dc=1.0, model='three_arm', tau_hr_s=0.05, reduce='mean')`、台帳から引くなら `opsflyvision.get("fly_t4t5_field")`)

## 使い方

Direction-selective response over the whole eye, in the six hexagonal directions.

T4 (ON) and T5 (OFF) are the first direction-selective cells in the fly, and
two mechanisms make them so: *preferred-direction enhancement*, which is the
Hassenstein-Reichardt multiplication, and *null-direction suppression*, which
is the Barlow-Levick division. Haag et al. measured both in one cell and wrote
them as three arms reading three adjacent columns — an enhancing arm E one
column *before* the centre, the direct arm D, and a suppressing arm S one
column *after* it::

    R = (dc + k_e * LP[E]) * (dc + k_d * D) / (dc + k_s * LP[S])

with first-order low-passes of time constant ``tau_s`` on E and S. This op
runs that, or either mechanism alone, at every ommatidium and in all six
lattice directions at once.

movie: ``(T, n)`` one polarity channel — the ON or the OFF half of
:func:`fly_onoff_split`, not both. lattice: a :func:`fly_hex_lattice` result
(a :func:`fly_eye_merge` result is refused: its coordinates repeat, so a
neighbour would be looked up in the wrong patch).
dt_s: sample interval, seconds.
model: one of four, the first three sharing the same resting value ``dc`` so
that their responses are directly comparable —

  * ``"three_arm"`` — the whole model above (Haag et al., *eLife* 5:e17421,
    2016);
  * ``"enhance"`` — the numerator alone, ``(dc + k_e LP[E])(dc + k_d D)/dc``:
    preferred-direction *enhancement*, the Hassenstein-Reichardt
    multiplication with no veto;
  * ``"suppress"`` — the denominator alone, ``dc (dc + k_d D)/(dc + k_s
    LP[S])``: null-direction *suppression*, the Barlow-Levick division with
    no enhancement (Barlow & Levick, *J. Physiol.* 178:477, 1965);
  * ``"hr"`` — the classical opponent correlator ``LP[E]*D - E*LP[D]`` with
    its own time constant *tau_hr_s*, which is antisymmetric by construction
    and so is direction-selective without either of the two mechanisms above
    (Hassenstein & Reichardt, *Z. Naturforsch.* 11b:513, 1956). It is
    :func:`fly_emd_response` run over the lattice instead of a pair.
tau_s / k_e / k_d / k_s / dc: the three-arm parameters. The defaults are the
paper's (tau = 250 ms, k = 5/5/10, DC = 1.0). tau_hr_s: the correlator time
constant, used by ``model="hr"`` only.
reduce: how the time course becomes one number per direction — ``"mean"``
(the wide-field integration a tangential cell performs), ``"last"`` (the
value at the final sample, which is how a transient is read at a chosen
instant) or ``"max"``.

Returns a ``(6, n)`` float64 matrix: row *k* is the response to motion in
hexagonal direction *k* (counter-clockwise from +azimuth, see
:data:`HEX_STEPS`), averaged over time, with the model's resting value
subtracted so that no stimulus reads exactly 0. It is the ``(k, n)`` shape
:func:`fly_hs_readout` and :func:`fly_flow_from_directions` take.

Ommatidia at the rim, which have no neighbour on one side, read exactly 0 in
that direction: a detector missing an arm has no motion to report, and
inventing one at the edge would put a ring of false flow around every eye.

Ground truth, and it is the paper's claim written as algebra: because the
three arms multiply, **the direction selectivity of the whole model is the
product of the selectivities of its two halves**. For any stimulus and any
pair of opposite directions,

    ratio("three_arm") == ratio("enhance") * ratio("suppress")

exactly, where ``ratio = R_preferred / R_null`` taken on ``R + dc``. Two
columns lit in turn, a step of amplitude 1 held for ``tau``, with the paper's
constants, give ``R + dc`` = ``(dc + k_e(1-1/e))(dc + k_d)/dc`` = **24.96**
preferred and ``dc(dc + k_d)/(dc + k_s(1-1/e))`` = **0.820** null: 4.16 from
enhancement, 7.32 from suppression, 30.46 together. The tests measure all
three and the identity between them.

**Raises** ``ValueError``: a non-2-D / too-short / non-finite *movie*, a
column count that is not the lattice's ommatidium count, a non-positive
*dt_s* / *tau_s* / *tau_hr_s* / *dc*, a negative gain, an unknown *model*,
and any malformed *lattice*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fly_lamina_filter](../lamina/fly_lamina_filter.md) · [fly_onoff_split](../lamina/fly_onoff_split.md) · [fly_flow_from_directions](fly_flow_from_directions.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`direction`)

[fly_flow_from_directions](fly_flow_from_directions.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
