---
op: vol_crop_domain
dim: 3d
category: domain
in: voxel
out: voxel
examples: [roi_domain_boundary]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_crop_domain — 3D `domain` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_crop_domain(vol, domain=None, margin=0)` (実装を直接呼ぶなら `import volops; volops.vol_crop_domain(vol, domain=None, margin=0)`、台帳から引くなら `ops3d.get("vol_crop_domain")`)
- **台帳経由の戻り値**: `fullseye.ledger.vol_crop_domain(...)` は**宣言 out 型 `voxel` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.vol_crop_domain.raw(...)`、または `volops.vol_crop_domain` を直接呼ぶ。
  - 本体の返り: `(part, offset)`

## 使い方

Crop a volume to the tight bounding box of a domain (HALCON ``crop_domain``).

**This is the memory lever of the domain family**: a 512**3 CT scan whose
part of interest fits in 128**3 costs 64x less memory and compute once
cropped — and the Hessian operators (:func:`vol_frangi` / :func:`vol_sato`),
capped at ``MAX_EIGEN_VOXELS``, often become *possible* only after this
step. Gray values inside the box are kept verbatim (the box, not the mask,
defines the crop — pair with :func:`vol_reduce_domain` first if voxels
outside the mask but inside the box must read 0).

*domain* defaults to the volume's own **non-zero support** (``vol != 0`` —
a gray volume is cropped to wherever it has any signal; note this differs
from the ``> 0.5`` convention used when an explicit binary *domain* is
passed). *margin* is forwarded to :func:`vol_bounding_box`.

Returns ``(cropped, offset)`` — the ``(d, h, w)`` float64 sub-volume and the
``(z0, y0, x0)`` voxel offset of its origin in the input frame. Keep the
offset: :func:`vol_uncrop` maps results back, and
:func:`vol_boundary_points` accepts it as *origin* so point coordinates stay
in the uncropped frame. An empty domain raises ``ValueError`` (fail-closed).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [roi_domain_boundary](../../../../examples_3d/roi_domain_boundary.py) — `py -3.11 examples_3d/roi_domain_boundary.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`domain`)

[vol_reduce_domain](vol_reduce_domain.md) · [vol_bounding_box](vol_bounding_box.md) · [vol_uncrop](vol_uncrop.md) · [vol_tiled_map](vol_tiled_map.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
