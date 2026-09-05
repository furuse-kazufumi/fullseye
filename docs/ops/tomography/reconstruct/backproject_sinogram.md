---
op: backproject_sinogram
dim: tomography
category: reconstruct
in: sinogram
out: image2d
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# backproject_sinogram — TOMOGRAPHY `reconstruct` op

- **データ種**: `sinogram` → `image2d`
- **呼び出し**: `import tomography; tomography.backproject_sinogram(sinogram, angles_deg=None, size=None, span_deg=None)` (または `opstomography.get("backproject_sinogram")`)

## 使い方

Plain, **un-filtered** back-projection — the blurred baseline.

Smear each projection back along the rays it came from and sum. The result is
the true slice convolved with ``1/|r|``, so it is correct in the large and
wrong everywhere in detail.

Two numbers, because only one of them is the interesting one. Raw, on the
Shepp-Logan phantom with 180 views, this operator's values run 0.768 to 2.493
where the truth runs 0.0 to 0.0167 — the ``1/|r|`` kernel has no finite
integral, so an un-filtered back-projection has **no meaningful absolute
scale at all** and its normalised RMS error against the truth is 104. After
the best least-squares rescaling onto the truth — which is what any display
with an auto window does for you, silently — the error is **0.168** against
**0.0246** for :func:`filtered_backprojection`, a factor of **6.8**. That
second number is the ramp filter's real contribution; the first is a warning
that a picture which looks approximately right after auto-windowing can be
off by a factor of 100 in the numbers underneath it.

It is a registered operator and not a private helper because the blur *is* the
lesson, and because it is the correct starting point for iterative methods.

Not to be confused with :func:`fullseye.backproject`, which lifts pixels into
3-D using a depth map and a camera model; that one is projective geometry, this
one is an integral transform, and the only thing they share is a word.

:param sinogram: ``(n_angles, n_detectors)``, rows = angles.
:param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
:param size: output side; ``None`` -> the inscribed square, ``n_det/sqrt2``
    rounded down to an odd number.
:param span_deg: angular range used for the ``d(theta)`` weight; ``None`` ->
    inferred from *angles_deg* (or 180 for the default scan).
:returns: ``(size, size)`` float64 image.
:raises ValueError: as :func:`filtered_backprojection`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[radon_transform](../forward/radon_transform.md)

## 同カテゴリ(`reconstruct`)

[filtered_backprojection](filtered_backprojection.md) · [sart_reconstruct](sart_reconstruct.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
