---
op: laser_line_coherent
dim: optics
category: coherent
in: 
out: image2d
examples: [poc_laser_line_speckle_floor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# laser_line_coherent — OPTICS `coherent` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.laser_line_coherent(shape=(96, 512), wavelength_um=0.65, sin_u_obs=0.05, pixel_um=2.0, line_width_um=20.0, height_um=20.0, sin_theta=0.5, row0=None, polarizations=1, n_patterns=1, pixel_oversample=2, roughness_rad=None, noise=0.0, seed=0, noise_seed=None, *, method='exact')` (実装を直接呼ぶなら `import coherent; coherent.laser_line_coherent(shape=(96, 512), wavelength_um=0.65, sin_u_obs=0.05, pixel_um=2.0, line_width_um=20.0, height_um=20.0, sin_theta=0.5, row0=None, polarizations=1, n_patterns=1, pixel_oversample=2, roughness_rad=None, noise=0.0, seed=0, noise_seed=None, *, method='exact')`、台帳から引くなら `opsoptics.get("laser_line_coherent")`)

## 使い方

A sheet-of-light laser line on a rough surface, imaged with its speckle (``image2d``).

Object-side coordinates, magnification 1: one output pixel covers ``pixel_um`` on the
part. The line is a Gaussian band along the columns, intensity 1/e² half-width
``line_width_um`` (as seen by the camera), centred on the row
``row0 + height_um · sin_theta / pixel_um`` (``height_um`` a number or one value per
column, default 20 µm so that ``sin_theta`` acts on the default call; ``row0`` defaults
to the middle row) — the triangulation shift. Its amplitude
multiplies a random phase screen fixed to the part (``seed``), the field passes the
observation pupil ``sin_u_obs`` (cut-off ``sin_u/λ``), and the intensity is integrated
over each pixel (``pixel_oversample``). ``polarizations`` × ``n_patterns`` independent
patterns are averaged (a moving diffuser / several wavelengths). ``noise`` adds
Gaussian read noise of that standard deviation relative to the line's peak mean
intensity (seeded by ``noise_seed``, so a static part with several noisy frames is
``same seed, different noise_seed``). The mean peak intensity is 1.

The true centre row is returned implicitly by the formula above; see
:func:`triangulation_speckle_limit` for the floor this sets. Limits: scalar, paraxial,
in focus, no foreshortening of the line width with θ, no Scheimpflug, phase screen
uncorrelated between fine samples.

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

- [poc_laser_line_speckle_floor](../../../../examples/poc_laser_line_speckle_floor.py) — `py -3.11 examples/poc_laser_line_speckle_floor.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`coherent`)

[coherent_image](coherent_image.md) · [speckle_field](speckle_field.md) · [speckle_statistics](speckle_statistics.md) · [triangulation_speckle_limit](triangulation_speckle_limit.md) · [speckle_reduction](speckle_reduction.md)

---
*Provenance: coherent.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
