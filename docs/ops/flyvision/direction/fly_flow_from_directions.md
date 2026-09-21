---
op: fly_flow_from_directions
dim: flyvision
category: direction
in: matrix × table
out: matrix
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# fly_flow_from_directions — FLYVISION `direction` op

- **データ種**: `matrix × table` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_flow_from_directions(responses, lattice)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_flow_from_directions(responses, lattice)`、台帳から引くなら `opsflyvision.get("fly_flow_from_directions")`)

## 使い方

Six directional responses per ommatidium in, one local flow vector out.

The lobula plate does not keep six numbers per point of the visual field; it
keeps the direction and strength of the motion there, split over four layers
of opposite preference. This op is that reduction, done as the vector sum on
the tangent plane that makes opposite hexagonal directions cancel exactly::

    f_i = (2/6) * sum_k R[k, i] * (cos t_ik, sin t_ik)

where ``t_ik`` is the angle of the step to ommatidium *i*'s neighbour in
direction *k*, measured in the local tangent plane with azimuth scaled by
``cos(elevation)`` so that it is an angle on the sphere rather than a
difference of coordinates. The ``2/6`` normalises the sum so that a
cosine-tuned set of responses of amplitude ``A`` returns a vector of length
``A`` — with six directions the raw sum is ``3A``.

responses: ``(6, n)``, the return of :func:`fly_t4t5_field`.
lattice: the :func:`fly_hex_lattice` it was measured on (a merged eye is
refused — neighbours are local, the fit downstream is not).

Returns ``(n, 2)`` float64: for each ommatidium the flow component along the
local azimuth (left positive) and along the local elevation (up positive), in
the response's own units. This is the ``(n, 2)`` field
:func:`fly_egomotion_from_flow` and :func:`fly_matched_filter` speak.

Ommatidia at the rim, which do not have all six neighbours, return exactly
zero: a partial sum over the circle does not cancel, so keeping it would draw
a ring of inward flow around the eye and the fit downstream would read that
ring as a rotation.

Ground truth: for responses ``R[k] = A cos(theta_k - theta_0)`` the returned
vector has length ``A`` and angle ``theta_0`` exactly (regular geometry, where
the six steps are 60 degrees apart); opposite directions cancel, so a
symmetric flicker response of any size returns exactly zero.

**Raises** ``ValueError``: *responses* that is not ``(6, n)``, a column count
that is not the lattice's ommatidium count, non-finite entries, and any
malformed *lattice*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fly_lamina_filter](../lamina/fly_lamina_filter.md) · [fly_onoff_split](../lamina/fly_onoff_split.md) · [fly_t4t5_field](fly_t4t5_field.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`direction`)

[fly_t4t5_field](fly_t4t5_field.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
