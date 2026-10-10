---
op: residue_crt
dim: residue
category: robust
in: matrix × signal
out: table
examples: [poc_residue_crt]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# residue_crt — RESIDUE `robust` op

- **データ種**: `matrix × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.residue_crt(residues, periods, weights=None, lo=0.0, hi=None) -> 'dict'` (実装を直接呼ぶなら `import residue; residue.residue_crt(residues, periods, weights=None, lo=0.0, hi=None) -> 'dict'`、台帳から引くなら `opsresidue.get("residue_crt")`)

## 使い方

Weighted robust CRT over real periods -> ``dict``.

Solve ``v ≡ residues[i] (mod periods[i])`` for ``v`` in ``[lo, hi)``.
``residues`` has the band axis first, shape ``(N,)`` or ``(N, ...)`` — every
trailing element is solved independently (one pixel, one sample).
``weights`` (same shape, or ``(N,)``) say how much each band is trusted —
typically the product of the two amplitudes the phase came from, so a band
with no contrast gets no vote.

Method: every candidate ``v = r_ref + k p_ref`` of the longest period inside
the range is scored by phasor agreement ``sum_i w_i cos(2 pi (v - r_i)/p_i)``
(the maximum-likelihood criterion for von-Mises phase noise); the best one is
refined by the inverse-variance-weighted mean of the signed residuals.

Returns ``{"value", "score", "margin", "residual", "n_candidates",
"unambiguous_range"}``: ``score`` in ``[-1, 1]`` (1 = all bands agree
exactly), ``margin`` = best minus runner-up score (small = the answer was a
near tie — treat as unreliable), ``residual`` per band in the units of
``v``. ``hi`` defaults to ``lo`` + the least common multiple of the periods
(when they are commensurate); a range wider than that is refused, because
two values in it would have identical residues.

Exactness: integer residues of pairwise-coprime integer periods reproduce
:func:`residue_integer_crt` exactly. Robustness: with periods ``Γ M_i`` (``M_i``
coprime integers) a value is recovered exactly whenever every residue error is
below ``Γ/4`` (Wang & Xia's bound); beyond it the margin collapses first.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_residue_crt](../../../../examples/poc_residue_crt.py) — `py -3.11 examples/poc_residue_crt.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`robust`)

[residue_fault_locate](residue_fault_locate.md)

---
*Provenance: residue.py — RESIDUE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
