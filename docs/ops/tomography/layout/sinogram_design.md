---
op: sinogram_design
dim: tomography
category: layout
in: 
out: table
examples: [ct_reconstruction, tomography_reconstruct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# sinogram_design — TOMOGRAPHY `layout` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import tomography; tomography.sinogram_design(n_angles=180, n_detectors=None, size=256, detector_pitch_mm=1.0, span_deg=180.0)` (または `opstomography.get("sinogram_design")`)

## 使い方

What a scan geometry can and cannot resolve — **before** anything is built.

The axial counterpart of :func:`visiondesign.imaging_budget` and of
:func:`interferometry.csi_design`: no data goes in, only the geometry, and
what comes out are the limits that the geometry has already decided.

Returns a dict with, among others:

* ``resolvable_feature_mm`` — ``2 * pitch``: two detector samples per cycle is
  the Nyquist floor, and no reconstruction algorithm recovers a detail finer
  than the detector saw.
* ``views_for_full_sampling`` — ``ceil(pi/2 * n_detectors)``, the classical
  matching of angular to radial sampling (:data:`VIEWS_PER_DETECTOR`).
* ``undersampling_factor`` — that number over ``n_angles``. **1.0 or below is
  a fully sampled scan.** Above it you are doing sparse-view CT on purpose and
  the reconstruction algorithm has to make up the difference; the measured
  cost is in this module's docstring and in the test suite's break table.
* ``streak_free_radius_px`` — ``1 / d(theta)`` with ``d(theta)`` in radians:
  the radius, in pixels, at which the *azimuthal* sample spacing between
  neighbouring views (``r * d(theta)``) grows past one sample. Outside it,
  filtered back-projection lays down visible streaks. For 180 views over 180
  degrees this is 57.3 px, i.e. a 256-px phantom is already streaking at its
  corners. It does **not** depend on the detector pitch: the radius is
  quoted in the same unit the sample spacing is, so the pitch cancels
  (``pitch / d(theta)`` is the same radius in millimetres, which is what an
  earlier version returned under the pixel label — 28.6 "px" at 0.5 mm,
  114.6 at 2 mm, for a geometry whose streak radius had not changed).
* ``sinogram_bytes`` / ``elements`` — what you are about to allocate.
* ``verdict`` — ``"fully sampled"`` / ``"sparse view"``.

:param n_angles: planned number of views.
:param n_detectors: planned detector bins; ``None`` -> enough to cover the
    diagonal of a *size* x *size* image.
:param size: reconstruction grid side in pixels.
:param detector_pitch_mm: physical detector bin spacing.
:param span_deg: angular range of the scan.
:returns: dict of floats / ints / str.
:raises ValueError: on non-int counts, non-positive pitch or span.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`
- [tomography_reconstruct](../../../../examples/tomography_reconstruct.py) — `py -3.11 examples/tomography_reconstruct.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`layout`)

[projection_angles](projection_angles.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
