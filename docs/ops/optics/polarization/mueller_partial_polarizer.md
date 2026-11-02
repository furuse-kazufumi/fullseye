---
op: mueller_partial_polarizer
dim: optics
category: polarization
in: 
out: matrix
gpu: なし
examples: [polarization_camera_pipeline]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# mueller_partial_polarizer — OPTICS `polarization` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.mueller_partial_polarizer(angle_deg=0.0, extinction_ratio=1000.0, transmission=1.0)` (実装を直接呼ぶなら `import optics; optics.mueller_partial_polarizer(angle_deg=0.0, extinction_ratio=1000.0, transmission=1.0)`、台帳から引くなら `opsoptics.get("mueller_partial_polarizer")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Mueller matrix of a linear polariser with a finite extinction ratio (a linear diattenuator). → (4, 4), or (*shape, 4, 4) for an angle field.

A real polariser passes intensity transmittance ``T1 = transmission`` for
light polarised along its axis and ``T2 = T1 / extinction_ratio`` for light
across it. Writing ``P = T1 + T2``, ``D = T1 - T2``, ``Q = 2 sqrt(T1 T2)``
and ``c = cos 2a``, ``s = sin 2a`` (the axis at *angle_deg*), the matrix is

    ``0.5 * [[P,   D c,             D s,             0],``
    ``       [D c, P c^2 + Q s^2,   (P - Q) c s,     0],``
    ``       [D s, (P - Q) c s,     P s^2 + Q c^2,   0],``
    ``       [0,   0,               0,               Q]]``

— the textbook diattenuator ``diag``-block form rotated to *angle_deg*.
It is also exactly the Mueller matrix of the Jones matrix
``R(a) diag(sqrt T1, sqrt T2) R(-a)`` (a pure diattenuator has no
retardance and no depolarisation), and the tests check that equality
through the generic Jones → Mueller conversion, a separate code path.

Ground truth (closed form, checked in the tests): unpolarised light comes
out with intensity ``(T1 + T2)/2`` and degree of polarisation
``(ER - 1)/(ER + 1)``; the intensity transmitted through two such
polarisers, parallel vs crossed, is ``(T1^2 + T2^2)/2`` vs ``T1 T2`` —
the measured extinction ratio of the pair is ``(ER^2 + 1)/(2 ER)``, not
``ER``; Malus's law becomes ``T2 + (T1 - T2) cos^2(theta)`` for fully
polarised input at angle theta to the axis; ``ER -> infinity`` tends to
``T1 *`` :func:`mueller_element` ``("polarizer")``; ``ER = 1`` is a
neutral-density filter ``T1 * I``.

*angle_deg* may be an array (one matrix per entry, as
:func:`mueller_element`); *extinction_ratio* and *transmission* are
scalars. Angles follow the module convention (from +x toward +y = down the
rows, clockwise on a displayed image).

**Raises** ``ValueError``: non-finite / non-real / bool / string arguments;
*extinction_ratio* < 1 (an "extinction ratio" below 1 means the axis is the
other one — rotate by 90 degrees instead of passing the reciprocal) or
infinite (use :func:`mueller_element` for the ideal polariser);
*transmission* outside ``(0, 1]`` (a passive element cannot amplify, and a
zero-transmission element has no axis); an angle field over
:data:`MAX_FIELD_ELEMENTS` / 16 entries.

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

## 型が繋がる次の op(`matrix` を入力に取れる)

[abcd_trace](../geometric/abcd_trace.md) · [emva_filter_distortion](../sensorchar/emva_filter_distortion.md) · [mueller_apply](mueller_apply.md) · [mueller_checks](mueller_checks.md) · [equirect_rotate](../omni360/equirect_rotate.md) · [pixel_shift_capture](../pixelshift/pixel_shift_capture.md) · [pixel_shift_merge](../pixelshift/pixel_shift_merge.md) · [pixel_shift_motion_mask](../pixelshift/pixel_shift_motion_mask.md)

## 同カテゴリ(`polarization`)

[jones_element](jones_element.md) · [jones_apply](jones_apply.md) · [stokes_from_jones](stokes_from_jones.md) · [mueller_element](mueller_element.md) · [mueller_apply](mueller_apply.md) · [stokes_analyze](stokes_analyze.md) · [polarization_demosaic](polarization_demosaic.md) · [polarization_demosaic_color](polarization_demosaic_color.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
