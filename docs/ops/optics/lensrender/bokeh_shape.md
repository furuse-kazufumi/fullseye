---
op: bokeh_shape
dim: optics
category: lensrender
in: table
out: table
gpu: なし
examples: [poc_photograph_through_prescription]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# bokeh_shape — OPTICS `lensrender` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.bokeh_shape(system, field_xy_mm=None, defocus_mm=0.5, pupil_samples=512, object_mm=None, wavelength_um=None, grid=64) -> 'dict'` (実装を直接呼ぶなら `import lensrender; lensrender.bokeh_shape(system, field_xy_mm=None, defocus_mm=0.5, pupil_samples=512, object_mm=None, wavelength_um=None, grid=64) -> 'dict'`、台帳から引くなら `opsoptics.get("bokeh_shape")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

The out-of-focus footprint of a point source - the intersection of the pupil images, the cat's eye -> dict.

The point sits at *field_xy_mm* in the object plane at *object_mm* (a height in mm; for an object at infinity a pair of angles in degrees;
default: (0, 8) degrees for an object at infinity, a height of 5 % of the object distance otherwise), the sensor is *defocus_mm* behind the system's image plane.
A hexapolar pupil bundle of about *pupil_samples* rays is traced forward (``raytrace.ray_bundle``, which stops a ray at every semi-diameter);
the rays that get through land on the shifted sensor and their convex hull is the footprint. The table has ``polygon_xy_mm`` (the hull,
counter-clockwise, relative to its centroid, on the sensor axes), ``mask`` (a ``grid x grid`` boolean image of the footprint, ``extent_mm`` wide),
``area_mm2``, the same for the on-axis point (``axis_area_mm2``), ``area_ratio`` (cat's eye / on-axis disc), ``vignetting_factor`` (the share of the pupil
area that gets through relative to the axis, from the ray bundle), ``n_valid``, ``centroid_xy_mm``, ``symmetry_error_mm`` (how far the footprint is from its mirror image
about the meridional plane, 0 in exact arithmetic) and the footprint points ``points_xy_mm``. The geometric defocus disc of a point on axis has the
diameter ``2 |defocus| NA'`` (tested). The system must be axisymmetric (the field is traced along +y and rotated).

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

- [poc_photograph_through_prescription](../../../../examples/poc_photograph_through_prescription.py) — `py -3.11 examples/poc_photograph_through_prescription.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`lensrender`)

[lens_scene](lens_scene.md) · [exit_pupil_samples](exit_pupil_samples.md) · [trace_sensor_rays](trace_sensor_rays.md) · [scene_radiance](scene_radiance.md) · [render_scene_through_lens](render_scene_through_lens.md) · [render_ghost_overlay](render_ghost_overlay.md) · [render_compare_prescriptions](render_compare_prescriptions.md)

---
*Provenance: lensrender.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
