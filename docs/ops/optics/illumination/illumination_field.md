---
op: illumination_field
dim: optics
category: illumination
in: table
out: image2d
examples: [poc_document_scan, poc_spectrometer_illumination]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# illumination_field — OPTICS `illumination` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.illumination_field(train, source_radiance=None, shape=(65, 65), field_mm=None, n_pupil=16)` (実装を直接呼ぶなら `import illumdesign; illumdesign.illumination_field(train, source_radiance=None, shape=(65, 65), field_mm=None, n_pupil=16)`、台帳から引くなら `opsoptics.get("illumination_field")`)

## 使い方

Irradiance on the specimen of an illumination train (``image2d``), by paraxial backward tracing.

For every specimen pixel (x, y) and every direction (u, v) on an *n_pupil* x *n_pupil* grid
of the illumination cone, the ray is traced back through each stop (rays outside a stop are
blocked) to the source plane, where the radiance is looked up: ``E(x) = sum L(source point) du dv``
(paraxial, so for a uniform source filling the cone ``E = L pi NA^2`` — a gate).

*train*: the table from :func:`illumination_train` (or the same element list built by hand).
*source_radiance*: ``None`` = uniform radiance 1 over the source disc; or a 2-D array of
non-negative radiance laid over the square [-r, r]^2 of the source (r = source radius), bilinear
lookup, zero outside the disc — a filament, an LED die, a fibre bundle.
*shape*: the output grid (rows, cols). *field_mm*: half-width of the square specimen window
(``None`` = 0.65 x the lit field diameter). *n_pupil*: direction samples per axis.

Returns the irradiance map (float64, rows = +y down to -y as an image), in radiance x sr units.

**Raises** ``ValueError``: not a train, non-finite/negative radiance map, work above
``MAX_TRAIN_WORK``, no light reaching the specimen.

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

- [poc_document_scan](../../../../examples/poc_document_scan.py) — `py -3.11 examples/poc_document_scan.py`
- [poc_spectrometer_illumination](../../../../examples/poc_spectrometer_illumination.py) — `py -3.11 examples/poc_spectrometer_illumination.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`illumination`)

[light_source](light_source.md) · [irradiance_map](irradiance_map.md) · [illumination_uniformity](illumination_uniformity.md) · [defect_contrast](defect_contrast.md) · [lighting_sweep](lighting_sweep.md) · [illumination_design](illumination_design.md) · [solid_angle_light](solid_angle_light.md) · [solid_angle_boundaries](solid_angle_boundaries.md)

---
*Provenance: illumdesign.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
