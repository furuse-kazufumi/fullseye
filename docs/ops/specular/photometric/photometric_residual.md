---
op: photometric_residual
dim: specular
category: photometric
in: images
out: image2d
examples: [specular_photometric]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# photometric_residual — SPECULAR `photometric` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import specularity; specularity.photometric_residual(images, lights, normals=None, albedo=None, normalize=True)` (または `opsspecular.get("photometric_residual")`)

## 使い方

How badly the Lambertian model fails, per pixel. → (H, W) RMS residual.

``sqrt(mean_n (albedo * (n.L_n) - I_n)^2)`` — the root-mean-square
disagreement between the linear model and the measurements, in the units of
the input radiance. On a synthetic Lambertian surface with the true
float64 normals and albedo supplied it measures 1.4e-16 at worst; with them
omitted the floor rises to 4.5e-08, because
:func:`photometric.photometric_stereo` returns float32 and that is its
precision, not a modelling error (supplying the *same* truth cast to
float32 reproduces 4.5e-08 exactly). It is large where the assumption
actually broke: 0.50 at worst on the same scene with 3 of 8 lights blocked
by a cast shadow — fifteen orders of magnitude above the clean floor. All
four numbers measured in ``tests/test_specularity.py``.

This is the diagnostic that tells you *whether* you need
:func:`photometric_stereo_robust` before you reach for it, and it is the
map an inspection routine thresholds to find glossy defects.

With *normals* and *albedo* omitted it solves them first with
:func:`photometric.photometric_stereo` and reports the residual of that fit
— the honest self-assessment of the plain estimator. Pass them to score an
estimate that came from somewhere else (a robust fit, a CAD model, a
previous frame).

Note the residual uses ``n.L`` **without** the ``max(., 0)`` clamp, because
that is the linear system the solver actually inverted; a pixel in attached
shadow therefore shows a residual, which is the intended signal rather than
an artefact.

**Raises** ``ValueError``: *images* / *lights* problems as in
:func:`photometric_stereo_robust`; *normals* is not ``(H, W, 3)`` matching
the images; *albedo* is not ``(H, W)``; exactly one of *normals* / *albedo*
is given (the pair is meaningless apart — the model is ``albedo * n``).

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [specular_photometric](../../../../examples/specular_photometric.py) — `py -3.11 examples/specular_photometric.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[polarization_render](../polarization/polarization_render.md)

## 同カテゴリ(`photometric`)

[photometric_stereo_robust](photometric_stereo_robust.md)

---
*Provenance: specularity.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
