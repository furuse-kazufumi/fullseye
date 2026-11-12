---
op: ct_forward_project
dim: tomography
category: ct_scan
in: voxel × ctgeometry
out: projstack
gpu: なし
examples: [ct_scan_modes, poc_ct_casting_sparse_views, poc_real_walnut_cbct]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# ct_forward_project — TOMOGRAPHY `ct_scan` op

- **データ種**: `voxel × ctgeometry` → `projstack`
- **呼び出し**: `import fullseye as fs; fs.ledger.ct_forward_project(volume, geometry, device='auto')` (実装を直接呼ぶなら `import ctscan; ctscan.ct_forward_project(volume, geometry, device='auto')`、台帳から引くなら `opstomography.get("ct_forward_project")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Project a volume along every ray of *geometry*: the discrete operator ``A``.

Rays are sampled at one voxel step, trilinearly, a sample outside the volume
counting zero. For a parallel slice this is the definition of
:func:`tomography.radon_transform`.

:param volume: ``(Z, Y, X)`` of the geometry's ``vol_shape``.
:param geometry: dict from :func:`ct_scan_geometry`.
:param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
:returns: ``(view, V, U)`` float array of line integrals.
:raises ValueError: on a shape that disagrees with the geometry. Empty input
    (``volume`` with 0 elements) raises ``ValueError``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`
- [poc_ct_casting_sparse_views](../../../../examples/poc_ct_casting_sparse_views.py) — `py -3.11 examples/poc_ct_casting_sparse_views.py`
- [poc_real_walnut_cbct](../../../../examples/poc_real_walnut_cbct.py) — `py -3.11 examples/poc_real_walnut_cbct.py`

## 型が繋がる次の op(`projstack` を入力に取れる)

[ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md) · [tv_reconstruct](tv_reconstruct.md) · [ct_dual_energy_reconstruct](ct_dual_energy_reconstruct.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
