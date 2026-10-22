---
op: fly_expansion_readout
dim: flyvision
category: looming
in: matrix × table
out: table
examples: [poc_zebra_stripes_fly_eye]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fly_expansion_readout — FLYVISION `looming` op

- **データ種**: `matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_expansion_readout(flow, lattice, axis=None, weights=None)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_expansion_readout(flow, lattice, axis=None, weights=None)`、台帳から引くなら `opsflyvision.get("fly_expansion_readout")`)

## 使い方

Time-to-contact from the flow over the whole eye — and the aperture effect's 2x.

A fronto-parallel surface approached at speed ``v`` from distance ``d`` moves
the line of sight at polar angle ``theta`` outward at ``sin theta cos theta /
tau`` with ``tau = d/v``. This op projects the measured flow onto the outward
radial direction and fits that one number, ``1/tau``, by weighted least
squares::

    1/tau = sum w f_r sin cos / sum w (sin cos)^2

and, independently, fits a linear field ``f = A x + b`` on the gnomonic plane
and reads the divergence ``tr A``, which :mod:`sceneflow` converts the same
way (``ttc = 2/div``).

The reason to have both: a correlation-type detector only sees the motion
component **across** a contrast edge. Over vertical stripes every edge is
vertical, so the elevation component of the flow is lost (the aperture
problem), the radial projection keeps on average half the expansion, and
both readouts return **2 tau** — the surface looks twice as far as it is.
A checkerboard has edges in both directions and returns tau. That is the
identity How et al. (2020) argued from, written as a number.

flow:    ``(n, 2)`` azimuth/elevation flow per ommatidium (radians per
         second), the return of :func:`fly_flow_from_directions`.
lattice: the eye it was measured on (hexagonal or Vogel).
axis:    the direction of travel = focus of expansion, body coordinates;
         ``None`` = the lattice's optical axis.
weights: ``None`` or ``(n,)`` non-negative weights (e.g. 0 on the rim, where
         :func:`fly_flow_from_directions` reports nothing).

Returns a dict ``{"tau_s", "rate_1_s", "tau_div_s", "divergence_1_s",
"aperture_ratio", "residual_rms", "n_ommatidia"}`` — the radial-fit
time-to-contact and its rate, the divergence-fit time-to-contact and the
divergence, the ratio of the smaller to the larger diagonal of ``A`` (1 for
isotropic expansion, 0 under a pure aperture effect), the rms of the radial
residual and how many ommatidia voted. A non-expanding field (rate <= 0)
returns ``NaN`` for the time-to-contact — a documented non-finite, as in
:func:`fly_tau_from_expansion`: a receding surface has no time-to-contact.

Ground truth (pinned in the tests): the exact plane flow returns
``tau_s == tau`` and ``tau_div_s == tau`` to 1e-9 (the divergence is fitted
on gnomonic velocities, where a plane approach is exactly linear); the same
flow with its elevation component removed returns ``2 tau`` from both
readouts within 1% on a 10-degree field (``aperture_ratio`` 0) — a
hexagonal lattice is 6-fold symmetric, so ``sum cos^2 phi = sum sin^2 phi``
over it, and the residual is the sphere's departure from that plane.

**Raises** ``ValueError``: a *flow* that is not ``(n, 2)`` for this lattice
(an empty *flow* is refused), non-finite entries, a malformed *lattice* /
*axis* / *weights*, all-zero weights, and fewer than 6 voting ommatidia.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_zebra_stripes_fly_eye](../../../../examples/poc_zebra_stripes_fly_eye.py) — `py -3.11 examples/poc_zebra_stripes_fly_eye.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](../selfmotion/fly_matched_filter.md) · [fly_egomotion_from_flow](../selfmotion/fly_egomotion_from_flow.md) · [fly_eye_merge](../selfmotion/fly_eye_merge.md) · [fly_view_plane_texture](../stimulus/fly_view_plane_texture.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [lattice_moire_peak](../alias/lattice_moire_peak.md)

## 同カテゴリ(`looming`)

[fly_lgmd_eta](fly_lgmd_eta.md) · [fly_tau_from_expansion](fly_tau_from_expansion.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
