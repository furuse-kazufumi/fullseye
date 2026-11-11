---
op: hdr_exposure_series_simulate
dim: optics
category: hdr
in: image2d
out: images
gpu: なし
examples: [poc_hdr_glossy_metal_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# hdr_exposure_series_simulate — OPTICS `hdr` op

- **データ種**: `image2d` → `images`
- **呼び出し**: `import fullseye as fs; fs.ledger.hdr_exposure_series_simulate(radiance, exposures, eta=0.6, K=0.1, sigma_d_e=8.0, dark_offset_dn=4.0, bits=8, full_well_e=None, gamma=1.0, seed=0, as_float=True)` (実装を直接呼ぶなら `import hdrfusion; hdrfusion.hdr_exposure_series_simulate(radiance, exposures, eta=0.6, K=0.1, sigma_d_e=8.0, dark_offset_dn=4.0, bits=8, full_well_e=None, gamma=1.0, seed=0, as_float=True)`、台帳から引くなら `opsoptics.get("hdr_exposure_series_simulate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Shoot a known-radiance scene as an exposure series with an EMVA 1288 sensor model (``images``).

``radiance`` = 画素あたり・時間の単位あたりの光子数 ``μ_p / t``(既知の真値)。各露出 ``t`` で
電子 ``~ Poisson(η μ_p t)``(満杯 ``full_well_e`` で頭打ち)、暗雑音 ``N(0, σ_d²)`` [e⁻]、
``y = offset + K (電子 + 暗雑音)`` [DN]、``[0, 2^bits − 1]`` で切り(飽和)、応答
``x^(1/γ)``(``γ = 1`` は線形 = EMVA の線形モデルそのもの)、量子化。
``as_float=True`` は ``Z / (2^bits − 1)``(``hdr_merge`` 等が ``levels = 2^bits`` で正確に段に戻す)、
``False`` は整数の段。``seed`` を固定すれば決定的(露出ごとに別の乱数列)。

The true inverse response for ``γ`` is ``X(Z) = ((2^b−1)(Z/(2^b−1))^γ − offset) / (K η)``
photons (the mean, ignoring quantisation). Ground truth: with ``γ = 1`` the photon transfer
(``var_y`` vs ``μ_y``) of the output has slope ``K`` (:func:`sensorchar.emva_photon_transfer`).

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。ただし宣言された欠測を除く: `bottle_fit_from_pattern` の `u_map` は測れなかった画素を NaN で受け取る(∞ は拒否)。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。ただし宣言された欠測を除く: `bottle_background_map` は光線が使えない画素(全反射など)の `u_mm` を NaN で返し、`valid` マスクと本数を併せて返す。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_hdr_glossy_metal_inspection](../../../../examples/poc_hdr_glossy_metal_inspection.py) — `py -3.11 examples/poc_hdr_glossy_metal_inspection.py`

## 型が繋がる次の op(`images` を入力に取れる)

[film_thickness_map](../film/film_thickness_map.md) · [equirect_stabilize](../omni360/equirect_stabilize.md) · [equirect_from_fisheye_pair](../omni360/equirect_from_fisheye_pair.md) · [equirect_from_perspectives](../omni360/equirect_from_perspectives.md) · [grating_three_image_retrieve](../grating_interf/grating_three_image_retrieve.md) · [grating_step_period_estimate](../grating_interf/grating_step_period_estimate.md) · [retardation_unwrap_multiwavelength](../photoelastic/retardation_unwrap_multiwavelength.md) · [render_transport](../light_transport/render_transport.md)

## 同カテゴリ(`hdr`)

[camera_response_debevec](camera_response_debevec.md) · [camera_response_robertson](camera_response_robertson.md) · [camera_response_linear](camera_response_linear.md) · [hdr_merge](hdr_merge.md) · [exposure_fusion_mertens](exposure_fusion_mertens.md) · [hdr_radiance_error](hdr_radiance_error.md) · [hdr_dynamic_range](hdr_dynamic_range.md)

---
*Provenance: hdrfusion.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
