---
op: scintillator_sensor_qe
dim: tomography
category: spectral_xray
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# scintillator_sensor_qe — TOMOGRAPHY `spectral_xray` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.scintillator_sensor_qe(scintillator='CSI:TL', thickness_mm: 'float' = 0.6, e_min_kev: 'float' = 10.0, e_max_kev: 'float' = 150.0, n_points: 'int' = 141, photodetector_qe=None, emission_spectrum=None, light_yield_per_mev=None, light_collection: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import dualxray; dualxray.scintillator_sensor_qe(scintillator='CSI:TL', thickness_mm: 'float' = 0.6, e_min_kev: 'float' = 10.0, e_max_kev: 'float' = 150.0, n_points: 'int' = 141, photodetector_qe=None, emission_spectrum=None, light_yield_per_mev=None, light_collection: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opstomography.get("scintillator_sensor_qe")`)

## 使い方

シンチレータ積層のセンサの量子効率: X 線 1 個 → シンチレータの吸収 → 発光 → 光検出器の電子の数。

エネルギー E の X 線 1 個あたり:

  * 吸収効率 A(E) = 1 − exp(−μ(E) t)。μ は ``scintillator`` のレコードの X 線の列(NIST SRD 126)と密度、
    t = ``thickness_mm``。:func:`dual_kvp_channels` と同じ関数で計算する(CSI:TL は既定の ``CSI`` と同じ値)。
  * 光子の数 N(E) = A(E) · Y · E · η_c。Y = 光収率(単位 photons/MeV。材料表の値で、``light_yield_per_mev``
    で上書き)、E は MeV、η_c = ``light_collection``(光が光検出器に届く割合、既定 1 = 全部届く理想)。
    吸収した X 線はエネルギーを全部置いていくとみなす(K 蛍光の逃げとコンプトンの逃げは入れない)。
  * 重なり Q̄ = ∫ S(λ) QE(λ) dλ(S は ∫ S dλ = 1 に正規化した発光スペクトル)。電子の数 = N(E) · Q̄。

発光スペクトル S: ``emission_spectrum`` に (λ nm, 相対強度) の pairs を渡せばそれを正規化して使う。
渡さなければ材料表から —— 表に発光の幅(FWHM)があればその幅のガウス、**無ければ発光の極大の 1 本の線**
(Q̄ = QE(λ_peak))。2026-10-23 時点で幅を一次情報で確かめられた材料は無いので、表から作るのは線になる。
返り値の ``emission_model`` がどちらかを言う。``photodetector_qe`` は (λ nm, QE) の pairs で、既定は
``spectralrad.silicon_photodiode_qe()``(Si フォトダイオード、集める深さ 3 µm、反射防止膜なし)。
発光が QE の波長範囲の外にはみ出すと ValueError(外の光を 0 と数えて重なりを小さく出さない)。

返り値: dict(scintillator, thickness_mm, energy_kev, absorption_efficiency, light_photons, electrons,
overlap = Q̄, light_yield_photons_per_mev, light_collection, emission_model, emission(正規化した pairs、
線なら None), emission_peak_nm, photodetector, decay_time_ns, sources(使った値の出典), unverified)。
光収率の無い材料(GD2O2S:TB)で ``light_yield_per_mev`` を渡さなければ ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`spectral_xray`)

[material_xray_table](material_xray_table.md) · [material_xray_attenuation](material_xray_attenuation.md) · [material_xray_constants](material_xray_constants.md) · [material_effective_z](material_effective_z.md) · [xray_tube_spectrum](xray_tube_spectrum.md) · [xray_beam_quality](xray_beam_quality.md) · [photon_counting_channels](photon_counting_channels.md) · [dual_kvp_channels](dual_kvp_channels.md)

---
*Provenance: dualxray.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
