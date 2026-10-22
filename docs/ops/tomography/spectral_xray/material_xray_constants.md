---
op: material_xray_constants
dim: tomography
category: spectral_xray
in: 
out: table
examples: [poc_dual_energy_xray]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# material_xray_constants — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.material_xray_constants(material='CU', energy_kev: 'float' = 8.0, density_g_cm3=None) -> 'dict'` (実装を直接呼ぶなら `import materials; materials.material_xray_constants(material='CU', energy_kev: 'float' = 8.0, density_g_cm3=None) -> 'dict'`、台帳から引くなら `opstomography.get("material_xray_constants")`)

## 使い方

1 エネルギーの X 線の定数(μ/ρ・μ_en/ρ・μ・半価層・平均自由行程)と出典を返す。

返り値: dict(name, energy_kev, mu_rho_cm2_g, mu_en_rho_cm2_g, density_g_cm3, mu_per_cm,
hvl_mm = 10·ln 2/μ, mfp_mm = 10/μ, edges(±20 % の範囲にある吸収端の (元素, 端, keV)), kind, reference)。
単色 X 線の半価層は ln 2/μ そのもの(多色の線質の半価層は ``dualxray.xray_beam_quality``)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: materials.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
