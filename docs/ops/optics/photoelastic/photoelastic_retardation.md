---
op: photoelastic_retardation
dim: optics
category: photoelastic
in: image2d
out: table
examples: [photoelastic_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# photoelastic_retardation — OPTICS `photoelastic` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.photoelastic_retardation(stress_difference_pa, thickness_m, stress_optic_coefficient, wavelength_m)` (実装を直接呼ぶなら `import photoelastic; photoelastic.photoelastic_retardation(stress_difference_pa, thickness_m, stress_optic_coefficient, wavelength_m)`、台帳から引くなら `opsoptics.get("photoelastic_retardation")`)

## 使い方

等方材料の応力光学則 δ = 2π t C (σ1−σ2)/λ → dict(rad・nm・縞次数・材料縞値)。

``stress_optic_coefficient`` C is in Pa⁻¹ (1 brewster = 1e-12 Pa⁻¹); the
birefringence is ``Δn = C (σ1 − σ2)`` and the material fringe value
``f_σ = λ/C`` [N/m per fringe], so ``N = t (σ1 − σ2) / f_σ``.
The retarder axis is the σ1 direction (:func:`principal_stress`
``angle_deg``) in the convention of ``optics.mueller_element``.

Returns ``delta_rad``, ``retardation_nm``, ``fringe_order``,
``birefringence`` and ``fringe_value_n_per_m``.

**Raises** ``ValueError``: a non-finite/empty stress, |C| outside
[1e-15, 1e-8] Pa⁻¹ (a value in brewster or in MPa⁻¹ passed as Pa⁻¹), and
the thickness / wavelength checks of :func:`retardation_from_birefringence`.

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photoelastic_roundtrip](../../../../examples/photoelastic_roundtrip.py) — `py -3.11 examples/photoelastic_roundtrip.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`photoelastic`)

[brazilian_disc_stress](brazilian_disc_stress.md) · [kirsch_plate_stress](kirsch_plate_stress.md) · [principal_stress](principal_stress.md) · [retardation_from_birefringence](retardation_from_birefringence.md) · [retardation_convert](retardation_convert.md) · [cubic_photoelastic_birefringence](cubic_photoelastic_birefringence.md) · [silicon_piezo_optic_coefficients](silicon_piezo_optic_coefficients.md) · [polariscope_intensity](polariscope_intensity.md)

---
*Provenance: photoelastic.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
