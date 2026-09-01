---
op: photometric_stereo_robust
dim: specular
category: photometric
in: images
out: normalmap
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# photometric_stereo_robust — SPECULAR `photometric` op

- **データ種**: `images` → `normalmap`
- **呼び出し**: `import specularity; specularity.photometric_stereo_robust(images, lights, method='ransac', threshold=0.05, max_subsets=512, normalize=True, seed=0, min_inliers=3)` (または `opsspecular.get("photometric_stereo_robust")`)

## 使い方

Photometric stereo that survives shadows and highlights. → (normals, albedo, inliers).

Woodham's (1980) linear model ``I_n = albedo * max(n.L_n, 0)`` is exact only
where every light reaches the pixel and the surface is Lambertian. A cast
shadow zeroes one measurement, a highlight inflates another, and least
squares spreads the error over the whole normal — the estimate does not
fail, it **tilts**, which is worse. This operator solves the three-light
system exactly on subsets and keeps the subset the data agrees with.

*method*:

* ``"lstsq"`` — the plain least-squares solution, delegated to
  :func:`photometric.photometric_stereo`. Present so the non-robust baseline
  is available through the same call and its failure is a measurement rather
  than a claim. On a Gaussian bump lit by 8 lights, with ``k`` of them
  blocked by a cast shadow, the mean angular error is (all measured in
  ``tests/test_specularity.py``):

  ==== ========== ============ ============
  k    ``lstsq``  ``median``   ``ransac``
  ==== ========== ============ ============
  1    31.70 deg  0.00011 deg  0.00011 deg
  2    53.11 deg  0.00011 deg  0.00011 deg
  3    64.40 deg  0.00011 deg  0.00011 deg
  4    70.52 deg  0.00011 deg  0.00011 deg
  5    ---        **NaN**      0.00011 deg
  6    ---        **NaN**      **NaN**
  ==== ========== ============ ============

  0.00011 degrees is not "almost right", it is **the floor**: the returned
  normals are float32 (:mod:`photometric`'s convention), and casting the
  exact normals to float32 and back measures the same 0.000115 degrees.
  ``NaN`` means *this pixel is not solvable from what was believed there* —
  see "unsolvable pixels" below.
* ``"ransac"`` — Fischler-Bolles maximum consensus. Every 3-light subset is
  solved exactly, residuals are counted against *threshold*, and the subset
  with the largest consensus wins per pixel; the normal is then refitted by
  least squares on that consensus set. Tolerates up to ``N - 3`` blocked
  lights if the survivors agree — at ``k = 5`` of 8 exactly three lights are
  left and the answer is still exact.
* ``"median"`` — Rousseeuw's least median of squares. The subset minimising
  the median residual wins. Needs **more than half** the lights to be good,
  and needs no threshold at all — use it when the outlier magnitude is
  unknown. Its 50 % breakdown point is why the ``k = 5`` and ``k = 6`` rows
  are NaN rather than wrong: past half, its winning subset is one that
  believes nothing, and that is reported as "not solved".

**A measurement of zero is not evidence.** Woodham's model is
``I = albedo * max(n.L, 0)``, so a shadowed measurement of zero states
``n.L <= 0`` — an *inequality*. The linear solve reads it as the equation
``n.L = 0``, which is a different and stronger claim, and ``g = 0``
reproduces every zeroed frame exactly. A set of blocked lights is therefore
a perfectly self-consistent "black surface" hypothesis that can outscore the
truth. Found by adversarial audit, and it did not raise anything:

=====  ================  =====================  ==============================
k of 8  before, ``median``  inlier mask said     what was actually true
=====  ================  =====================  ==============================
4      70.52 deg wrong   **8 of 8 believed**    4 of the 8 frames were zero
5      8.99 deg          5 believed             the 5 believed were the *zeros*
6      8.99 deg          6 believed             the 6 believed were the *zeros*
=====  ================  =====================  ==============================

The ``k = 4`` row is the one to look at: at the worst estimate the diagnostic
reported a clean bill of health. The ``k = 5`` / ``k = 6`` rows are worse
than they look — 8.99 degrees is not a near miss, it is the degenerate
``albedo = 0`` solution falling back to ``(0, 0, 1)``, which happens to be
close on a shallow bump and would be arbitrary on any other surface, and the
mask named the zeroed lights as the believed ones.

So a light is believed at a pixel only when **the fit explains its
measurement to within the method's tolerance and its measurement is farther
from zero than that same tolerance** — the same tolerance in both clauses,
whichever tolerance the method uses (``threshold * peak`` for ``"ransac"``,
``max(2.5 sigma, 1e-9 * peak)`` for ``"median"``). Counting a measurement
that is itself inside the tolerance of zero is counting a tautology, since
zero albedo predicts it under *every* normal. The rule is exact, not
heuristic: on a scene with one light at grazing incidence the believed mask
equals ``I_n > threshold * peak`` pixel for pixel (verified by array
equality, 40x40, believed at 93.2 % of pixels, error 0.00011 deg).

That single change also repairs the estimates, because the zeroed frames
stop winning the consensus: ``k = 4`` goes from 70.52 to 0.00011 degrees for
both methods, and ``ransac`` at ``k = 5`` from 8.99 degrees to 0.00011. It
does **not** repair a general outlier, and is not claimed to — a highlight
is positive and the zero test cannot see it. Measured with ``j`` of 8 frames
given a ``+3.0`` additive spike, the true 50 % breakdown is unchanged and
still disclosed:

==== ============ ============
j    ``median``   ``ransac``
==== ============ ============
1    0.00011 deg  0.00011 deg
2    0.00011 deg  0.00011 deg
3    0.00011 deg  0.00011 deg
4    7.42 deg     65.42 deg
==== ============ ============

**The error is not monotone in the number of blocked lights, and never was.**
Before the repair the sequence over ``k = 0..6`` for ``"median"`` ran
0.00011, 0.00011, 0.00011, 0.00011, **70.52**, 8.99, 8.99 — the worst value
sits in the middle. That is the median's 50 % breakdown point, not a bug: at
``k = 4`` the two hypotheses have equal support and the wrong one is picked
at full confidence, while at ``k = 5, 6`` the "black surface" wins outright
and the degenerate ``(0, 0, 1)`` fallback happens to be near the truth on a
shallow surface. Do not read a small error at large ``k`` as recovery.

*threshold* is **relative to the brightest measurement at that pixel**, so
the decision is invariant to exposure: scaling every image by 1e-3, 1e3 or
1e6 returns a **bit-identical inlier mask** and normals that differ by at
most 0.000115 degrees — the float32 output floor again, not an exposure
effect. The word "bit-identical" applies to the mask and not to the normals,
because the arithmetic downstream of the identical decision still rounds
differently at a different scale.

Enumeration is exhaustive and therefore deterministic whenever
``C(N, 3) <= max_subsets``; *seed* only matters past that point, and the
regime is not hidden — a subset count above :data:`MAX_SUBSETS`, a pixel
count above :data:`MAX_ROBUST_PIXELS` or a total work product above
:data:`MAX_ROBUST_WORK` all raise instead of running for an hour.

Returns ``(normals, albedo, inliers)``: ``normals`` ``(H, W, 3)`` float32
unit vectors in :mod:`photometric`'s convention (``(0, 0, 1)`` where the
albedo is degenerate), ``albedo`` ``(H, W)`` float32, and ``inliers``
``(N, H, W)`` bool — **which lights were believed at which pixel**, after
the zero test above, so a blocked light is never named as believed.

**Unsolvable pixels are ``NaN``.** Three unknowns need three independent
equations; a pixel whose believed lights number fewer than *min_inliers*
(default and minimum 3), or whose believed directions are coplanar so the
3x3 normal matrix is singular, gets ``NaN`` in both *normals* and *albedo*.
It used to keep the winning 3-light subset's solution instead, which is how
an underdetermined pixel came back as a confident 1.3-degree answer: the
minimum-norm solution of 3 unknowns in 2 equations is near the truth only
when the surface happens to be nearly flat. The two arrays therefore agree
with the mask by construction — ``numpy.isnan(albedo)`` is exactly
``inliers.sum(axis=0) < min_inliers`` plus the singular pixels — and a
caller that never checks will get ``NaN`` propagating rather than a
plausible number. ``method="lstsq"`` is exempt: it is the deliberately
non-robust baseline, it uses every light at every pixel, and its all-true
mask says exactly that.

**Raises** ``ValueError``: *images* is not an ``(N, H, W)`` stack or exceeds
:data:`MAX_LIGHTS` / :data:`MAX_STACK_ELEMENTS` / :data:`MAX_ROBUST_PIXELS`;
*lights* is not ``(N, 3)`` matching the frames or contains a zero-length
direction; fewer than 3 lights; *method* not in :data:`ROBUST_METHODS`;
*threshold* not positive; the work product exceeds
:data:`MAX_ROBUST_WORK`; every 3-light subset is singular (all light
directions coplanar through the origin, which no amount of robustness can
repair).

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[brdf_blinn_phong](../reflectance/brdf_blinn_phong.md) · [brdf_microfacet](../reflectance/brdf_microfacet.md) · [dichromatic_render](../reflectance/dichromatic_render.md)

## 同カテゴリ(`photometric`)

[photometric_residual](photometric_residual.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
