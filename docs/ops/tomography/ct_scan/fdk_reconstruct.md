---
op: fdk_reconstruct
dim: tomography
category: ct_scan
in: projstack × ctgeometry
out: voxel
gpu: なし
examples: [ct_scan_modes]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# fdk_reconstruct — TOMOGRAPHY `ct_scan` op

- **データ種**: `projstack × ctgeometry` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.fdk_reconstruct(projections, geometry, filter_name='ramp', cutoff=1.0, device='auto', allow_incomplete=False)` (実装を直接呼ぶなら `import ctscan; ctscan.fdk_reconstruct(projections, geometry, filter_name='ramp', cutoff=1.0, device='auto', allow_incomplete=False)`、台帳から引くなら `opstomography.get("fdk_reconstruct")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Filtered back-projection for every scan with a formula: FDK and its relatives.

The Feldkamp-Davis-Kress steps, on one code path: weight each sample by the cosine
of its ray and by the scan's redundancy, ramp-filter along the detector rows, then
back-project with the ``(DSO / U)^2`` weight. A fan is one row, a short scan takes
Parker's weight, an offset detector Wang's, a helix a row window normalised per
voxel, laminography a ``sin(tilt)`` scale, and a parallel beam has no divergence
weight. The equiangular detector takes the ``(gamma / sin gamma)^2`` kernel.

A scan with no formula, or an arc too short to determine the object, is refused
and named: use :func:`sirt_reconstruct` or :func:`tv_reconstruct`.

:param projections: ``(view, V, U)`` line integrals.
:param geometry: dict from :func:`ct_scan_geometry`.
:param filter_name: one of :data:`tomography.FILTERS` except ``"none"``.
:param cutoff: fraction of Nyquist to keep, ``(0, 1]``.
:param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
:param allow_incomplete: reconstruct an arc under the minimum anyway. The result
    is missing a wedge of the object and the density reads low.
:returns: ``(Z, Y, X)`` float attenuation volume.
:raises ValueError: on a shape that disagrees with the geometry, a tomosynthesis
    scan, or an incomplete arc. Empty input (``projections`` with 0 elements) raises
    ``ValueError``.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[radon_volume](../volume/radon_volume.md) · [ct_forward_project](ct_forward_project.md)

## 同カテゴリ(`ct_scan`)

[ct_scan_geometry](ct_scan_geometry.md) · [shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
