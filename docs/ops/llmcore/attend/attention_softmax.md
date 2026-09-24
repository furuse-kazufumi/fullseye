---
op: attention_softmax
dim: llmcore
category: attend
in: tokens × tokens × tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_softmax — LLMCORE `attend` op

- **データ種**: `tokens × tokens × tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_softmax(query, key, value, mask=None, window=None, scale=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_softmax(query, key, value, mask=None, window=None, scale=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_softmax")`)

## 使い方

一括の注意(参照実装)→ tokens。**この族の答え合わせの基準**。

(T, T) のスコア行列を実際に作ってから softmax する、いちばん素直な書き方。
``attention_tiled`` / ``attention_linear`` / ``attention_grouped`` はこれと
一致することで正しさを示す。

Args:
    query: (T, d) float。
    key: (S, d) float。
    value: (S, dv) float。
    mask: None / ``"causal"`` / ``"window"`` / (T, S) の bool 配列。
    window: ``mask="window"`` のときの窓幅。
    scale: スコアの倍率。None なら 1/√d。
Returns:
    tokens (T, dv) float: 注意で混ぜた列。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rms_norm](../prepare/rms_norm.md) · [rope_rotate](../prepare/rope_rotate.md) · [attention_scores](../score/attention_scores.md) · [attention_apply](../score/attention_apply.md) · [attention_tiled](attention_tiled.md) · [attention_linear](attention_linear.md) · [attention_grouped](attention_grouped.md) · [kv_cache_decode](../decode/kv_cache_decode.md)

## 同カテゴリ(`attend`)

[attention_tiled](attention_tiled.md) · [attention_linear](attention_linear.md) · [attention_grouped](attention_grouped.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
