---
op: ellipsoid_projections
dim: tomography
category: ct_scan
in: ctgeometry
out: projstack
gpu: なし
examples: [ct_scan_modes, poc_ct_casting_sparse_views]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# ellipsoid_projections — TOMOGRAPHY `ct_scan` op

- **データ種**: `ctgeometry` → `projstack`
- **呼び出し**: `import fullseye as fs; fs.ledger.ellipsoid_projections(geometry, ellipsoids=None, device='auto')` (実装を直接呼ぶなら `import ctscan; ctscan.ellipsoid_projections(geometry, ellipsoids=None, device='auto')`、台帳から引くなら `opstomography.get("ellipsoid_projections")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Exact line integrals of a sum of ellipsoids, for any scan in this family.

Each ray is mapped to the frame where the ellipsoid is a unit sphere, and the
chord length comes from the quadratic's discriminant. No voxels, no interpolation
and no projector are involved, which is what makes this the ground truth the
projector and every reconstruction here are measured against.

:param geometry: dict from :func:`ct_scan_geometry`.
:param ellipsoids: ``(N, 8)`` rows; ``None`` gives :data:`SHEPP_LOGAN_3D`.
:param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
:returns: ``(view, V, U)`` float array.
:raises ValueError: on a geometry not from :func:`ct_scan_geometry`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`
- [poc_ct_casting_sparse_views](../../../../examples/poc_ct_casting_sparse_views.py) — `py -3.11 examples/poc_ct_casting_sparse_views.py`

## 型が繋がる次の op(`projstack` を入力に取れる)

[ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md) · [tv_reconstruct](tv_reconstruct.md) · [ct_dual_energy_reconstruct](ct_dual_energy_reconstruct.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
