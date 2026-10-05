---
op: hist_distance
dim: math
category: estimation
in: signal × signal
out: measurement
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# hist_distance — MATH `estimation` op

- **データ種**: `signal × signal` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.hist_distance(p, q, metric: 'str' = 'kl', *, eps: 'float' = 1e-12) -> 'float'` (実装を直接呼ぶなら `import mathestimation; mathestimation.hist_distance(p, q, metric: 'str' = 'kl', *, eps: 'float' = 1e-12) -> 'float'`、台帳から引くなら `opsmath.get("hist_distance")`)

## 使い方

2 つのヒストグラム(非負、和で正規化する)の距離・発散。

* ``"kl"`` —— Kullback–Leibler D(p‖q) = Σ p log(p/q)(非対称。q が 0 で p が正だと無限大 → eps で床)。
* ``"js"`` —— Jensen–Shannon(対称、0..log 2、平方根は距離の公理を満たす)。
* ``"bhattacharyya"`` —— −log Σ √(pq)。 ``"hellinger"`` —— √(1 − Σ √(pq))(0..1)。
* ``"chi2"`` —— ½ Σ (p−q)²/(p+q)。
門: 正規分布どうしの KL の閉じた式 / KL ≥ 0 で等号は同一分布 / MI = KL(p_xy ‖ p_x p_y)。

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

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`estimation`)

[assign_hungarian](assign_hungarian.md) · [stat_ttest_paired](stat_ttest_paired.md) · [stat_ttest_welch](stat_ttest_welch.md) · [stat_ks_test](stat_ks_test.md) · [stat_chi2_gof](stat_chi2_gof.md) · [crlb_gaussian](crlb_gaussian.md) · [kalman_smooth](kalman_smooth.md) · [mat_expm](mat_expm.md)

---
*Provenance: mathestimation.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
