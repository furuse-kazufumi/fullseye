---
op: opd_samples
dim: optics
category: design
in: table
out: table
gpu: なし
examples: [anim3d_lens_aberrations, poc_lens_tolerancing, poc_noncoaxial_optics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# opd_samples — OPTICS `design` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.opd_samples(system, field=None, size=64, wavelength_um=None, image_mm=None, aim=None, vignetting=None)` (実装を直接呼ぶなら `import raytrace; raytrace.opd_samples(system, field=None, size=64, wavelength_um=None, image_mm=None, aim=None, vignetting=None)`、台帳から引くなら `opsoptics.get("opd_samples")`)
- **台帳経由の戻り値**: `fullseye.ledger.opd_samples(...)` は**宣言 out 型 `table` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.opd_samples.raw(...)`、または `raytrace.opd_samples` を直接呼ぶ。
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

OPD (waves) at grid pupil samples: returns ``(px, py, opd, valid)``.

The grid is ``linspace(-1, 1, size)`` in each pupil coordinate, so the
outermost sample *centres* sit on the pupil edge (``rho = ±1``): the pupil
diameter spans ``size − 1`` sample spacings. ``optics.pupil_psf`` counts
the other way (its grid's full width of ``size`` cells is the diameter), so
feeding it this map needs ``f_number = N·(size−1)/size`` for the same PSF
scale (``lensimage.psf_from_opd`` does the bookkeeping for you).

*aim* (``"paraxial"`` / ``"stop"``, default the system's) is the ray aiming of :func:`ray_bundle`.
Vignetting (*vignetting*, default the system's per-field factors) is a **mask** here: the grid stays the
physical pupil (so ``lensimage`` keeps its PSF scale) and only the samples inside the vignetted ellipse
are valid — the same pupil region the spot diagram fills. The reference is the unvignetted chief ray.

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

- [anim3d_lens_aberrations](../../../../examples/anim3d_lens_aberrations.py) — `py -3.11 examples/anim3d_lens_aberrations.py`
- [poc_lens_tolerancing](../../../../examples/poc_lens_tolerancing.py) — `py -3.11 examples/poc_lens_tolerancing.py`
- [poc_noncoaxial_optics](../../../../examples/poc_noncoaxial_optics.py) — `py -3.11 examples/poc_noncoaxial_optics.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](paraxial_trace.md) · [seidel_coefficients](seidel_coefficients.md) · [spot_stats](spot_stats.md) · [tolerance_analysis](tolerance_analysis.md) · [wavefront_from_opd](wavefront_from_opd.md)

## 同カテゴリ(`design`)

[lens_system](lens_system.md) · [thick_lens](thick_lens.md) · [glass](glass.md) · [example_system](example_system.md) · [glass_catalog](glass_catalog.md) · [sellmeier](sellmeier.md) · [paraxial_trace](paraxial_trace.md) · [seidel_coefficients](seidel_coefficients.md)

---
*Provenance: raytrace.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
