---
op: vifp
dim: imgmetrics
category: perceptual
in: image2d × image2d
out: scalar
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# vifp — IMGMETRICS `perceptual` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.vifp(ref, dist, data_range: 'float' = 255.0, sigma_nsq: 'float' = 2.0, nscales: 'int' = 4) -> 'float'` (実装を直接呼ぶなら `import iqafsim; iqafsim.vifp(ref, dist, data_range: 'float' = 255.0, sigma_nsq: 'float' = 2.0, nscales: 'int' = 4) -> 'float'`、台帳から引くなら `opsimgmetrics.get("vifp")`)

## 使い方

VIF の画素領域版(Sheikh & Bovik 2006 §V の scalar GSM、公開 vifp_mscale の規約)。1 = 同一、**higher is better**。

各スケール s = 1..4: 窓 N = 2^(4−s+1)+1、ガウス σ = N/5(17/3.4、9/1.8、5/1.0、3/0.6)。s > 1 では窓で平滑して 2 間引き。局所統計(μ、σ²、σ12)は
'valid' 相関、g = σ12/(σ1²+1e-10)、σ_v² = σ2² − g σ12、σ1² < 1e-10・σ2² < 1e-10・g < 0 の画素は規約どおり潰す、σ_v² ≤ 1e-10 → 1e-10。
VIF = Σ log10(1 + g² σ1²/(σ_v² + σ_n²)) / Σ log10(1 + σ1²/σ_n²)。**非対称**(参照の情報量で割る: vif(a, b) ≠ vif(b, a))、コントラスト強調で
**1 を超える**(TID2013 の作者値も最大 1.1379 = 歪み 17)—— 忠実度でなく情報量の比。入力 (H, W) か (H, W, 3)(3-ch は Y)。
TID2013 の VIFP.txt(論文の「VIFP」、steerable 版の「VIF」とは別行)と 4 桁一致するのは **Y′ limited の灰色画像**
(``iqatid.tid2013_evaluate(root, vifp, luma="limited_u8")``、3,000 組 max |差| 6.8e-5)。
**Raises** ``ValueError``: 形が違う、最小スケールで窓より小さい、参照が平坦(分母 0)、sigma_nsq ≤ 0。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[luma_limited_u8](../iqa/luma_limited_u8.md) · [rank_data](../iqa/rank_data.md) · [tid2013_index](../iqa/tid2013_index.md)

## 同カテゴリ(`perceptual`)

[fsim](fsim.md) · [fsimc](fsimc.md) · [fsim_pair](fsim_pair.md) · [gmsd](gmsd.md) · [gmsd_map](gmsd_map.md) · [phase_congruency_pc](phase_congruency_pc.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
