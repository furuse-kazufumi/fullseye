---
op: material_effective_z
dim: tomography
category: spectral_xray
in: 
out: table
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# material_effective_z — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.material_effective_z(material='WATER', exponent: 'float' = 2.94, density_g_cm3=None) -> 'dict'` (実装を直接呼ぶなら `import materials; materials.material_effective_z(material='WATER', exponent: 'float' = 2.94, density_g_cm3=None) -> 'dict'`、台帳から引くなら `opstomography.get("material_effective_z")`)

## 使い方

組成から実効原子番号(Mayneord / Spiers の冪の式)と電子密度を返す。

Z_eff = (Σ aᵢ Zᵢ^p)^(1/p)、aᵢ = wᵢ (Z/A)ᵢ / Σ wⱼ (Z/A)ⱼ は**電子の割合**、p = 2.94 は光電効果の
断面積の Z 依存(≈ Z^3.94/原子 → Z^2.94/電子)から来る慣用の指数。水は 7.42(公表値)。
電子密度 ρₑ = ρ N_A Σ wᵢ Zᵢ/Aᵢ [電子/cm³] と、水に対する比も返す。
デュアルエナジーの像から推定する実効 Z(``dualxray.effective_z_map``)は、この「組成の Z_eff」と
同じものではない(光電効果の比で定義した Z は、スペクトルの位置で値が数 % 動く)—— その差を
PoC で数える。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: materials.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
