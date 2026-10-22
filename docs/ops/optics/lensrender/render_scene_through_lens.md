---
op: render_scene_through_lens
dim: optics
category: lensrender
in: table
out: table
examples: [poc_photograph_through_prescription]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# render_scene_through_lens — OPTICS `lensrender` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_scene_through_lens(system, scene=None, sensor=None, pupil_samples=64, wavelengths=None, exposure_s=0.0001, illuminant=None, seed=0, defocus_mm=0.0, oversample=1, pupil_pattern='halton', pupil_uv=None, pupil_jitter=True, focus_mm=None, add_noise=True, output='float', band_nm=None, source_rings=24) -> 'dict'` (実装を直接呼ぶなら `import lensrender; lensrender.render_scene_through_lens(system, scene=None, sensor=None, pupil_samples=64, wavelengths=None, exposure_s=0.0001, illuminant=None, seed=0, defocus_mm=0.0, oversample=1, pupil_pattern='halton', pupil_uv=None, pupil_jitter=True, focus_mm=None, add_noise=True, output='float', band_nm=None, source_rings=24) -> 'dict'`、台帳から引くなら `opsoptics.get("render_scene_through_lens")`)

## 使い方

Photograph a :func:`lens_scene` through the prescription *system*: sensor-side ray tracing -> dict.

For every pixel (and ``oversample`` x ``oversample`` points inside it) and every wavelength, the exit pupil is sampled at
``pupil_samples`` points (Halton or hexapolar, each pixel's pattern turned by a fixed golden-ratio angle when
*pupil_jitter* is on, so the noiseless image does not depend on *seed*), each ray is traced backwards through the lens
(:func:`trace_sensor_rays`), shaded in the scene (:func:`scene_radiance`) and weighted by ``cos^2(theta) / d^2`` times the
pupil-sample area: the Monte Carlo estimate of ``E = integral L cos(theta) d(omega)`` over the exit pupil
(Kolb, Mitchell & Hanrahan 1995), times ``(n_image / n_object)^2``. Point ``sources`` of the scene are added by forward
ray tracing. The spectral irradiance becomes electrons per wavelength,
``E dlambda A_pixel t (lambda / hc) QE(lambda)``, and the sum goes through the shot noise, the dark electrons, the read
noise and the quantiser of ``lensimage._sensor`` (*add_noise* False returns the expected values). *sensor* is a dict
``{"pixel_pitch_um", "size": (rows, cols), "qe", "full_well", "read_noise_e", "dark_e", "bits", "center_mm"}`` (``center_mm`` moves the window to another point of a larger sensor); *wavelengths* default to the F, d, C lines
(each band is as wide as the spacing of the list, or *band_nm*); *illuminant* is the relative spectral shape of the scene's lights (pairs
``(nm, value)``); *defocus_mm* moves the sensor along the light (positive = away from the lens) and *focus_mm* puts it at the
paraxial image of an object at that distance (default: the system's own image plane); *oversample* subdivides each pixel.
The picture is upright (see the module doc). The table has ``image`` (``float`` in 0..1, or ``uint16`` DN with
``output="uint16"``), ``image_noiseless``, ``channels`` / ``channels_noiseless`` (one image per wavelength, own noise), ``electrons_mean`` and
``electrons_per_wavelength``, ``irradiance_W_m2_nm`` (K, H, W), ``pupil_transmission`` (H, W: the share of the pupil that is not
vignetted), the wavelengths and the geometry. Geometric optics only: no diffraction.

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

[lens_scene](lens_scene.md) · [exit_pupil_samples](exit_pupil_samples.md) · [trace_sensor_rays](trace_sensor_rays.md) · [scene_radiance](scene_radiance.md) · [bokeh_shape](bokeh_shape.md) · [render_ghost_overlay](render_ghost_overlay.md) · [render_compare_prescriptions](render_compare_prescriptions.md)

---
*Provenance: lensrender.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
