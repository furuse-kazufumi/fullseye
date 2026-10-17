---
op: radiosity_progressive_3d
dim: optics
category: radiosity
in: table × signal
out: table
examples: [poc_pocket_interreflection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# radiosity_progressive_3d — OPTICS `radiosity` op

- **データ種**: `table × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.radiosity_progressive_3d(patches, emission, form_factors=None, albedo=None, tol=1e-06, max_shots=None, n_quad=3)` (実装を直接呼ぶなら `import radiosity3d; radiosity3d.radiosity_progressive_3d(patches, emission, form_factors=None, albedo=None, tol=1e-06, max_shots=None, n_quad=3)`、台帳から引くなら `opsoptics.get("radiosity_progressive_3d")`)

## 使い方

Progressive-refinement radiosity (Cohen et al. 1988, shooting, eqs. 7–8) on a 3-D patch set, with the evidence that it converged.

Solves ``B = E + diag(ρ) F̃ B`` (``F̃_ji = F_ij A_i/A_j``, eq. 8) by shooting: all
patches start with ``B = ΔB = E`` (the emitted, or first-reflected, radiosity);
repeatedly the patch with the largest **unshot energy** ``ΔB_i A_i`` shoots —
every patch ``j`` gains ``ΔRad = ρ_j ΔB_i F_ij A_i/A_j`` in both ``B_j`` and
``ΔB_j`` — and its ``ΔB_i`` is reset to 0. Ties (equal after rounding to 1e-12
relative) go to the lower index; nothing is random.

**Stopping rule — our choice, not Cohen's**: the paper stops "when the solution
converges to within the desired tolerance" without a number. Here the shooting
stops when the residual unshot energy ``Σ ΔB_i A_i`` falls to ``tol`` times the
initial energy ``Σ E_i A_i`` (a bound on the energy still missing from the
solution). ``max_shots`` (default ``200 × N``) caps the work; hitting it returns
``converged=False``.

*emission* ``E`` is ``(N,)`` or ``(N, C)`` (C colour channels), non-negative.
*albedo* defaults to the patches' (RGB when *emission* has 3 channels, else the
channel mean). *form_factors* defaults to :func:`form_factor_matrix` (``n_quad``).

Returns a dict (``table``) with ``kind = "rad_solution"``, ``radiosity`` (N, C),
``unshot_history`` (the residual energy before each shot), ``n_shots``,
``converged``, ``tol``, ``residual_energy`` (relative), ``initial_energy`` and the
``stop_rule`` text.

**Raises** ``ValueError``: an empty or unmarked table (not ``radiosity_patches``);
emission or albedo of the wrong shape, negative or non-finite; an albedo outside
``[0, 1]``; *tol* not in ``(0, 1]``; a form-factor matrix of the wrong shape. (An
albedo of 1 in a closed enclosure never loses energy: the shooting then stops at
*max_shots* with ``converged=False`` instead of raising.)

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

[form_factor_parallel_rects](form_factor_parallel_rects.md) · [form_factor_perpendicular_rects](form_factor_perpendicular_rects.md) · [form_factor_polygons](form_factor_polygons.md) · [radiosity_patches](radiosity_patches.md) · [form_factor_matrix](form_factor_matrix.md) · [render_optscene_gi](render_optscene_gi.md)

---
*Provenance: radiosity3d.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
