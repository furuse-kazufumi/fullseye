---
op: sart_reconstruct
dim: tomography
category: reconstruct
in: sinogram
out: image2d
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# sart_reconstruct — TOMOGRAPHY `reconstruct` op

- **データ種**: `sinogram` → `image2d`
- **呼び出し**: `import tomography; tomography.sart_reconstruct(sinogram, angles_deg=None, size=None, n_iter=10, relaxation=0.3, initial=None, nonnegative=True)` (または `opstomography.get("sart_reconstruct")`)

## 使い方

SART — simultaneous algebraic reconstruction, one angle at a time.

An iterative solver for ``A x = p`` where ``A`` is the projector: for each
view in turn, project the current estimate, take the residual, and
back-project it with the row and column sums of ``A`` as normalisers::

    x <- x + lambda * BP_theta( (p_theta - FP_theta(x)) / rowsum_theta )
                      / colsum_theta

*rowsum* is the length of each ray through the grid and *colsum* is how many
rays touched each pixel, so the update is dimensionally a density and does not
depend on the grid size. One "iteration" is one pass over all views.

Why it exists next to :func:`filtered_backprojection`: FBP inverts an integral
transform and therefore *needs* the transform to have been sampled; SART
solves a linear system and merely does worse when the system is
underdetermined. Measured, it is better at every view count tested (the table
in :func:`filtered_backprojection`), by 1.43x at 180 views and 2.9x at 8.

The cost is honest and it is the reason this is not the default: 10 sweeps
over 180 views is 1800 forward *and* 1800 back-projections against FBP's 180
back-projections, measured at **37.7 s** against **0.12 s** for a 256-px
reconstruction — a factor of **312**. At 8 views it is 2.14 s against 0.01 s,
the same ratio applied to a much smaller number.

``nonnegative=True`` clips the estimate at zero after every sweep. Attenuation
coefficients cannot be negative, so this is a genuine constraint and not a
cosmetic clip, and it carries a large part of the advantage above — measured
on the analytic Shepp-Logan sinogram, normalised RMS with the constraint
against without:

    views     with     without
      180    0.0175    0.0300
       45    0.0353    0.0626
        8    0.1257    0.1428

so at 180 views the constraint alone is worth 1.7x, and it is the *only*
reason SART leads FBP there at all (FBP scores 0.0250, between the two).

:param sinogram: ``(n_angles, n_detectors)``, rows = angles.
:param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
:param size: output side; ``None`` -> the inscribed square.
:param n_iter: sweeps over the full angle set, ``1 .. 500``.
:param relaxation: step size ``lambda``, ``(0, 2)``. Over 1 the iteration can
    oscillate; over 2 it provably diverges, and is refused.
:param initial: starting estimate, ``(size, size)``; ``None`` -> zeros.
:param nonnegative: clip to ``>= 0`` after each sweep.
:returns: ``(size, size)`` float64 image.
:raises ValueError: as :func:`filtered_backprojection`, plus a relaxation
    outside ``(0, 2)`` and an *initial* whose shape is not ``(size, size)``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[radon_transform](../forward/radon_transform.md)

## 同カテゴリ(`reconstruct`)

[backproject_sinogram](backproject_sinogram.md) · [filtered_backprojection](filtered_backprojection.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
