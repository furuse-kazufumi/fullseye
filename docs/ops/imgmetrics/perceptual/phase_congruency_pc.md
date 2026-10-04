---
op: phase_congruency_pc
dim: imgmetrics
category: perceptual
in: image2d
out: image2d
examples: [poc_iqa_fsim_gmsd_vif]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# phase_congruency_pc — IMGMETRICS `perceptual` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.phase_congruency_pc(img, data_range: 'float' = 255.0, nscale: 'int' = 4, norient: 'int' = 4, min_wavelength: 'float' = 6.0, mult: 'float' = 2.0, sigma_onf: 'float' = 0.55, dtheta_on_sigma: 'float' = 1.2, k: 'float' = 2.0, epsilon: 'float' = 0.0001) -> 'np.ndarray'` (実装を直接呼ぶなら `import iqafsim; iqafsim.phase_congruency_pc(img, data_range: 'float' = 255.0, nscale: 'int' = 4, norient: 'int' = 4, min_wavelength: 'float' = 6.0, mult: 'float' = 2.0, sigma_onf: 'float' = 0.55, dtheta_on_sigma: 'float' = 1.2, k: 'float' = 2.0, epsilon: 'float' = 0.0001) -> 'np.ndarray'`、台帳から引くなら `opsimgmetrics.get("phase_congruency_pc")`)

## 使い方

位相一致 PC(x) = Σ_o E_o(x) / Σ_o Σ_s A_{s,o}(x) ∈ [0, 1] (Kovesi 1999、FSIM 論文 式 4 の規約: log-Gabor 4 スケール × 4 向き)。

既存の ``phase_congruency``(backends_transform2、Riesz/モノジェニック版、方向を持たない、ノブ a/b)とは**別物**なので接尾 ``_pc``。
E_o = Σ_s [e ē + o ō − |e ō − o ē|] (ē, ō = その向きの総和ベクトルの単位方向、ε = 1e-4 はこの単位ベクトル化だけに入れる)から
Kovesi の雑音しきい値 T を引いて 0 で切る: 最小スケールの |EO|² の中央値 → Rayleigh の平均 −median/ln 0.5 → 雑音電力 → フィルタの重なりを含む
雑音エネルギーの平均 + k σ、最後に 1.7 で割る(Kovesi の経験則)。周波数広がりの sigmoid 重みは掛けない(FSIM の式 4 に無い)。
利得不変: 入力を定数倍しても PC は変わらない —— ただし ε の分だけ(ε = 1e-4 で最大 3e-5、ε に厳密比例)。入力 (H, W)((H, W, 3) は Y)。
既定値は FSIM 論文 §IV-A(λ_min = 6、mult = 2、σ_r = 0.55、σ_θ = π/4/1.2、k = 2)。
**Raises** ``ValueError``: 2×2 未満、非有限、data_range ≤ 0。

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

[fsim](fsim.md) · [fsimc](fsimc.md) · [fsim_pair](fsim_pair.md) · [gmsd](gmsd.md) · [gmsd_map](gmsd_map.md) · [vifp](vifp.md)

---
*Provenance: iqafsim.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
