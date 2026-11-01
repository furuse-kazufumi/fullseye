---
op: polarization_stokes_map
dim: specular
category: polarization
in: polsweep
out: table
gpu: なし
examples: [polarization_camera_pipeline]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# polarization_stokes_map — SPECULAR `polarization` op

- **データ種**: `polsweep` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.polarization_stokes_map(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)` (実装を直接呼ぶなら `import specularity; specularity.polarization_stokes_map(images, angles_deg=(0.0, 45.0, 90.0, 135.0), max_violation_frac=0.0)`、台帳から引くなら `opsspecular.get("polarization_stokes_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Per-pixel linear Stokes images with DoLP and AoLP maps from an analyser sweep (4 DoFP angles or any N >= 3, least squares). → dict of (H, W) maps.

:func:`polarization_stokes` answers for the whole field (a spatial mean);
this is the same fit kept **per pixel**:
``I(t) = 0.5 (S0 + S1 cos 2t + S2 sin 2t)`` solved for every pixel —
in closed form for the four angles 0/45/90/135 of a division-of-focal-plane
sensor (``S0 = (I0 + I45 + I90 + I135)/2``, ``S1 = I0 - I90``,
``S2 = I45 - I135``, the least-squares solution for that design), and by
least squares for any other set of N >= 3 analyser angles.

Returns a dict:

* ``s0``, ``s1``, ``s2`` — ``(H, W)`` linear Stokes images. Stack them with
  a zero ``S3`` (``np.stack([s0, s1, s2, 0 * s0], -1)``) and they feed
  :func:`optics.mueller_apply`'s field form directly.
* ``dolp`` — ``sqrt(S1^2 + S2^2) / S0`` in ``[0, 1]``.
* ``aolp_deg`` — ``0.5 * atan2(S2, S1)`` in degrees, mapped into
  ``[0, 180)`` (an axis, so 0 and 180 are the same).
* ``lit`` — bool, ``S0 > 0``.
* ``aolp_defined`` — bool, ``S0 > 0`` and ``hypot(S1, S2) > 1e-12 * S0``.
* ``residual`` — RMS over the N frames of ``frame - fitted Malus curve``,
  in the frames' units (added 2026-10-24). A sweep of a real scene fits
  exactly, so a large value says the frames do not agree with each other:
  a misregistered or saturated channel. For the four DoFP angles it is
  ``|I0 + I90 - I45 - I135| / 4``; for three angles it is always 0 (the
  fit is exact and nothing is left to check).

**Where the ratios do not exist, the value is 0 and a mask says so — never
NaN.** At ``S0 = 0`` DoLP is 0/0: it is returned as 0.0, the same
convention :func:`polarization_dolp_map` states, with ``lit`` False. Where
the linear part is zero (unpolarised light, or no light) AoLP has no
orientation: ``aolp_deg`` is 0.0 there and ``aolp_defined`` is False.
"Zero" is relative — ``hypot(S1, S2) <= 1e-12 * S0`` — because the fit
leaves rounding dust: a uniform unpolarised sweep fits DoLP ~3e-16 at
every scale from 1e-6 to 1e9 (measured), and with an exact-zero test
400/400 such pixels reported an "angle" that was pure rounding. DoLP itself
is returned as fitted (that 3e-16 is an honest number).
Use the masks before thresholding or averaging angles; a 0 in
``aolp_deg`` is not a measurement of 0 degrees.

**Angles.** *angles_deg* and the returned AoLP use the library convention:
from +x (along a row) toward +y (down the rows), clockwise on a displayed
image (see ``_DEFAULT_ANGLES`` in this module and the polarisation section
of :mod:`optics`). A synthetic sweep made with
``optics.mueller_element("polarizer", t)`` of a beam at 21.5 degrees comes
back as 21.5; the same frames labelled with negated angles come back as
158.5 — the test file pins both.

**Physicality.** The fit refuses sweeps whose fitted minimum is negative
(as :func:`polarization_separate`, controlled by *max_violation_frac*).
When that clamp is allowed, a pixel can fit ``hypot(S1, S2) > S0``; its
``(S1, S2)`` is then scaled back onto ``S0`` (as
:func:`polarization_stokes` does for the mean) and a negative ``S0`` is
set to 0, so every returned pixel is a physical Stokes vector. With the
default ``max_violation_frac=0`` that only touches rounding-level
excesses.

Ground truth (closed form, in ``tests/test_polarization_per_pixel_2026_10_23.py``):
unpolarised light through an ideal polariser → DoLP 1 and AoLP = the
polariser angle, per pixel, for a whole field of different angles; through
:func:`optics.mueller_partial_polarizer` → DoLP ``(ER - 1)/(ER + 1)``;
Malus's law frames rebuilt from the returned ``S0, S1, S2`` reproduce the
input frames; the spatial mean of ``s0, s1, s2`` equals
:func:`polarization_stokes` (no clamp in play).

S3 is not returned: linear analysers cannot measure it (see
:func:`polarization_stokes`).

**Raises** ``ValueError``: as :func:`polarization_separate` — *images* is
not an ``(N, H, W)`` stack with N >= 3, exceeds the caps, or is
non-finite; *angles_deg* does not match N or leaves the fit
rank-deficient; more than *max_violation_frac* of the pixels fit a negative
minimum. Also (2026-10-24): *images* has no pixels; *angles_deg* is
ill-conditioned or looks like radians; a frame value below the negative
floor counts as a violating pixel.

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [polarization_camera_pipeline](../../../../examples/polarization_camera_pipeline.py) — `py -3.11 examples/polarization_camera_pipeline.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`polarization`)

[polarization_render](polarization_render.md) · [polarization_separate](polarization_separate.md) · [polarization_dolp_map](polarization_dolp_map.md) · [polarization_stokes](polarization_stokes.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
