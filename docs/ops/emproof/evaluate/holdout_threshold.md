---
op: holdout_threshold
dim: emproof
category: evaluate
in: signal × signal × signal × signal
out: table
examples: [poc_em_second_opinion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# holdout_threshold — EMPROOF `evaluate` op

- **データ種**: `signal × signal × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.holdout_threshold(train_pos, train_neg, test_pos, test_neg, target_fpr: 'float' = 0.05) -> 'dict'` (実装を直接呼ぶなら `import emproof; emproof.holdout_threshold(train_pos, train_neg, test_pos, test_neg, target_fpr: 'float' = 0.05) -> 'dict'`、台帳から引くなら `opsemproof.get("holdout_threshold")`)

## 使い方

閾値を**訓練側で選び、評価は別の側で**測る(score が高いほど「疑わしい」)。

``tau`` = 訓練の負例(仕込んでいない成分・対)の偽陽性率が ``target_fpr`` 以下になる最小の閾値
(負例スコアの上位 ``target_fpr`` 分位)。返すのは ``tau`` と、訓練・評価それぞれの AUC・TPR・FPR、件数。
評価側の数字だけを主張に使う ―― 閾値を選んだ側で測った TPR は必ず楽観する(evolve の holdout 規律を
op に切り出したもの)。AUC は Mann–Whitney(同点 0.5)。

>>> r = holdout_threshold(tr_pos, tr_neg, te_pos, te_neg, target_fpr=0.05)
>>> r["tau"], r["test_auc"], r["test_tpr"], r["test_fpr"]

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_second_opinion](../../../../examples/poc_em_second_opinion.py) — `py -3.11 examples/poc_em_second_opinion.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`evaluate`)

—

---
*Provenance: emproof.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
