---
op: lens_system
dim: optics
category: design
in: 
out: table
examples: [lens_calibration_loop_demo, lens_defect_dataset_demo, lens_design_demo, lens_optimize_demo]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# lens_system — OPTICS `design` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import raytrace; raytrace.lens_system(surfaces=None, stop=None, object_mm=inf, wavelength_um=0.58756, index_object=1.0, image_mm=None, field=None)` (または `opsoptics.get("lens_system")`)

## 使い方

Build a validated sequential prescription (the ``table`` every other op consumes).

*surfaces* is a list; each entry is a dict ``{"R", "t", "n", "k", "ap",
"mirror", "decenter", "tilt", "asph"}`` or a tuple ``(R, t, n[, k[, ap]])``:

* ``R`` radius (mm, ``inf`` for flat), ``t`` thickness to the next surface
  (mm, the last one is the distance to the image plane when *image_mm* is
  not given — use ``None`` to place the image at the paraxial focus),
  ``n`` medium after the surface (index, ``(nd, vd)`` or :func:`glass`),
  ``k`` conic (default 0), ``ap`` semi-aperture in mm (default ``None`` =
  unlimited), ``mirror`` bool, ``decenter`` ``(dx, dy)`` mm, ``tilt``
  ``(ax, ay)`` degrees about x and y, ``asph`` even aspheric coefficients
  ``(A4, A6, A8, …)`` in mm⁻³, mm⁻⁵, … (default none = pure conic).
* *stop*: index of the aperture-stop surface (default: the first surface).
  The stop's ``ap`` is the stop radius (required unless every surface has
  one, in which case the smallest is used).
* *object_mm*: distance from the first vertex to the object (``inf`` for a
  collimated object); *index_object*: index of object space.
* *field*: default field for the analysis ops — degrees (infinite object)
  or object height in mm (finite object). Default 0 (on axis).

Default (no *surfaces*): a plano-convex BK7 singlet, ``f ≈ 100 mm``,
``f/4``, stop at the first surface — a sensible starting point for the
examples and for the no-argument registry call.

Returns a plain dict (JSON-friendly) — pass it to the other functions.

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

- [lens_calibration_loop_demo](../../../../examples/lens_calibration_loop_demo.py) — `py -3.11 examples/lens_calibration_loop_demo.py`
- [lens_defect_dataset_demo](../../../../examples/lens_defect_dataset_demo.py) — `py -3.11 examples/lens_defect_dataset_demo.py`
- [lens_design_demo](../../../../examples/lens_design_demo.py) — `py -3.11 examples/lens_design_demo.py`
- [lens_optimize_demo](../../../../examples/lens_optimize_demo.py) — `py -3.11 examples/lens_optimize_demo.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](paraxial_trace.md) · [seidel_coefficients](seidel_coefficients.md) · [spot_stats](spot_stats.md) · [tolerance_analysis](tolerance_analysis.md) · [wavefront_from_opd](wavefront_from_opd.md) · [spot_diagram](spot_diagram.md)

## 同カテゴリ(`design`)

[thick_lens](thick_lens.md) · [glass](glass.md) · [example_system](example_system.md) · [glass_catalog](glass_catalog.md) · [sellmeier](sellmeier.md) · [paraxial_trace](paraxial_trace.md) · [seidel_coefficients](seidel_coefficients.md) · [spot_stats](spot_stats.md)

---
*Provenance: raytrace.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
