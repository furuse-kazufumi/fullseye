---
op: photon_uncertainty
dim: photon
category: counting
in: image2d
out: image2d
examples: [photon_timeresolved]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# photon_uncertainty — PHOTON `counting` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import photoncount; photoncount.photon_uncertainty(counts, relative=False, zero_floor=0.0)` (または `opsphoton.get("photon_uncertainty")`)

## 使い方

Per-pixel Poisson error bar of a photon-count frame.

For a Poisson variable the variance *equals* the mean, so the one-sigma
uncertainty of a single measurement ``N`` is ``sqrt(N)`` — no calibration, no
noise model to fit. With ``relative=True`` the returned map is the relative
uncertainty ``1/sqrt(N)`` instead (its reciprocal is the per-pixel SNR).

*zero_floor* replaces counts below it before the square root. It exists
because ``N = 0`` gives ``sqrt(0) = 0``, i.e. "this pixel is exactly zero
with no uncertainty", which is wrong: the 95% Poisson upper limit for a
single observed zero is about 3 photons. Set ``zero_floor=1.0`` for the
common "one-count prior" convention. It is **not** applied silently — the
default is 0.0 and the absolute map really does return 0 there.

Returns a float64 ``(H, W)`` image.

**Raises** ``ValueError``: negative, non-finite or non-2-D *counts*, a
negative *zero_floor*, and — instead of returning ``inf`` —
``relative=True`` with any pixel at 0 after the floor (that is the division
``1/sqrt(0)``; pass ``zero_floor > 0`` to say what a zero should mean).

## 詳しい使い方ガイド

- [photon_timeresolved ファミリ ガイド](../guides/photon_timeresolved.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photon_timeresolved](../../../../examples/photon_timeresolved.py) — `py -3.11 examples/photon_timeresolved.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[photon_sample](photon_sample.md) · [photon_statistics](photon_statistics.md) · [anscombe_transform](../transform/anscombe_transform.md) · [anscombe_inverse](../transform/anscombe_inverse.md)

## 同カテゴリ(`counting`)

[photon_sample](photon_sample.md) · [photon_statistics](photon_statistics.md)

---
*Provenance: photoncount.py — PHOTON operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
