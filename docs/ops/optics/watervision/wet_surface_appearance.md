---
op: wet_surface_appearance
dim: optics
category: watervision
in: 
out: table
gpu: なし
examples: [poc_water_inspection_images]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# wet_surface_appearance — OPTICS `watervision` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.wet_surface_appearance(albedo, roughness, water_film_um, view_deg, light_deg, n_water=None) -> 'dict'` (実装を直接呼ぶなら `import watervision; watervision.wet_surface_appearance(albedo, roughness, water_film_um, view_deg, light_deg, n_water=None) -> 'dict'`、台帳から引くなら `opsoptics.get("wet_surface_appearance")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

The darkening and the gloss of a surface under a thin water film (Lekner & Dorf 1988; Twomey et al. 1986) -> dict.

A dry diffuse surface of albedo ``a`` returns ``a`` of the light. Under a water film the light that the surface
scatters upward reaches the water-air interface; the part beyond the critical angle (and the Fresnel share below it) is
reflected back down, hits the surface again and is partly absorbed again. With ``r`` the hemispherical,
cosine-weighted internal reflectance of the interface (computed by quadrature, about 0.47 for water) and ``R_s`` the Fresnel
reflectance of the incoming light at ``light_deg``, the geometric series of the trapped light gives, for a
Lambertian surface, ``a_film = a (1 - R_s) (1 - r) / (1 - a r)``. This is below ``a`` for every ``a`` in (0, 1) and the
darkening is stronger for darker surfaces (a = 0.5 loses about a third). ``water_film_um`` enters only through an
assumed coverage ``c = 1 - exp(-film / 2 um)`` (a film thicker than a few micrometres wets all the roughness; interference
in films thinner than a wavelength is not modelled), ``wet_albedo = (1 - c) a + c a_film``, so a film of 0 returns
``a`` exactly. The film also glosses: its smooth surface mirrors the light with the Fresnel reflectance of water (``n`` = 1.33; the dry
dielectric uses 1.5) in a lobe half as wide as the dry one (Gaussian, sigma ``0.03 (1 + 4 roughness)`` rad for the dry
surface), radiance factor ``pi F G(eps) / cos(light)`` with ``eps`` the angle between
the mirrored light and the viewing direction (``|light_deg - view_deg|`` in the plane of incidence, the viewer opposite the light).

``albedo`` in [0, 1] and ``roughness`` in [0, 1] broadcast with ``water_film_um`` (>= 0); ``view_deg`` and ``light_deg`` are scalars in
[0, 90). The table has ``wet_albedo``, ``dry_albedo``, ``ratio`` (wet / dry, 1 where the albedo is 0), ``film_albedo`` (the
fully wet value), ``coverage``, ``internal_reflectance_mean`` (r), ``fresnel_light`` (R_s), ``specular_dry``, ``specular_wet``,
``specular_fraction_dry`` / ``specular_fraction_wet`` (the share of the specular radiance factor in the total), ``wet_albedo_rgb``
(shape + (3,), with the index of water at 0.61 / 0.54 / 0.465 um), ``n_water_rgb``, ``n_water`` and ``darker`` (all wet albedos
below the dry ones where the film is thick). Albedos or roughness outside [0, 1], a negative film and angles outside [0, 90)
are refused.

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

- [poc_water_inspection_images](../../../../examples/poc_water_inspection_images.py) — `py -3.11 examples/poc_water_inspection_images.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`watervision`)

[caustic_irradiance](caustic_irradiance.md) · [bottle_image](bottle_image.md) · [fill_level_from_image](fill_level_from_image.md) · [wet_dry_inspection_pair](wet_dry_inspection_pair.md) · [underwater_inspection_image](underwater_inspection_image.md) · [caustic_floor_segmentation](caustic_floor_segmentation.md)

---
*Provenance: watervision.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
