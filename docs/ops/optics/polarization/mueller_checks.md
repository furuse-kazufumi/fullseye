---
op: mueller_checks
dim: optics
category: polarization
in: matrix
out: table
examples: [polarization_camera_pipeline]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# mueller_checks — OPTICS `polarization` op

- **データ種**: `matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mueller_checks(mueller, tol=1e-09)` (実装を直接呼ぶなら `import optics; optics.mueller_checks(mueller, tol=1e-09)`、台帳から引くなら `opsoptics.get("mueller_checks")`)

## 使い方

Say whether a 4x4 matrix is a physically realisable Mueller matrix, and
how depolarising it is.

Returns a dict:

``physical``
    ``True`` iff the coherency matrix ``H = 1/4 sum_ij M_ij (sigma_i (x) sigma_j^*)``
    is positive semidefinite — Cloude's criterion (1986), the necessary and
    sufficient condition for M to be a convex sum of pure (Mueller–Jones)
    matrices (Gil, 2007). ``coherency_eigenvalues`` carries the four real
    eigenvalues (descending) so the caller sees *how* far from physical.
``pure``
    one non-zero eigenvalue: M comes from a single Jones matrix (no
    depolarisation). Every element from :func:`mueller_element` except the
    depolariser is pure.
``depolarization_index``
    Gil–Bernabeu ``P_Delta = sqrt((sum_ij M_ij^2 - M_00^2) / (3 M_00^2))``:
    1 for a pure matrix, 0 for the ideal depolariser.
``passive``
    the largest transmittance ``M_00 + sqrt(M_01^2 + M_02^2 + M_03^2)`` is
    ``<= 1`` — a passive element cannot amplify.
``transmittance_max`` / ``transmittance_min``
    those two bounds of the transmitted intensity over all input states.

Ground truth in the tests: every :func:`mueller_element` kind is physical
and passive; the pure ones have eigenvalues ``(M_00, 0, 0, 0)`` to 1e-12 and
``P_Delta = 1``; the ideal depolariser has ``P_Delta = 0``; a matrix with
``M_11 > M_00`` (more polarised output than input) is refused as
non-physical; a gain matrix (``2 I``) is physical but not passive.

**Raises** ``ValueError``: not a real 4x4 matrix, non-finite, or
``M_00 <= 0`` (no transmitted intensity — every ratio would be 0/0).

Provenance: Cloude, S. R. (1986), *Optik* 75, 26; Gil, J. J. & Bernabeu, E.
(1986), *Optica Acta* 33, 185 (depolarisation index); the check set mirrors
what py-pol (del Hoyo & Sánchez Brea, MIT) exposes as ``is_physical`` /
``is_pure`` / ``is_transmissive``, re-implemented from the definitions.

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

- [polarization_camera_pipeline](../../../../examples/polarization_camera_pipeline.py) — `py -3.11 examples/polarization_camera_pipeline.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md) · [spot_diagram](../design/spot_diagram.md)

## 同カテゴリ(`polarization`)

[jones_element](jones_element.md) · [jones_apply](jones_apply.md) · [stokes_from_jones](stokes_from_jones.md) · [mueller_element](mueller_element.md) · [mueller_apply](mueller_apply.md) · [stokes_analyze](stokes_analyze.md) · [polarization_demosaic](polarization_demosaic.md) · [mueller_from_intensities](mueller_from_intensities.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
