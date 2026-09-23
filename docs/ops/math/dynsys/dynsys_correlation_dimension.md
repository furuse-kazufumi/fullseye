---
op: dynsys_correlation_dimension
dim: math
category: dynsys
in: points
out: measurement
examples: [poc_what_a_picture_cannot_check]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# dynsys_correlation_dimension — MATH `dynsys` op

- **データ種**: `points` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.dynsys_correlation_dimension(points, n_radii=24, r_lo=None, r_hi=None, max_points=4000, seed=0)` (実装を直接呼ぶなら `import mathops; mathops.dynsys_correlation_dimension(points, n_radii=24, r_lo=None, r_hi=None, max_points=4000, seed=0)`、台帳から引くなら `opsmath.get("dynsys_correlation_dimension")`)

## 使い方

Grassberger-Procaccia correlation dimension — the slope of ``log C(r)``.

``C(r)`` is the fraction of point pairs closer than ``r``; for a self-similar
set it grows like ``r**D``, and *D* is read off the straight part of the
log-log plot (fitted on the middle 60 % of the radii, where the curve is free
of the small-``r`` noise floor and the large-``r`` saturation).

★**Why this earns its place**: unlike box counting it needs no grid, and its
answers are known for simple sets — a circle gives **1**, a filled square
**2**, a Cantor set ``log2/log3 = 0.6309``. It measures a different quantity
from the existing ``fractal_dimension`` (box counting), so the two are an
independent pair rather than two names for one number.

Returns a ``measurement``: the fitted dimension.

**Raises** ``ValueError``: fewer than 32 points; not a 2-D array; non-finite
input; a degenerate cloud (every point identical); a radius range that leaves
no pairs.

Limits: sub-sampled to *max_points* (pairs grow quadratically). ★The
dominant error is **not** the sub-sampling but the **radius window**: the
default range is the 1st-25th percentile of pair distances, and on a *bounded*
set its upper end runs into the boundary, where ``C(r)`` saturates and flattens
the slope. Measured on a unit square (true D = 2): 1.879 with the default
window and 1.873 / 1.879 / 1.871 at 400 / 1,500 / 3,000 points —— more points
do **not** help; narrowing the window to ``r_lo=0.01, r_hi=0.1`` gives 1.947
and ``0.002 / 0.05`` gives 2.050. Pass *r_lo* / *r_hi* explicitly when the
answer matters, and report the window with the number.

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

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`dynsys`)

[ode_flow_states](ode_flow_states.md) · [ode_vector_field_grid](ode_vector_field_grid.md) · [dynsys_poincare_section](dynsys_poincare_section.md) · [dynsys_lyapunov_spectrum](dynsys_lyapunov_spectrum.md) · [dynsys_bifurcation_map](dynsys_bifurcation_map.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
