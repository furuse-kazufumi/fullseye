---
op: sinogram_center_shift
dim: tomography
category: geometry
in: sinogram
out: sinogram
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# sinogram_center_shift — TOMOGRAPHY `geometry` op

- **データ種**: `sinogram` → `sinogram`
- **呼び出し**: `import tomography; tomography.sinogram_center_shift(sinogram, shift_px=None, angles_deg=None)` (または `opstomography.get("sinogram_center_shift")`)

## 使い方

Re-centre a sinogram on its axis of rotation.

Shifts every projection by ``-shift_px`` along the detector axis with linear
interpolation. With ``shift_px=None`` the shift is measured first by
:func:`sinogram_center_of_rotation`, which makes this the one-call fix.

Round-trip on the Shepp-Logan phantom, shifting by *d* and back:

    d        max |error|    relative to the peak line integral
    1.00 px   0.0e+00        0.0e+00     (an integer shift is exact)
    0.50 px   1.4e-01        1.2e-01
    0.25 px   1.1e-01        9.2e-02

A *fractional* shift is **not** a small operation and this is the operator's
honest limitation: 12 % of the peak, on a phantom with sharp edges, from one
round trip. Interpolation is a low-pass filter and the sinogram of an edge is
not band-limited, so there is nothing to recover on the way back. Using a
Fourier shift instead would trade this visible blur for invisible ringing at
the detector edges, which is worse in the way that matters here. The
consequence is in :func:`sinogram_center_of_rotation`'s table: an integer
centre error is fully repairable, a half-pixel one is not.

:param sinogram: ``(n_angles, n_detectors)``.
:param shift_px: axis offset in detector bins; ``None`` -> measure it.
:param angles_deg: view angles, used only when *shift_px* is ``None``.
:returns: ``(n_angles, n_detectors)`` float64 sinogram.
:raises ValueError: if ``|shift_px|`` is at or past half the detector width —
    past that the object has been shifted out of the field of view and what
    comes back is edge padding, which reconstructs as a plausible, empty slice.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](../artifact/beam_hardening_apply.md) · [beam_hardening_correct](../artifact/beam_hardening_correct.md) · [ring_artifact_apply](../artifact/ring_artifact_apply.md) · [ring_artifact_remove](../artifact/ring_artifact_remove.md) · [metal_trace_interpolate](../artifact/metal_trace_interpolate.md)

## 同カテゴリ(`geometry`)

[sinogram_center_of_rotation](sinogram_center_of_rotation.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
