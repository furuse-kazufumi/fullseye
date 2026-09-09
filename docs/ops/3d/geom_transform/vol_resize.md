---
op: vol_resize
dim: 3d
category: geom_transform
in: voxel
out: voxel
examples: [vol_geometry_transform]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_resize — 3D `geom_transform` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_resize(vol, factor=None, shape=None, order=1, spacing=None, mode='nearest', cval=0.0)` (実装を直接呼ぶなら `import volxform; volxform.vol_resize(vol, factor=None, shape=None, order=1, spacing=None, mode='nearest', cval=0.0)`、台帳から引くなら `ops3d.get("vol_resize")`)
- **台帳経由の戻り値**: `fullseye.ledger.vol_resize(...)` は**宣言 out 型 `voxel` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.vol_resize.raw(...)`、または `volxform.vol_resize` を直接呼ぶ。
  - 本体の返り: `spacing 付き時`

## 使い方

Resample a volume to a new grid (``scipy.ndimage.zoom``, cell semantics).

Exactly **one** of *factor* / *shape* selects the target grid:

* ``factor`` — a positive scalar or ``(fz, fy, fx)``; the output shape is
  ``round(dim * f)`` per axis (scipy's rule, each ``>= 1``).
* ``shape`` — the exact output ``(D', H', W')`` (positive integers).

Sampling uses ``grid_mode=True`` (cell semantics): a voxel is a *cell*, so
an integer upscale ``f`` maps input voxel ``i`` exactly onto the output
block ``[f*i, f*(i+1))`` (exact at ``order=0``), and the volume's physical
extent is preserved by the recomputed spacing — not the endpoint-aligned
convention of scipy's ``grid_mode=False`` default.

*mode* / *cval* set how samples that fall outside the input cells (the outer
half-voxel shell of every upscale at ``order >= 1``) are filled. The default
``"nearest"`` extends the border voxel, so **a constant volume resizes to
the same constant** and a ramp keeps its end values. Until 2026-09-03 the
call was hard-wired to ``"grid-constant"`` with ``cval=0``, which blended
the outer shell toward 0 — an upscale x2 of an all-ones volume came back
with ``min = 0.42`` on its faces, an artefact that then leaked into every
downstream measurement. Other accepted modes: ``"reflect"``, ``"mirror"``,
``"grid-mirror"``, ``"grid-wrap"``, and ``"grid-constant"`` (with *cval*)
when a zero-padded border is genuinely wanted. ``"constant"`` / ``"wrap"``
are rejected with a hint (scipy needs the ``grid-`` variants here).

**The return shape depends on** *spacing*:

* ``spacing=None`` (default) — returns the resampled ``(D', H', W')``
  float64 volume alone.
* *spacing* given (``(sz, sy, sx)`` or a ``VolumeMeta``) — returns a
  **2-tuple** ``(out, new_spacing)`` where
  ``new_spacing = (sz * D/D', sy * H/H', sx * W/W')``, so
  ``out.shape * new_spacing == vol.shape * spacing`` per axis: the physical
  size in millimetres is invariant. Keep the new spacing — every
  spacing-aware operator downstream needs it.

*order* is the spline degree (exact integer 0..5; 0 = nearest — the choice
for masks / labels, 1 = trilinear — the grey-value default; >1 can
overshoot, see the module notes). Shrinking aliases (no band-limiting) —
mean-pool with :func:`volops.volume_downsample` first for large reductions.

Raises ``ValueError`` when both or neither of *factor* / *shape* are given,
or when the **output** would exceed ``MAX_VOXELS`` (checked before any
allocation — a huge factor cannot balloon memory).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vol_geometry_transform](../../../../examples_3d/vol_geometry_transform.py) — `py -3.11 examples_3d/vol_geometry_transform.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`geom_transform`)

[vol_rotate](vol_rotate.md) · [vol_affine](vol_affine.md)

---
*Provenance: volxform.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
