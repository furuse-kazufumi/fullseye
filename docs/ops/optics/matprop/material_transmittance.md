---
op: material_transmittance
dim: optics
category: matprop
in: 
out: pairs
examples: [poc_fiber_light_guide, poc_material_optical_library, poc_nir_silicon_transmission]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# material_transmittance — OPTICS `matprop` op

- **データ種**: `なし` → `pairs`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.material_transmittance(material='SI', thickness_mm: 'float' = 0.7, wl_min_nm: 'float' = 900.0, wl_max_nm: 'float' = 1400.0, n_points: 'int' = 101, include_fresnel: 'bool' = True, extra_absorption=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import materials; materials.material_transmittance(material='SI', thickness_mm: 'float' = 0.7, wl_min_nm: 'float' = 900.0, wl_max_nm: 'float' = 1400.0, n_points: 'int' = 101, include_fresnel: 'bool' = True, extra_absorption=None) -> 'np.ndarray'`、台帳から引くなら `opsoptics.get("material_transmittance")`)

## 使い方

平行平板(厚さ ``thickness_mm``)の透過率 T(λ) を ``pairs``(λ [nm], T)で返す。

T = (1 − R)² e^{−αt} / (1 − R² e^{−2αt})(両面の多重反射を足した非コヒーレントの式、
R は垂直入射の |(m − 1)/(m + 1)|²、α = 4πk/λ)。``include_fresnel=False`` で内部透過率
e^{−αt} だけにする(硝材カタログの「内部透過率」と同じ量)。
厚さ 0 は T = 1 になるが、負や非有限は ValueError。

``extra_absorption``: 材料の表に無い吸収を足す ``pairs``(λ [nm], α [1/cm])。例: ドープした Si の自由キャリア吸収
``silicon_free_carrier_absorption(1e19, "n", ...)`` をそのまま渡す。格子の全波長を覆わなければ ValueError
(外挿しない)、負の α も ValueError。表面の反射 R は材料の n,k のまま(自由キャリアの n の変化は小さいので無視)。

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

- [poc_fiber_light_guide](../../../../examples/poc_fiber_light_guide.py) — `py -3.11 examples/poc_fiber_light_guide.py`
- [poc_material_optical_library](../../../../examples/poc_material_optical_library.py) — `py -3.11 examples/poc_material_optical_library.py`
- [poc_nir_silicon_transmission](../../../../examples/poc_nir_silicon_transmission.py) — `py -3.11 examples/poc_nir_silicon_transmission.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](../imaging/mtf50.md) · [energy_to_photons](../spectral/energy_to_photons.md) · [spectral_product](../spectral/spectral_product.md) · [spectral_integral](../spectral/spectral_integral.md) · [spectral_integral_table](../spectral/spectral_integral_table.md) · [spectral_stats](../spectral/spectral_stats.md) · [kubelka_munk_reflectance](../spectral/kubelka_munk_reflectance.md) · [hyperspectral_capture](../spectral/hyperspectral_capture.md)

## 同カテゴリ(`matprop`)

[material_table](material_table.md) · [material_record](material_record.md) · [material_optical_constants](material_optical_constants.md) · [material_dispersion](material_dispersion.md) · [material_extinction](material_extinction.md) · [material_absorption](material_absorption.md) · [material_reflectance](material_reflectance.md) · [abbe_number](abbe_number.md)

---
*Provenance: materials.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
