---
op: bearing_defect_frequencies
dim: acoustics
category: bearing
in: 
out: table
examples: [acoustic_condition_monitoring]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# bearing_defect_frequencies — ACOUSTICS `bearing` op

- **データ種**: `` → `table`
- **呼び出し**: `import acoustics; acoustics.bearing_defect_frequencies(rpm=1800.0, n_elements=9, element_diameter=8.0, pitch_diameter=40.0, contact_angle_deg=0.0)` (または `opsacoustics.get("bearing_defect_frequencies")`)

## 使い方

The four characteristic rates of a rolling-element bearing, from geometry.

Derived, not tabulated. Under pure rolling the cage advances at half the sum
of the race surface speeds, which with ``r = d/D cos(alpha)`` gives, per
shaft revolution rate ``f_r = rpm/60``:

* ``FTF``  (cage / fundamental train) ``= f_r (1 - r) / 2``
* ``BPFO`` (ball pass, outer race)    ``= N f_r (1 - r) / 2 = N * FTF``
* ``BPFI`` (ball pass, inner race)    ``= N f_r (1 + r) / 2``
* ``BSF``  (ball spin)                ``= f_r (1 - r^2) D / (2 d)``

Two exact identities fall out and are asserted in the tests, because they
catch a transposed ``d`` and ``D`` immediately: ``BPFO + BPFI = N f_r``
exactly, and ``BPFO = N * FTF`` exactly. Measured for the defaults
(1800 rpm, 9 elements, d = 8, D = 40, alpha = 0): ``ratio = 0.200000``,
``f_r = 30.000000``, ``FTF = 12.000000``, ``BPFO = 108.000000``,
``BPFI = 162.000000``, ``BSF = 72.000000`` Hz, with
``BPFO + BPFI - 9 f_r = 0.000e+00`` and ``BPFO - 9 FTF = 0.000e+00`` —
exactly zero in float64, not merely small.

Returns a dict with ``shaft_hz``, ``ftf_hz``, ``bpfo_hz``, ``bpfi_hz``,
``bsf_hz``, ``ratio`` (``d/D cos alpha``), and the inputs echoed back.
Also ``bsf_hz_2x``: a rolling element normally strikes *both* races per
spin, so a spall on the element itself is usually seen at ``2 * BSF``, and
reporting only ``BSF`` is the classic way to miss it.

These are the **no-slip kinematic** rates. Real bearings slip by roughly a
percent, so an observed line within about 1 % of one of these is a match and
an exact match is a coincidence; that tolerance is the caller's to apply.

**Raises** ``ValueError``: non-real / string / bool scalars, ``rpm <= 0``,
``n_elements`` not an int >= 2, non-positive diameters, an
``element_diameter >= pitch_diameter`` (geometrically impossible — the
rolling elements would not fit inside the pitch circle, and the usual cause
is the two arguments being swapped, which otherwise returns a negative FTF
and a plausible-looking BPFI), and ``|contact_angle_deg| >= 90``.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [acoustic_condition_monitoring](../../../../examples/acoustic_condition_monitoring.py) — `py -3.11 examples/acoustic_condition_monitoring.py`

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md)

## 同カテゴリ(`bearing`)

[envelope_spectrum](envelope_spectrum.md) · [spectral_kurtosis](spectral_kurtosis.md) · [cepstrum](cepstrum.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
