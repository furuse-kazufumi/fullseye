---
op: tid2013_compare
dim: imgmetrics
category: iqa
in: any × any × any
out: table
examples: [poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# tid2013_compare — IMGMETRICS `iqa` op

- **データ種**: `any × any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tid2013_compare(values, author_values, mos, published: 'Optional[Tuple[float, float]]' = None, inf_as: 'Optional[float]' = None) -> 'dict'` (実装を直接呼ぶなら `import iqatid; iqatid.tid2013_compare(values, author_values, mos, published: 'Optional[Tuple[float, float]]' = None, inf_as: 'Optional[float]' = None) -> 'dict'`、台帳から引くなら `opsimgmetrics.get("tid2013_compare")`)

## 使い方

自前の値と作者の値(同じ組、同じ順)の行ごとの差と、MOS との順位相関を比べる。

``inf_as`` = 自前の ``inf`` を差を取る前に置き換える値。作者は PSNR の完全一致を **100000.0** と書く(psnr.txt の 106 行、歪み 18)ので
``inf_as=100000.0`` で行ごとの差が 0 になる。省略時に ``inf`` があれば ``ValueError``(黙って落とさない)。順位相関は inf を順序として使う。
作者の印は psnr.txt に **111 行**あるが、BT.601 の式で Y′ が参照と一致するのは 106 行 —— 残り 5 行(参照 I12 の彩度変化 5 段)は
28 画素の輝度が **ちょうど k.5** に落ち、丸めの向きが作者の算術と食い違って 1 LSB 差 → 86.6 dB(半偶数・半切り上げ・float32・整数式を
試しても 111 にはならない、2026-10-04)。そこで ``diff_max_finite``(作者も自分も完全一致でない行だけの最大差)と
``sentinel_mismatch_idx`` / ``sentinel_mismatch_values``(作者が印・自分は有限の行とその値)を**別に返す**。門は両方を見る。
返り値: ``n``、``n_inf``、``n_sentinel_author``、``diff_max``(|自前 − 作者| の最大、印の行も含む)、``diff_max_finite`` / ``argmax_finite``、
``sentinel_mismatch_idx`` / ``sentinel_mismatch_values``、``inf_not_sentinel_idx``(自分が inf・作者は数値)、``diff_mean``(符号つき平均)、``diff_rms``、``argmax``(最大差の行)、
``srocc`` / ``krocc``(自前 vs MOS)、``srocc_author`` / ``krocc_author``(作者値 vs MOS)、``published`` を渡せば
``d_srocc_published`` / ``d_krocc_published``(自前 − 公表)と ``d_srocc_author_published`` / ``d_krocc_author_published``。
**Raises** ``ValueError``: 長さ不一致・nan・``inf_as`` 無しの inf。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_tid2013](../../../../examples/poc_iqa_tid2013.py) — `py -3.11 examples/poc_iqa_tid2013.py`

## 型が繋がる次の op(`table` を入力に取れる)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [tid2013_index](tid2013_index.md) · [tid2013_by_distortion](tid2013_by_distortion.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
