---
op: vol_granulometry
dim: 3d
category: feature
in: voxel
out: measurement
examples: [ct_porosity_and_fibre_morphometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# vol_granulometry — 3D `feature` op

- **データ種**: `voxel` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_granulometry(vol_binary, radii=None, spacing=None)` (実装を直接呼ぶなら `import volops; volops.vol_granulometry(vol_binary, radii=None, spacing=None)`、台帳から引くなら `ops3d.get("vol_granulometry")`)
- **台帳経由の戻り値**: `fullseye.ledger.vol_granulometry(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.vol_granulometry.raw(...)`、または `volops.vol_granulometry` を直接呼ぶ。
  - 本体の返り: `中央径`

## 使い方

Pore / particle **size distribution** of a binary volume (opening series).

Opening by a ball of radius ``r`` deletes every feature narrower than ``2r``.
Tracking the surviving volume fraction as ``r`` grows gives the cumulative
size distribution ``F(r)``; its negative increment is the size density — the
fraction of material that sits in features of that size.  This is Matheron's
granulometry, the measurement behind every "pore size distribution" plot in
casting, foam and powder work.

Computed from the local-thickness volume rather than by repeated openings:
the two agree exactly (a voxel survives the opening of radius ``r`` iff its
local thickness is at least ``2r``) and one distance transform replaces N
morphological passes.

*radii* are in the units of *spacing* (millimetres when *spacing* is given,
voxels otherwise); leave it ``None`` for ``min(spacing)``-steps up to the
largest thickness present.  Returns ``{"radii": [...], "surviving_fraction":
[...], "density": [...], "mean_size": float, "d50": float, "units": "mm"|"voxel"}``
where sizes are **diameters** (``2r``), because that is what a pore diameter
means.

**Applicability.** (1) A distribution is only as good as the threshold that
made the binary volume — report it.  (2) Features touching the volume border
are truncated and bias the distribution downward; crop or state it.
(3) ``d50`` is interpolated between the two bracketing radii, so it is no
finer than the radius step.

HALCON has no granulometry operator.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_porosity_and_fibre_morphometry](../../../../examples_3d/ct_porosity_and_fibre_morphometry.py) — `py -3.11 examples_3d/ct_porosity_and_fibre_morphometry.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_frangi](vol_frangi.md) · [vol_local_std](vol_local_std.md) · [vol_local_thickness](vol_local_thickness.md) · [vol_orientation_coherence](vol_orientation_coherence.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
