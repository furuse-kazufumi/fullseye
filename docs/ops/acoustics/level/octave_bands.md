---
op: octave_bands
dim: acoustics
category: level
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# octave_bands — ACOUSTICS `level` op

- **データ種**: `` → `table`
- **呼び出し**: `import acoustics; acoustics.octave_bands(fraction=3, f_min=22.0, f_max=22050.0, base=10)` (または `opsacoustics.get("octave_bands")`)

## 使い方

Fractional-octave band centres and edges, from the defining construction.

The band system is a geometric progression through 1 kHz:
``f_c = 1000 * G**(x/b)`` for odd ``b`` and ``1000 * G**((2x+1)/(2b))`` for
even ``b``, with edges at ``f_c * G**(-+1/(2b))``. ``base=10`` uses
``G = 10**(3/10)`` (the base-ten system, in which ten third-octaves span
almost exactly a decade); ``base=2`` uses ``G = 2`` exactly. No published
table of centre frequencies is transcribed — the *exact* centres are
computed, which is why ``centers`` reads 1000.0, 1258.925, 1584.893 rather
than the 1000, 1250, 1600 a published series would give.

**The parity of ``fraction`` changes where 1 kHz sits, and this surprises
people.** With an odd ``b`` (1/1, 1/3) there is a band *centred* on exactly
1000.0 Hz. With an even ``b`` (1/2, 1/6, 1/12, 1/24) the offset in the
exponent means there is **no 1 kHz band at all** — instead 1000.0 Hz is
exactly a band *edge*, shared by two bands. Measured across
``fraction`` = 1, 2, 3, 6, 12, 24: a centre lands on 1000.0 for 1 and 3, and
a lower edge lands on it for 2, 6, 12 and 24, in every case to within
``rtol=1e-12``. That is the defining construction, not an artefact, and it
matters when a level is quoted "at 1 kHz": in an even system that number
comes from one of two adjacent half-bands, not from a band on the tone.

``nominal`` is the exact centre rounded to three significant figures, for
labelling only. It is a rounding, **not** the published nominal series, and
it differs from it: measured, the 1/1-octave centres round to 31.6, 63.1,
126.0, 251.0, 501.0, 1000.0, 2000.0, 3980.0, 7940.0, 15800.0, where the
published series has 125 and 250 where this has 126 and 251. Do arithmetic
with ``centers`` and supply your own labels if they have to match a report.

Returns a dict: ``centers``, ``lower``, ``upper``, ``nominal``, ``fraction``,
``base``, ``ratio`` (``G**(1/b)``), ``bandwidth`` (``upper - lower``),
``index`` (the integer ``x``).

Exact identities, asserted in the tests: ``upper/lower = G**(1/b)`` for every
band, ``center = sqrt(lower*upper)`` (the centre is the geometric mean of its
edges, by construction), and successive centres are in the ratio ``G**(1/b)``.
Measured for ``fraction=3, base=10`` over 22 Hz - 22.05 kHz (30 bands): the
band containing 1000 Hz has ``lower = 891.250938``, ``center = 1000.000000``,
``upper = 1122.018454``; ``upper/lower - G**(1/3) = 2.2e-16``;
``|center - sqrt(lower*upper)| <= 1.8e-12`` over all bands; and successive
centre ratios deviate from ``G**(1/3)`` by at most 6.7e-16. With ``base=2``
the octave centres come out exactly 31.25, 62.5, 125, 250, 500, 1000, 2000,
4000, 8000, 16000 Hz.

**Raises** ``ValueError``: ``fraction`` not an int in ``[1, 24]``, ``base``
not 2 or 10, non-positive or non-finite ``f_min`` / ``f_max``,
``f_min >= f_max``, and a request for more than :data:`MAX_BANDS` bands.

## 詳しい使い方ガイド

- [acoustic_condition_monitoring ファミリ ガイド](../guides/acoustic_condition_monitoring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[istft](../transform/istft.md)

## 同カテゴリ(`level`)

[octave_spectrum](octave_spectrum.md) · [weighting_response](weighting_response.md) · [apply_weighting](apply_weighting.md) · [equivalent_level](equivalent_level.md) · [percentile_level](percentile_level.md)

---
*Provenance: acoustics.py — ACOUSTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
