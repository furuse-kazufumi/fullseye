---
op: vol_region_props
dim: 3d
category: regionprops
in: labels
out: table
examples: [vessel_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_region_props — 3D `regionprops` op

- **データ種**: `labels` → `table`
- **呼び出し**: `import volops; volops.vol_region_props(labels, spacing=None, surface='auto')` (または `ops3d.get("vol_region_props")`)

## 使い方

Per-component quantitative descriptors from a label volume.

*labels* is the ``int`` volume returned by :func:`vol_label` (or any integer
labelling; voxels ``<= 0`` are background). Pass *spacing* ``(sz, sy, sx)`` (or
a :class:`volio.VolumeMeta`) to report physical volume in mm**3 and physical
surface area in mm**2. *surface* selects the surface-area estimator:
``"auto"`` (marching cubes when ``scikit-image`` is importable, else exposed
faces), ``"marching"`` (require marching cubes), or ``"faces"`` (always the
face count).

Returns a ``list[dict]`` (one per label ``1..n``, in ascending label order),
each with:

``label`` id · ``voxel_count`` · ``volume`` (voxels, or mm**3 with spacing) ·
``centroid`` ``(z, y, x)`` in voxel-index coordinates · ``bbox``
``(z0, z1, y0, y1, x0, x1)`` with **exclusive** upper bounds (slice ``stop``) ·
``surface_area`` (voxel-face units, or mm**2 with spacing) · ``sphericity``
(Wadell, ~1 for a sphere, lower for a slab; approximate — see module note).

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vessel_metrology](../../../../examples_3d/vessel_metrology.py) — `py -3.11 examples_3d/vessel_metrology.py`

## 型が繋がる次の op(`table` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [mesh_select_lod](../resolution/mesh_select_lod.md)

## 同カテゴリ(`regionprops`)

[label_components](label_components.md) · [region_props](region_props.md) · [largest_component](largest_component.md) · [filter_by_volume](filter_by_volume.md) · [inner_box3](inner_box3.md) · [vol_label](vol_label.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
