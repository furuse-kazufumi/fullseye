---
op: ocean_height_field
dim: optics
category: watermedia
in: 
out: table
examples: [poc_water_transparent_media]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# ocean_height_field — OPTICS `watermedia` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ocean_height_field(size, extent_m, wind_speed_mps, wind_dir_deg, t=0.0, seed=0, kind='pierson_moskowitz', directional='cos2', choppiness=0.0, depth_m=None, spreading_s=10.0, fetch_m=None, single_mode=None) -> 'dict'` (実装を直接呼ぶなら `import watermedia; watermedia.ocean_height_field(size, extent_m, wind_speed_mps, wind_dir_deg, t=0.0, seed=0, kind='pierson_moskowitz', directional='cos2', choppiness=0.0, depth_m=None, spreading_s=10.0, fetch_m=None, single_mode=None) -> 'dict'`、台帳から引くなら `opsoptics.get("ocean_height_field")`)

## 使い方

A Tessendorf (2001) FFT sea surface at time ``t`` -> dict (height, slopes, normal map, displacement).

The wave-number spectrum is the omnidirectional spectrum of :func:`ocean_spectrum` carried to the plane,
``psi(k, theta) = S(omega) D(theta) (d omega / d k) / k``, with the dispersion ``omega^2 = g k`` (deep water) or
``omega^2 = g k tanh(k h)`` when ``depth_m`` is given. ``D`` is ``cos2`` (``2/pi cos^2`` within 90 degrees of the wind) or
``cos2s`` (``cos^(2s)((theta - theta_w) / 2)``, ``s = spreading_s``), both normalised to 1 over the circle. The
random amplitudes are ``h0(k) = (xi_r + j xi_i)/sqrt(2) sqrt(psi / 2) dk`` and ``h(k, t) = h0(k) e^(-j omega t) +
conj(h0(-k)) e^(+j omega t)``, which is Hermitian, so the height is real (``imag_residual`` reports the largest
imaginary part left by the transform). The mean, the Nyquist row and column are zeroed. ``seed`` fixes the amplitudes:
the same seed gives the same sea at every ``t``. ``choppiness`` moves each point horizontally by ``choppiness`` times
the Tessendorf displacement (0 gives exactly zero displacement). ``size`` is the number of points per side (the
grid is ``size x size`` over ``extent_m`` metres, wrap-around); ``wind_dir_deg`` is the direction the waves travel,
from +x towards +y. ``single_mode=(mx, my, amplitude_m)`` replaces the random sea with one travelling cosine wave.
The table has ``height``, ``slope_x``, ``slope_y`` (dh/dx, dh/dy), ``normal`` (H, W, 3), ``displacement_x`` / ``displacement_y``,
``x_m`` / ``y_m``, ``extent_m``, ``variance_expected_m2`` and ``slope_variance_expected`` (the sums of the spectrum over
the modes in use), ``cox_munk_slope_variance`` (0.003 + 0.00512 U, Cox & Munk 1954), ``slope_variance_with_tail`` and ``omega_mode`` (single mode only).
A sea of this kind has no capillary waves, so its resolved slope variance is far below the Cox & Munk value; ``slope_variance_with_tail`` adds the
saturation range ``alpha / 2 ln(k_c / k_nyquist)`` of the spectrum up to the gravity-capillary wave number ``k_c = 370 rad/m``. That agrees with Cox & Munk
at 5 m/s and falls 40 % short at 10 m/s (the constant ``alpha`` of the Pierson-Moskowitz range does not grow with the wind); both are shown in the PoC.

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

- [poc_water_transparent_media](../../../../examples/poc_water_transparent_media.py) — `py -3.11 examples/poc_water_transparent_media.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`watermedia`)

[ocean_spectrum](ocean_spectrum.md) · [fresnel_water_air](fresnel_water_air.md) · [snell_window](snell_window.md) · [refracted_view](refracted_view.md) · [water_attenuation](water_attenuation.md) · [underwater_image](underwater_image.md) · [phase_function_hg](phase_function_hg.md) · [scattering_phase_petzold](scattering_phase_petzold.md)

---
*Provenance: watermedia.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
