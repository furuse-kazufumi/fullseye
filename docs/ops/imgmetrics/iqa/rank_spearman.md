---
op: rank_spearman
dim: imgmetrics
category: iqa
in: any × any
out: scalar
examples: [poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# rank_spearman — IMGMETRICS `iqa` op

- **データ種**: `any × any` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.rank_spearman(x, y) -> 'float'` (実装を直接呼ぶなら `import iqatid; iqatid.rank_spearman(x, y) -> 'float'`、台帳から引くなら `opsimgmetrics.get("rank_spearman")`)

## 使い方

Spearman の順位相関 ρ = 平均順位どうしの Pearson 相関(同順位があっても正しい形。古典式 1 − 6Σd²/(n(n²−1)) は
同順位が無いときだけ一致)。単調増加で 1、反転で −1。どちらかが定数なら ``nan``(順位の分散が 0、相関は定義されない)。
±inf は順序だけ使う(完全一致の PSNR = inf を落とさない)。**Raises** ``ValueError``: 長さ不一致・2 未満・nan。

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

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
