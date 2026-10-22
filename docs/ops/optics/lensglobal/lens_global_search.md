---
op: lens_global_search
dim: optics
category: lensglobal
in: table
out: table
examples: [poc_lens_global_search]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# lens_global_search — OPTICS `lensglobal` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lens_global_search(system=None, variables=None, merit=None, n_starts: 'int' = 8, seed: 'int' = 0, spread: 'float' = 0.5, iterations: 'int' = 40, duplicate_tolerance: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import lensglobal; lensglobal.lens_global_search(system=None, variables=None, merit=None, n_starts: 'int' = 8, seed: 'int' = 0, spread: 'float' = 0.5, iterations: 'int' = 40, duplicate_tolerance: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsoptics.get("lens_global_search")`)

## 使い方

多始点の局所最適化(lensopt.optimize_lens)で局所解を集め、merit 順に返す(``table``)。

Start 0 is *system* as given; starts 1 .. *n_starts*-1 move every variable to ``x (1 + spread u)``
with ``u`` uniform in [-1, 1] drawn from ``numpy.random.default_rng(seed)`` (a variable that is
zero, such as a flat, moves by *spread* times the typical size of its kind). A perturbed start
that is not a valid prescription is redrawn (up to 25 times, then ValueError). Every start is
optimised by ``lensopt.optimize_lens`` with the *same* merit and the *same* EFL target (the EFL
of *system* unless ``merit["efl_target"]`` says otherwise), so the optima are comparable.
*merit* is a dict of ``fields wavelengths rings efl_target efl_weight field_weights pupil_fill
min_thickness max_thickness min_radius damping tolerance``; *variables* are as in ``optimize_lens``.

Returns ``{"optima", "best", "n_starts", "n_distinct", "basins", "seed", "spread"}``. ``optima``
holds every start's result sorted by merit (ties by start index): ``{"start", "merit",
"start_merit", "rms_spot", "efl", "system", "values", "status", "converged", "duplicate_of"}``
where ``duplicate_of`` is the ``start`` of an earlier (better) optimum with the same variables
(every variable within *duplicate_tolerance* relative, floor 1e-9) or None. ``basins`` lists the
distinct optima with the number of starts that reached each. Deterministic for a given seed.

Example::

    r = lens_global_search(singlet, ["c0", "c1"], {"efl_target": 100.0}, n_starts=12, seed=3)
    r["best"]["merit"], r["n_distinct"]

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

- [poc_lens_global_search](../../../../examples/poc_lens_global_search.py) — `py -3.11 examples/poc_lens_global_search.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`lensglobal`)

[glass_nearest](glass_nearest.md) · [lens_substitute_glasses](lens_substitute_glasses.md)

---
*Provenance: lensglobal.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
