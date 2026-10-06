---
op: tid2013_evaluate
dim: imgmetrics
category: iqa
in: any × any
out: table
examples: [poc_iqa_fsim_gmsd_vif, poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# tid2013_evaluate — IMGMETRICS `iqa` op

- **データ種**: `any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tid2013_evaluate(root, fn: 'Callable[[np.ndarray, np.ndarray], float]', *, subset=None, luma: 'str' = 'limited_u8', index: 'Optional[dict]' = None) -> 'dict'` (実装を直接呼ぶなら `import iqatid; iqatid.tid2013_evaluate(root, fn: 'Callable[[np.ndarray, np.ndarray], float]', *, subset=None, luma: 'str' = 'limited_u8', index: 'Optional[dict]' = None) -> 'dict'`、台帳から引くなら `opsimgmetrics.get("tid2013_evaluate")`)

## 使い方

自前の指標 ``fn(ref, dist) -> float`` を TID2013 の組に当て、MOS との順位相関を返す。

``luma`` = ``"limited_u8"``(作者規約の Y′ uint8 (H, W) を渡す、psnr.txt / ssim.txt と比べるとき)/ ``"rgb"``(uint8 (H, W, 3) を
そのまま渡す、psnrc.txt と比べるとき)。``subset`` = ``None``(3000 組全部)/ 個数(台帳の先頭 n)/ 名前の列(大文字小文字無視、
拡張子は任意)。参照画像は 25 枚を一度だけ読む。
返り値: ``values`` (n,)、``mos`` (n,)、``idx``(台帳の行番号)、``names``、``srocc``、``krocc``(τ_b)、``n``、``n_inf``、``luma``、``seconds``。
``fn`` が ``inf`` を返すのは**正当**(PSNR の完全一致)。TID2013 では歪み 18「彩度変化」の 125 組のうち **106 組で Y′ が参照と
1 画素も変わらず**、作者は psnr.txt にその行を **100000.0** と書き、ssim.txt は 1.0(:func:`tid2013_compare` の ``inf_as``)。
順位相関では inf を最大の順位として扱う。**Raises** ``ValueError``: ``luma`` が未知、``fn`` が数か ±inf を返さない(nan は拒否)、subset が不正。

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

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [tid2013_index](tid2013_index.md) · [tid2013_by_distortion](tid2013_by_distortion.md)

## 同カテゴリ(`iqa`)

[luma_limited_u8](luma_limited_u8.md) · [rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
