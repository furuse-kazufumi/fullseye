---
op: grating_dispersion
dim: optics
category: spectrometer
in: 
out: table
examples: [poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# grating_dispersion — OPTICS `spectrometer` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.grating_dispersion(groove_density_per_mm=1200.0, wavelength_nm=550.0, incidence_deg=10.0, order=1, focal_length_mm=100.0, illuminated_width_mm=25.0)` (実装を直接呼ぶなら `import gratingspec; gratingspec.grating_dispersion(groove_density_per_mm=1200.0, wavelength_nm=550.0, incidence_deg=10.0, order=1, focal_length_mm=100.0, illuminated_width_mm=25.0)`、台帳から引くなら `opsoptics.get("grating_dispersion")`)

## 使い方

格子の式 mλ = d(sin α + sin β) を解き、角分散・逆線分散・分解能・重なる次数を表にする。

groove_density_per_mm: 溝の密度 G [本/mm]。溝の間隔は d = 1/G。
wavelength_nm: 波長 λ。incidence_deg: 入射角 α(法線から、Palmer の符号)。order: 次数 m(0 は拒否)。
focal_length_mm: カメラ(結像側)の焦点距離 f(線分散に使う)。
illuminated_width_mm: 照らされた格子の幅 W(分散方向)。溝の数 N = W/d。

返り値(table):

* ``beta_deg`` —— 回折角 β。``deviation_deg`` = α − β(入射光と回折光のなす角)。
* ``angular_dispersion_deg_per_nm`` / ``angular_dispersion_rad_per_nm`` —— dβ/dλ = m / (d cos β)。
* ``reciprocal_linear_dispersion_nm_per_mm`` —— P = d cos β / (|m| f)。
* ``anamorphic_magnification`` —— cos α / cos β(回折光と入射光のビーム幅の比)。
* ``grooves_illuminated`` / ``resolving_power`` (= |m| N) / ``resolving_power_max`` (= 2W/λ) /
  ``rayleigh_limit_nm`` (= λ / (|m| N)) / ``diffraction_fwhm_nm`` (= 0.8859 λ / (|m| N))。
* ``free_spectral_range_nm`` —— λ / |m|。``littrow_deg`` —— この次数で α = β になる角(無ければ None)。
* ``orders`` —— 伝わる全次数の (m, β [deg]) の表。
* ``overlaps`` —— 同じ β へ出る他の次数の波長 (m', λ' = mλ/m')(迷光の次数。λ' は 50 nm 以上のみ)。

**Raises** ``ValueError``: 0 次、伝わらない次数、非正の密度・波長・焦点距離・幅、|α| ≥ 90°。

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

[czerny_turner_design](czerny_turner_design.md) · [spectrometer_bandpass](spectrometer_bandpass.md) · [spectrometer_slit_image](spectrometer_slit_image.md) · [spectrometer_spectrum](spectrometer_spectrum.md)

---
*Provenance: gratingspec.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
