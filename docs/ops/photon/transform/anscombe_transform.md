---
op: anscombe_transform
dim: photon
category: transform
in: image2d
out: image2d
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# anscombe_transform — PHOTON `transform` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import photoncount; photoncount.anscombe_transform(image, gain=1.0, read_sigma=0.0, offset=0.0, clip=False)` (または `opsphoton.get("anscombe_transform")`)

## 使い方

Anscombe variance-stabilising transform: Poisson counts -> ~unit-variance.

Photon-limited data has signal-dependent noise, which every classical
denoiser (Gaussian, bilateral, NLM, wavelet, BM3D) assumes away. The Anscombe
transform ``A(x) = 2*sqrt(x + 3/8)`` makes the variance approximately 1
*independently of the signal*, so the standard route is transform -> denoise
with a unit-sigma Gaussian denoiser -> :func:`anscombe_inverse`.

The **generalised** form (Starck/Murtagh/Bijaoui) also absorbs the sensor's
analogue chain, and takes exactly the parameters
:func:`backends_aug.aug_read_noise` injects::

    A(x) = (2/g) * sqrt(g*(x - offset) + (3/8)*g^2 + sigma_r^2)

with *gain* ``g`` in ADU per photon, *read_sigma* the Gaussian read noise in
ADU and *offset* the black level in ADU. The defaults ``g=1, sigma_r=0,
offset=0`` reduce it to the classical form exactly.

Measured stabilisation — ``var(A(X))`` for ``X ~ Poisson(lambda)``, computed
**exactly** by summing the Poisson pmf (no sampling, so anyone can reproduce
these; ``tests/test_photoncount.py`` pins them and the sampled versions):

========  ========
lambda    var(A)
========  ========
1         0.717443
2         0.924297
4         0.998754
10        1.000910
100       1.000006
========  ========

So "variance 1" is true from about 4 photons/pixel upward and **false below
it** — at 1 photon/pixel the variance is 0.717, a 28% shortfall, which is
the honest statement of the transform's low-count limit. Below a few photons
an exact Poisson method (or the exact unbiased inverse, see
:func:`anscombe_inverse`) is required.

**It does not help a linear smoother, and the tests say so.** Measured on a
two-level scene (4 and 64 photons/pixel, seed 5): a plain Gaussian filter
applied to the raw counts reaches RMSE 2.387, and the same filter through
the Anscombe route reaches 2.459 — i.e. *slightly worse*. That is expected:
averaging is already the right thing to do to Poisson counts, so stabilising
the variance first buys nothing. The transform pays off for denoisers whose
**parameter is an absolute noise scale** — thresholds, sigma filters,
wavelet shrinkage, NLM, BM3D — because that parameter becomes one constant
instead of a per-pixel function. Measured with a 5x5 sigma filter at a
3-sigma threshold on that same scene: 1.191 through the transform against
2.307 in the raw domain using the same 3-sigma rule with a globally
estimated sigma. (An *oracle* raw threshold, swept against ground truth one
does not have in practice, reaches 1.080 — so the honest headline is
"one principled constant instead of a tuned guess", not "always better".)

Returns a float64 array of the same shape as *image*.

**Raises** ``ValueError``: non-finite *image*, non-positive *gain*, negative
*read_sigma*, and — unless ``clip=True`` — any pixel whose argument under the
square root is negative (which can happen for real read-noise data dipping
below the black level). ``clip=True`` floors the argument at 0 and is the
documented, opt-in behaviour; the default refuses rather than quietly
manufacturing a value.

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[photon_sample](../counting/photon_sample.md) · [photon_statistics](../counting/photon_statistics.md) · [photon_uncertainty](../counting/photon_uncertainty.md) · [anscombe_inverse](anscombe_inverse.md)

## 同カテゴリ(`transform`)

[anscombe_inverse](anscombe_inverse.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
