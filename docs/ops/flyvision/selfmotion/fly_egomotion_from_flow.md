---
op: fly_egomotion_from_flow
dim: flyvision
category: selfmotion
in: matrix × table
out: table
examples: [poc_fly_optomotor_steering]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fly_egomotion_from_flow — FLYVISION `selfmotion` op

- **データ種**: `matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_egomotion_from_flow(flow, lattice, axes=None, weights=None)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_egomotion_from_flow(flow, lattice, axes=None, weights=None)`、台帳から引くなら `opsflyvision.get("fly_egomotion_from_flow")`)

## 使い方

Least-squares rotation of the eye from its flow field — and how badly the
eye's own shape conditions the answer.

Given the flow ``f_i`` at known viewing directions ``d_i``, a pure rotation
``w`` predicts ``f_i = -(w x d_i)``, which is **linear in w**: projecting on
the tangent basis gives ``f_az = -w . (d x e_az)`` and
``f_el = -w . (d x e_el)``, so the estimate is one ``2n x 3`` least-squares
solve with no iteration and no starting guess (Franz et al.'s linear
egomotion estimate, *Biol. Cybern.* 2004).

The catch is not the algebra, it is the eye. A single patch of ommatidia sees
a small piece of the sphere, and over a small piece the flow of a yaw and the
flow of a sideways translation — or of a pitch — look nearly the same. This
op therefore returns the **condition number** of that solve next to the
answer, so that "the fit converged" and "the fit was identifiable" stay
separate claims.

flow: ``(n, 2)`` azimuth/elevation components per ommatidium
(:func:`fly_flow_from_directions` or :func:`fly_matched_filter`).
lattice: the eye they were measured on.
axes: ``None`` to solve for the full 3-D rotation, or a ``(k, 3)`` array of
axes to restrict the fit to (``[[0, 0, 1]]`` = yaw only, the well-conditioned
question a forward-looking eye can actually answer).
weights: ``None`` or ``(n,)`` non-negative per-ommatidium weights — a
confidence, e.g. the local contrast, or zeros to drop the rim.

Returns a dict::

    {"omega_rad_s": (3,), "yaw_rad_s": float, "pitch_rad_s": float,
     "roll_rad_s": float, "residual_rms": float, "flow_rms": float,
     "explained": float, "condition": float, "n_ommatidia": int}

with yaw about +z (left positive), pitch about +y, roll about +x, and
``explained = 1 - residual_rms/flow_rms`` (1.0 = the flow is exactly a
rotation, 0.0 = the fit explains none of it).

Ground truth: handed a :func:`fly_matched_filter` template scaled by a known
rate, it returns that rate to machine precision and ``explained = 1``; handed
a pure translation field it returns a small rate with a low ``explained``; and
the condition number of a narrow forward eye is large (the tests measure it)
while the yaw-only fit is near 1.

**Raises** ``ValueError``: a *flow* that is not ``(n, 2)`` for this lattice,
non-finite entries, a malformed *axes* / *weights*, all-zero weights, and a
lattice with fewer ommatidia than the fit has unknowns.

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_optomotor_steering](../../../../examples/poc_fly_optomotor_steering.py) — `py -3.11 examples/poc_fly_optomotor_steering.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fly_t4t5_field](../direction/fly_t4t5_field.md) · [fly_flow_from_directions](../direction/fly_flow_from_directions.md) · [fly_matched_filter](fly_matched_filter.md) · [fly_eye_merge](fly_eye_merge.md) · [fly_hex_resample](../sample/fly_hex_resample.md) · [fly_hs_readout](../integrate/fly_hs_readout.md)

## 同カテゴリ(`selfmotion`)

[fly_matched_filter](fly_matched_filter.md) · [fly_eye_merge](fly_eye_merge.md)

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
