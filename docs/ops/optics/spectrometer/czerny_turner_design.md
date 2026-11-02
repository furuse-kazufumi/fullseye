---
op: czerny_turner_design
dim: optics
category: spectrometer
in: 
out: table
gpu: なし
examples: [poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# czerny_turner_design — OPTICS `spectrometer` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.czerny_turner_design(groove_density_per_mm=1200.0, wavelength_min_nm=500.0, wavelength_max_nm=750.0, incidence_deg=9.0, collimator_f_mm=52.083, detector_length_mm=28.672, collimator_offaxis_deg=6.5, order=1, camera_f_mm=None, n_curve=41)` (実装を直接呼ぶなら `import gratingspec; gratingspec.czerny_turner_design(groove_density_per_mm=1200.0, wavelength_min_nm=500.0, wavelength_max_nm=750.0, incidence_deg=9.0, collimator_f_mm=52.083, detector_length_mm=28.672, collimator_offaxis_deg=6.5, order=1, camera_f_mm=None, n_curve=41)`、台帳から引くなら `opsoptics.get("czerny_turner_design")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Czerny–Turner(平面格子 + 2 枚の凹面鏡)の 1 次設計: カメラの焦点距離・コマを消す角・波長の写像。

groove_density_per_mm / order / incidence_deg: 格子と入射角 α(中心波長でも端でも同じ α)。
wavelength_min_nm / wavelength_max_nm: 検出器に並べる帯域。中心 λ_c はその中点で、検出器の中央に来る。
collimator_f_mm: コリメータ鏡の焦点距離(曲率半径の半分)。
detector_length_mm: 検出器の長さ L(分散方向)。帯域の両端が検出器の両端に乗るようにカメラの f を決める。
collimator_offaxis_deg: コリメータ鏡の軸外し角 θ₁(入射と反射のなす角の半分)。
camera_f_mm: カメラ鏡の焦点距離を与える(None なら帯域が L にちょうど乗る値を厳密に解く)。
n_curve: 波長 → 位置の写像の標本数。

返り値(table、``kind = "czerny_turner"``。下流の op がそのまま受ける):

* ``center_wavelength_nm`` / ``beta_center_deg`` / ``deviation_deg``(α − β_c)。
* ``camera_f_mm``(使った値)/ ``camera_f_linear_mm``(線形近似 f = L d cos β_c / (m Δλ)、
  Feng 2021 の式 (16))/ ``camera_f_exact_mm``(像の写像 x = f tan(β − β_c) で両端が L に乗る値)。
* ``mirror_radii_mm`` —— (2 f_col, 2 f_cam)。
* ``shafer_offaxis_deg`` —— Shafer の条件でコマを消すカメラ鏡の軸外し角 θ₂。
* ``dispersion_curve`` —— pairs(λ [nm], 検出器の位置 x [mm])。``nonlinearity_mm`` は直線からの最大のずれ。
* ``reciprocal_dispersion_nm_per_mm`` —— (端, 中心, 端) の P。
* ``detector_coverage_mm`` —— 帯域の両端の位置。``second_order_band_nm`` —— 帯域へ 2 次で重なる波長の範囲
  (λ_min/2 〜 λ_max/2)。``order_overlap_from_nm`` —— 帯域の中の光自身が 2 次で重なり始める波長
  (2 λ_min が帯域内なら。無ければ None)。

**Raises** ``ValueError``: 帯域が逆・帯域の一部が伝わらない、検出器に乗らない、Shafer の解が無い、
非正の長さ、|α| ≥ 90°。

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

- [poc_spectrometer_illumination](../../../../examples/poc_spectrometer_illumination.py) — `py -3.11 examples/poc_spectrometer_illumination.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`spectrometer`)

[grating_dispersion](grating_dispersion.md) · [spectrometer_bandpass](spectrometer_bandpass.md) · [spectrometer_slit_image](spectrometer_slit_image.md) · [spectrometer_spectrum](spectrometer_spectrum.md)

---
*Provenance: gratingspec.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
