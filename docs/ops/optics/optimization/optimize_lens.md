---
op: optimize_lens
dim: optics
category: optimization
in: table
out: table
examples: [lens_optimize_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# optimize_lens — OPTICS `optimization` op

- **データ種**: `table` → `table`
- **呼び出し**: `import lensopt; lensopt.optimize_lens(system, variables=None, fields=None, wavelengths=None, rings=4, efl_target=None, efl_weight=None, field_weights=None, iterations=30, damping=0.001, tolerance=1e-07, min_thickness=0.5, max_thickness=None, min_radius=1.0, pupil_fill=0.98)` (または `opsoptics.get("optimize_lens")`)

## 使い方

Damped-least-squares (Levenberg–Marquardt) optimisation of a prescription (``table``).

*variables*: surface parameters to move — strings ``"R<i>"``/``"c<i>"``
(curvature; a radius may pass through flat), ``"t<i>"`` (thickness),
``"k<i>"`` (conic), ``"A4_<i>"``, ``"A6_<i>"`` … (even aspheric
coefficients). Default: every finite radius. *efl_target*: hold the
effective focal length (default: the starting EFL, so a design does not
"improve" by getting longer); pass ``0`` / ``False`` to leave it free.
Fields / wavelengths / rings / weights as in :func:`merit_function`.

Each iteration builds the Jacobian by forward differences, solves
``(JᵀJ + λ diag(JᵀJ)) δ = −Jᵀr`` and accepts the step only if the merit
falls (then λ /= 3; otherwise λ ×= 4 and retried, up to 6 times); a step
that yields an invalid prescription counts as a failure. Stops when the
relative merit change is below *tolerance* twice in a row (``converged``,
``status="converged"``), when two iterations in a row accept no step or λ
blows past 1e8 (``status="stalled"``, ``converged=False``), or after
*iterations* (``status="iterations"``). Thickness is clamped to
``[min_thickness, max_thickness]`` and ``|R| >= min_radius`` — the start
included, so the returned system always obeys the bounds.

Returns ``{"system": optimised prescription, "merit_initial",
"merit_final", "rms_initial", "rms_final", "efl_initial", "efl_final",
"history": [merit per accepted iteration], "iterations", "converged",
"variables": [{"name", "surface", "initial", "final"}], "rays_lost"}``.

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

- [lens_optimize_demo](../../../../examples/lens_optimize_demo.py) — `py -3.11 examples/lens_optimize_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md) · [spot_diagram](../design/spot_diagram.md)

## 同カテゴリ(`optimization`)

[merit_function](merit_function.md) · [bend_singlet](bend_singlet.md)

---
*Provenance: lensopt.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
