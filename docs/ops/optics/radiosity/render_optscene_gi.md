---
op: render_optscene_gi
dim: optics
category: radiosity
in: table × table × table
out: table
examples: [poc_pocket_interreflection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# render_optscene_gi — OPTICS `radiosity` op

- **データ種**: `table × table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_optscene_gi(scene, camera, lights, bounces=None, patch_mm=2.0, outer_mm=None, tol=1e-06, n_quad=3, supersample=1, study_bounces=8, study_tol=0.01)` (実装を直接呼ぶなら `import radiosity3d; radiosity3d.render_optscene_gi(scene, camera, lights, bounces=None, patch_mm=2.0, outer_mm=None, tol=1e-06, n_quad=3, supersample=1, study_bounces=8, study_tol=0.01)`、台帳から引くなら `opsoptics.get("render_optscene_gi")`)

## 使い方

Inspection render with interreflection: the photometry of ``render_optscene`` plus n bounces (or the converged sum) between Lambertian patches.

The same scene (``optscene.scene_*``), camera (``optical_camera``) and lights
(``illumdesign.light_source`` results) as :func:`optscene.render_optscene`. The
direct part is computed with the very same irradiance function, so
``bounces=0`` reproduces ``render_optscene`` exactly (a test gate). On top of it
the surfaces are cut into patches (:func:`radiosity_patches`, at most *patch_mm*
inside pockets and *outer_mm* (default *patch_mm*) elsewhere
on a side), their view factors computed with occlusion
(:func:`form_factor_matrix`), and the light reflected between them added:

* ``bounces=None`` — converged, by progressive shooting
  (:func:`radiosity_progressive_3d`, stop at residual energy ``tol``);
* ``bounces=k`` — the Neumann partial sum: light that bounced at most ``k``
  times between surfaces before reaching the camera (``0`` = direct only,
  ``1`` = one interreflection).

Each pixel's interreflected irradiance is gathered from the patch radiosities
with the point-to-polygon closed form at the pixel's own surface point
(final gather, one visibility ray per patch), so it is smooth inside a patch.
Pixel radiance = ``ρ/π (E_direct + E_interreflected)`` in the same linear units as
``render_optscene``. Light intensity enters linearly (the geometry is cached by
a SHA-256 of the scene's shapes, camera and patch size — materials and light
intensity are read on every call, so a calibration loop that varies albedo or
intensity re-solves only the radiosity).

*study_bounces* ``K > 0`` adds a **bounce study**: the images after 0..K bounces,
the increment of each (max abs change / image peak), the observed ratio of
successive increments ``g`` (the geometric analogue of an observed order of
convergence), a GCI-style estimate ``1.25 · Δ_k g/(1 − g)`` of what the remaining
bounces still add, whether ``k`` is in the asymptotic range (``g`` moved by at most
5 % at ``k`` and at ``k − 1``; before it the estimate can be optimistic), the actual error
against the converged image, and ``bounces_needed`` = the first ``k`` in the
asymptotic range whose GCI estimate is below *study_tol*.

Returns a dict (``table``) with ``kind = "gi_render"``, ``image`` (H, W, 3),
``direct`` (H, W, 3, identical to ``render_optscene``), ``difference`` (H, W, 3)
= image − direct (the interreflection map), ``indirect_share`` (H, W),
``bounces``, ``converged``, ``n_shots``, ``unshot_history``, ``n_patches``,
``patch_radiosity`` (N, 3), ``bounce_study`` (list of rows, or ``None``),
``bounces_needed`` and ``notes``.

**Raises** ``ValueError``: an empty scene, or an unsupported one (see :func:`radiosity_patches`:
Lambertian boxes, box-minus-box pockets, finite planes; an infinite plane only
black); no lights; *bounces* not ``None`` or an integer in ``[0, 1000]``; bad
*patch_mm*, *tol*, *n_quad*, *supersample*, *study_bounces* or *study_tol*; an
all-zero image (as ``render_optscene``).

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

- [poc_pocket_interreflection](../../../../examples/poc_pocket_interreflection.py) — `py -3.11 examples/poc_pocket_interreflection.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`radiosity`)

[form_factor_parallel_rects](form_factor_parallel_rects.md) · [form_factor_perpendicular_rects](form_factor_perpendicular_rects.md) · [form_factor_polygons](form_factor_polygons.md) · [radiosity_patches](radiosity_patches.md) · [form_factor_matrix](form_factor_matrix.md) · [radiosity_progressive_3d](radiosity_progressive_3d.md)

---
*Provenance: radiosity3d.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
