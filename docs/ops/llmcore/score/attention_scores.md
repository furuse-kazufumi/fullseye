---
op: attention_scores
dim: llmcore
category: score
in: tokens × tokens
out: attnmap
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_scores — LLMCORE `score` op

- **データ種**: `tokens × tokens` → `attnmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_scores(query, key, scale=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_scores(query, key, scale=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_scores")`)

## 使い方

生の注意スコア QKᵀ/√d → attnmap (T, S)。

Args:
    query: (T, d) float。問い合わせる側。
    key: (S, d) float。引かれる側。d は query と同じ。
    scale: スコアの倍率。None なら 1/√d(Vaswani ら 2017 —— 内積が d に比例して
        育ち softmax が尖るのを打ち消す)。
Returns:
    attnmap (T, S) float: softmax にかける前の生のスコア。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`attnmap` を入力に取れる)

[attention_weights](attention_weights.md) · [attention_apply](attention_apply.md)

## 同カテゴリ(`score`)

[attention_weights](attention_weights.md) · [attention_apply](attention_apply.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
