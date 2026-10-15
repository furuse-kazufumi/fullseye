---
op: oct_design
dim: optics
category: oct
in: 
out: table
examples: [poc_industrial_oct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# oct_design — OPTICS `oct` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.oct_design(center_nm=840.0, bandwidth_nm=50.0, n_pixels=2048, wl_min_nm=None, wl_max_nm=None, mode='sd', spectrometer_fwhm_px=1.0, linewidth_nm=None, n_group=1.0, beam_waist_um=None, focal_mm=None, beam_diameter_mm=None, photons_mirror_per_pixel=None, photons_ref_per_pixel=None, eta=0.8, sigma_d=10.0, window='hann', reflectivity=None, grid='lambda')` (実装を直接呼ぶなら `import octscan; octscan.oct_design(center_nm=840.0, bandwidth_nm=50.0, n_pixels=2048, wl_min_nm=None, wl_max_nm=None, mode='sd', spectrometer_fwhm_px=1.0, linewidth_nm=None, n_group=1.0, beam_waist_um=None, focal_mm=None, beam_diameter_mm=None, photons_mirror_per_pixel=None, photons_ref_per_pixel=None, eta=0.8, sigma_d=10.0, window='hann', reflectivity=None, grid='lambda')`、台帳から引くなら `opsoptics.get("oct_design")`)

## 使い方

OCT の性能を**撮る前に**閉形式で(``table``): 軸分解能・深さ範囲・感度の roll-off・SNR・横分解能と焦点深度。

* 軸分解能(FWHM、ガウス光源、窓なし)δz = (2 ln 2/π) λ0²/Δλ ≈ 0.44 λ0²/Δλ(空気中)、媒質中は ÷ n_g。
  ``window`` を掛けると広がる(倍率 ``window_broadening`` は光源 × 窓の |FT| の FWHM から数値で求める。
  ガウス光源が範囲の中に収まっていれば hann で約 1.2 倍)。
* 深さ範囲(片道の光路、ナイキスト)z_max = π/(2 δk) = λ0²/(4 δλ)(δλ = 1 画素の波長幅)、媒質中は ÷ n_g。
  ``grid="lambda"``(既定)は λ 等間隔の分光器(δk は中心の値)、``"k"`` は k 等間隔の分光器(Hu & Rollins 2007)。
* roll-off(振幅): SD は画素の箱 |sin(z δk)/(z δk)| と分光器の分解能のガウス exp(−2σ²z²)(σ = 分解能の
  FWHM/2.355、k で)。SS は瞬時線幅 ``linewidth_nm`` のガウスだけ(``mode="ss"``)。−6 dB の深さを数値で解く。
* SNR(ショット雑音 + 読み出し雑音、窓つき): 画素 i の参照光の電子 N_r,i と、反射率 1 の鏡の電子 N_s,i で
  SNR = (Σ w_i √(N_r,i N_s,i))² / Σ w_i² (N_r,i + σ_d²)(参照光が強ければ η × 試料の光子の総数 × 窓の係数)。
  ``sensitivity_db`` = 10 log10(SNR)(弱い反射体の SNR を反射率 1 へ外挿した値 = 検出の下限 1/R_min)。
  ``reflectivity`` R を渡すと、その反射体自身のショット雑音(N_s,i R)も分母に入れた SNR を ``snr_db`` に返す
  (強い反射体では参照光が支配的という前提が崩れ、外挿より小さくなる)。光子が渡されないときは None。
* 横分解能: ビームのくびれ半径 w0(1/e²)から、慣用の Δx = 2 w0 = (4λ/π)(f/d) と、A スキャンの振幅で見た
  点像の FWHM √(2 ln 2) w0(往復で exp(−2x²/w²))。焦点深度 b = 2 z_R = 2π w0² n/λ(慣用 = π Δx²/(2λ))。

返り値: dict(kind="oct_design", axial_resolution_air_um, axial_resolution_um, depth_range_air_um,
depth_range_um, pixel_nm, dk_pixel, rolloff_6db_air_um, rolloff_6db_um, rolloff(pairs: 光路 µm, 振幅),
snr_db / sensitivity_db, lateral_resolution_um, lateral_fwhm_um, depth_of_focus_um, …)。

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

- [poc_industrial_oct](../../../../examples/poc_industrial_oct.py) — `py -3.11 examples/poc_industrial_oct.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`oct`)

[oct_dispersion_broadening](oct_dispersion_broadening.md) · [oct_interferogram](oct_interferogram.md) · [oct_bscan_simulate](oct_bscan_simulate.md) · [oct_from_spectra](oct_from_spectra.md) · [oct_k_linearize](oct_k_linearize.md) · [oct_dispersion_estimate](oct_dispersion_estimate.md) · [oct_dispersion_compensate](oct_dispersion_compensate.md) · [oct_ascan](oct_ascan.md)

---
*Provenance: octscan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
