---
op: gauss_cubature
dim: math
category: numerics
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# gauss_cubature — MATH `numerics` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gauss_cubature(n: 'int', dim: 'int' = 2, a=-1.0, b=1.0) -> 'dict'` (実装を直接呼ぶなら `import mathnumerics; mathnumerics.gauss_cubature(n: 'int', dim: 'int' = 2, a=-1.0, b=1.0) -> 'dict'`、台帳から引くなら `opsmath.get("gauss_cubature")`)

## 使い方

Gauss–Legendre のテンソル積で、箱 [a, b]^dim(a, b は軸ごとでも可)の求積の節点 (n^dim, dim) と重み。

画像の画素平均・ボリュームの体積積分・PSF の積分に。各軸で 2n−1 次までの多項式の積を**厳密に**積分する
(門: x^p y^q で p, q <= 2n−1 は厳密、どれかが 2n で誤差)。点の数は n^dim なので高次元では急に増える
(dim > 6 では低食い違い列の方が向く)。

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

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md)

## 同カテゴリ(`numerics`)

[erf](erf.md) · [erfc](erfc.md) · [bessel](bessel.md) · [gauss_quadrature](gauss_quadrature.md) · [chebyshev_coeffs_nd](chebyshev_coeffs_nd.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md) · [low_discrepancy](low_discrepancy.md) · [chebyshev_nodes](chebyshev_nodes.md)

---
*Provenance: mathnumerics.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
