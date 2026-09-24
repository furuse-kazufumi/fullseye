---
op: attention_linear
dim: llmcore
category: attend
in: tokens × tokens × tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# attention_linear — LLMCORE `attend` op

- **データ種**: `tokens × tokens × tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.attention_linear(query, key, value, causal: 'bool' = False) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.attention_linear(query, key, value, causal: 'bool' = False) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("attention_linear")`)

## 使い方

softmax を外した注意 → tokens。**(QKᵀ)V == Q(KᵀV) —— 結合則そのもの**。

Katharopoulos ら 2020。softmax を外すと行列積の結合則が使え、(T, T) を作らずに
(d, dv) の状態だけで足りる。**同じ数の別の括り方**なので答えは一致し(相対差 7.1e-16)、
計算量は O(T²d) から O(Td²) に移る —— 交差点は **T == d**(実測: T=d=64 で比 0.9、
T=1024 で 14.6 倍)。★T を 2048 にしても比は 14.4 で頭打ちになる。式が言う 32 倍には
届かない —— 二次の側が帯域律速に入るから。

Args:
    query: (T, d) float。
    key: (S, d) float。
    value: (S, dv) float。``causal=True`` では S == T。
    causal: True なら「自分より前だけ」を累積状態で足す(逐次 1 回で線形時間)。
Returns:
    tokens (T, dv) float: **softmax を通していない**ので行和 1 の凸結合ではない。
    ``attention_softmax`` の代わりではなく、**別の注意**。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rms_norm](../prepare/rms_norm.md) · [rope_rotate](../prepare/rope_rotate.md) · [attention_scores](../score/attention_scores.md) · [attention_apply](../score/attention_apply.md) · [attention_softmax](attention_softmax.md) · [attention_tiled](attention_tiled.md) · [attention_grouped](attention_grouped.md) · [kv_cache_decode](../decode/kv_cache_decode.md)

## 同カテゴリ(`attend`)

[attention_softmax](attention_softmax.md) · [attention_tiled](attention_tiled.md) · [attention_grouped](attention_grouped.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
