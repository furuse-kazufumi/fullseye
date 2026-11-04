---
op: ellipsoid_phantom
dim: tomography
category: ct_scan
in: 
out: voxel
gpu: なし
examples: [ct_scan_modes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# ellipsoid_phantom — TOMOGRAPHY `ct_scan` op

- **データ種**: `なし` → `voxel`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ellipsoid_phantom(shape=(128, 128, 128), ellipsoids=None, supersample=2)` (実装を直接呼ぶなら `import ctscan; ctscan.ellipsoid_phantom(shape=(128, 128, 128), ellipsoids=None, supersample=2)`、台帳から引くなら `opstomography.get("ellipsoid_phantom")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Rasterise a sum of uniform ellipsoids onto a ``(Z, Y, X)`` grid.

The normalised cube ``[-1, 1]^3`` maps onto the grid with half-width ``X/2`` voxels
on every axis, so voxels stay cubic. Each voxel is the mean of ``supersample^3``
sub-samples, so an edge voxel carries its true volume fraction.

:param shape: ``(Z, Y, X)``, or one int for a cube.
:param ellipsoids: ``(N, 8)`` rows; ``None`` gives :data:`SHEPP_LOGAN_3D`.
:param supersample: anti-alias factor per axis, ``1 .. 4``.
:returns: float64 volume.
:raises ValueError: on a degenerate ellipsoid or an oversized grid.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[radon_volume](../volume/radon_volume.md) · [ct_forward_project](ct_forward_project.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
