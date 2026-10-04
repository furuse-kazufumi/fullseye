---
op: rank_kendall_b
dim: imgmetrics
category: iqa
in: any × any
out: scalar
examples: [poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# rank_kendall_b — IMGMETRICS `iqa` op

- **データ種**: `any × any` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.rank_kendall_b(x, y, chunk: 'int' = 512) -> 'float'` (実装を直接呼ぶなら `import iqatid; iqatid.rank_kendall_b(x, y, chunk: 'int' = 512) -> 'float'`、台帳から引くなら `opsimgmetrics.get("rank_kendall_b")`)

## 使い方

Kendall の τ_b(同順位補正あり)= (C − D) / sqrt((n0 − n1)(n0 − n2))。

C / D = 一致 / 不一致の対の数、n0 = n(n−1)/2、n1 / n2 = x 側 / y 側で同順位の対の数。O(n²) を ``chunk`` 行ずつの
放送で数える(n = 3000 で 4.5e6 対、数秒)。単調増加で 1、反転で −1。どちらかが定数なら ``nan``。TID2013 の公表 Kendall は
τ_b(14 本が 3 桁一致、τ_a だと 4 本外れる)。±inf は順序だけ使う。**Raises** ``ValueError``: 長さ不一致・2 未満・nan。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_tid2013](../../../../examples/poc_iqa_tid2013.py) — `py -3.11 examples/poc_iqa_tid2013.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [tid2013_index](tid2013_index.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
