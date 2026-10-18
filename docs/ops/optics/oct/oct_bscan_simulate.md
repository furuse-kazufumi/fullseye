---
op: oct_bscan_simulate
dim: optics
category: oct
in: 
out: table
examples: [poc_industrial_oct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# oct_bscan_simulate — OPTICS `oct` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.oct_bscan_simulate(sample2d=None, width_um=1500.0, n_columns=256, center_nm=840.0, bandwidth_nm=50.0, mode='sd', n_pixels=1024, wl_min_nm=None, wl_max_nm=None, spectrometer_fwhm_px=1.0, linewidth_nm=None, sweep_nonlinearity=0.0, photons_ref_per_pixel=20000.0, photons_mirror_per_pixel=None, eta=0.8, sigma_d=10.0, K=1.0, beam_waist_um=6.0, focus_um=None, illumination='point', focus_medium_index=1.5, oversample=4, noise=True, seed=0)` (実装を直接呼ぶなら `import octscan; octscan.oct_bscan_simulate(sample2d=None, width_um=1500.0, n_columns=256, center_nm=840.0, bandwidth_nm=50.0, mode='sd', n_pixels=1024, wl_min_nm=None, wl_max_nm=None, spectrometer_fwhm_px=1.0, linewidth_nm=None, sweep_nonlinearity=0.0, photons_ref_per_pixel=20000.0, photons_mirror_per_pixel=None, eta=0.8, sigma_d=10.0, K=1.0, beam_waist_um=6.0, focus_um=None, illumination='point', focus_medium_index=1.5, oversample=4, noise=True, seed=0)`、台帳から引くなら `opsoptics.get("oct_bscan_simulate")`)

## 使い方

断面(``sample2d``)を横に走査した **B スキャンの干渉スペクトルの束**(``table``)。

``sample2d`` = {"materials": [周囲, 層 1, …, 基板], "interfaces_um": [(W_fine,) の物理深さ, …] (上から、
W_fine は任意の本数で横に線形補間。深さ 0 = 周囲の媒質の中の基準面)、"surface_um": 基準面の光路
(参照腕との差、空気中 µm)、"scatter": [{"layer": i,
"density_per_mm2", "amplitude"}] (断面内の点散乱体 —— 塗装の顔料・接着剤のフィラー)、
"inclusions": [{"x_um", "z_um", "radius_um", "material"}] (空洞・異物。上下の面で反射し、
その下の界面の光路を変える)、"points": [{"x_um", "z_um", "amplitude"}] (置いた点散乱体 —— 横の点像の採点用)、"attenuation_per_mm": 層ごとの減衰}。省略時は段差を越えるコートの例。

各列: 細かい横の副標本(ビーム半径の 1/3 間隔)ごとに上から材料の区間を作り、境界 = 反射体、
光路 = 材料ごとの距離。ビームの重み exp(−2(x − x')²/w(z)²)(往復、w(z) = w0 √(1 + (Δz/z_R)²))、
共焦点の結合: ``illumination="point"`` は (1 + u²)^(−1/2)、``"line"``(ライン照明、片方向だけ共焦点)は
(1 + u²)^(−1/4)、u = (z − z_f)/z_R、z_R = π w0² n/λ0。ライン照明は 1 回で全列を撮る(走査の時間ずれなし)。

返り値: dict(kind="oct_bscan_spectra", spectra (W, N), wavelength_nm, k_rad_per_um, reference_spectrum,
sample_only_spectrum(列ごとの試料腕だけ・雑音なし —— 自己相関のアーチファクトの素),
x_um, truth={interfaces_um (n_if, W), inclusions}, settings)。

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

[oct_design](oct_design.md) · [oct_dispersion_broadening](oct_dispersion_broadening.md) · [oct_interferogram](oct_interferogram.md) · [oct_from_spectra](oct_from_spectra.md) · [oct_k_linearize](oct_k_linearize.md) · [oct_dispersion_estimate](oct_dispersion_estimate.md) · [oct_dispersion_compensate](oct_dispersion_compensate.md) · [oct_ascan](oct_ascan.md)

---
*Provenance: octscan.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
