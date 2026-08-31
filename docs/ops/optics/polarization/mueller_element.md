---
op: mueller_element
dim: optics
category: polarization
in: 
out: matrix
examples: [optics_imaging]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# mueller_element — OPTICS `polarization` op

- **データ種**: `` → `matrix`
- **呼び出し**: `import optics; optics.mueller_element(kind='polarizer', angle_deg=0.0, retardance_deg=90.0)` (または `opsoptics.get("mueller_element")`)

## 使い方

A 4x4 real Mueller matrix for one polarisation element.

*kind* is one of :data:`MUELLER_KINDS` — the same five as
:func:`jones_element` plus ``"depolarizer"`` (ideal, ``diag(1, 0, 0, 0)``),
which has **no Jones counterpart at all**. That extra kind is the reason
this family exists: Jones algebra can only carry fully polarised light,
Mueller algebra carries partial polarisation, scattering and depolarisation
— which is what a real polarisation camera sees.

Angles are doubled inside (``c = cos(2a)``, ``s = sin(2a)``) because the
Stokes parameters live on the Poincare sphere, where a physical rotation by
``a`` is a rotation by ``2a``.

Returns a ``(4, 4)`` float64 matrix acting on ``[S0, S1, S2, S3]``; apply it
with :func:`mueller_apply` and compose a train as
``M_last @ ... @ M_first``.

Ground truth it reproduces exactly: an ideal polariser transmits exactly
half of unpolarised light (``[1,0,0,0] -> S0 = 0.5``) and fully polarises
it; two polarisers at relative angle theta transmit ``0.5*cos^2(theta)``
(Malus); a rotator by 45 degrees turns horizontal into 45-degree linear;
the depolariser leaves ``S0`` and kills ``S1..S3``. Cross-checked against
the Jones family in the tests — for every kind and a sweep of angles, the
Jones path and the Mueller path return the **same Stokes vector to 1e-14**,
which is the only construction that catches a sign slip in either one.

**Raises** ``ValueError``: an unknown *kind*; non-finite *angle_deg* or
*retardance_deg*.

Ideal, lossless (except the polariser's physical loss), normal-incidence
elements; no diattenuation-plus-retardance combinations, no depolarisation
other than the ideal case.

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[abcd_trace](../geometric/abcd_trace.md) · [mueller_apply](mueller_apply.md)

## 同カテゴリ(`polarization`)

[jones_element](jones_element.md) · [jones_apply](jones_apply.md) · [stokes_from_jones](stokes_from_jones.md) · [mueller_apply](mueller_apply.md) · [stokes_analyze](stokes_analyze.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
