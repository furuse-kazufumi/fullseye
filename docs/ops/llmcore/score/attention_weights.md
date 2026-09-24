---
op: attention_weights
dim: llmcore
category: score
in: attnmap
out: attnmap
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_weights — LLMCORE `score` op

- **データ種**: `attnmap` → `attnmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_weights(scores, mask=None, window=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_weights(scores, mask=None, window=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_weights")`)

## 使い方

行ごとの softmax(マスクつき)→ attnmap。**行和は 1、mask 位置は厳密に 0**。

行ごとに最大値を引いてから指数を取る。これは飾りではない —— 引かずに ``exp`` すると
スコアが大きいとき**全行が inf/NaN になる**(実測: 96 行中 96 行)。引けば 0 行。

Args:
    scores: (T, T) float の生スコア(``attention_scores`` の出力)。
    mask: None(全対)/ ``"causal"``(下三角)/ ``"window"``(幅 ``window`` の因果窓)/
        (T, T) の bool 配列。True が「見てよい」。
    window: ``mask="window"`` のときの窓幅(自分を含む個数)。
Returns:
    attnmap (T, T) float: 各行が確率分布(和 1)。mask が False の位置は厳密に 0。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`attnmap` を入力に取れる)

[attention_apply](attention_apply.md)

## 同カテゴリ(`score`)

[attention_scores](attention_scores.md) · [attention_apply](attention_apply.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
