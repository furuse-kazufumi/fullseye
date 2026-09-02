---
op: render_through_lens
dim: optics
category: imaging_sim
in: image2d × table
out: image2d
examples: [lens_defect_dataset_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# render_through_lens — OPTICS `imaging_sim` op

- **データ種**: `image2d × table` → `image2d`
- **呼び出し**: `import lensimage; lensimage.render_through_lens(image, system, pixel_pitch_um=5.5, field_of_view=None, zones=3, noise=None, seed=0, illumination='traced', size=None, oversample=None)` (または `opsoptics.get("render_through_lens")`)

## 使い方

Render an ideal irradiance image as the sensor behind *system* would record it (``image2d``).

*image* (H×W, non-negative) is the ideal (paraxial) image on a sensor of
*pixel_pitch_um* pixels centred on the optical axis; with *field_of_view*
(half field to the sensor corner: degrees for an object at infinity,
object height in mm otherwise) the picture is first zoomed so the corner
sees that field. Pipeline: (a) inverse distortion remap
(:func:`distortion_map` grid, ``scipy.ndimage.map_coordinates`` order 1);
(b) spatially varying blur — a ``zones×zones`` lattice of tile centres,
each with its own pixel-integrated :func:`psf_from_opd` (the +y-field PSF
rotated to the tile azimuth), blended with bilinear (tent) weights so
seams vanish; (c) relative illumination: ``"traced"`` = fraction of the
field's ray bundle that reaches the image (vignetting, from
:func:`raytrace.ray_bundle`) normalised to the axis, times cos⁴ (obliquity,
objects at infinity only), ``"cos4"`` = the classic law alone, ``"none"``;
(d) sensor, when *noise* is ``True`` or a dict ``{"full_well": 20000,
"read_e": 3.0, "bits": 12, "exposure": 1.0, "dark_e": 0.0}``: electrons =
irradiance × exposure × full_well, Poisson shot noise
(:func:`photoncount.photon_sample`), Gaussian read noise, quantisation to
*bits*, returned as DN/(2^bits − 1). With ``noise=None`` the float
irradiance is returned untouched (deterministic; the noisy path is
deterministic for a given *seed* too).

*oversample* defaults to whatever keeps at least 2 PSF samples per pixel
(``max(4, ceil(2·λ·F#/pitch))``). Ground truth: a δ image through the
f/2 paraboloid gives the pixel-integrated Airy PSF; a checkerboard through
it comes back undistorted (correlation > 0.99); energy is conserved to 1 %
with illumination off; noise off is bit-reproducible.

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

- [lens_defect_dataset_demo](../../../../examples/lens_defect_dataset_demo.py) — `py -3.11 examples/lens_defect_dataset_demo.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [illumination_uniformity](../illumination/illumination_uniformity.md)

## 同カテゴリ(`imaging_sim`)

[psf_from_opd](psf_from_opd.md) · [distortion_map](distortion_map.md) · [defect_dataset](defect_dataset.md) · [calibration_views](calibration_views.md)

---
*Provenance: lensimage.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
