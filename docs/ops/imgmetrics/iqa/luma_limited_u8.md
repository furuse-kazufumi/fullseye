---
op: luma_limited_u8
dim: imgmetrics
category: iqa
in: any
out: any
examples: [poc_iqa_tid2013]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# luma_limited_u8 — IMGMETRICS `iqa` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.luma_limited_u8(rgb) -> 'np.ndarray'` (実装を直接呼ぶなら `import iqatid; iqatid.luma_limited_u8(rgb) -> 'np.ndarray'`、台帳から引くなら `opsimgmetrics.get("luma_limited_u8")`)

## 使い方

RGB (H, W, 3) uint8 → Y′ = round(16 + (65.481 R + 128.553 G + 24.966 B) / 255) の uint8 (H, W)。

ITU-R BT.601 の **limited range**(studio swing)の輝度。黒 (0,0,0) → 16、白 (255,255,255) → 235。full range の
Y = 0.299 R + 0.587 G + 0.114 B(黒 0・白 255)とは**別の量**で、PSNR(peak 255 のまま)は 20 log10(255/219) = 1.321 dB
低く出る。TID2013 の作者値 psnr.txt(「luminance component」)と ssim.txt は **この規約で 4 桁一致**した(10 組、2026-10-04。
full range だと PSNR −1.3 dB・SSIM 最大 0.05 ずれ、丸めないと PSNR が +0.002〜0.07 dB ずれる)。ページにも readme にも
どの輝度かは書かれておらず、実測で特定した規約。丸めは ``np.round``(半偶数)。輝度が **ちょうど k.5** に落ちる画素は丸めの向きが
算術の順序で変わり、作者と 1 LSB 食い違うことがある(TID2013 では参照 I12 の 28 画素。彩度変化 5 組で作者 = 完全一致、ここでは 86.6 dB。
半切り上げでも float32 でも揃わない)。PSNR が 60 dB を超える領域だけの話で、それ以外の 2,995 組は 0.0005 dB 以内。
**Raises** ``ValueError``: 形が (H, W, 3) でない、dtype が uint8 でない。

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

[rank_data](rank_data.md) · [rank_spearman](rank_spearman.md) · [rank_kendall_b](rank_kendall_b.md) · [tid2013_published](tid2013_published.md) · [tid2013_root](tid2013_root.md) · [tid2013_index](tid2013_index.md) · [tid2013_metric_values](tid2013_metric_values.md) · [tid2013_evaluate](tid2013_evaluate.md)

---
*Provenance: iqatid.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
