---
op: hyperspectral_band_weights
dim: optics
category: spectral
in: 
out: matrix
examples: [poc_hyperspectral_foreign_matter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# hyperspectral_band_weights — OPTICS `spectral` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.hyperspectral_band_weights(wavelengths_nm=None, band_centers_nm=(950.0, 960.0, 970.0, 980.0, 990.0, 1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0, 1060.0, 1070.0, 1080.0, 1090.0, 1100.0, 1110.0, 1120.0, 1130.0, 1140.0, 1150.0, 1160.0, 1170.0, 1180.0, 1190.0, 1200.0, 1210.0, 1220.0, 1230.0, 1240.0, 1250.0, 1260.0, 1270.0, 1280.0, 1290.0, 1300.0, 1310.0, 1320.0, 1330.0, 1340.0, 1350.0, 1360.0, 1370.0, 1380.0, 1390.0, 1400.0, 1410.0, 1420.0, 1430.0, 1440.0, 1450.0, 1460.0, 1470.0, 1480.0, 1490.0, 1500.0, 1510.0, 1520.0, 1530.0, 1540.0, 1550.0, 1560.0, 1570.0, 1580.0, 1590.0, 1600.0, 1610.0, 1620.0, 1630.0, 1640.0, 1650.0), band_fwhm_nm=10.0, source_temperature_k=3000.0, irradiance_w_m2=10000.0, f_number=2.0, pixel_um=25.0, exposure_s=0.001, optics_material='SILICA', optics_thickness_mm=None, qe_cutoff_nm=1700.0)` (実装を直接呼ぶなら `import spectralrad; spectralrad.hyperspectral_band_weights(wavelengths_nm=None, band_centers_nm=(950.0, 960.0, 970.0, 980.0, 990.0, 1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0, 1060.0, 1070.0, 1080.0, 1090.0, 1100.0, 1110.0, 1120.0, 1130.0, 1140.0, 1150.0, 1160.0, 1170.0, 1180.0, 1190.0, 1200.0, 1210.0, 1220.0, 1230.0, 1240.0, 1250.0, 1260.0, 1270.0, 1280.0, 1290.0, 1300.0, 1310.0, 1320.0, 1330.0, 1340.0, 1350.0, 1360.0, 1370.0, 1380.0, 1390.0, 1400.0, 1410.0, 1420.0, 1430.0, 1440.0, 1450.0, 1460.0, 1470.0, 1480.0, 1490.0, 1500.0, 1510.0, 1520.0, 1530.0, 1540.0, 1550.0, 1560.0, 1570.0, 1580.0, 1590.0, 1600.0, 1610.0, 1620.0, 1630.0, 1640.0, 1650.0), band_fwhm_nm=10.0, source_temperature_k=3000.0, irradiance_w_m2=10000.0, f_number=2.0, pixel_um=25.0, exposure_s=0.001, optics_material='SILICA', optics_thickness_mm=None, qe_cutoff_nm=1700.0)`、台帳から引くなら `opsoptics.get("hyperspectral_band_weights")`)

## 使い方

反射率 → 帯域ごとの電子数の**線形写像** W(B × L)。電子数 = W @ R(λ)(雑音前)。

鎖: ハロゲン(黒体 *source_temperature_k*、ベルト面の 900〜2500 nm の放射照度を
*irradiance_w_m2* に合わせる)→ Lambert 面の放射輝度 L = E R/π → レンズ(F 値 *f_number*、
像面照度 π L T/(4N²)、物体は遠方)→ ガラスの内部透過率(``materials.material_transmittance``、
*optics_material* の厚さ *optics_thickness_mm*(None = 表面反射だけ)—— 光学系も観察対象と同じ材料表を引く)→ 分光の
帯域(Gauss、半値全幅 *band_fwhm_nm*)→ 光子数(λ/hc)→ InGaAs の QE
(:func:`ingaas_photodiode_qe`、*qe_cutoff_nm*)× 画素面積 × 露光時間。

返り値: (B, L) の ndarray。*wavelengths_nm* は反射率の波長格子(nm、昇順、各帯の ±3σ を覆うこと。
None なら 900〜2500 nm を 5 nm おき = ``spectral_reflectance_from_material`` の既定の格子)。

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

- [poc_hyperspectral_foreign_matter](../../../../examples/poc_hyperspectral_foreign_matter.py) — `py -3.11 examples/poc_hyperspectral_foreign_matter.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[abcd_trace](../geometric/abcd_trace.md) · [emva_filter_distortion](../sensorchar/emva_filter_distortion.md) · [mueller_apply](../polarization/mueller_apply.md) · [mueller_checks](../polarization/mueller_checks.md) · [equirect_rotate](../omni360/equirect_rotate.md) · [pixel_shift_capture](../pixelshift/pixel_shift_capture.md) · [pixel_shift_merge](../pixelshift/pixel_shift_merge.md) · [pixel_shift_motion_mask](../pixelshift/pixel_shift_motion_mask.md)

## 同カテゴリ(`spectral`)

[blackbody_spectrum](blackbody_spectrum.md) · [cie_illuminant_a](cie_illuminant_a.md) · [led_spectrum](led_spectrum.md) · [bandpass_spectrum](bandpass_spectrum.md) · [silicon_photodiode_qe](silicon_photodiode_qe.md) · [energy_to_photons](energy_to_photons.md) · [spectral_product](spectral_product.md) · [spectral_integral](spectral_integral.md)

---
*Provenance: spectralrad.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
