---
op: bottle_background_map
dim: optics
category: watervision
in: 
out: table
gpu: なし
examples: [poc_bottle_pattern_inverse]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# bottle_background_map — OPTICS `watervision` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.bottle_background_map(radius_mm, wall_mm, height_mm, fill_fraction, n_glass, n_liquid, background_distance_mm=150.0, camera_distance_mm=500.0, pixel_pitch_um=20.0, size=None, n_air=1.0) -> 'dict'` (実装を直接呼ぶなら `import watervision; watervision.bottle_background_map(radius_mm, wall_mm, height_mm, fill_fraction, n_glass, n_liquid, background_distance_mm=150.0, camera_distance_mm=500.0, pixel_pitch_um=20.0, size=None, n_air=1.0) -> 'dict'`、台帳から引くなら `opsoptics.get("bottle_background_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Where on a flat patterned background each pixel of a (part-)filled bottle looks -> dict (the map ``u`` in mm).

The same bottle and camera as :func:`bottle_image` (outer radius ``radius_mm``, glass wall ``wall_mm``, height ``height_mm``,
axis vertical, base at z = 0, pinhole ``camera_distance_mm`` from the axis, rows are the horizontal sections, ``pixel_pitch_um``
in the plane of the axis, row ``j`` at ``z = height - (j + 0.5) pitch``), but instead of a brightness it returns the coordinate
``u`` (mm, along the image rows) at which the ray of every pixel meets a flat pattern ``background_distance_mm`` behind the
axis. A pattern drawn on that plane (stripes, a checkerboard) is then seen at ``pattern(u)``: that is the distortion the bottle
imposes. The liquid (``n_liquid``) fills the bottle to ``fill_fraction * height_mm`` with a flat surface; no meniscus, no bubbles.
The ray of every row is traced through the circles of the section (outer wall, inner wall) with the vector form of
Snell's law; the vertical position on the background is the row's own height (the rows are independent, as in
:func:`bottle_image`: no refraction at the shoulder or the base, no tilt out of the section).

The table has ``u_mm`` (rows, cols; NaN where the pixel cannot be used), ``valid`` (True where ``u_mm`` is a number),
``weight`` (the Fresnel transmittance product of the ray, 1 outside the bottle; multiply the pattern contrast by it),
``u_straight_mm`` (the column coordinate without a bottle, ``x (dc + db) / dc``), ``x_mm``, ``z_mm``, ``pixel_pitch_mm``,
``fill_row_from_top``, ``liquid_rows``, ``fill_z_mm``, the counts ``tir_rays`` (rays that met a total internal reflection),
``backward_rays`` and ``unresolved_rays`` (all of them left NaN, never a guess) and the inputs echoed. Rows of equal geometry are
computed once, so they are bit identical. ``n_glass <= 1``, ``n_liquid <= 1``, ``n_air < 1`` or not below both, a fill outside
[0, 1], a wall not thinner than the radius, a background not behind the bottle and a camera not further than one
diameter are refused.

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

- [poc_bottle_pattern_inverse](../../../../examples/poc_bottle_pattern_inverse.py) — `py -3.11 examples/poc_bottle_pattern_inverse.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`watervision`)

[caustic_irradiance](caustic_irradiance.md) · [bottle_image](bottle_image.md) · [fill_level_from_image](fill_level_from_image.md) · [bottle_fit_from_pattern](bottle_fit_from_pattern.md) · [wet_surface_appearance](wet_surface_appearance.md) · [wet_dry_inspection_pair](wet_dry_inspection_pair.md) · [underwater_inspection_image](underwater_inspection_image.md) · [caustic_floor_segmentation](caustic_floor_segmentation.md)

---
*Provenance: watervision.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
