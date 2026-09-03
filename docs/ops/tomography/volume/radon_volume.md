---
op: radon_volume
dim: tomography
category: volume
in: voxel
out: sinostack
examples: [tomography_reconstruct]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# radon_volume — TOMOGRAPHY `volume` op

- **データ種**: `voxel` → `sinostack`
- **呼び出し**: `import tomography; tomography.radon_volume(volume, angles_deg=None, n_detectors=None, oversample=1)` (または `opstomography.get("radon_volume")`)

## 使い方

Project every slice of a ``(Z, H, W)`` volume -> a ``(Z, A, D)`` stack.

Parallel-beam geometry with the rotation axis along ``Z``, which is the case
where the 3-D problem really is a stack of independent 2-D ones — each slice
projects into its own sinogram and nothing crosses between them. (A cone beam
does not have this property and is not implemented; saying so is cheaper than
a wrong ``FDK``.)

The output's axis order is ``(slice, angle, detector)`` so that ``stack[k]``
is a sinogram in this module's own convention and every 2-D operator here
applies to it unchanged.

:param volume: ``(Z, H, W)`` float volume, ``Z >= 1``.
:param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``, 180 views.
:param n_detectors: bins; ``None`` -> covers the in-plane diagonal.
:param oversample: ray samples per pixel, ``1 .. 8``.
:returns: ``(Z, n_angles, n_detectors)`` float64 stack.
:raises ValueError: on a non-3-D input or a stack over
    :data:`MAX_STACK_ELEMENTS`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [tomography_reconstruct](../../../../examples/tomography_reconstruct.py) — `py -3.11 examples/tomography_reconstruct.py`

## 型が繋がる次の op(`sinostack` を入力に取れる)

[fbp_volume](fbp_volume.md)

## 同カテゴリ(`volume`)

[fbp_volume](fbp_volume.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
