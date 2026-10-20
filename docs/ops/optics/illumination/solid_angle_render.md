---
op: solid_angle_render
dim: optics
category: illumination
in: normalmap × table
out: image2d
examples: [poc_illumination_cone_vs_na]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# solid_angle_render — OPTICS `illumination` op

- **データ種**: `normalmap × table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.solid_angle_render(normals, light, view_na=0.1, roughness_deg=0.0, f0=0.9, diffuse_albedo=0.0, n_samples=64, seed=0)` (実装を直接呼ぶなら `import illumdesign; illumdesign.solid_angle_render(normals, light, view_na=0.1, roughness_deg=0.0, f0=0.9, diffuse_albedo=0.0, n_samples=64, seed=0)`、台帳から引くなら `opsoptics.get("solid_angle_render")`)

## 使い方

Image of a normal map under a cone light through a lens of NA *view_na* (``image2d``).

*normals*: (H, W, 3) surface normals in camera coordinates (+z toward the
camera; zero-length = background, rendered 0) — e.g. from a height map's
gradient, ``metalfinish.micro_normals`` (hairline / turning marks) or
``metalfinish.blast_normals`` (satin). *light*: :func:`solid_angle_light`.
Every pixel is viewed along +z with the same object-side cone (a
telecentric camera) and lit by the same cone (the far-field light), so the
image is a function of the local normal only:

``B = F · share_of_pupil_lit + ρ · sin²α · cos γ``

The specular share uses *n_samples* rays over the narrower cone (the
pupil, uniform in direction cosines, or the source cap; the same
quadrature for every pixel, so there is no pixel noise),
each mirrored by the normal tilted by a micro-facet slope drawn once per
ray (*roughness_deg* σ, a scalar or an (H, W) map for satin patches);
``F`` = *f0* (Fresnel at near-normal incidence, a constant over the small
angles involved); the diffuse body term with albedo *diffuse_albedo* uses
the closed form of the projected solid angle of a uniform cap
``π sin²α cos γ`` (γ = angle between the normal and the cone axis; exact
while the cap stays above the facet's horizon) divided by π. Values are
relative to the source radiance (1 = mirror, full pupil, F = 1). With few
samples a partial overlap is quantised to 1/*n_samples*.

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

- [poc_illumination_cone_vs_na](../../../../examples/poc_illumination_cone_vs_na.py) — `py -3.11 examples/poc_illumination_cone_vs_na.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`illumination`)

[light_source](light_source.md) · [irradiance_map](irradiance_map.md) · [illumination_uniformity](illumination_uniformity.md) · [defect_contrast](defect_contrast.md) · [lighting_sweep](lighting_sweep.md) · [illumination_design](illumination_design.md) · [solid_angle_light](solid_angle_light.md) · [solid_angle_boundaries](solid_angle_boundaries.md)

---
*Provenance: illumdesign.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
