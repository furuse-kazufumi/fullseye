---
op: dolp_to_zenith
dim: optics
category: shape_from_polarization
in: image2d
out: table
gpu: なし
examples: [poc_shape_from_polarization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# dolp_to_zenith — OPTICS `shape_from_polarization` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dolp_to_zenith(dolp, refractive_index=1.5, model='diffuse', out_of_range='clamp')` (実装を直接呼ぶなら `import sfpolar; sfpolar.dolp_to_zenith(dolp, refractive_index=1.5, model='diffuse', out_of_range='clamp')`、台帳から引くなら `opsoptics.get("dolp_to_zenith")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Invert DoLP to the set of zenith angles that produce it — one for the diffuse model, two (straddling Brewster) for the specular model.

Returns a dict (a ``table``):

* ``zenith_deg`` — ``(K, *dolp.shape)``; ``K = 1`` for ``"diffuse"``,
  ``K = 2`` for ``"specular"`` (row 0 = the branch below Brewster's angle,
  row 1 = the branch above it). Where the specular DoLP is 1 (to 1e-12)
  both rows hold Brewster's angle.
* ``n_solutions`` — integer map: 1 or 2 (specular; 1 only at Brewster),
  1 (diffuse), **0 where no zenith produces the DoLP** — a diffuse DoLP
  above ``(n^2-1)/(n^2+1)``, which noise or a wrong index produces.
* ``brewster_deg`` (specular) / ``dolp_max`` — the model's limits.

``out_of_range`` decides what the unreachable pixels hold: ``"clamp"``
(default — the nearest reachable angle, 90 degrees for the diffuse model,
**flagged by** ``n_solutions == 0``, so a caller cannot mistake it for a
solution), ``"nan"`` or ``"raise"``.

The inversion is bisection on the monotone branches of
:func:`sfp_dolp_model`'s closed form (64 halvings — finer than float64).
Near Brewster's angle the specular curve is flat, so a DoLP rounding error
of 1e-16 moves the zenith by up to ~1e-6 degrees; that is the conditioning
of the problem, not of the solver.

**Raises** ``ValueError``: DoLP outside ``[0, 1]`` or non-finite;
*refractive_index* not ``> 1``; unknown *model* / *out_of_range*; with
``out_of_range="raise"``, any unreachable pixel.

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

[sfp_dolp_model](sfp_dolp_model.md) · [aolp_to_azimuth](aolp_to_azimuth.md) · [sfp_render](sfp_render.md) · [sfp_normals](sfp_normals.md) · [sfp_disambiguate](sfp_disambiguate.md) · [sfp_estimate_index](sfp_estimate_index.md) · [sfp_height](sfp_height.md)

---
*Provenance: sfpolar.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
