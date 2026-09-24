---
op: attention_grouped
dim: llmcore
category: attend
in: tokens × tokens × tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_grouped — LLMCORE `attend` op

- **データ種**: `tokens × tokens × tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_grouped(query, key, value, n_heads: 'int', n_kv_heads: 'int', mask=None, window=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_grouped(query, key, value, n_heads: 'int', n_kv_heads: 'int', mask=None, window=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_grouped")`)

## 使い方

頭を束ねる注意(GQA)→ tokens。**n_kv_heads == n_heads で MHA、== 1 で MQA に厳密一致**。

Ainslie ら 2023。query は ``n_heads`` 本に割り、key/value は ``n_kv_heads`` 本しか
持たずに使い回す。両端が既存の 2 つ(MHA / MQA)に**厳密に**落ちる(どちらも 0.0e+00)
ので、「中間を取る」という主張が端で検算できる。

Args:
    query: (T, n_heads·dh) float。頭ごとに幅 dh で並んでいる。
    key: (S, n_kv_heads·dh) float。
    value: (S, n_kv_heads·dh) float。
    n_heads: query の頭の数。``n_kv_heads`` の倍数であること。
    n_kv_heads: key/value の頭の数。1 なら MQA、``n_heads`` なら MHA。
    mask: None / ``"causal"`` / ``"window"`` / (T, S) の bool 配列。
    window: ``mask="window"`` のときの窓幅。
Returns:
    tokens (T, n_heads·dh) float: 頭ごとの出力を横に連結したもの。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rms_norm](../prepare/rms_norm.md) · [rope_rotate](../prepare/rope_rotate.md) · [attention_scores](../score/attention_scores.md) · [attention_apply](../score/attention_apply.md) · [attention_softmax](attention_softmax.md) · [attention_tiled](attention_tiled.md) · [attention_linear](attention_linear.md) · [kv_cache_decode](../decode/kv_cache_decode.md)

## 同カテゴリ(`attend`)

[attention_softmax](attention_softmax.md) · [attention_tiled](attention_tiled.md) · [attention_linear](attention_linear.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
