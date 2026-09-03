---
op: ring_artifact_apply
dim: tomography
category: artifact
in: sinogram
out: sinogram
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# ring_artifact_apply — TOMOGRAPHY `artifact` op

- **データ種**: `sinogram` → `sinogram`
- **呼び出し**: `import tomography; tomography.ring_artifact_apply(sinogram, gain_sigma=0.02, seed=0, offsets=None)` (または `opstomography.get("ring_artifact_apply")`)

## 使い方

Give the detector a per-bin gain error — the source of ring artefacts.

A detector bin whose gain is ``g`` reports ``I = g I_true``, so after the
logarithm the line integral picks up a **constant offset** ``-ln g`` at that
bin, the same at every angle. Back-projecting a constant column smears it
around the rotation axis, and the reconstruction grows a ring at the radius
that bin's rays are tangent to. One bad pixel, one perfect circle.

The offsets are drawn once from ``N(0, gain_sigma)`` with a fixed *seed* and
applied to every row, because the whole point is that the error does **not**
vary with angle — that is what distinguishes a ring from noise, and what makes
:func:`ring_artifact_remove` possible.

:param sinogram: ``(n_angles, n_detectors)``.
:param gain_sigma: standard deviation of the per-bin offset, ``>= 0``.
:param seed: RNG seed; there is no ``None`` (determinism is a contract here).
:param offsets: explicit ``(n_detectors,)`` offsets; overrides the random draw.
:returns: ``(n_angles, n_detectors)`` float64 sinogram.
:raises ValueError: on a negative sigma, a non-int seed, or an *offsets* whose
    length is not the detector count.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](beam_hardening_apply.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_remove](ring_artifact_remove.md) · [metal_trace_interpolate](metal_trace_interpolate.md) · [sinogram_center_of_rotation](../geometry/sinogram_center_of_rotation.md)

## 同カテゴリ(`artifact`)

[beam_hardening_apply](beam_hardening_apply.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_remove](ring_artifact_remove.md) · [metal_trace_interpolate](metal_trace_interpolate.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
