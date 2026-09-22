---
op: fly_matched_filter
dim: flyvision
category: selfmotion
in: table
out: matrix
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# fly_matched_filter — FLYVISION `selfmotion` op

- **データ種**: `table` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_matched_filter(lattice, axis=(0.0, 0.0, 1.0), motion='rotation', depth_m=1.0)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_matched_filter(lattice, axis=(0.0, 0.0, 1.0), motion='rotation', depth_m=1.0)`、台帳から引くなら `opsflyvision.get("fly_matched_filter")`)

## 使い方

The flow field one unit of self-motion writes on the eye — the template a
wide-field neuron is matched to.

Krapp & Hengstenberg measured the local motion sensitivity of single
lobula-plate tangential cells across the whole visual field and found a
structured vector field, one that looks like the optic flow of a particular
rotation of the fly (*Nature* 384:463, 1996). Reading self-motion out of such
a cell is then a matched filter (Franz & Krapp, *Biol. Cybern.* 83:185, 2000):
correlate the measured flow against the template of the motion you are asking
about. This op builds the template, for the isotropic world model — every
point at the same distance — which is the case in which the rotation template
is exactly the geometry and nothing is assumed about the scene:

  * ``motion="rotation"``: one radian per second about the unit vector *axis*
    moves the viewing direction ``d`` at ``-axis x d``, which is already
    tangent to the sphere. Its length is ``sin`` of the angle between the axis
    and the line of sight, so the template is zero on the axis itself.
  * ``motion="translation"``: one metre per second along *axis*, with every
    point at *depth_m* metres, moves it at ``-(v - (v.d) d)/Z``. The depth is
    an input, not a measurement — translation flow and distance are the same
    unknown and no eye can separate them from one frame pair.

lattice: a :func:`fly_hex_lattice` result. axis: the rotation axis or
translation direction in body coordinates (x forward, y left, z up); it is
normalised, and a zero vector is refused. depth_m: the uniform distance,
``motion="translation"`` only.

Returns ``(n, 2)`` float64 — the azimuth and elevation components of the flow
at each ommatidium, in radians per second, the same layout
:func:`fly_flow_from_directions` returns.

Ground truth: for a rotation, ``|f| = sin(angle(axis, d))`` exactly, so it is
0 where the line of sight is along the axis and 1 where it is perpendicular;
and the flow is perpendicular to both the axis and the line of sight. For a
translation, ``|f| = sin(angle)/depth`` and the flow points away from the
direction of travel (the focus of expansion is where the template vanishes).

**Raises** ``ValueError``: a malformed *lattice*, an *axis* that is not three
finite numbers or is zero-length, an unknown *motion*, and a non-positive
*depth_m*.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[fly_lamina_filter](../lamina/fly_lamina_filter.md) · [fly_onoff_split](../lamina/fly_onoff_split.md) · [fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_egomotion_from_flow](fly_egomotion_from_flow.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`selfmotion`)

[fly_egomotion_from_flow](fly_egomotion_from_flow.md) · [fly_eye_merge](fly_eye_merge.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
