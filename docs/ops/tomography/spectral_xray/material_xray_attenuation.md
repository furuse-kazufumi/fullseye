---
op: material_xray_attenuation
dim: tomography
category: spectral_xray
in: 
out: pairs
examples: [poc_dual_energy_xray, poc_geodetic_height_frames]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# material_xray_attenuation — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.material_xray_attenuation(material='CU', e_min_kev: 'float' = 10.0, e_max_kev: 'float' = 150.0, n_points: 'int' = 141, quantity: 'str' = 'mu_rho', density_g_cm3=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import materials; materials.material_xray_attenuation(material='CU', e_min_kev: 'float' = 10.0, e_max_kev: 'float' = 150.0, n_points: 'int' = 141, quantity: 'str' = 'mu_rho', density_g_cm3=None) -> 'np.ndarray'`、台帳から引くなら `opstomography.get("material_xray_attenuation")`)

## 使い方

材料の X 線の減衰を ``pairs``(E [keV], 値)で返す(質量減衰係数 μ/ρ [cm²/g] が既定)。

``material``: 名前(``WATER`` / ``MUSCLE`` / ``BONE`` / ``PVC`` / ``CU`` / ``SAPPHIRE`` …、
:func:`material_xray_table` の一覧)、化学式(``"Al2O3"``)、または
``{"composition": "C2H4" か {"SiO2": 0.7, …} か ((Z, w), …), "density_g_cm3": 0.93}``。
``quantity``: ``mu_rho``(全減衰、干渉性散乱を含む)/ ``mu_en_rho``(エネルギー吸収)/
``mu``(線減衰係数 μ = ρ·μ/ρ [1/cm]、密度が要る)。

格子は ``e_min_kev``〜``e_max_kev`` の対数等間隔 ``n_points`` 点。吸収端(Cu の K 端 8.979 keV など)
の上下は表の 2 行のあいだで飛ぶ —— 格子に端ちょうどの点があれば端の上の値になる。
表は 1 keV〜1 MeV(NIST の行の log–log 補間、NIST が推奨する補間)。範囲の外は ValueError。

公表値(NIST SRD 126): Cu の 8 keV で 52.55 cm²/g、K 端 8.979 keV で 38.29 → 278.4 cm²/g、
水の 60 keV で 0.2059 cm²/g。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dual_energy_xray](../../../../examples/poc_dual_energy_xray.py) — `py -3.11 examples/poc_dual_energy_xray.py`
- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md) · [xray_channel_projection](xray_channel_projection.md)

---
*Provenance: materials.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
