---
op: vol_local_thickness
dim: 3d
category: feature
in: voxel
out: voxel
examples: [ct_porosity_and_fibre_morphometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# vol_local_thickness — 3D `feature` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_local_thickness(vol_binary, spacing=None, max_radius=None)` (実装を直接呼ぶなら `import volops; volops.vol_local_thickness(vol_binary, spacing=None, max_radius=None)`、台帳から引くなら `ops3d.get("vol_local_thickness")`)

## 使い方

Local thickness map: the diameter of the largest ball that covers each voxel.

For every foreground voxel this is ``max{ 2r : the voxel lies inside some ball
of radius r that fits entirely in the foreground }`` — the classical
granulometric size, and the quantity trabecular-bone and industrial-CT work
calls *local thickness* (a pore's local thickness is its diameter; a wall's is
its thickness).  Computed from the exact distance transform: take the voxels
whose distance is at least ``r`` as ball centres and paint the balls they
cover, largest radius first.

★**Distinct from ``vol_wall_thickness``**, which walks a single probe segment
``p0 -> p1`` and returns a list of crossings.  This one is a *volume*, so the
thickness of every feature is available at once and can be histogrammed.

Pass *spacing* ``(sz, sy, sx)`` (or a :class:`volio.VolumeMeta`) and the
result is in **millimetres**; otherwise in voxels.  *max_radius* caps the
search (in the same units); leave it ``None`` to derive it from the largest
distance actually present, which costs one pass more but never saturates.

**Applicability.** (1) The foreground comes from a single threshold, so
beam hardening or a brightness gradient biases the thickness across the
volume — flatten first.  (2) With anisotropic voxels the ball is a ball in
millimetres, not in voxels, so *spacing* is not cosmetic.  (3) A feature
three voxels across is quantised at better than 30% only if you say so:
report the voxel size next to any thickness number.

Returns a ``(D, H, W)`` float64 volume, 0 on the background.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_porosity_and_fibre_morphometry](../../../../examples_3d/ct_porosity_and_fibre_morphometry.py) — `py -3.11 examples_3d/ct_porosity_and_fibre_morphometry.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_local_std](vol_local_std.md) · [vol_orientation_coherence](vol_orientation_coherence.md) · [vol_euler_number](vol_euler_number.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
