---
op: polarization_demosaic
dim: optics
category: polarization
in: image2d
out: polsweep
examples: [polarization_camera_pipeline]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# polarization_demosaic — OPTICS `polarization` op

- **データ種**: `image2d` → `polsweep`
- **呼び出し**: `import fullseye as fs; fs.ledger.polarization_demosaic(raw, layout=((90.0, 45.0), (135.0, 0.0)))` (実装を直接呼ぶなら `import optics; optics.polarization_demosaic(raw, layout=((90.0, 45.0), (135.0, 0.0)))`、台帳から引くなら `opsoptics.get("polarization_demosaic")`)

## 使い方

Split a polarisation-sensor mosaic into the four analyser images.

A polarisation camera puts four micro-polarisers on each 2x2 block of
pixels; the raw frame is one (H, W) array in which neighbouring pixels saw
the scene through different analysers. This returns a ``(4, H, W)`` array
of images ``[I_0, I_45, I_90, I_135]`` (the ``polsweep`` sort, in
:data:`POLARIZATION_SWEEP_ANGLES` order, so the result feeds
:func:`specularity.polarization_stokes` and ``polarization_dolp_map``
directly), each interpolated to full resolution.

Interpolation is **bilinear**, the same estimate a Bayer demosaic makes for
a colour plane that occupies one pixel in four: a missing pixel is the mean
of its measured 4-neighbours (edge-adjacent) or 4-neighbours (diagonal),
which is exactly the ``[[1, 2, 1], [2, 4, 2], [1, 2, 1]] / 4`` kernel applied
to the masked plane. Ground truth: on a plane that is **linear** in x and y
the interpolation is exact (a bilinear estimate of an affine field is the
field), so the test plants four affine fields, mosaics them, and demands
every returned image equal its field to 1e-12 away from the border. The
border is handled by mirroring the **mosaic** two pixels outward before
interpolating (an even, non-duplicating reflection keeps the 2x2 phase), so
a uniform field is exact up to the edge and a gradient is mirrored there —
a symmetric bias on the outermost row and column, and said so. Against
Polanalyser's OpenCV bilinear path the interior agrees to the 16-bit
quantisation (1.8e-5) and only the outer two pixels differ (2026-09-18).

*layout* is the angle at each 2x2 position, ``((a00, a01), (a10, a11))`` in
degrees; the default is the Sony IMX250MZR block. Every angle in
:data:`POLARIZATION_SWEEP_ANGLES` must appear exactly once.

**Raises** ``ValueError``: *raw* is not a 2-D array, has an odd height or
width (the block would be cut), contains non-finite values, or *layout* is
not a permutation of the four sweep angles.

Provenance: the layout convention and the "four Bayer planes" reading of
the mosaic follow Polanalyser (Maeda, MIT); the interpolation is the
classic bilinear Bayer demosaic. This is a re-implementation from that
description, not copied code, and it does not depend on OpenCV. Colour
polarisation sensors (IMX250MYR, a 4x4 block) are handled by
:func:`polarization_demosaic_color`.

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

## 型が繋がる次の op(`polsweep` を入力に取れる)

—

## 同カテゴリ(`polarization`)

[jones_element](jones_element.md) · [jones_apply](jones_apply.md) · [stokes_from_jones](stokes_from_jones.md) · [mueller_element](mueller_element.md) · [mueller_apply](mueller_apply.md) · [stokes_analyze](stokes_analyze.md) · [polarization_demosaic_color](polarization_demosaic_color.md) · [mueller_from_intensities](mueller_from_intensities.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
