---
op: dynsys_bifurcation_map
dim: math
category: dynsys
in: 
out: pairs
examples: [poc_what_a_picture_cannot_check]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# dynsys_bifurcation_map — MATH `dynsys` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dynsys_bifurcation_map(kind='logistic', r_lo=2.5, r_hi=4.0, n_r=800, burn_in=300, keep=100, x0=0.5)` (実装を直接呼ぶなら `import mathops; mathops.dynsys_bifurcation_map(kind='logistic', r_lo=2.5, r_hi=4.0, n_r=800, burn_in=300, keep=100, x0=0.5)`、台帳から引くなら `opsmath.get("dynsys_bifurcation_map")`)

## 使い方

The orbit diagram of a 1-D map — period doubling, as points you can count.

For each parameter value the map is iterated ``burn_in`` times (discarded) and
the next ``keep`` states are returned. ``logistic`` is ``r x (1 - x)``,
``sine`` is ``r sin(pi x)``, ``tent`` is ``r min(x, 1-x) * 2``.

★**Why this earns its place**: the first period-doubling values are known
exactly for the logistic map — ``r = 3`` and ``r = 1 + sqrt 6 = 3.449489...``
— and the ratio of successive intervals tends to **Feigenbaum's constant**
``4.669201...``, which is universal. Counting distinct states per ``r`` turns
the picture into integers (1, 2, 4, 8, ...) that can be checked.

Returns a ``pairs`` array of ``(r, x)``.

**Raises** ``ValueError``: unknown map; ``r_lo >= r_hi``; non-positive counts;
a grid over the cap; ``x0`` outside the unit interval.

HALCON: no operator.

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

[ode_flow_states](ode_flow_states.md) · [ode_vector_field_grid](ode_vector_field_grid.md) · [dynsys_poincare_section](dynsys_poincare_section.md) · [dynsys_lyapunov_spectrum](dynsys_lyapunov_spectrum.md) · [dynsys_correlation_dimension](dynsys_correlation_dimension.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
