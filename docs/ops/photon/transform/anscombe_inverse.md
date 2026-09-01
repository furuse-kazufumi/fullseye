---
op: anscombe_inverse
dim: photon
category: transform
in: image2d
out: image2d
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# anscombe_inverse — PHOTON `transform` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import photoncount; photoncount.anscombe_inverse(values, gain=1.0, read_sigma=0.0, offset=0.0, mode='algebraic')` (または `opsphoton.get("anscombe_inverse")`)

## 使い方

Invert :func:`anscombe_transform` — algebraically, or without bias.

``mode="algebraic"`` is the exact algebraic inverse of
:func:`anscombe_transform`::

    x = ((g*A/2)^2 - (3/8)*g^2 - sigma_r^2)/g + offset

so ``anscombe_inverse(anscombe_transform(x)) == x`` to machine precision
(measured over 100001 values of ``x`` spanning ``[0, 1e4]``: max absolute
error 2.7e-12, max relative error 3.7e-16 for ``x > 1``). It is, however,
**biased**: ``E[A(X)] != A(E[X])``, so applying it to a *denoised* (i.e.
averaged) Anscombe image underestimates the intensity.

``mode="unbiased"`` is the closed-form exact unbiased inverse of Makitalo &
Foi (IEEE TIP 2011)::

    x = D^2/4 + (1/4)*sqrt(3/2)/D - (11/8)/D^2 + (5/8)*sqrt(3/2)/D^3 - 1/8

which is defined for the **classical** transform only (``gain=1``,
``read_sigma=0``, ``offset=0``) — passing generalised parameters with this
mode raises rather than returning a formula that does not apply.

Measured bias — apply the inverse to the *ideal denoised* value
``D = E[A(X)]``, ``X ~ Poisson(lambda)``, and compare with ``lambda``. Both
computed **exactly** from the Poisson pmf (no sampling):

========  ==================  ==================
lambda    algebraic bias      unbiased bias
========  ==================  ==================
1         -0.179361           -0.003668
2         -0.231074           -0.006374
4         -0.249688           +0.003779
10        -0.250227           +0.016904
30        -0.250019           +0.017041
100       -0.250002           +0.011960
========  ==================  ==================

The algebraic inverse converges to a **constant -1/4 photon** offset, which
at 1 photon/pixel is a 18% error; the closed form keeps the worst case to
0.017 photons (a 49x reduction at ``lambda = 1``, 15x at its own worst point
near ``lambda = 10-30``). It is a closed-form *approximation* of the exact
unbiased inverse, so it is not bias-free — those +0.017 are the honest
residual, not round-off.

The result is clipped at 0 — stated here rather than done quietly — but the
clip essentially never fires: the closed form's positive root is
**exactly** ``A(0) = 2*sqrt(3/8) = 1.2247448714`` (measured: the root and
``A(0)`` agree to 0.0), which is also the smallest value
:func:`anscombe_transform` can produce, so over the whole valid domain the
formula is non-negative to round-off (measured minimum -1.11e-16 over
``D`` in ``[A(0), 6]`` on 500001 samples). Below ``A(0)`` it does go
genuinely negative (-0.0217 at ``D = 1.20``), which is why values there are
refused outright rather than clipped.

Returns a float64 array of the same shape as *values*.

**Raises** ``ValueError``: non-finite *values*, an unknown *mode*, a
non-positive *gain*, a negative *read_sigma*, ``mode="unbiased"`` combined
with any non-default generalised parameter, and — instead of dividing by
zero — ``mode="unbiased"`` with any value ``<= 0`` (the ``1/D^3`` term).

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[photon_sample](../counting/photon_sample.md) · [photon_statistics](../counting/photon_statistics.md) · [photon_uncertainty](../counting/photon_uncertainty.md) · [anscombe_transform](anscombe_transform.md)

## 同カテゴリ(`transform`)

[anscombe_transform](anscombe_transform.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
