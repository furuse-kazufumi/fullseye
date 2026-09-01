---
op: photon_sample
dim: photon
category: counting
in: image2d
out: image2d
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# photon_sample — PHOTON `counting` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import photoncount; photoncount.photon_sample(image, photons_per_unit=100.0, dark_rate=0.0, seed=0)` (または `opsphoton.get("photon_sample")`)

## 使い方

Poisson-sample an expected-photon image into an actual photon count image.

*image* is a non-negative 2-D map of scene radiance in arbitrary units;
``lambda = image * photons_per_unit + dark_rate`` is the expected number of
photons in each pixel over the exposure, and the result is one Poisson
realisation of it. *dark_rate* is the dark-count contribution (a SPAD counts
thermally generated carriers even in the dark) in the same photon units.

Returns the **counts themselves** as a float64 ``(H, W)`` image (integer
valued). That is the deliberate difference from
:func:`backends_aug.aug_shot_noise`, which returns ``Poisson(v*K)/K`` clipped
to ``[0, 1]`` for training-data augmentation: every operator downstream here
(Fano factor, Anscombe, Coates, dToF) needs ``N``, and the rescale-and-clip
is not invertible.

``seed`` is a required non-negative integer and the RNG is
``numpy.random.default_rng(seed)`` — same seed, same frame, on any machine.

Ground truth it reproduces (pinned in ``tests/test_photoncount.py``): the
sample mean and sample variance both converge to ``lambda``. Measured on a
flat ``lambda = 100`` field of 512x512 pixels at seed 0 — mean 99.9796,
Fano factor 1.001089, so the photon-limited SNR is ``sqrt(lambda)``: 9.9990
predicted from the mean, 9.9935 actually achieved.

**Raises** ``ValueError``: negative or non-finite *image*, negative
*photons_per_unit* / *dark_rate*, a non-integer or negative *seed*, an image
over :data:`MAX_IMAGE_ELEMENTS`, and — instead of letting numpy fail deep
inside the sampler — any ``lambda`` over :data:`MAX_LAMBDA`.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[photon_statistics](photon_statistics.md) · [photon_uncertainty](photon_uncertainty.md) · [anscombe_transform](../transform/anscombe_transform.md) · [anscombe_inverse](../transform/anscombe_inverse.md)

## 同カテゴリ(`counting`)

[photon_statistics](photon_statistics.md) · [photon_uncertainty](photon_uncertainty.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
