---
op: wave_nodal_lines
dim: math
category: wave
in: matrix
out: mask
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# wave_nodal_lines — MATH `wave` op

- **データ種**: `matrix` → `mask`
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_nodal_lines(field, tol=0.0)` (実装を直接呼ぶなら `import mathops; mathops.wave_nodal_lines(field, tol=0.0)`、台帳から引くなら `opsmath.get("wave_nodal_lines")`)

## 使い方

Where a signed field changes sign — the nodal set, as a mask.

A pixel is marked when it differs in sign from its right or lower neighbour
(or is within *tol* of zero). That is the discrete version of "the sand
collects where the plate does not move".

★**Why this earns its place**: the count is predictable. A plain ``(m, n)``
rectangular mode has ``m-1`` interior nodal lines in one direction and ``n-1``
in the other, so the mask can be graded against integers rather than by eye.

Returns a ``mask``.

**Raises** ``ValueError``: not a 2-D array; non-finite values; negative *tol*.

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`mask` を入力に取れる)

—

## 同カテゴリ(`wave`)

[wave_membrane_mode](wave_membrane_mode.md) · [wave_mode_frequencies](wave_mode_frequencies.md) · [wave_two_slit](wave_two_slit.md) · [wave_fringe_period](wave_fringe_period.md) · [wave_grating_orders](wave_grating_orders.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
