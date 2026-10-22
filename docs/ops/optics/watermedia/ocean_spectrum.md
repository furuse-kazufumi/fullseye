---
op: ocean_spectrum
dim: optics
category: watermedia
in: 
out: table
examples: [poc_water_transparent_media]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# ocean_spectrum — OPTICS `watermedia` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ocean_spectrum(wind_speed_mps, fetch_m=None, kind='pierson_moskowitz', omega=None, gamma=3.3) -> 'dict'` (実装を直接呼ぶなら `import watermedia; watermedia.ocean_spectrum(wind_speed_mps, fetch_m=None, kind='pierson_moskowitz', omega=None, gamma=3.3) -> 'dict'`、台帳から引くなら `opsoptics.get("ocean_spectrum")`)

## 使い方

One-dimensional wave spectrum S(omega) of a wind sea, with its significant height and peak period -> dict.

``pierson_moskowitz`` (Pierson & Moskowitz 1964, a fully developed sea): ``S = alpha g^2 omega^-5
exp(-1.25 (omega_p / omega)^4)`` with ``alpha = 0.0081`` and ``omega_p = (4 beta / 5)^(1/4) g / U = 0.877 g / U`` (``U`` is
the wind speed at 10 m). Its zeroth moment is ``m0 = alpha U^4 / (4 beta g^2)`` so ``Hs = 4 sqrt(m0) = 0.2092 U^2 / g``
(the rule of thumb is 0.21 U^2 / g); ``hs_closed_form_m`` is that value (None where there is no closed form) and ``hs_m`` the numerical integral of the
returned spectrum. ``jonswap`` (Hasselmann et al. 1973) multiplies the same shape by the peak enhancement
``gamma ** exp(-(omega - omega_p)^2 / (2 sigma^2 omega_p^2))`` (``gamma = 3.3``, ``sigma = 0.07`` below the peak and
``0.09`` above). With ``fetch_m`` the fetch-limited ``alpha = 0.076 (U^2 / (F g))^0.22`` and ``omega_p = 22 (g^2 / (U F))^(1/3)``
are used, without it the fully developed Pierson-Moskowitz ``alpha`` and ``omega_p``: JONSWAP with ``gamma = 1`` is then
exactly Pierson-Moskowitz. ``omega`` is an optional increasing grid (rad/s); the default is 6000 points on a
logarithmic grid from 0.15 to 25 times ``omega_p``. The table has ``omega``, ``S``, ``hs_m``, ``tp_s`` (2 pi / omega_p),
``omega_peak`` (the parameter), ``omega_peak_numeric`` (the maximum of S) and ``m0``. A negative or zero wind or fetch is
refused; ``fetch_m`` with the fully developed kind is refused too.

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

[ocean_height_field](ocean_height_field.md) · [fresnel_water_air](fresnel_water_air.md) · [snell_window](snell_window.md) · [refracted_view](refracted_view.md) · [water_attenuation](water_attenuation.md) · [underwater_image](underwater_image.md) · [phase_function_hg](phase_function_hg.md) · [scattering_phase_petzold](scattering_phase_petzold.md)

---
*Provenance: watermedia.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
