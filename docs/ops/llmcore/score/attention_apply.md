---
op: attention_apply
dim: llmcore
category: score
in: attnmap × tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_apply — LLMCORE `score` op

- **データ種**: `attnmap × tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_apply(weights, value) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_apply(weights, value) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_apply")`)

## 使い方

注意の重みで値を混ぜる → tokens。**行和 1 なので出力は入力の凸結合**。

Args:
    weights: (T, S) float。行和が 1 であること(``attention_weights`` の出力)。
    value: (S, dv) float。混ぜられる側。
Returns:
    tokens (T, dv) float: 各行が value の行の凸結合。**値域は value を出ない**
    (同時に幅は縮む —— 平均は対比を潰す)。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rms_norm](../prepare/rms_norm.md) · [rope_rotate](../prepare/rope_rotate.md) · [attention_scores](attention_scores.md) · [attention_softmax](../attend/attention_softmax.md) · [attention_tiled](../attend/attention_tiled.md) · [attention_linear](../attend/attention_linear.md) · [attention_grouped](../attend/attention_grouped.md) · [kv_cache_decode](../decode/kv_cache_decode.md)

## 同カテゴリ(`score`)

[attention_scores](attention_scores.md) · [attention_weights](attention_weights.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
