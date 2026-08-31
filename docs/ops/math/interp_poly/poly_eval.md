---
op: poly_eval
dim: math
category: interp_poly
in: signal × signal
out: signal
examples: [math_metrology, signal_filter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# poly_eval — MATH `interp_poly` op

- **データ種**: `signal × signal` → `signal`
- **呼び出し**: `import mathops; mathops.poly_eval(coeffs, x)` (または `opsmath.get("poly_eval")`)

## 使い方

Evaluate a polynomial (coefficients highest-power-first) at *x*.

*coeffs* is the 1-D array :func:`poly_fit` returns in ``"coeffs"`` (or any
hand-written one, ``[c_d, ..., c_1, c_0]``); *x* is a finite scalar or 1-D
array. A scalar returns a Python float, an array returns float64.
Evaluation is by Horner's scheme (``np.polyval``) — numerically the right
way to evaluate, though it cannot repair a badly-conditioned *fit* (see
:func:`poly_fit`'s ``cond``).

HALCON: no polynomial tuple operator (compose ``tuple_pow`` + arithmetic).

Raises ValueError when a finite input overflows float64 — a degree-*d*
polynomial at ``|x|`` well above 1 grows like ``|x|**d``, so mixing up the
two arguments (a long signal used as coefficients) silently produced ``inf``
before this guard (chain fuzzer wave-7: 256 coefficients evaluated at
``|x|<=22`` -> ``22**255``). An unusable ``inf`` must not flow downstream.

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

- [math_metrology](../../../../examples/math_metrology.py) — `py -3.11 examples/math_metrology.py`
- [signal_filter](../../../../examples/signal_filter.py) — `py -3.11 examples/signal_filter.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](interp_linear.md) · [interp_cubic](interp_cubic.md) · [poly_fit](poly_fit.md)

## 同カテゴリ(`interp_poly`)

[interp_linear](interp_linear.md) · [interp_cubic](interp_cubic.md) · [poly_fit](poly_fit.md) · [poly_roots](poly_roots.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
