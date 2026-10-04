---
op: gmsd_map
dim: imgmetrics
category: perceptual
in: image2d × image2d
out: image2d
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# gmsd_map — IMGMETRICS `perceptual` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.gmsd_map(ref, dist, data_range: 'float' = 255.0, c: 'float' = 170.0, down_step: 'int' = 2) -> 'np.ndarray'` (実装を直接呼ぶなら `import iqafsim; iqafsim.gmsd_map(ref, dist, data_range: 'float' = 255.0, c: 'float' = 170.0, down_step: 'int' = 2) -> 'np.ndarray'`、台帳から引くなら `opsimgmetrics.get("gmsd_map")`)

## 使い方

GMS 地図 (2 m_r m_d + c)/(m_r² + m_d² + c) ∈ (0, 1] (論文 式 3)。m = Prewitt([1 0 −1]×3 /3)勾配の大きさ、前処理は 2×2 平均 + 2 間引き
(:func:`_average_downsample`、原実装の 'same' 規約)。入力 (H, W) か (H, W, 3)(3-ch は Y = 0.299R+0.587G+0.114B、作者の慣例)。
**Raises** ``ValueError``: 形が違う、c ≤ 0、down_step < 1。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_iqa_fsim_gmsd_vif](../../../../examples/poc_iqa_fsim_gmsd_vif.py) — `py -3.11 examples/poc_iqa_fsim_gmsd_vif.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](../fidelity/mse.md) · [rmse](../fidelity/rmse.md) · [psnr](../fidelity/psnr.md) · [ssim](../fidelity/ssim.md) · [ms_ssim](../fidelity/ms_ssim.md) · [ssim_map](../fidelity/ssim_map.md) · [image_entropy](../information/image_entropy.md) · [joint_entropy](../information/joint_entropy.md)

## 同カテゴリ(`perceptual`)

[fsim](fsim.md) · [fsimc](fsimc.md) · [fsim_pair](fsim_pair.md) · [gmsd](gmsd.md) · [vifp](vifp.md) · [phase_congruency_pc](phase_congruency_pc.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
