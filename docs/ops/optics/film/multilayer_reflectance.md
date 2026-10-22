---
op: multilayer_reflectance
dim: optics
category: film
in: 
out: pairs
examples: [poc_simcal_thin_film, poc_thin_film_reflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# multilayer_reflectance — OPTICS `film` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.multilayer_reflectance(layers=(('SIO2', 100.0),), substrate='SI', wl_min_nm=400.0, wl_max_nm=800.0, n_points=201, angle_deg=0.0, polarization='unpolarized', na=0.0, roughness_nm=0.0, ambient=1.0, quantity='reflectance', wavelengths_nm=None)` (実装を直接呼ぶなら `import filmoptics; filmoptics.multilayer_reflectance(layers=(('SIO2', 100.0),), substrate='SI', wl_min_nm=400.0, wl_max_nm=800.0, n_points=201, angle_deg=0.0, polarization='unpolarized', na=0.0, roughness_nm=0.0, ambient=1.0, quantity='reflectance', wavelengths_nm=None)`、台帳から引くなら `opsoptics.get("multilayer_reflectance")`)

## 使い方

多層膜の分光反射率(または透過率・吸収率)を ``pairs``(λ [nm], 値)で返す。特性行列(転送行列)の厳密解。

layers:       入射側から順の ``[(材料, 厚さ nm), ...]``。材料は材料表の鍵(``"SIO2"`` / ``"SI3N4"`` / ``"PMMA"``
              / ``"TIO2"`` …)・材料レコード・実数・複素数 n + ik。空にすると基板だけ(裸の面の Fresnel)。
substrate:    基板(半無限)。既定は材料表の Si(Green 2008、k つき)。
wl_min_nm / wl_max_nm / n_points: 波長の等間隔格子。``wavelengths_nm`` を渡せばそちらを使う(昇順)。
angle_deg:    入射角(入射側の媒質の中)。
polarization: "unpolarized"(s と p の平均)/ "s" / "p"。
na:           集光の開口数(> 0 なら法線まわりの円錐で角度平均。瞳を一様に満たす照明 = 重みは sin²θ に一様)。
              angle_deg と同時には指定できない。
roughness_nm: 共形な粗さの RMS σ。R に exp(−(4π n₀ σ cos θ₀ / λ)²)(Debye–Waller)が掛かる。
ambient:      入射側の媒質(実数か材料表の鍵、透明であること)。液浸なら ``"WATER"``。
quantity:     "reflectance" / "transmittance"(基板の中へ入る割合)/ "absorptance"(層での吸収 = 1 − R − T)。
              粗さ > 0 では T と A を出さない(散乱光の行き先をこのモデルは持たない → ValueError)。

返り値: (K, 2) の pairs。

真値: 1 層なら Airy の閉じた式(テストと PoC に独立に書いた式)と一致する。膜厚 0 は裸の基板の Fresnel、
λ/4 の AR 膜(n = √n_sub)は設計波長で R = 0、(HL)^N の鏡は閉形式 ((1 − q)/(1 + q))²、q = (n_s/n₀)(n_H/n_L)^{2N}(H が入射側)。
吸収の無い積層では R + T = 1。

>>> p = multilayer_reflectance([("SIO2", 500.0)], "SI", 400.0, 800.0, 5)
>>> p.shape
(5, 2)

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

- [poc_simcal_thin_film](../../../../examples/poc_simcal_thin_film.py) — `py -3.11 examples/poc_simcal_thin_film.py`
- [poc_thin_film_reflectometry](../../../../examples/poc_thin_film_reflectometry.py) — `py -3.11 examples/poc_thin_film_reflectometry.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_integral_table](../spectral/spectral_integral_table.md) · [spectral_stats](../spectral/spectral_stats.md) · [kubelka_munk_reflectance](../spectral/kubelka_munk_reflectance.md) · [hyperspectral_capture](../spectral/hyperspectral_capture.md)

## 同カテゴリ(`film`)

[film_color](film_color.md) · [film_thickness_fft](film_thickness_fft.md) · [film_thickness_fit](film_thickness_fit.md) · [film_thickness_map](film_thickness_map.md)

---
*Provenance: filmoptics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
