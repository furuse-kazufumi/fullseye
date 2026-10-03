---
op: mat_logm
dim: math
category: estimation
in: matrix
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# mat_logm — MATH `estimation` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.mat_logm(A) -> 'np.ndarray'` (実装を直接呼ぶなら `import mathestimation; mathestimation.mat_logm(A) -> 'np.ndarray'`、台帳から引くなら `opsmath.get("mat_logm")`)

## 使い方

行列の主対数 log A(e^X = A となる X のうち固有値の虚部が (−π, π] のもの、scipy)。

負の実固有値を持つ行列は実の主対数を持たない → ValueError(複素数を黙って返さない)。

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [mat_svd](../linalg/mat_svd.md) · [mat_eigh](../linalg/mat_eigh.md) · [mat_pinv](../linalg/mat_pinv.md) · [mat_cond](../linalg/mat_cond.md) · [mat_lu](../linalg/mat_lu.md) · [mat_qr](../linalg/mat_qr.md)

## 同カテゴリ(`estimation`)

[assign_hungarian](assign_hungarian.md) · [hist_distance](hist_distance.md) · [stat_ttest_paired](stat_ttest_paired.md) · [stat_ttest_welch](stat_ttest_welch.md) · [stat_ks_test](stat_ks_test.md) · [stat_chi2_gof](stat_chi2_gof.md) · [crlb_gaussian](crlb_gaussian.md) · [kalman_smooth](kalman_smooth.md)

---
*Provenance: mathestimation.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
