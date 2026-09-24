---
op: attention_tiled
dim: llmcore
category: attend
in: tokens × tokens × tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_tiled — LLMCORE `attend` op

- **データ種**: `tokens × tokens × tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_tiled(query, key, value, tile: 'int' = 64, mask=None, window=None, scale=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_tiled(query, key, value, tile: 'int' = 64, mask=None, window=None, scale=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_tiled")`)

## 使い方

タイル + online softmax の注意(FlashAttention の芯)→ tokens。**近似ではない**。

Dao ら 2022。key/value を ``tile`` 行ずつ読み、走っている最大値と分母をその場で
補正しながら足す。作る中間行列は (T, ``tile``) だけで、**(T, T) を一度も作らない** ——
速さの出どころは近似ではなく、置き場所。``attention_softmax`` との相対差は
タイル 128 枚でも **1.2e-15**(タイル 1 枚で 8.2e-16 なので、枚数を 128 倍しても 1.5 倍)。

Args:
    query: (T, d) float。
    key: (S, d) float。
    value: (S, dv) float。
    tile: 一度に読む key/value の行数。小さいほど中間行列が小さく、枚数が増える。
    mask: None / ``"causal"`` / ``"window"`` / (T, S) の bool 配列。
    window: ``mask="window"`` のときの窓幅。
    scale: スコアの倍率。None なら 1/√d。
Returns:
    tokens (T, dv) float: ``attention_softmax`` と機械精度で一致する。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rms_norm](../prepare/rms_norm.md) · [rope_rotate](../prepare/rope_rotate.md) · [attention_scores](../score/attention_scores.md) · [attention_apply](../score/attention_apply.md) · [attention_softmax](attention_softmax.md) · [attention_linear](attention_linear.md) · [attention_grouped](attention_grouped.md) · [kv_cache_decode](../decode/kv_cache_decode.md)

## 同カテゴリ(`attend`)

[attention_softmax](attention_softmax.md) · [attention_linear](attention_linear.md) · [attention_grouped](attention_grouped.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
