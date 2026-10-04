---
op: tid2013_metric_values
dim: imgmetrics
category: iqa
in: any × any
out: any
examples: [poc_iqa_fsim_gmsd_vif, poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tid2013_metric_values — IMGMETRICS `iqa` op

- **データ種**: `any × any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.tid2013_metric_values(root, metric: 'str') -> 'np.ndarray'` (実装を直接呼ぶなら `import iqatid; iqatid.tid2013_metric_values(root, metric: 'str') -> 'np.ndarray'`、台帳から引くなら `opsimgmetrics.get("tid2013_metric_values")`)

## 使い方

作者の計算値 ``metrics_values/<metric>.txt``(大文字小文字無視、3000 行、名前なし)を (3000,) float で返す。
行の順は :func:`tid2013_index` の ``names`` と同じ。``metric`` は :func:`tid2013_published` の鍵(psnr / psnrc / ssim / mssim …)。
**Raises** ``ValueError``: ファイルが無い、行数 ≠ 3000、非数。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`
- [poc_iqa_tid2013](../../../../examples/poc_iqa_tid2013.py) — `py -3.11 examples/poc_iqa_tid2013.py`

## 型が繋がる次の op(`any` を入力に取れる)

[rgb_to_lab](../colorspace/rgb_to_lab.md) · [lab_to_rgb](../colorspace/lab_to_rgb.md) · [rgb_to_xyz](../colorspace/rgb_to_xyz.md) · [xyz_to_lab](../colorspace/xyz_to_lab.md) · [delta_e_2000](../colordiff/delta_e_2000.md) · [delta_e_76](../colordiff/delta_e_76.md) · [delta_e_map](../colordiff/delta_e_map.md) · [mse](../fidelity/mse.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
