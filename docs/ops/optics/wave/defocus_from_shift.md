---
op: defocus_from_shift
dim: optics
category: wave
in: 
out: measurement
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# defocus_from_shift — OPTICS `wave` op

- **データ種**: `なし` → `measurement`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.defocus_from_shift(shift_um=10.0, wavelength_um=0.55, f_number=5.6)` (実装を直接呼ぶなら `import optics; optics.defocus_from_shift(shift_um=10.0, wavelength_um=0.55, f_number=5.6)`、台帳から引くなら `opsoptics.get("defocus_from_shift")`)

## 使い方

Defocus wavefront error (waves at the pupil edge) of an axial focus shift.

Moving the detector (or, equivalently, the focus) by ``shift_um`` along the
axis of an ``f/N`` beam adds the quadratic wavefront error
``W(rho) = W20 * rho^2`` with

    ``W20 = shift / (8 * lambda * N^2)``  [waves]

— the paraxial Seidel defocus term, ``rho`` the normalised pupil radius
(1 at the edge). This is the number :func:`pupil_psf` takes as
``defocus_waves``, so the two compose: a longitudinal chromatic aberration
(focal shift versus wavelength, e.g. from ``raytrace.chromatic_shift`` or a
published ``df/f(lambda)``) becomes a per-band ``defocus_waves`` here and a
per-band PSF there.

Returns a float (a ``measurement``). The sign is the sign of *shift_um*:
**positive = the detector sits beyond the focus** (the beam has converged
and is diverging again). For a symmetric pupil the PSF does not depend on
the sign; for an asymmetric one (a slit, a W, an off-axis hole) the sign
**flips the PSF through the centre** — that is exactly the handle a
one-photoreceptor eye can read the direction of defocus from.

Ground truth (closed form, ``tests/test_optics.py``): ``shift = 8 lambda N^2``
is exactly one wave; the function is linear in *shift_um* and inverse in
*wavelength_um* and in ``N^2`` (checked at two of each). At ``N = 1.5``,
``lambda = 0.55 um`` (a cephalopod-scale ``f/1.5`` eye) a 250 um focus shift
is 25.3 waves.

**Raises** ``ValueError``: non-finite *shift_um*; non-positive or non-finite
*wavelength_um* / *f_number*.

Paraxial: ``W20 = shift/(8 N^2)`` is the small-angle expansion of the exact
``shift * (1 - cos theta)`` sag; at ``f/1.5`` (``sin theta = 1/3``) the exact
edge value is 5.7 % below the paraxial one — the number is a *defocus
convention*, not a high-NA wavefront.

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

- [optics_imaging](../../../../examples/optics_imaging.py) — `py -3.11 examples/optics_imaging.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [fourier_plane_filter](fourier_plane_filter.md) · [four_f_filter](four_f_filter.md) · [gaussian_beam](gaussian_beam.md) · [pupil_psf](pupil_psf.md) · [pupil_blur](pupil_blur.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
