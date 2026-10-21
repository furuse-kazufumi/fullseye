---
op: xray_beam_quality
dim: tomography
category: spectral_xray
in: pairs
out: table
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# xray_beam_quality — TOMOGRAPHY `spectral_xray` op

- **データ種**: `pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.xray_beam_quality(spectrum, material: 'str' = 'AL') -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.xray_beam_quality(spectrum, material: 'str' = 'AL') -> 'dict'`、台帳から引くなら `opstomography.get("xray_beam_quality")`)

## 使い方

スペクトルの線質: 第 1・第 2 半価層、均等度、平均エネルギー、実効エネルギーを返す。

半価層は**空気カーマ**が半分になる吸収体の厚さ(線量計で測る量の定義どおり):
K(x) ∝ Σ φ(E) E (μ_en/ρ)_air(E) e^{−μ(E) x}。HVL₁ は K(x) = K(0)/2、HVL₂ は K(x) = K(0)/4 から
HVL₁ を引いたもの、均等度 = HVL₁/HVL₂(単色なら 1)。実効エネルギーは単色で同じ HVL₁ を
与えるエネルギー(μ(E_eff) = ln 2/HVL₁)。``material`` は吸収体(既定 Al、Cu も使う)。

返り値: dict(hvl1_mm, hvl2_mm, homogeneity, mean_energy_kev(光子数の平均), effective_energy_kev,
material)。公表の線質(IEC 61267 の RQA 系列など)と比べる量。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
