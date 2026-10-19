---
op: sfp_normals
dim: optics
category: shape_from_polarization
in: polsweep
out: table
examples: [poc_shape_from_polarization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# sfp_normals — OPTICS `shape_from_polarization` op

- **データ種**: `polsweep` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sfp_normals(sweep, refractive_index=1.5, model='specular', angles_deg=(0.0, 45.0, 90.0, 135.0), violation_tol=0.05, out_of_range='invalid')` (実装を直接呼ぶなら `import sfpolar; sfpolar.sfp_normals(sweep, refractive_index=1.5, model='specular', angles_deg=(0.0, 45.0, 90.0, 135.0), violation_tol=0.05, out_of_range='invalid')`、台帳から引くなら `opsoptics.get("sfp_normals")`)

## 使い方

From a polariser sweep to the explicit set of candidate surface normals per pixel — 2 for the diffuse model, 4 for the specular model (2 zeniths x 2 azimuths).

*sweep* is an ``(N, H, W)`` stack through linear analysers at *angles_deg*
(the ``polsweep`` sort; :func:`optics.polarization_demosaic` gives it from a
raw mosaic). Per pixel the sinusoid ``I(t) = a0 + a1 cos 2t + a2 sin 2t`` is
fitted (the same least-squares fit as :func:`specularity.polarization_dolp_map`),
giving ``DoLP = hypot(a1, a2)/a0`` and ``AoLP = 0.5 atan2(a2, a1)``; then
:func:`dolp_to_zenith` and :func:`aolp_to_azimuth` give the zenith and
azimuth candidates.

A fitted minimum below zero (modulation above the mean, DoLP > 1) is
impossible for light. Near Brewster's angle the true minimum is ~0, so
sensor noise pushes it slightly negative; *violation_tol* is the largest
excess ``DoLP - 1`` that is read as noise (DoLP clipped to 1). A larger
excess marks the pixel **invalid** — the frames do not match *angles_deg*,
or the pixel saw something other than a polariser sweep. Such a pixel is
reported in ``violation``, never silently clipped.
(:func:`specularity.polarization_dolp_map` refuses the whole image instead;
a shape map with one hot pixel is still a shape map, so here the decision
is per pixel and :func:`sfp_disambiguate` refuses invalid pixels inside its
mask by default.)

*out_of_range*: a DoLP that no zenith produces (diffuse model, above
``(n^2-1)/(n^2+1)``) makes the pixel ``"invalid"`` (default) or is
``"clamp"``-ed to the reachable limit and kept, flagged in ``clamped``.

Returns a dict (a ``table``, marked ``kind == "sfp_candidates"``):

* ``candidates`` ``(K, H, W, 3)`` unit normals; specular order is
  ``[low zenith & azimuth 0, low & azimuth 1, high & azimuth 0, high &
  azimuth 1]``, diffuse ``[azimuth 0, azimuth 1]``. Zero vectors at
  invalid pixels (see ``valid``) — never NaN, never a made-up unit normal.
* ``zenith_deg`` ``(1|2, H, W)``, ``azimuth_deg`` ``(2, H, W)``,
  ``dolp``, ``aolp_deg``, ``intensity`` (``S0``) ``(H, W)``.
* ``n_distinct`` ``(H, W)`` — how many genuinely different normals the
  pixel admits: 4 (specular), 2 at Brewster's angle or for the diffuse
  model, 0 where nothing fits or the pixel is dark.
* ``valid`` ``(H, W)`` bool — lit, physically possible and invertible;
  ``violation`` / ``clamped`` ``(H, W)`` bool — why a pixel is suspect.
* ``model``, ``refractive_index``, ``brewster_deg``.

Nothing here chooses among the candidates; a single "best" normal map
returned at this stage would be a guess dressed as a measurement.

**Raises** ``ValueError``: not an ``(N, H, W)`` stack of >= 3 finite
non-negative frames; angles that do not match or do not determine the fit;
*violation_tol* outside ``[0, 1]``; index not ``> 1``; unknown *model* /
*out_of_range*.

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

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`shape_from_polarization`)

[sfp_dolp_model](sfp_dolp_model.md) · [dolp_to_zenith](dolp_to_zenith.md) · [aolp_to_azimuth](aolp_to_azimuth.md) · [sfp_render](sfp_render.md) · [sfp_disambiguate](sfp_disambiguate.md) · [sfp_estimate_index](sfp_estimate_index.md) · [sfp_height](sfp_height.md)

---
*Provenance: sfpolar.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
