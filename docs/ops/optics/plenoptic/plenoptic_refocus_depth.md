---
op: plenoptic_refocus_depth
dim: optics
category: plenoptic
in: lightfield × table
out: table
gpu: なし
examples: [poc_plenoptic_camera]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# plenoptic_refocus_depth — OPTICS `plenoptic` op

- **データ種**: `lightfield × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plenoptic_refocus_depth(lf, system, slope)` (実装を直接呼ぶなら `import plenoptic; plenoptic.plenoptic_refocus_depth(lf, system, slope)`、台帳から引くなら `opsoptics.get("plenoptic_refocus_depth")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Convert light-field refocus slope(s) to object distance in metres.

*slope* is in the unit of :func:`lightfield.lf_refocus` and
:func:`lightfield.lf_depth_from_focus` on a field from
:func:`plenoptic_decode`: decoded spatial samples (lenslets) of parallax per
view step.  Zero slope is the main-lens conjugate of the MLA plane and maps
to the configured object distance.

Paraxial model of the unfocused (1.0) camera, in the geometry
:func:`plenoptic_capture` traces.  :func:`plenoptic_decode` samples ``U``
views across one lenslet pitch, so one view step moves the exit-pupil
coordinate by ``dX = (pitch/U) * xp_radius / (microimage_diameter/2)``.  A
point imaged ``delta`` behind the MLA plane, with the exit pupil ``D`` in
front of it, shifts on the MLA by ``dX * delta/(D+delta)`` per view, hence
``slope = (dX/pitch) * delta/(D+delta)``; Newton's equation of the
paraxial main lens turns the image position into the object distance.

Before 2026-11-04 the image shift was ``slope * angular_step * pitch`` with
``angular_step = pixel_pitch/mla_to_sensor`` -- a factor ``1/angular_step**2``
(~3000x for the PoC camera) too small, so every measured slope mapped back
to the focus distance.  The relation is now gated against rays traced
forward through the prescription (``tests/test_plenoptic.py``): rel. error
below 1e-6 for an ideal lens and 2e-4 for the PoC's three-element lens.

Sign: follows :func:`plenoptic_capture`'s non-inverting pixel-to-pupil
map, which is the opposite of a physical lenslet; negate real-sensor slopes.

Limits: it is paraxial.  Spherical aberration of a real aperture moves the
best-focus slope of the full pupil away from the paraxial one -- for the PoC
lens at F/3.7 the decoded 1.0 m plane sits at slope -0.029, not 0 (measured
in ``examples/poc_plenoptic_camera.py``).  ``depth_resolution_m`` is half
the depth span of a slope change of ``+-1/(U-1)``: one decoded sample of
parallax across the full angular baseline.

**Raises** ``ValueError``: *lf* not ``(V,U,H,W)``, ``V != U`` (one slope
cannot describe two different per-view pupil steps), fewer than two views,
a focused (2.0) system (its MLA is not at the main-lens image plane, so
slope means something else), a non-finite slope, or a slope whose image
point lies at or beyond the exit pupil (``slope*pitch/dX >= 1``).

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。ただし宣言された欠測を除く: `bottle_fit_from_pattern` の `u_map` は測れなかった画素を NaN で受け取る(∞ は拒否)。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。ただし宣言された欠測を除く: `bottle_background_map` は光線が使えない画素(全反射など)の `u_mm` を NaN で返し、`valid` マスクと本数を併せて返す。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_plenoptic_camera](../../../../examples/poc_plenoptic_camera.py) — `py -3.11 examples/poc_plenoptic_camera.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`plenoptic`)

[mla_surface](mla_surface.md) · [plenoptic_system](plenoptic_system.md) · [plenoptic_capture](plenoptic_capture.md) · [plenoptic_mla_calibrate](plenoptic_mla_calibrate.md) · [plenoptic_decode](plenoptic_decode.md)

---
*Provenance: plenoptic.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
