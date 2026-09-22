---
op: fly_hs_readout
dim: flyvision
category: integrate
in: matrix × table
out: measurement
examples: [poc_fly_vision]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# fly_hs_readout — FLYVISION `integrate` op

- **データ種**: `matrix × table` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.fly_hs_readout(responses, lattice, n_pref, el_min_deg=0.0, rectify=True)` (実装を直接呼ぶなら `import flyvision; flyvision.fly_hs_readout(responses, lattice, n_pref, el_min_deg=0.0, rectify=True)`、台帳から引くなら `opsflyvision.get("fly_hs_readout")`)

## 使い方

Horizontal-system wide-field readout: opponent sum over the upper field.

Given a stack of motion-detector responses over the ommatidia — the first
*n_pref* rows the preferred-direction type, the rest the anti-preferred — the
opponent readout over the ommatidia above the horizon is::

    (a - b) / (a + b + 1e-6)

where ``a`` and ``b`` are the (optionally rectified) totals of the preferred
and anti-preferred responses over the columns with ``el > el_min_deg``.

Only the upper visual field is used because the ground flow of forward motion
is ``1/distance`` while the rotational flow it must be separated from is
distance-independent: an eye 1.2 mm above the floor sees floor flow of
330-1000 deg/s, above the ~200 deg/s bandwidth of the motion detectors, so the
lower field carries speed the correlator cannot read and is excluded.

responses: a ``(k, n)`` matrix of responses, ``n`` matching the lattice.
lattice:   the dict returned by :func:`fly_hex_lattice`.
n_pref:    how many leading rows are the preferred-direction type
           (``1 <= n_pref < k``).
el_min_deg: the horizon; only ommatidia above it contribute.
rectify:   half-wave rectify (clip negatives to 0) before summing.

Returns the opponent ratio as a float in ``[-1, 1]``.

Ground truth: with the preferred rows active only in the upper field and the
anti-preferred rows silent, the readout is ``+1`` (and the sign and value
match the hand calculation); an ``el_min_deg`` above every ommatidium raises
(pinned in the tests).

**Raises** ``ValueError``: a non-2-D / empty / non-finite *responses*, a
*responses* over the element cap, a *lattice* that is not a
:func:`fly_hex_lattice` result, a column count not matching the lattice, a
*n_pref* outside ``[1, k-1]``, a non-real *el_min_deg*, a non-bool *rectify*,
and an *el_min_deg* above every ommatidium (no upper field to read).

## 詳しい使い方ガイド

- [fly_vision ファミリ ガイド](../guides/fly_vision.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_fly_vision](../../../../examples/poc_fly_vision.py) — `py -3.11 examples/poc_fly_vision.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`integrate`)

—

---
*Provenance: flyvision.py — FLYVISION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
