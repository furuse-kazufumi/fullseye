---
op: interp_barycentric
dim: math
category: numerics
in: signal × signal × signal
out: signal
examples: [numerics_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# interp_barycentric — MATH `numerics` op

- **データ種**: `signal × signal × signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.interp_barycentric(xk, yk, x) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathnumerics; mathnumerics.interp_barycentric(xk, yk, x) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("interp_barycentric")`)

## 使い方

点 (xk, yk) を通る多項式(次数 len−1)を、重心公式で x に評価する(Berrut & Trefethen 2004)。

係数を経由しない(Vandermonde 行列は解かない)ので高次でも数値的に安定。等間隔点では
**Runge 現象**(端の振動)がそのまま出る —— それは公式の欠陥ではなく、点の置き方の問題。
門: 次数 len−1 以下の多項式は厳密に再現する。

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

- [numerics_tour](../../../../examples/numerics_tour.py) — `py -3.11 examples/numerics_tour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [interp_scattered](../interp_poly/interp_scattered.md)

## 同カテゴリ(`numerics`)

[erf](erf.md) · [erfc](erfc.md) · [bessel](bessel.md) · [gauss_quadrature](gauss_quadrature.md) · [gauss_cubature](gauss_cubature.md) · [chebyshev_coeffs_nd](chebyshev_coeffs_nd.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md) · [low_discrepancy](low_discrepancy.md)

---
*Provenance: mathnumerics.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
