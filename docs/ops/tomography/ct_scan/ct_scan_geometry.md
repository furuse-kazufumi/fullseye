---
op: ct_scan_geometry
dim: tomography
category: ct_scan
in: 
out: ctgeometry
gpu: なし
examples: [ct_scan_modes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# ct_scan_geometry — TOMOGRAPHY `ct_scan` op

- **データ種**: `なし` → `ctgeometry`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ct_scan_geometry(scan='cone', n_views=360, n_u=256, n_v=256, vol_shape=(256, 256, 256), voxel=1.0, du=None, dv=None, dso=None, dsd=None, detector='flat', arc_deg=None, start_deg=0.0, angles_deg=None, offset_u=0.0, pitch=1.0, turns=None, tilt_deg=30.0)` (実装を直接呼ぶなら `import ctscan; ctscan.ct_scan_geometry(scan='cone', n_views=360, n_u=256, n_v=256, vol_shape=(256, 256, 256), voxel=1.0, du=None, dv=None, dso=None, dsd=None, detector='flat', arc_deg=None, start_deg=0.0, angles_deg=None, offset_u=0.0, pitch=1.0, turns=None, tilt_deg=30.0)`、台帳から引くなら `opstomography.get("ct_scan_geometry")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Describe one CT scan: per view, where the source and the detector are.

Every other operator in this family reads this dict and nothing else, so a new
scan is a new orbit here and never a new projector. The result carries, for each
view, ``source`` (for a parallel beam the ray direction), ``det_center``, ``det_u``
and ``det_v`` in physical units with the origin at the volume centre.

The orbits. ``"cone"`` is a circle around the z axis with a flat panel, the
industrial default; ``"fan"`` the same with a single detector row, for a single
slice; ``"helical"`` the cone with the source and detector moving along z, ``pitch``
detector heights per turn; ``"laminography"`` a circle tilted so that the beam meets
the board normal at ``tilt_deg`` (90 is an ordinary CT, and ``dso=None`` with
``scan="laminography"`` is the parallel-beam form); ``"tomosynthesis"`` a source arc
of ``arc_deg`` over a detector that does not move; ``"parallel"`` parallel rays.

A short scan is ``arc_deg < 360``, a few-view scan a small ``n_views``, a
limited-angle scan a small ``arc_deg`` or an explicit ``angles_deg``, and an
offset detector ``offset_u`` bins. Those are parameters of the orbit, not new scans.

:param scan: one of :data:`SCANS`.
:param n_views: views, ``1 .. 65536``; ignored when *angles_deg* is given.
:param n_u: detector columns.
:param n_v: detector rows.
:param vol_shape: ``(Z, Y, X)`` of the reconstruction, or one int for a cube.
:param voxel: voxel edge in physical units.
:param du: detector column pitch; ``None`` gives one voxel at the isocentre.
:param dv: detector row pitch; ``None`` gives one voxel at the isocentre.
:param dso: source to isocentre distance; ``None`` gives 3 volume widths.
:param dsd: source to detector distance; ``None`` gives ``2 * dso``.
:param detector: one of :data:`DETECTORS`.
:param arc_deg: orbit length; ``None`` gives 360, or 180 for ``"parallel"``, or 40
    for ``"tomosynthesis"``.
:param start_deg: first view angle.
:param angles_deg: explicit increasing view angles; overrides *n_views* and *arc_deg*.
:param offset_u: detector shift in bins along u, for an extended field of view.
:param pitch: helical table feed per turn, in detector heights at the isocentre.
:param turns: helical turns; ``None`` covers the volume height.
:param tilt_deg: laminography angle between the beam and the rotation axis.
:returns: geometry dict; ``vol_shape``, ``n_views``, ``n_v``, ``n_u`` and the per-view
    arrays are the public fields.
:raises ValueError: on an unknown scan or detector, a non-positive length, a source
    inside the volume, ``arc`` above 360, or an oversized request.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_scan_modes](../../../../examples/ct_scan_modes.py) — `py -3.11 examples/ct_scan_modes.py`

## 型が繋がる次の op(`ctgeometry` を入力に取れる)

[ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md) · [tv_reconstruct](tv_reconstruct.md) · [ct_dual_energy_reconstruct](ct_dual_energy_reconstruct.md)

## 同カテゴリ(`ct_scan`)

[shepp_logan_3d](shepp_logan_3d.md) · [ellipsoid_phantom](ellipsoid_phantom.md) · [ellipsoid_projections](ellipsoid_projections.md) · [ct_forward_project](ct_forward_project.md) · [ct_adjoint_project](ct_adjoint_project.md) · [fdk_reconstruct](fdk_reconstruct.md) · [sirt_reconstruct](sirt_reconstruct.md) · [os_sart_reconstruct](os_sart_reconstruct.md)

---
*Provenance: ctscan.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
