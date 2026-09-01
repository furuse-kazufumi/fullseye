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
  4    70.52 deg  70.52 deg    70.20 deg
  ==== ========== ============ ============

  0.00011 degrees is not "almost right", it is **the floor**: the returned
  normals are float32 (:mod:`photometric`'s convention), and casting the
  exact normals to float32 and back measures the same 0.000115 degrees.
  The ``k = 4`` row is the breakdown point and it is in the table rather
  than omitted — with half the lights blocked, the four zeroed measurements
  are themselves a perfectly consistent "black surface" model, so no
  consensus rule can prefer the true one.
* ``"ransac"`` — Fischler-Bolles maximum consensus. Every 3-light subset is
  solved exactly, residuals are counted against *threshold*, and the subset
  with the largest consensus wins per pixel; the normal is then refitted by
  least squares on that consensus set. Tolerates up to ``N - 3`` bad lights
  if the good ones agree.
* ``"median"`` — Rousseeuw's least median of squares. The subset minimising
  the median residual wins. Needs **more than half** the lights to be good,
  and needs no threshold at all — use it when the outlier magnitude is
  unknown.

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
``(N, H, W)`` bool — **which lights were believed at which pixel**. Pixels
with fewer than *min_inliers* believed lights keep the winning subset's
solution and are visible as a thin inlier count in that mask; that is the
honest signal that the normal there rests on the minimum three
measurements.

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
