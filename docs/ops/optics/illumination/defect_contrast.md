---
op: defect_contrast
dim: optics
category: illumination
in: table
out: table
examples: [illumination_design_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# defect_contrast — OPTICS `illumination` op

- **データ種**: `table` → `table`
- **呼び出し**: `import illumdesign; illumdesign.defect_contrast(light, surface='satin', slopes_deg=(2.0, 5.0, 10.0, 20.0), camera=(0.0, 0.0, 300.0), point=(0.0, 0.0), n_azimuth=12, pigment_albedo_ratio=0.5)` (または `opsoptics.get("defect_contrast")`)

## 使い方

Contrast of topographic and pigment defects under a light (``table``).

For each facet slope in *slopes_deg* the radiance toward *camera* of a
facet tilted by that slope (azimuth swept in *n_azimuth* steps) is compared
with the flat surface at *point*: ``contrast = (L_defect − L_flat) /
(L_defect + L_flat)`` (Michelson, −1..1; the sign says whether the flank
appears brighter or darker than the surround). Reported per slope as
``mean``, ``max_abs`` and ``azimuth_of_max``. ``pigment`` is the contrast
of a flat patch whose albedo is *pigment_albedo_ratio* × the surround —
the number specular glare dilutes. ``scatter`` is the contrast of a
**rough** patch (a chipped edge, a pit floor, a fine scratch: micro-facets
of every slope, modelled as Lambertian with reflectance ``F + (1 − F)ρ``,
the Fresnel fraction the flat surface would have sent into its specular
direction now scattered) against the surround — the defect class dark-field lighting is
built for, since a smooth facet only lights up when it mirrors the source
into the camera while a rough patch scatters some of *any* light there,
and at grazing incidence that Fresnel fraction is large. ``regime`` is
``"bright_field"`` when
the flat surface returns specular light to the camera (specular ≥ diffuse
radiance) and ``"dark_field"`` otherwise. *surface*: a preset (``matte``,
``satin``, ``glossy``, ``mirror``, ``brushed_metal``) or a dict ``{albedo,
roughness, f0}``.

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

- [mv_illumination_practice](../guides/mv_illumination_practice.md) — 照明の実務知識 — 波長・偏光・点灯方式・外光・安全

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [illumination_design_demo](../../../../examples/illumination_design_demo.py) — `py -3.11 examples/illumination_design_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md) · [spot_diagram](../design/spot_diagram.md)

## 同カテゴリ(`illumination`)

[light_source](light_source.md) · [irradiance_map](irradiance_map.md) · [illumination_uniformity](illumination_uniformity.md) · [lighting_sweep](lighting_sweep.md) · [illumination_design](illumination_design.md)

---
*Provenance: illumdesign.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
