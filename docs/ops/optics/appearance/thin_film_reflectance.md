---
op: thin_film_reflectance
dim: optics
category: appearance
in: signal
out: signal
examples: [appearance_structural_colour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# thin_film_reflectance — OPTICS `appearance` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import matappear; matappear.thin_film_reflectance(nm, thickness_nm=350.0, n_film=1.33, n_sub=1.0, cos_theta=1.0, n_out=1.0) -> 'np.ndarray'` (または `opsoptics.get("thin_film_reflectance")`)

## 使い方

薄膜(厚さ d、屈折率 n_film)の分光反射率。Airy(多重反射)の閉じた式。

nm:           波長 [nm] (配列可)。
thickness_nm: 膜厚 [nm]。シャボン玉なら 200–800、陽極酸化被膜なら 50–300。
n_film/n_sub/n_out: 膜 / 基板 / 入射側の屈折率(実数、吸収なし)。
cos_theta:    入射側での入射角の cos(配列可、nm とブロードキャストできる形)。

返り値: 反射率 R(0–1)。nm と cos_theta のブロードキャスト形。

物理: 膜内の伝搬による位相差 δ = 2π·(2 n_film d cosθ_film)/λ。境界のフレネル係数
(s 偏光と p 偏光の平均 = 無偏光)を r1, r2 として R = |r1 + r2 e^{-iδ}|² / |1 + r1 r2 e^{-iδ}|²。
λ/4 の奇数倍で反射が極大(n_film > n_sub のとき)になり、**厚みを変えると色が動く**のが
シャボン玉の色。膜厚 0 では R が基板単体のフレネル反射に一致する(テストで確認)。

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない
- [mv_illumination_practice](../guides/mv_illumination_practice.md) — 照明の実務知識 — 波長・偏光・点灯方式・外光・安全

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [appearance_structural_colour](../../../../examples/appearance_structural_colour.py) — `py -3.11 examples/appearance_structural_colour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[cie_xyz_from_wavelength](cie_xyz_from_wavelength.md) · [spectrum_to_srgb](spectrum_to_srgb.md) · [fresnel_dielectric](../interface/fresnel_dielectric.md) · [fresnel_conductor](../interface/fresnel_conductor.md) · [metal_optical_constants](../mirror/metal_optical_constants.md) · [beer_lambert_transmittance](../glassbody/beer_lambert_transmittance.md) · [slab_transmittance](../glassbody/slab_transmittance.md) · [prism_min_deviation_deg](../glassbody/prism_min_deviation_deg.md)

## 同カテゴリ(`appearance`)

[cie_xyz_from_wavelength](cie_xyz_from_wavelength.md) · [spectrum_to_srgb](spectrum_to_srgb.md) · [grating_wavelengths](grating_wavelengths.md) · [grating_rgb](grating_rgb.md) · [thin_film_rgb](thin_film_rgb.md) · [ward_anisotropic](ward_anisotropic.md)

---
*Provenance: matappear.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
