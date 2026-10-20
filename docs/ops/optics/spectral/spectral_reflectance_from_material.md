---
op: spectral_reflectance_from_material
dim: optics
category: spectral
in: 
out: pairs
examples: [poc_hyperspectral_foreign_matter]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# spectral_reflectance_from_material — OPTICS `spectral` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.spectral_reflectance_from_material(material='NUT_KERNEL', particle_um=None, thickness_mm=10.0, background_reflectance=0.05, water_fraction=None, carbon_black_fraction=0.0, internal_reflectance=0.6, wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)` (実装を直接呼ぶなら `import spectralrad; spectralrad.spectral_reflectance_from_material(material='NUT_KERNEL', particle_um=None, thickness_mm=10.0, background_reflectance=0.05, water_fraction=None, carbon_black_fraction=0.0, internal_reflectance=0.6, wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)`、台帳から引くなら `opsoptics.get("spectral_reflectance_from_material")`)

## 使い方

材料表の近赤外の吸収帯から、粒(破片)の拡散反射率スペクトルを作る(観察対象の側)。

1. α(λ) = ``materials.material_nir_absorption``(帯の重ね合わせ、水は表の Hale & Querry)
   + カーボンブラック(``materials.carbon_black_absorption``、*carbon_black_fraction* 質量分率)。
2. S = S_ref · (d_ref / *particle_um*)(散乱は粒径に反比例、S_ref と d_ref は材料の表の値)。
3. 層の拡散反射 R_KM = :func:`kubelka_munk_reflectance`(既定は厚さ 10 mm の粒が *background_reflectance*
   の上に載る —— 薄い破片ほどベルトが透ける。None なら無限厚で、背景は効かない)。
4. 界面: Saunderson (1942) の補正 R = r_s + (1 − r_s)(1 − r_i) R_KM / (1 − r_i R_KM)、
   r_s = ((n − 1)/(n + 1))²(表の n_nir の垂直入射 Fresnel)、r_i = *internal_reflectance*
   (中から見た拡散光の内部反射、0.4〜0.6 が典型)。鏡面の光沢は**波長に平坦**なので、
   黒い樹脂でも 4〜5 % の平らな反射が残り、帯の形が消える。

返り値: pairs(λ nm, R)。粒が粗い・厚いほど暗く帯が深く、細かいほど明るく浅い(Kubelka–Munk
の S 依存)。

出典: Kubelka (1948)、J. L. Saunderson, J. Opt. Soc. Am. 32, 727 (1942)、帯の表は
``materials.NIR_BAND_MODELS`` の注。

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

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](energy_to_photons.md) · [spectral_product](spectral_product.md) · [spectral_integral](spectral_integral.md) · [spectral_stats](spectral_stats.md) · [kubelka_munk_reflectance](kubelka_munk_reflectance.md) · [hyperspectral_capture](hyperspectral_capture.md) · [film_thickness_fft](../film/film_thickness_fft.md)

## 同カテゴリ(`spectral`)

[blackbody_spectrum](blackbody_spectrum.md) · [cie_illuminant_a](cie_illuminant_a.md) · [led_spectrum](led_spectrum.md) · [bandpass_spectrum](bandpass_spectrum.md) · [silicon_photodiode_qe](silicon_photodiode_qe.md) · [energy_to_photons](energy_to_photons.md) · [spectral_product](spectral_product.md) · [spectral_integral](spectral_integral.md)

---
*Provenance: spectralrad.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
