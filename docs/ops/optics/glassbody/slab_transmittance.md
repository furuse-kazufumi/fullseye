---
op: slab_transmittance
dim: optics
category: glassbody
in: signal
out: signal
examples: [glass_and_mirror_optics, machined_metal_and_materials]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# slab_transmittance — OPTICS `glassbody` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import glassmirror; glassmirror.slab_transmittance(cos_i, n1=1.0, n2=1.5, thickness_mm=3.0, sigma_per_mm=0.0) -> 'np.ndarray'` (または `opsoptics.get("slab_transmittance")`)

## 使い方

平行平板(窓ガラス)の透過率。**両面での多重反射**と内部吸収を含む。

cos_i / n1 / n2 / thickness_mm / sigma_per_mm は上記と同じ。

返り値: 全透過率 T。式は T = (1−R)²·a / (1 − R²·a²)、a = 内部透過率
(板内の斜め光路 L = d/cosθ_t を使う)。無限級数の和 = 多重反射を数え落とさない形。

検算: 吸収 0・垂直入射の air→BK7(n=1.5)板は T = 0.9231(= 2n/(n²+1) の
よく知られた値)。σ を上げると単調に下がり、臨界角超(板の内側から)では 0。

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

- [glass_and_mirror_optics](../../../../examples/glass_and_mirror_optics.py) — `py -3.11 examples/glass_and_mirror_optics.py`
- [machined_metal_and_materials](../../../../examples/machined_metal_and_materials.py) — `py -3.11 examples/machined_metal_and_materials.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[cie_xyz_from_wavelength](../appearance/cie_xyz_from_wavelength.md) · [spectrum_to_srgb](../appearance/spectrum_to_srgb.md) · [thin_film_reflectance](../appearance/thin_film_reflectance.md) · [fresnel_dielectric](../interface/fresnel_dielectric.md) · [fresnel_conductor](../interface/fresnel_conductor.md) · [metal_optical_constants](../mirror/metal_optical_constants.md) · [beer_lambert_transmittance](beer_lambert_transmittance.md) · [prism_min_deviation_deg](prism_min_deviation_deg.md)

## 同カテゴリ(`glassbody`)

[beer_lambert_transmittance](beer_lambert_transmittance.md) · [refract_rays](refract_rays.md) · [prism_min_deviation_deg](prism_min_deviation_deg.md)

---
*Provenance: glassmirror.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
