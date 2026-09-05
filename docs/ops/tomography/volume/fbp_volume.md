---
op: fbp_volume
dim: tomography
category: volume
in: sinostack
out: voxel
examples: [tomography_reconstruct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# fbp_volume — TOMOGRAPHY `volume` op

- **データ種**: `sinostack` → `voxel`
- **呼び出し**: `import tomography; tomography.fbp_volume(stack, angles_deg=None, size=None, filter_name='ramp', cutoff=1.0, span_deg=None)` (または `opstomography.get("fbp_volume")`)

## 使い方

Reconstruct every sinogram of a ``(Z, A, D)`` stack -> a ``(Z, S, S)`` volume.

The inverse of :func:`radon_volume`, slice by slice. The result is a plain
volume and every existing 3-D operator applies to it directly — windowing,
labelling, boundary extraction, marching cubes — which is the point of
returning ``voxel`` rather than something tomography-specific.

One number worth carrying into that pipeline: the reconstructed slice grid is
isotropic **in-plane only**. The slice spacing is whatever the scan used, and
it is usually coarser; the volume itself does not carry it. Passing this
volume to a measurement without its spacing is the most common way a
tomographic volume becomes a wrong number — see
``examples/tomography_reconstruct.py``, which measures the size of the error.

:param stack: ``(Z, n_angles, n_detectors)``.
:param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
:param size: output side per slice; ``None`` -> the inscribed square.
:param filter_name: one of :data:`FILTERS`.
:param cutoff: fraction of Nyquist to keep.
:param span_deg: angular range for the ``d(theta)`` weight.
:returns: ``(Z, size, size)`` float64 volume.
:raises ValueError: on a non-3-D stack, or an output over
    :data:`MAX_STACK_ELEMENTS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [tomography_reconstruct](../../../../examples/tomography_reconstruct.py) — `py -3.11 examples/tomography_reconstruct.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[radon_volume](radon_volume.md)

## 同カテゴリ(`volume`)

[radon_volume](radon_volume.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
