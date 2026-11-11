---
op: bottle_fit_from_pattern
dim: optics
category: watervision
in: 
out: table
gpu: なし
examples: [poc_bottle_pattern_inverse]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# bottle_fit_from_pattern — OPTICS `watervision` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.bottle_fit_from_pattern(u_map, x_mm, pixel_pitch_um, camera_distance_mm, background_distance_mm, known=None, free_background=False, rows_per_section=None, restarts=3) -> 'dict'` (実装を直接呼ぶなら `import watervision; watervision.bottle_fit_from_pattern(u_map, x_mm, pixel_pitch_um, camera_distance_mm, background_distance_mm, known=None, free_background=False, rows_per_section=None, restarts=3) -> 'dict'`、台帳から引くなら `opsoptics.get("bottle_fit_from_pattern")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Read the bottle back from the distortion of a background pattern -> dict (radius, wall, indices, fill line, and how well each is known).

``u_map`` (rows, cols) is the background coordinate (mm) each pixel looks at (the ``u_mm`` of :func:`bottle_background_map`, or
a phase-shifting measurement of it; NaN where unusable); ``x_mm`` the column positions in the plane of the axis,
``pixel_pitch_um`` the pitch, the camera and the pattern are ``camera_distance_mm`` and ``background_distance_mm`` from the
axis (known from the set-up). The fill line is found first, from the jump of the map between rows (the liquid and the air
bend the pattern differently): rows above it are the empty section, rows below the filled one (``level_mm`` as in
:func:`fill_level_from_image`: ``(rows below the boundary) * pitch``). Each section is reduced to one profile (the median over its
rows, ``rows_per_section`` of them if given, the two rows next to the boundary left out) and a closed-form model of
concentric circles, written without the tracer (an angle and an impact parameter per ray), is fitted by Levenberg-Marquardt
over ``radius_mm``, ``wall_mm``, ``n_glass`` and ``n_liquid`` (the filled section; a bottle with no fill line is one section
whose core index is fitted). ``known`` is a dict of values held fixed (``"radius_mm"``, ``"wall_mm"``, ``"n_glass"``,
``"n_liquid"``); ``free_background=True`` also fits the distance of the pattern. The start is a scan of the radius from the
silhouette (where the map leaves the straight line) with ``restarts`` (1 to 3) different index starts; the table reports how far the
starts that reach the same cost disagree (``start_spread``).

The table has ``radius_mm``, ``wall_mm``, ``n_glass``, ``n_liquid``, ``background_distance_mm``, ``free`` (the fitted names),
``sigma`` (1 sigma of each free name from the Gauss-Newton covariance with the residual scatter as the noise, None if not free),
``corr`` (correlation matrix of the free names) with ``corr_names``, ``cond`` (condition number of the Jacobian with unit-length
columns: a large value means some combination of the parameters is hardly seen), ``singular_values``, ``weak_direction`` (the
combination with the smallest singular value, one number per free name) and ``weak_rel_sigma`` (the 1 sigma relative change along
it), ``residual_rms_mm``, ``n_columns`` and ``columns_rejected`` (resolved pixels the model calls blocked), ``converged``,
``iterations``, ``level_found`` / ``level_mm`` / ``level_row`` / ``level_jump_mm`` (False and None when the rows do not
jump: an empty or a full bottle has no fill line to read; ``level_mm`` is then None), ``fill_state`` (``"partial"`` or ``"uniform"``).
``poorly_determined`` lists the fitted names whose 1 sigma exceeds 1 % of the value or that sit on a bound, and ``separated`` is
True only when the fit converged and that list is empty. This is a rule of thumb for the error of the noise, not a guarantee: the 1 %
was chosen after measuring (at 25 % the flag called 15-20 % of the wrong wall estimates, and 73-76 % of the trials with n_glass off
by more than 0.02, separated; at 1 % none of 535 wrong trials in two disjoint seed sets), the covariance assumes the model is exact, and a
model error such as an off-centre inner wall changes the estimates without changing the residual, the sigma or this flag.
``n_liquid`` is None when no row of the map is left in the filled section. Quantities that barely move the pattern (a thin wall against the
glass index when the edge pixels are lost, the pattern distance against the liquid index) come back there, with a large
``sigma`` and ``cond``; they are not separated, and the table says so rather than giving a number without it.
The model assumes concentric circles with a uniform wall, a horizontal 2-D section, an ideal pinhole, a flat background, exactly known
distances and pitch, no dispersion and a flat liquid surface; the maps of :func:`bottle_background_map` obey the same assumptions, so a test on
them proves consistency, not that a real bottle is recovered. A map with
fewer than 12 usable columns, a wrong shape, an unknown ``known`` name or a camera not beyond one diameter are refused.

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

- [poc_bottle_pattern_inverse](../../../../examples/poc_bottle_pattern_inverse.py) — `py -3.11 examples/poc_bottle_pattern_inverse.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`watervision`)

[caustic_irradiance](caustic_irradiance.md) · [bottle_image](bottle_image.md) · [fill_level_from_image](fill_level_from_image.md) · [bottle_background_map](bottle_background_map.md) · [wet_surface_appearance](wet_surface_appearance.md) · [wet_dry_inspection_pair](wet_dry_inspection_pair.md) · [underwater_inspection_image](underwater_inspection_image.md) · [caustic_floor_segmentation](caustic_floor_segmentation.md)

---
*Provenance: watervision.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
