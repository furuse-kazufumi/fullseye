---
op: vol_euler_number
dim: 3d
category: feature
in: voxel
out: measurement
examples: [ct_porosity_and_fibre_morphometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# vol_euler_number — 3D `feature` op

- **データ種**: `voxel` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_euler_number(vol_binary, connectivity=26)` (実装を直接呼ぶなら `import volops; volops.vol_euler_number(vol_binary, connectivity=26)`、台帳から引くなら `ops3d.get("vol_euler_number")`)
- **台帳経由の戻り値**: `fullseye.ledger.vol_euler_number(...)` は**宣言 out 型 `measurement` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.vol_euler_number.raw(...)`、または `volops.vol_euler_number` を直接呼ぶ。
  - 本体の返り: `chi(b0-b1+b2)`

## 使い方

Euler characteristic of a binary volume, split into its three Betti numbers.

``chi = b0 - b1 + b2`` where ``b0`` counts **separate objects**, ``b1``
counts **tunnels** (handles that pass right through) and ``b2`` counts
**enclosed cavities**.  For porous media that split is the whole point:
``b1`` is open, connected porosity — the paths a fluid can take — while
``b2`` is closed porosity that no fluid reaches.  A single ``chi`` cannot
tell a foam with many tunnels from one with many sealed bubbles; the three
numbers can.

*connectivity* is ``6``, ``18`` or ``26`` for the foreground; the background
is counted with the complementary neighbourhood (``26`` vs ``6``), which is
what makes the pair of counts consistent — using the same neighbourhood for
both is the classical way to produce a set that is simultaneously connected
and disconnected.

Returns ``{"euler": chi, "objects": b0, "tunnels": b1, "cavities": b2,
"connectivity": connectivity}``.  ``b1`` is derived as ``b0 + b2 - chi``, so
it inherits the exactness of the other three.

HALCON's ``euler_number`` is 2-D (regions) only; there is no voxel
equivalent.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_porosity_and_fibre_morphometry](../../../../examples_3d/ct_porosity_and_fibre_morphometry.py) — `py -3.11 examples_3d/ct_porosity_and_fibre_morphometry.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

[vol_gaussian_psf](../restoration/vol_gaussian_psf.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fresnel_reflectance](../optics/fresnel_reflectance.md) · [snell_angle](../optics/snell_angle.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [edt_jfa_vector](edt_jfa_vector.md) · [vol_frangi](vol_frangi.md) · [vol_local_std](vol_local_std.md) · [vol_local_thickness](vol_local_thickness.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
