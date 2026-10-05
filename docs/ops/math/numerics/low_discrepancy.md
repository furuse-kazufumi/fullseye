---
op: low_discrepancy
dim: math
category: numerics
in: 
out: matrix
examples: [numerics_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# low_discrepancy — MATH `numerics` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.low_discrepancy(n: 'int', dim: 'int' = 2, kind: 'str' = 'halton', *, skip: 'int' = 0, seed: 'int | None' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathnumerics; mathnumerics.low_discrepancy(n: 'int', dim: 'int' = 2, kind: 'str' = 'halton', *, skip: 'int' = 0, seed: 'int | None' = None) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("low_discrepancy")`)

## 使い方

[0, 1)^dim の低食い違い点列 (n, dim)。

* ``"halton"`` —— 座標ごとに異なる素数を基数にした van der Corput 列(自前の実装、決定的)。
  ``skip`` 個を読み飛ばす(先頭の 0 を避けるなら 1)。高次元(> 8 程度)では座標間に縞が出るので注意。
* ``"sobol"`` —— scipy.stats.qmc.Sobol(``seed`` を与えるとスクランブル)。n は 2 の冪が最良。
* ``"random"`` —— 比較用の一様乱数(``seed`` 必須、再現性のため)。

門: なめらかな関数の積分誤差は乱数の N^{−1/2} より速く減る / 星形食い違い量が乱数より小さい。

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [mat_svd](../linalg/mat_svd.md) · [mat_eigh](../linalg/mat_eigh.md) · [mat_pinv](../linalg/mat_pinv.md) · [mat_cond](../linalg/mat_cond.md) · [mat_lu](../linalg/mat_lu.md) · [mat_qr](../linalg/mat_qr.md)

## 同カテゴリ(`numerics`)

[erf](erf.md) · [erfc](erfc.md) · [bessel](bessel.md) · [gauss_quadrature](gauss_quadrature.md) · [gauss_cubature](gauss_cubature.md) · [chebyshev_coeffs_nd](chebyshev_coeffs_nd.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md) · [chebyshev_nodes](chebyshev_nodes.md)

---
*Provenance: mathnumerics.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
