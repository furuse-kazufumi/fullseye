---
op: rms_norm
dim: llmcore
category: prepare
in: tokens
out: tokens
examples: [poc_attention_identities]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# rms_norm — LLMCORE `prepare` op

- **データ種**: `tokens` → `tokens`
- **呼び出し**: `import fullseye as fs; fs.ledger.rms_norm(tokens, eps: 'float' = 0.0, weight=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import llmcore; llmcore.rms_norm(tokens, eps: 'float' = 0.0, weight=None) -> 'np.ndarray'`、台帳から引くなら `opsllmcore.get("rms_norm")`)

## 使い方

RMS 正規化 → tokens。**既定(eps=0, weight なし)では出力の RMS が厳密に 1**。

Zhang・Sennrich 2019。LayerNorm から平均を引く段を落としたもので、残るのは
「行のノルムを揃える」だけ —— だから **RMS が 1 になることが検算になる**
(実測 2.2e-16)。``eps`` を入れると 1 からずれる。それが ``eps`` の値段。

Args:
    tokens: (T, d) float。1 行が 1 トークン。
    eps: 平方根の中に足す下駄。0 なら RMS は厳密に 1、正なら 1 未満に縮む。
    weight: (d,) float か None。学習で付く軸ごとの倍率(掛けるだけなので RMS は動く)。
Returns:
    tokens (T, d) float: 各行を自分の RMS で割ったもの(``weight`` があれば掛けたもの)。
    **全成分が 0 の行**は割れないので ValueError(黙って 0/0 の NaN を返さない)。

## 詳しい使い方ガイド

- [llmcore ファミリ ガイド](../guides/llmcore.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_attention_identities](../../../../examples/poc_attention_identities.py) — `py -3.11 examples/poc_attention_identities.py`

## 型が繋がる次の op(`tokens` を入力に取れる)

[rope_rotate](rope_rotate.md) · [attention_scores](../score/attention_scores.md) · [attention_apply](../score/attention_apply.md) · [attention_softmax](../attend/attention_softmax.md) · [attention_tiled](../attend/attention_tiled.md) · [attention_linear](../attend/attention_linear.md) · [attention_grouped](../attend/attention_grouped.md) · [kv_cache_decode](../decode/kv_cache_decode.md)

## 同カテゴリ(`prepare`)

[rope_rotate](rope_rotate.md)

---
*Provenance: llmcore.py — LLMCORE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
