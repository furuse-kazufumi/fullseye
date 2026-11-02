---
op: sfp_disambiguate
dim: optics
category: shape_from_polarization
in: table
out: normalmap
gpu: なし
examples: [poc_shape_from_polarization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# sfp_disambiguate — OPTICS `shape_from_polarization` op

- **データ種**: `table` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.sfp_disambiguate(candidates, prior='convex', mask=None, center=None, prior_normals=None, coarse_depth=None, brewster_tol=0.02, invalid='raise')` (実装を直接呼ぶなら `import sfpolar; sfpolar.sfp_disambiguate(candidates, prior='convex', mask=None, center=None, prior_normals=None, coarse_depth=None, brewster_tol=0.02, invalid='raise')`、台帳から引くなら `opsoptics.get("sfp_disambiguate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Pick one normal per pixel from the candidate set of :func:`sfp_normals`, using a stated prior — convexity with Brewster-ridge segmentation, or a coarse depth / normal map.

``prior="convex"`` (an object bulging toward the camera, such as a dome,
a lens or a cap): the azimuth is the candidate pointing **away from**
*center* (default: the centroid of *mask*). For the specular model the two
zenith branches are separated by the **Brewster ridge** — the pixels whose
DoLP is within *brewster_tol* of 1: the connected region of the mask that
contains *center* (minus the ridge) takes the branch below Brewster's angle,
the rest of the mask the branch above. Inside the ridge band the branch is
read from the radial slope of the DoLP (a convex surface tilts more toward
its rim, so the DoLP rises outward below Brewster's angle and falls outward
above it). If the object never reaches Brewster's
angle there is no ridge and every pixel stays on the low branch, which is
right for a shallow dome. If noise breaks the ridge, the outside leaks in
and takes the low branch — measured in the tests, not hidden.

``prior="normals"`` / ``prior="depth"``: per pixel, the candidate closest
in angle to *prior_normals* ``(H, W, 3)`` — or to the normals of
*coarse_depth* ``(H, W)`` (height toward the camera, pixel units,
:func:`photometric.surface_normals`). This resolves both ambiguities at
once, and a coarse depth needs to be right only to within the angular
distance between candidates.

Pixels outside *mask* (default ``candidates["valid"]``) are set to
``(0, 0, 1)`` (flat background, the convention of
:func:`photometric.integrate_normals`). Invalid pixels inside the mask
(``valid`` is False: dark, physically impossible, or out of the model's
reach): ``invalid="raise"`` refuses (fail-closed), ``"exclude"`` drops them
to the background.

Returns an ``(H, W, 3)`` float64 unit normal map (the ``normalmap`` sort).

**Raises** ``ValueError``: *candidates* not an :func:`sfp_normals`
result; unknown *prior* / *invalid*; a prior's array missing or of the
wrong shape; an empty mask; invalid pixels inside the mask with
``invalid="raise"``.

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

## 型が繋がる次の op(`normalmap` を入力に取れる)

[grating_rgb](../appearance/grating_rgb.md) · [thin_film_rgb](../appearance/thin_film_rgb.md) · [ward_anisotropic](../appearance/ward_anisotropic.md) · [micro_normals](../finish/micro_normals.md) · [blast_normals](../finish/blast_normals.md) · [finish_shade](../finish/finish_shade.md) · [oren_nayar](../material/oren_nayar.md) · [clearcoat_shade](../material/clearcoat_shade.md)

## 同カテゴリ(`shape_from_polarization`)

[sfp_dolp_model](sfp_dolp_model.md) · [dolp_to_zenith](dolp_to_zenith.md) · [aolp_to_azimuth](aolp_to_azimuth.md) · [sfp_render](sfp_render.md) · [sfp_normals](sfp_normals.md) · [sfp_estimate_index](sfp_estimate_index.md) · [sfp_height](sfp_height.md)

---
*Provenance: sfpolar.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
