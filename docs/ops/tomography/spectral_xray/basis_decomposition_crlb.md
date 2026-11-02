---
op: basis_decomposition_crlb
dim: tomography
category: spectral_xray
in: 
out: table
gpu: なし
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# basis_decomposition_crlb — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.basis_decomposition_crlb(thickness_cm=(5.0, 0.0), basis=('WATER', 'AL'), channels=None, photons_per_pixel: 'float' = 100000.0) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.basis_decomposition_crlb(thickness_cm=(5.0, 0.0), basis=('WATER', 'AL'), channels=None, photons_per_pixel: 'float' = 100000.0) -> 'dict'`、台帳から引くなら `opstomography.get("basis_decomposition_crlb")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

基底の厚み b での分解の分散の下限(Cramér–Rao)を閉形式で返す。

Fisher 情報 F = Σ_c (1/var_c) ∇mean_c ∇mean_cᵀ、∂mean_c/∂b_j = −n₀ Σ_k W g μ_j e^{−μ·b}
(計数では var_c = mean_c で Poisson の Fisher 情報そのもの、Roessl & Herrmann 2009 の式)。
CRLB = F⁻¹。返り値: dict(cov (B, B) [cm²], sigma_cm (B,), correlation, expected (C,), basis,
condition(F の条件数 —— 2 つの基底の μ(E) が似ているほど大きい))。
F が特異(チャネル < 基底、または同じ材料を 2 回)なら ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
