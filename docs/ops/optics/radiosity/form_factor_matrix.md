---
op: form_factor_matrix
dim: optics
category: radiosity
in: table
out: matrix
examples: [poc_pocket_interreflection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# form_factor_matrix — OPTICS `radiosity` op

- **データ種**: `table` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.form_factor_matrix(patches, n_quad=3, symmetric=True, far_ratio=8.0, memory_budget_mb=256.0)` (実装を直接呼ぶなら `import radiosity3d; radiosity3d.form_factor_matrix(patches, n_quad=3, symmetric=True, far_ratio=8.0, memory_budget_mb=256.0)`、台帳から引くなら `opsoptics.get("form_factor_matrix")`)

## 使い方

All patch-to-patch view factors F_ij of a ``radiosity_patches`` set (occlusion by the scene's rays).

Each pair is :func:`form_factor_polygons` (``n_quad × n_quad`` Gauss points on the
receiver, Lambert's contour sum to the sender) restricted to pairs that face each
other; when the patches came from a scene, each Gauss point tests one ray to the
sender's centre against the scene. Pairs farther apart than *far_ratio* times the
larger patch's diagonal use the receiver's centroid alone (the sender is still
exact); ``far_ratio=None`` integrates every pair fully. ``symmetric=True`` (default) enforces
reciprocity exactly by averaging ``A_i F_ij`` and ``A_j F_ji`` (the raw values agree
to the quadrature accuracy) — the progressive solver's ``F_ij A_i / A_j`` is then
  exactly ``F_ji``.

Candidate pairs use the former, faster all-at-once calculation while its largest
temporary fits *memory_budget_mb*, and 256-patch blocks otherwise.  The default
256 MB keeps the former path for a 384-patch closed box but blocks 4,096 patches,
whose candidate expression alone needs 1.00 GiB.  On the 2026-10-21 development
machine, whole-call CPU time / ``tracemalloc`` peak were 0.234 s / 115 MiB
(original), 0.219 s / 60 MiB (default), and 0.234 s / 60 MiB (forced blocks) for
384 patches; the isolated 4,096-patch candidate case measured 0.547 s / 1,152 MiB,
1.500 s / 195 MiB, and 1.516 s / 195 MiB respectively.  Pass 0 to always block,
or a sufficiently large value to never block.

Returns the ``(N, N)`` matrix (``matrix``), zero diagonal. In a closed enclosure
each row sums to 1 (to the quadrature accuracy); an opening shows as a row sum < 1.

**Raises** ``ValueError``: an empty or unmarked table (not ``radiosity_patches``);
  *n_quad* not an integer in ``[1, 16]``; *far_ratio* below 1; or a negative or
  non-finite *memory_budget_mb*.

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[abcd_trace](../geometric/abcd_trace.md) · [emva_filter_distortion](../sensorchar/emva_filter_distortion.md) · [mueller_apply](../polarization/mueller_apply.md) · [mueller_checks](../polarization/mueller_checks.md) · [pixel_shift_capture](../pixelshift/pixel_shift_capture.md) · [pixel_shift_merge](../pixelshift/pixel_shift_merge.md) · [pixel_shift_motion_mask](../pixelshift/pixel_shift_motion_mask.md) · [oct_from_spectra](../oct/oct_from_spectra.md)

## 同カテゴリ(`radiosity`)

[form_factor_parallel_rects](form_factor_parallel_rects.md) · [form_factor_perpendicular_rects](form_factor_perpendicular_rects.md) · [form_factor_polygons](form_factor_polygons.md) · [radiosity_patches](radiosity_patches.md) · [radiosity_progressive_3d](radiosity_progressive_3d.md) · [render_optscene_gi](render_optscene_gi.md)

---
*Provenance: radiosity3d.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
