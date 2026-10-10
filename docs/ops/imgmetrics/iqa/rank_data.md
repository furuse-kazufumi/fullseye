---
op: rank_data
dim: imgmetrics
category: iqa
in: any
out: any
examples: [poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# rank_data — IMGMETRICS `iqa` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.rank_data(x) -> 'np.ndarray'` (実装を直接呼ぶなら `import iqatid; iqatid.rank_data(x) -> 'np.ndarray'`、台帳から引くなら `opsimgmetrics.get("rank_data")`)

## 使い方

平均順位(1 始まり)。同順位は同じ値の順位の平均(scipy.stats.rankdata の 'average' と同じ定義)。

例: [10, 20, 20, 30] → [1, 2.5, 2.5, 4]。±inf は最大 / 最小の順位(互いに同順位)。**Raises** ``ValueError``: 長さ 2 未満・nan。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_tid2013](../../../../examples/poc_iqa_tid2013.py) — `py -3.11 examples/poc_iqa_tid2013.py`

## 型が繋がる次の op(`any` を入力に取れる)

[rgb_to_lab](../colorspace/rgb_to_lab.md) · [lab_to_rgb](../colorspace/lab_to_rgb.md) · [rgb_to_xyz](../colorspace/rgb_to_xyz.md) · [xyz_to_lab](../colorspace/xyz_to_lab.md) · [delta_e_2000](../colordiff/delta_e_2000.md) · [delta_e_76](../colordiff/delta_e_76.md) · [delta_e_map](../colordiff/delta_e_map.md) · [mse](../fidelity/mse.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
