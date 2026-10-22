---
op: set_vignetting
dim: optics
category: design
in: table
out: table
examples: [optical_design_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# set_vignetting — OPTICS `design` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.set_vignetting(system, fields=None, rings=8, wavelength_um=None, mode='four')` (実装を直接呼ぶなら `import raytrace; raytrace.set_vignetting(system, fields=None, rings=8, wavelength_um=None, mode='four')`、台帳から引くなら `opsoptics.get("set_vignetting")`)

## 使い方

Compute the vignetting factors that remove every aperture-clipped ray, as "set vignetting" does (``table``).

For each field (a list of radial field values; default the existing records' fields, else the
system's own ``field``) the real-ray-aimed pupil is searched along ±x and ±y for the edge of the
clear region (bisection to 1e-13): ``VDX, VDY`` are the centres and ``VCX, VCY`` one minus the
half-widths, ``VAN`` is 0.

*mode* ``"four"`` (the default) is the definition of the format's user guide (knowledge-base article
KA-01393): the factors are chosen so that exactly the four marginal rays — top ``(0, 1)``, bottom
``(0, -1)``, left ``(-1, 0)`` and right ``(1, 0)`` of the vignetted pupil — pass every aperture. It is
what reproduces the factors recorded in a file, but when the clear region is not an ellipse (e.g. two
offset circles) rays between the four can still be clipped. ``"grid"`` is the stricter option: if a
``rings``-ring hexapolar grid plus a 72-point rim of the resulting ellipse still has clipped rays the
ellipse is shrunk about its centre until none is, so afterwards no ray of the grid is clipped.
A field with nothing clipped gets all-zero factors
(to 1e-9 and in practice exactly). A field whose chief ray is itself clipped raises ``ValueError``.
Returns a copy of *system* with ``aim="stop"`` (the factors are fractions of the stop pupil, so they
belong to real-ray aiming) and the records for those fields replaced; ``vignetting_set`` records the
fields, grid (``rings``, ``n_checked`` rays per field), and wavelength the factors were verified on.

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

- [optical_design_metrics](../../../../examples/optical_design_metrics.py) — `py -3.11 examples/optical_design_metrics.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](paraxial_trace.md) · [seidel_coefficients](seidel_coefficients.md) · [spot_stats](spot_stats.md) · [tolerance_analysis](tolerance_analysis.md) · [wavefront_from_opd](wavefront_from_opd.md)

## 同カテゴリ(`design`)

[lens_system](lens_system.md) · [thick_lens](thick_lens.md) · [glass](glass.md) · [example_system](example_system.md) · [glass_catalog](glass_catalog.md) · [sellmeier](sellmeier.md) · [paraxial_trace](paraxial_trace.md) · [seidel_coefficients](seidel_coefficients.md)

---
*Provenance: raytrace.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
