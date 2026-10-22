---
op: underwater_inspection_image
dim: optics
category: watervision
in: rgbimage × image2d
out: table
examples: [poc_water_inspection_images]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# underwater_inspection_image — OPTICS `watervision` op

- **データ種**: `rgbimage × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.underwater_inspection_image(scene_albedo, distance_map_m, water_type, light='camera', lamp_power=1.0, camera_distance_m=None, depth_m=2.0, exposure_photons=10000.0, fov_deg=60.0, beam_exponent=6.0) -> 'dict'` (実装を直接呼ぶなら `import watervision; watervision.underwater_inspection_image(scene_albedo, distance_map_m, water_type, light='camera', lamp_power=1.0, camera_distance_m=None, depth_m=2.0, exposure_photons=10000.0, fov_deg=60.0, beam_exponent=6.0) -> 'dict'`、台帳から引くなら `opsoptics.get("underwater_inspection_image")`)

## 使い方

A hull or pipe inspection image: a lamp at the camera lights a wall through water -> dict (image, per-pixel SNR).

A thin layer over :func:`watermedia.underwater_image` (the Akkaynak and Treibitz form: direct signal plus backscatter veil).
``scene_albedo`` is (H, W) or (H, W, 3) and ``distance_map_m`` (H, W) the camera-to-surface distance (> 0). ``light="camera"``: the
only light is a lamp at the camera of ``lamp_power`` (relative power at 1 m); the wall is lit by
``lamp_power exp(-c r) / r^2`` (beam attenuation ``c`` of the water at 0.61 / 0.54 / 0.465 um), reflects its albedo and the return
path attenuates with ``Kd``. The lamp also lights the water in front of the lens: the veil of
the water type's single-scattering backscatter grows as ``1 - exp(-Kd r)`` and is weighted by the lamp's beam pattern,
``cos(theta)^beam_exponent`` with ``theta`` the angle of the pixel from the axis (``fov_deg`` across the width): strongest in the
centre, where the lamp and the camera look at the same water. A baseline between lamp and camera, ``camera_distance_m`` (default
None: the lamp is at the camera), reduces the overlap of the lit and the seen water by ``1 / (1 + (baseline / r)^2)``.
``light="ambient"``: daylight at ``depth_m`` and a veil of the daylight, uniform over the image (``lamp_power`` is not used). ``light="both"``: the lamp and the daylight together (the signals and the veils add).

``snr = sqrt(N) direct / sqrt(direct + backscatter + 1e-12)`` is the shot-noise limited signal to noise of the direct signal against
its own shot noise and the shot noise of the veil (``N = exposure_photons`` per unit radiance): it falls with distance because the
direct term falls and the veil grows. ``snr_clear`` is the same expression for water that does not
attenuate or scatter (equal to ``snr`` as the distance tends to 0). The table has ``image`` (H, W, 3), ``direct``, ``backscatter``,
``snr``, ``snr_clear``, ``snr_mean`` (over the three bands), ``veil_profile`` (H, W), ``transmission``, ``beam_attenuation_c``,
``kd``, ``water_type`` and ``light``. A zero or negative distance, an albedo outside [0, 1], an unknown water type and a bad light
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

[caustic_irradiance](caustic_irradiance.md) · [bottle_image](bottle_image.md) · [fill_level_from_image](fill_level_from_image.md) · [wet_surface_appearance](wet_surface_appearance.md) · [wet_dry_inspection_pair](wet_dry_inspection_pair.md) · [caustic_floor_segmentation](caustic_floor_segmentation.md)

---
*Provenance: watervision.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
