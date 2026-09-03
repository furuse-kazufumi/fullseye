---
op: sinogram_center_of_rotation
dim: tomography
category: geometry
in: sinogram
out: measurement
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# sinogram_center_of_rotation — TOMOGRAPHY `geometry` op

- **データ種**: `sinogram` → `measurement`
- **呼び出し**: `import tomography; tomography.sinogram_center_of_rotation(sinogram, angles_deg=None, min_condition=0.02)` (または `opstomography.get("sinogram_center_of_rotation")`)

## 使い方

Where the axis of rotation actually is, in detector bins from the centre.

The centre-of-mass identity, which is exact and needs no reconstruction: the
first moment of a projection is the projection of the object's centre of
mass, so::

    s_cm(theta) = x0 cos(theta) + y0 sin(theta) + c

with ``(x0, y0)`` the centre of mass in the slice and ``c`` the offset of the
rotation axis from the detector centre. Fitting the three unknowns by least
squares over all views gives *c* directly. Measured on the Shepp-Logan
phantom with 180 views, recovering a deliberately introduced shift, together
with the cost of not correcting it (normalised RMS error of the FBP
reconstruction against the truth):

    true shift   estimated    error     uncorrected   after this fix
      0.00 px    +0.0029 px   0.0029      0.0250          0.0249
      0.50 px    +0.5029 px   0.0029      0.0537          0.0358
      1.00 px    +1.0029 px   0.0029      0.1016          0.0249
      2.00 px    +2.0029 px   0.0029      0.1630          0.0249

Three things in that table are worth reading twice. **Half a pixel already
doubles the error** (0.0250 -> 0.0537) and does not look like a mistake — it
looks like a slightly soft reconstruction, which is why this is a measurement
and not an inspection. The estimator's own bias is a **constant 0.0029 px**
across every shift, so it is a property of the phantom and the detector
sampling, not of the size of the error being measured. And the half-pixel row
is the only one the fix does not fully repair (0.0358 against 0.0249),
because correcting a *fractional* shift means resampling, and the linear
interpolation costs more than the integer shifts do — see
:func:`sinogram_center_shift`.

Two things this needs, both refused rather than assumed. The object must be
**entirely inside the field of view** — the identity is about the whole mass,
and a truncated object has a different mass at every angle. And the views must
span enough angle for ``[cos, sin, 1]`` to be independent: over a narrow
wedge, ``cos(theta)`` and the constant are nearly the same vector and the fit
puts the object's own offset into *c*. The condition number is checked and a
degenerate design is refused.

:param sinogram: ``(n_angles, n_detectors)``, rows = angles.
:param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
:param min_condition: smallest acceptable reciprocal condition number of the
    ``[cos, sin, 1]`` design matrix. The default of **0.02** is calibrated,
    not chosen — the reciprocal condition number and the error it lets
    through, on a sinogram with a true 1.00-px shift:

        span      rcond      estimate    error
        180 deg   2.15e-01   +0.9939     0.0061 px
        120 deg   8.92e-02   +0.9900     0.0100 px
         90 deg   4.85e-02   +0.9485     0.0515 px
         60 deg   2.09e-02   +0.8993     0.1007 px   <- the default admits this
         45 deg   1.17e-02   +0.7041     0.2959 px   <- and refuses this
         20 deg   2.26e-03   +1.7113     0.7113 px
         10 deg   5.54e-04   -6.9765     7.9765 px

    The 10-degree row is why the check exists at all: the answer is finite,
    the sign is wrong, and the magnitude is eight pixels on a one-pixel
    error. Nothing about it looks like a failure.
:returns: ``float`` — the axis offset in detector bins, positive towards
    higher bin indices.
:raises ValueError: on a sinogram whose total mass is zero, on fewer than 3
    views, or on an angular span too narrow to separate the offset from the
    object's own position.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`geometry`)

[sinogram_center_shift](sinogram_center_shift.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
