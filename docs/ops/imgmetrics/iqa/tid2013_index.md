---
op: tid2013_index
dim: imgmetrics
category: iqa
in: any
out: table
examples: [poc_iqa_fsim_gmsd_vif, poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tid2013_index — IMGMETRICS `iqa` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tid2013_index(root) -> 'dict'` (実装を直接呼ぶなら `import iqatid; iqatid.tid2013_index(root) -> 'dict'`、台帳から引くなら `opsimgmetrics.get("tid2013_index")`)

## 使い方

``mos_with_names.txt`` を読んで組の台帳を返す。

返り値: ``names``(3000、配布物の綴りのまま)、``mos`` (3000,)、``ref`` / ``dist_type`` / ``level``(各 int 配列、1 始まり)、
``ref_files``(参照 25 枚のパス、番号順)、``dist_files``(歪み 3000 枚のパス、台帳の順)、``root``。
作者値 ``metrics_values/*.txt`` には名前が無く **この台帳の順**(i01_01_1 … i25_24_5)で並ぶので、順序はこの関数が握る。
**Raises** ``ValueError``: 行数 ≠ 3000、名前が iXX_YY_Z.bmp の形でない、名前集合が ``distorted_images/`` の BMP と一致しない
(大文字小文字無視)、参照 25 枚が揃わない、MOS が [0, 9] の外。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`
- [poc_iqa_tid2013](../../../../examples/poc_iqa_tid2013.py) — `py -3.11 examples/poc_iqa_tid2013.py`

## 型が繋がる次の op(`table` を入力に取れる)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [tid2013_by_distortion](tid2013_by_distortion.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_metric_values](tid2013_metric_values.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
