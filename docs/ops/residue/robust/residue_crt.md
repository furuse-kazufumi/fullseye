---
op: residue_crt
dim: residue
category: robust
in: matrix × signal
out: table
examples: [poc_itof_multifreq, poc_residue_crt]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# residue_crt — RESIDUE `robust` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.residue_crt(residues, periods, weights=None, lo=0.0, hi=None, on_outside='warn') -> 'dict'` (実装を直接呼ぶなら `import residue; residue.residue_crt(residues, periods, weights=None, lo=0.0, hi=None, on_outside='warn') -> 'dict'`、台帳から引くなら `opsresidue.get("residue_crt")`)

## 使い方

Weighted robust CRT over real periods -> ``dict``.

Solve ``v ≡ residues[i] (mod periods[i])`` for ``v`` in ``[lo, hi)``.
``residues`` has the band axis first, shape ``(N,)`` or ``(N, ...)`` — every
trailing element is solved independently (one pixel, one sample).
``weights`` (same shape, or ``(N,)``) say how much each band is trusted —
typically the product of the two amplitudes the phase came from, so a band
with no contrast gets no vote.

Method: per sample one band is the *reference* (Wang & Xia 2010, Sec. IV-A,
the remainder with the smallest noise variance; the variance of band ``i`` is
modelled as ``p_i^2 / w_i``, i.e. equal phase noise scaled by the weight, and
among equal-variance bands the one whose residue modulo ``Γ`` is closest to the
common remainder, eq. (55)/(58)). Every candidate ``v = r_ref + k p_ref`` inside
the range is scored by phasor agreement ``sum_i w_i cos(2 pi (v - r_i)/p_i)``
(the maximum-likelihood criterion for von-Mises phase noise); the best one is
refined by the inverse-variance-weighted mean of the signed residuals. A
candidate carries the reference's own error, so candidates up to ``Γ/4`` outside
``[lo, hi)`` are admitted (never so far that one value appears twice). Until
2026-10-15 the longest period was always the reference: with equal phase noise
that is the *noisiest* residue in units of ``v``, and in indirect ToF (16/80/120
MHz, σ_φ 0.33 rad) the folding error rate was 0.556 against 0.116 for trying
every hypothesis; now it is 0.116 (public raw data, 10 frames: 0.293 -> 0.131,
the same as the exhaustive decoder).

Guarantee (Wang & Xia 2010, eq. (47)): write the periods as ``Γ M_i`` (``Γ`` their
common factor, ``M_i`` integers). If every residue error is below ``Γ/4`` the
folding integers are exact and ``|value - v| < Γ/4`` whichever band is the
reference, because a wrong candidate moves at least one band by a non-zero multiple of
``Γ``, which strictly lowers that band's phasor term (if only zero-weight bands
tell two candidates apart, the margin is 0). In phase terms band ``i`` may err by
``2 pi (Γ/4) / p_i`` — least on the longest period. A sample whose residues modulo
``Γ`` do not fit in an arc shorter than ``Γ/2`` is provably outside that bound
(``within_bound`` False; the converse is not guaranteed — an error of a whole
``Γ`` is undetectable). ``on_outside`` says what happens then: ``"warn"``
(default, :class:`ResidueBoundWarning`), ``"raise"`` (``ValueError``), ``"nan"``
(value NaN, margin 0 for those samples) or ``"flag"`` (only ``within_bound``).
Incommensurate periods (explicit ``hi``) have no ``Γ`` and no guarantee: every
sample is outside.

Returns ``{"value", "score", "margin", "residual", "n_candidates",
"unambiguous_range", "gamma", "error_bound", "phase_bound_rad", "reference",
"within_bound"}``: ``score`` in ``[-1, 1]`` (1 = all bands agree exactly),
``margin`` = best minus runner-up score (small = the answer was a near tie —
treat as unreliable), ``residual`` per band in the units of ``v``; ``gamma`` =
``Γ``, ``error_bound`` = ``Γ/4``, ``phase_bound_rad`` per band, ``reference`` = the
band index used per sample. ``hi`` defaults to ``lo`` + the least common multiple
of the periods (when they are commensurate); a range wider than that is refused,
because two values in it would have identical residues.

Exactness: integer residues of pairwise-coprime integer periods reproduce
:func:`residue_integer_crt` exactly.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_itof_multifreq](../../../../examples/poc_itof_multifreq.py) — `py -3.11 examples/poc_itof_multifreq.py`
- [poc_residue_crt](../../../../examples/poc_residue_crt.py) — `py -3.11 examples/poc_residue_crt.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`robust`)

[residue_fault_locate](residue_fault_locate.md)

---
*Provenance: residue.py — RESIDUE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
