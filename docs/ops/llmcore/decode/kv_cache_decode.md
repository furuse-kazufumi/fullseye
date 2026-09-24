---
op: kv_cache_decode
dim: llmcore
category: decode
in: tokens × tokens × tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# kv_cache_decode — LLMCORE `decode` op

- **データ種**: `tokens × tokens × tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.kv_cache_decode(query_step, key_cache, value_cache, scale=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.kv_cache_decode(query_step, key_cache, value_cache, scale=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("kv_cache_decode")`)

## 使い方

1 トークン分だけ進める推論(KV Cache)→ tokens (1, dv)。

因果マスクの下では**未来を書き換えても前の出力が 1 ビットも動かない**(実測 0.0e+00)
ので、済んだ key/value を取っておいて 1 行だけ計算すればよい —— 逐次に 1 行ずつ
進めた結果は、全系列を一括で通した結果と一致する(相対差 1.6e-16)。
計算量は 1 歩あたり O(T d) で、一括の O(T² d) を T 歩に割ったものに等しい。

Args:
    query_step: (1, d) float。いま生成しようとしている 1 トークン。
    key_cache: (T, d) float。ここまでに見た key(自分を含む)。
    value_cache: (T, dv) float。同じ長さの value。
    scale: スコアの倍率。None なら 1/√d。
Returns:
    tokens (1, dv) float: 一括で通した最終行と一致する。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rms_norm](../prepare/rms_norm.md) · [rope_rotate](../prepare/rope_rotate.md) · [attention_scores](../score/attention_scores.md) · [attention_apply](../score/attention_apply.md) · [attention_softmax](../attend/attention_softmax.md) · [attention_tiled](../attend/attention_tiled.md) · [attention_linear](../attend/attention_linear.md) · [attention_grouped](../attend/attention_grouped.md)

## 同カテゴリ(`decode`)

—

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
