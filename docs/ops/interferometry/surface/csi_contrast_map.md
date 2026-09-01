---
op: csi_contrast_map
dim: interferometry
category: surface
in: zscan
out: image2d
examples: [coherence_scanning]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# csi_contrast_map — INTERFEROMETRY `surface` op

- **データ種**: `zscan` → `image2d`
- **呼び出し**: `import interferometry; interferometry.csi_contrast_map(stack, remove_bias=True)` (または `opsinterferometry.get("csi_contrast_map")`)

## 使い方

Peak fringe modulation per pixel — the contrast (and validity) map.

The maximum of each pixel's coherence envelope. Three uses, in order of how
often they matter:

  1. **Validity.** A pixel that never produced fringes — a hole, a steeply
     tilted facet that threw the light out of the aperture, a saturated or
     dark pixel — has near-zero modulation. This is the map you threshold to
     decide which heights from :func:`csi_height_map` to trust.
  2. **Reflectance.** In the forward model the envelope peak is exactly
     ``amplitude * reflectivity``, so with a known *amplitude* this map *is*
     the reflectivity. Verified in the tests: a known reflectivity map over a
     5.0-7.0 um surface is recovered with a maximum error of 7.32e-05 (the
     residual is envelope truncation again — the same surface spread over
     2.0-10.0 um gives 4.03e-04). It is a contrast map, not a photometric
     measurement, and it is accurate to about four decimal places, not to
     machine precision.
  3. **Focus.** It is the interferometric analogue of a focus measure, and it
     peaks where :func:`csi_height_map` says the surface is.

Why use 1 rather than trust the height map everywhere: measured on a flat
surface at 6.0 um with a **50x reflectance step** across the field (0.02 on
one half, 1.0 on the other) and 1 % noise, the ``"gaussian"`` height error is
0.146 um RMS on the bright half and **3.03 um RMS** on the dark half, and 30 %
of the dark pixels are refused outright. The bias barely moves (+0.14 um);
what explodes is the scatter, because the three-point fit is reading three
samples out of a noise floor. ``"centroid"`` degrades far more gracefully on
the same data (0.022 -> 0.157 um, 7x rather than 20x), which is the second
place in this module where the estimator ranking depends on the data rather
than on the algebra. This map is what separates the two populations: it reads
0.035 +- 0.004 on the dark half and 0.412 +- 0.007 on the bright one.

It is deliberately **not** normalised by the pedestal. The classical fringe
*visibility* is ``b/a``, and computing it would need the pedestal, which
``remove_bias`` has just thrown away; returning ``b`` and saying so is honest,
whereas returning ``b`` and calling it visibility would not be. Divide by
:func:`numpy.mean` of the stack along axis 0 if you want the ratio.

Returns a float64 ``(H, W)`` map. Same shape and validation as
:func:`csi_height_map`.

**Raises** ``ValueError``: a non-3-D stack, fewer than 3 planes, an empty
spatial extent, a stack over :data:`MAX_STACK_ELEMENTS`, a non-finite /
complex / masked stack, or a non-bool *remove_bias*.

## 詳しい使い方ガイド

- [coherence_scanning ファミリ ガイド](../guides/coherence_scanning.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [coherence_scanning](../../../../examples/coherence_scanning.py) — `py -3.11 examples/coherence_scanning.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`surface`)

[csi_height_map](csi_height_map.md)

---
*Provenance: interferometry.py — INTERFEROMETRY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
