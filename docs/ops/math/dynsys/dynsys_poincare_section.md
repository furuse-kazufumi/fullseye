---
op: dynsys_poincare_section
dim: math
category: dynsys
in: table
out: pairs
examples: [poc_what_a_picture_cannot_check]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# dynsys_poincare_section — MATH `dynsys` op

- **データ種**: `table` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.dynsys_poincare_section(states, axis=2, value=None, direction=1)` (実装を直接呼ぶなら `import mathops; mathops.dynsys_poincare_section(states, axis=2, value=None, direction=1)`、台帳から引くなら `opsmath.get("dynsys_poincare_section")`)

## 使い方

Where a trajectory crosses a plane — with the crossing point interpolated.

Takes the ``x`` block of :func:`ode_flow_states` and returns the points where
coordinate *axis* crosses *value* in the given *direction* (+1 upward, -1
downward, 0 either). The crossing is found by **linear interpolation between
the two straddling samples**, not by taking the nearer sample — otherwise the
section is quantised by the step size and a periodic orbit looks like a cloud.

★**Why this earns its place**: a periodic orbit must give **one** point (to
within the interpolation error), a period-2 orbit two, and a chaotic one a
fractal set. That is a check with a number in it, unlike "the picture looks
like a strange attractor".

Returns a ``pairs`` array of the remaining coordinates at each crossing.

**Raises** ``ValueError``: states not (S, n) with S >= 2; axis out of range;
direction not in (-1, 0, 1); non-finite input; no crossing found (reported,
not returned as an empty array that a caller may read as "no orbit").

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

- [poc_what_a_picture_cannot_check](../../../../examples/poc_what_a_picture_cannot_check.py) — `py -3.11 examples/poc_what_a_picture_cannot_check.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[neighbour_index_gaps](../construct/neighbour_index_gaps.md) · [curve_locality](../construct/curve_locality.md)

## 同カテゴリ(`dynsys`)

[ode_flow_states](ode_flow_states.md) · [ode_vector_field_grid](ode_vector_field_grid.md) · [dynsys_lyapunov_spectrum](dynsys_lyapunov_spectrum.md) · [dynsys_bifurcation_map](dynsys_bifurcation_map.md) · [dynsys_correlation_dimension](dynsys_correlation_dimension.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
