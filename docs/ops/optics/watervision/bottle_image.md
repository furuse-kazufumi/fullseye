---
op: bottle_image
dim: optics
category: watervision
in: 
out: table
examples: [poc_water_inspection_images]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# bottle_image — OPTICS `watervision` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.bottle_image(radius_mm, wall_mm, height_mm, fill_fraction, n_glass, n_liquid, meniscus_mm=0.0, bubbles=None, camera_distance_mm=500.0, pixel_pitch_um=20.0, size=None, light='backlight', n_air=1.0) -> 'dict'` (実装を直接呼ぶなら `import watervision; watervision.bottle_image(radius_mm, wall_mm, height_mm, fill_fraction, n_glass, n_liquid, meniscus_mm=0.0, bubbles=None, camera_distance_mm=500.0, pixel_pitch_um=20.0, size=None, light='backlight', n_air=1.0) -> 'dict'`、台帳から引くなら `opsoptics.get("bottle_image")`)

## 使い方

A side view of a cylindrical bottle, part filled with a liquid, ray-cast row by row -> dict.

The bottle (outer radius ``radius_mm``, glass wall ``wall_mm``, height ``height_mm``, axis vertical, base at z = 0) is looked at
by a pinhole camera ``camera_distance_mm`` from the axis. Every image row is the horizontal cross-section at its height: the
ray of a pixel is traced through the circles of the section (outer wall, inner wall, the edge of the liquid in a
meniscus row, bubbles) with the vector form of Snell's law and the unpolarised Fresnel transmittance at each interface.
Total internal reflection reflects the ray (at most 24 interface events are followed; a ray still wandering then is
counted in ``unresolved_rays`` and left dark). The liquid (``n_liquid``) fills the bottle up to ``fill_fraction * height_mm``;
``meniscus_mm`` lets it climb the wall by that much as ``(rho / r_inner)^6``. ``bubbles`` is a list of
``(x_mm, z_mm, r_mm)`` (or with a fourth ``y_mm`` along the viewing axis; default 0): air spheres in the liquid, drawn as
their circle in each row they cross. ``pixel_pitch_um`` is the sampling pitch in the plane of the axis, so
``1000 / pixel_pitch_um`` pixels are 1 mm there; ``size`` is ``(rows, cols)`` (default: the rows exactly cover the height,
the width is 1.15 times the diameter); row ``j`` is at ``z = height - (j + 0.5) pitch``.

``light="backlight"``: a diffuse panel of radiance 1 behind the bottle that emits only within +-8 degrees of the viewing axis
(soft edge 1 degree): a pixel is lit when its ray leaves the bottle inside that cone, times the product of the Fresnel
transmittances. The empty bottle bends rays little and is lit to near the edges; the filled one is a cylindrical lens, so only
a central band (half width ``alpha / (1/f - 1/dc)`` with the paraxial focal length ``f`` of :func:`watermedia.cylinder_lens_caustic`) is lit and the
flanks go dark; an air bubble in the liquid is a diverging lens and shows as a dark ring. ``light="frontlight"``: a matt wall of radiance 0.8 behind,
a dim dome plus a soft box at 35 degrees, and the first Fresnel reflection of the outer wall (``R`` times the environment radiance),
which gives the glint and the bright rim at grazing view. Interior reflections other than total internal reflection are not
followed, the rows are independent (no vertical refraction at the shoulder or the base), and rows without bubbles or
meniscus are computed once per kind (the empty and the full section), so rows of equal geometry are bit identical.

The table has ``image`` (rows, cols; no pixel exceeds 1), ``x_mm``, ``z_mm``, ``pixel_pitch_mm``, ``magnification_px_per_mm``,
``fill_row_from_top`` (the first liquid row), ``liquid_rows`` (rows with liquid; about ``fill_fraction height / pitch``),
``fill_z_mm``, ``paraxial_efl_mm`` and ``band_half_width_mm_paraxial`` (the predicted half width of the lit band of the filled
bottle, inf when the lens does not converge within the camera distance), ``central_transmittance_empty`` / ``..._filled``
(the product of the normal-incidence Fresnel transmittances of the four interfaces on the axis), ``unresolved_rays`` and the inputs
echoed. ``n_glass <= 1``, ``n_liquid <= 1``, ``n_air < 1`` or not below both, a fill outside [0, 1], a wall not thinner than the
radius, a meniscus that does not fit and a bubble outside the liquid are refused.

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

[caustic_irradiance](caustic_irradiance.md) · [fill_level_from_image](fill_level_from_image.md) · [wet_surface_appearance](wet_surface_appearance.md) · [wet_dry_inspection_pair](wet_dry_inspection_pair.md) · [underwater_inspection_image](underwater_inspection_image.md) · [caustic_floor_segmentation](caustic_floor_segmentation.md)

---
*Provenance: watervision.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
