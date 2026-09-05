---
op: ellipse_sinogram
dim: tomography
category: forward
in: 
out: sinogram
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# ellipse_sinogram — TOMOGRAPHY `forward` op

- **データ種**: `なし` → `sinogram`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import tomography; tomography.ellipse_sinogram(size=256, ellipses=None, angles_deg=None, n_detectors=None)` (または `opstomography.get("ellipse_sinogram")`)

## 使い方

The **closed-form** Radon transform of a sum of uniform ellipses.

The ground truth this module is tested against, and a usable operator in its
own right: a sinogram with no discretisation error to feed a reconstruction,
so that any error in the picture belongs to the reconstruction and not to the
projector.

For one ellipse with centre ``(x0, y0)``, semi-axes ``(a, b)``, rotation
``phi`` and density ``rho``, the line integral along ``x cos(t) + y sin(t) =
s`` is::

    A(t)^2 = a^2 cos^2(t - phi) + b^2 sin^2(t - phi)
    s'     = s - (x0 cos t + y0 sin t)
    p      = 2 rho a b sqrt(A^2 - s'^2) / A^2      for |s'| < A,  else 0

which for a disc (``a = b = r``, ``rho = 1``) collapses to the chord length
``2 sqrt(r^2 - s^2)``. Densities add, so a sum of ellipses projects to a sum
of these.

The result is in the **same pixel units** as :func:`radon_transform` applied
to :func:`ellipse_phantom` at the same *size*: the normalised half-width is
``size/2`` pixels, and a line integral scales with length, so the closed form
is multiplied by ``size/2``. Getting that factor wrong is invisible in the
picture — a sinogram has no absolute scale — and shows up only as a
reconstruction whose density is off by a constant, which is why it is pinned
by a test rather than by a comment.

:param size: the pixel grid the units refer to (as in :func:`ellipse_phantom`).
:param ellipses: as :func:`ellipse_phantom`; ``None`` -> :data:`SHEPP_LOGAN`.
:param angles_deg: view angles; ``None`` -> ``linspace(0, 180, 180,
    endpoint=False)``.
:param n_detectors: detector bins; ``None`` -> enough to cover the diagonal.
:returns: ``(n_angles, n_detectors)`` float64 sinogram.
:raises ValueError: on a degenerate ellipse or a sinogram over
    :data:`MAX_SINOGRAM_ELEMENTS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](../artifact/beam_hardening_apply.md) · [beam_hardening_correct](../artifact/beam_hardening_correct.md) · [ring_artifact_apply](../artifact/ring_artifact_apply.md) · [ring_artifact_remove](../artifact/ring_artifact_remove.md) · [metal_trace_interpolate](../artifact/metal_trace_interpolate.md)

## 同カテゴリ(`forward`)

[ellipse_phantom](ellipse_phantom.md) · [radon_transform](radon_transform.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
