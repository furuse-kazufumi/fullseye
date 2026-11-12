---
op: laser_line_center_centroid
dim: optics
category: light_section
in: image2d
out: table
gpu: なし
examples: [poc_3d_sensor_modalities, poc_weld_bead_profile]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# laser_line_center_centroid — OPTICS `light_section` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.laser_line_center_centroid(image, min_peak_rel=0.1, half_window=None, background=0.0, clip_negative=True)` (実装を直接呼ぶなら `import lightsection; lightsection.laser_line_center_centroid(image, min_peak_rel=0.1, half_window=None, background=0.0, clip_negative=True)`、台帳から引くなら `opsoptics.get("laser_line_center_centroid")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Sub-pixel centre of a bright laser line in every column by the intensity centroid (``table``).

列ごとに最大の行 ``p`` を探し、``[p − half_window, p + half_window]``(``None`` = 列全体)の
輝度から ``background`` を引いて負を 0 にした重みの重心を返す。最大値が画像全体の最大の
``min_peak_rel`` 倍以下の列は ``valid=False``(``row`` は NaN)。

For each column the peak row ``p`` is found, and the centroid of
``max(I − background, 0)`` over ``[p − half_window, p + half_window]`` (``None`` = the whole
column) is returned. Columns whose peak is at most ``min_peak_rel`` × the image maximum are
marked ``valid=False`` (``row`` NaN). ``clip_negative=False`` keeps negative weights (zero-mean
noise stays zero-mean: the estimator is then linear in the noise, which is what
:func:`light_section_uncertainty_budget`'s read-noise term assumes). Pixel-centre convention of :mod:`camera`: row ``r``
is the coordinate ``v = r`` exactly.

Returns ``{"kind": "laser_line_centers", "method": "centroid", "col", "row", "valid",
"peak", "n_valid", "saturated", "truncated"}``. Ground truth: a symmetric line profile has
its centroid at the true centre; the centroid of a column-binned image equals that of the
unbinned one (``tests/test_lightsection.py``). ★Limits: the centroid is biased toward the
window's centre when the window cuts an off-centre profile, and a background left in the
weights pulls it toward the column's middle.

★Saturation: the "peak" is the plateau of rows within 1e-9 of the column maximum that is
connected to the first maximum; the window is ``[lo − half_window, hi + half_window]``
around that plateau (one row for an unclipped line: the same as before). A clipped,
flat-topped line used to be windowed at the plateau's first row (−6.7 px at 20× over
full scale, still ``valid``). ``saturated`` marks the columns whose plateau has ≥ 3 rows,
or ≥ 2 rows at the image's maximum (the ceiling); only those columns get the plateau window,
every other column is windowed at its first maximum exactly as before (bit for bit). Two
equal rows below the ceiling are common in quantised, unclipped lines (uint8, σ 3 px: 6 % of
the columns at a peak of 200, 15 % at 60) and are not a plateau. The result in a saturated
column is a centroid of clipped data, so treat it as degraded. ★Not detected: a plateau
broken by a dip (dark-frame or flat-field correction after clipping leaves 1 LSB dips) —
the plateau ends at the dip and the window shifts toward it again (measured 3.5 px, gauss
3.2 px, ``valid``; 5.6 px before the plateau window); pass uncorrected data or clip it back
to the ceiling first. ``truncated`` marks the columns whose weight at
either end of the window (or of the image) is still ≥ ``max(min_peak_rel, 1e-3)`` × the
column's peak weight — the profile was cut, so the centroid is pulled toward the window's
middle (measured: σ 2 px, true 0.4 → 1.48). ``valid`` is not changed by either flag.

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

- [poc_3d_sensor_modalities](../../../../examples/poc_3d_sensor_modalities.py) — `py -3.11 examples/poc_3d_sensor_modalities.py`
- [poc_weld_bead_profile](../../../../examples/poc_weld_bead_profile.py) — `py -3.11 examples/poc_weld_bead_profile.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`light_section`)

[laser_line_center_gauss](laser_line_center_gauss.md) · [laser_line_center_steger](laser_line_center_steger.md) · [light_section_rig](light_section_rig.md) · [light_section_targets](light_section_targets.md) · [light_section_render](light_section_render.md) · [light_plane_calibrate](light_plane_calibrate.md) · [light_section_profile](light_section_profile.md) · [light_section_scan](light_section_scan.md)

---
*Provenance: lightsection.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
