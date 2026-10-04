---
op: fsim_pair
dim: imgmetrics
category: perceptual
in: rgbimage × rgbimage
out: table
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# fsim_pair — IMGMETRICS `perceptual` op

- **データ種**: `rgbimage × rgbimage` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fsim_pair(ref, dist, data_range: 'float' = 255.0, downsample: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import iqafsim; iqafsim.fsim_pair(ref, dist, data_range: 'float' = 255.0, downsample: 'bool' = True) -> 'dict'`、台帳から引くなら `opsimgmetrics.get("fsim_pair")`)

## 使い方

FSIM と FSIMc を一度に(位相一致は 1 枚 1 回しか計算しない —— 評価器や PoC はこちらを呼ぶ)。

手順(論文 §III): (1) F = max(1, round(min(H, W)/256)) で F×F 平均 + 間引き(TID2013 の 384×512 は F = 2 → 192×256)、(2) Y の位相一致 PC と
Scharr([3 0 −3; 10 0 −10; 3 0 −3]/16)勾配の大きさ G、(3) S_PC = (2 PC1 PC2 + T1)/(PC1² + PC2² + T1)、S_G = (2 G1 G2 + T2)/(G1² + G2² + T2)、
(4) FSIM = Σ S_G S_PC PC_m / Σ PC_m(PC_m = max(PC1, PC2))、(5) FSIMc は彩度 I / Q の S_I S_Q(T3 = T4 = 200)の λ = 0.03 乗の実部を掛ける。
入力は同じ形の (H, W) か (H, W, 3)(0–255; ``data_range`` で尺度を宣言)。**(H, W) のときは FSIMc = FSIM**(彩度の項が無い)。
TID2013 の作者値: FSIM.txt は **Y′ limited の灰色画像**、FSIMc.txt は色画像(モジュール docstring の表)—— 色画像 1 枚から両方を出すと FSIM の方は
FSIM.txt と合わない(max 0.0318)。返り値 ``{"fsim", "fsimc", "f"}``(f = 間引き係数)。恒等で 1。
**Raises** ``ValueError``: 形が違う、2×2 未満、位相一致が全画素 0(平坦画像: FSIM は 0/0 で定義されない)。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`

## 型が繋がる次の op(`table` を入力に取れる)

[luma_limited_u8](../iqa/luma_limited_u8.md) · [rank_data](../iqa/rank_data.md) · [tid2013_index](../iqa/tid2013_index.md) · [tid2013_by_distortion](../iqa/tid2013_by_distortion.md)

## 同カテゴリ(`perceptual`)

[fsim](fsim.md) · [fsimc](fsimc.md) · [gmsd](gmsd.md) · [gmsd_map](gmsd_map.md) · [vifp](vifp.md) · [phase_congruency_pc](phase_congruency_pc.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
