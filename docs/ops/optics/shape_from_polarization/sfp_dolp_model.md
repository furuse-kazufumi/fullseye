---
op: sfp_dolp_model
dim: optics
category: shape_from_polarization
in: image2d
out: image2d
examples: [poc_shape_from_polarization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sfp_dolp_model — OPTICS `shape_from_polarization` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.sfp_dolp_model(zenith_deg, refractive_index=1.5, model='specular')` (実装を直接呼ぶなら `import sfpolar; sfpolar.sfp_dolp_model(zenith_deg, refractive_index=1.5, model='specular')`、台帳から引くなら `opsoptics.get("sfp_dolp_model")`)

## 使い方

Degree of linear polarisation of reflected (specular) or emitted (diffuse) light versus zenith angle, from the Fresnel equations.

*zenith_deg* is the angle between the surface normal and the viewing
direction, in degrees, ``0 <= zenith <= 90`` (a scalar or an array of any
shape — an ``(H, W)`` zenith map gives an ``(H, W)`` DoLP map).

``model="specular"``: ``(R_s - R_p) / (R_s + R_p)`` for light reflected off
a dielectric of index *refractive_index*. It rises from 0 at normal
incidence to **exactly 1 at Brewster's angle** ``atan(n)`` (``R_p = 0``)
and falls back to 0 at grazing incidence — so one DoLP value has two
zenith angles.

``model="diffuse"``: ``(T_p - T_s) / (T_p + T_s)`` for light scattered
inside the body and refracted out through the surface. It rises
monotonically from 0 to ``(n^2 - 1)/(n^2 + 1)`` at 90 degrees (0.385 for
n = 1.5) — weaker, but one value has one angle.

Returns a float64 array of the input's shape (a 0-d array for a scalar).

**Raises** ``ValueError``: zenith outside ``[0, 90]`` or non-finite;
*refractive_index* not a finite real ``> 1``; unknown *model*.

*refractive_index* (here and in every op of this module) may also be a
material name of the shared table ``materials`` (e.g. ``"N-BK7"``,
``"PMMA"``, ``"WATER"``): its index at the d line (587.56 nm) is used.
Metals and materials that absorb there are refused.

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

- [poc_shape_from_polarization](../../../../examples/poc_shape_from_polarization.py) — `py -3.11 examples/poc_shape_from_polarization.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`shape_from_polarization`)

[dolp_to_zenith](dolp_to_zenith.md) · [aolp_to_azimuth](aolp_to_azimuth.md) · [sfp_render](sfp_render.md) · [sfp_normals](sfp_normals.md) · [sfp_disambiguate](sfp_disambiguate.md) · [sfp_estimate_index](sfp_estimate_index.md) · [sfp_height](sfp_height.md)

---
*Provenance: sfpolar.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
