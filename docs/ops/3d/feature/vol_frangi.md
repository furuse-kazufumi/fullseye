---
op: vol_frangi
dim: 3d
category: feature
in: voxel
out: voxel
examples: [vessel_metrology, volume_downsampling]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_frangi — 3D `feature` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_frangi(vol, scales=(1, 2, 3), alpha=0.5, beta=0.5, c=None, black_ridges=False)` (実装を直接呼ぶなら `import volops; volops.vol_frangi(vol, scales=(1, 2, 3), alpha=0.5, beta=0.5, c=None, black_ridges=False)`、台帳から引くなら `ops3d.get("vol_frangi")`)

## 使い方

3-D Frangi vesselness — multiscale tubular-structure enhancement.

For every ``sigma`` in *scales* the gamma-normalised Hessian is formed, its
three eigenvalues ``|l1| <= |l2| <= |l3|`` are taken, and the Frangi response

    V = (1 - exp(-Ra**2 / 2 alpha**2)) * exp(-Rb**2 / 2 beta**2)
          * (1 - exp(-S**2 / 2 c**2))

is evaluated, where ``Ra = |l2|/|l3|`` (plate vs. line), ``Rb = |l1|/sqrt|l2 l3|``
(blob deviation) and ``S = sqrt(l1**2 + l2**2 + l3**2)`` (structure strength).
The response is set to 0 where the contrast polarity is wrong (bright tube:
``l2 > 0`` or ``l3 > 0``; ``black_ridges=True`` flips this). The maximum over
scales is taken and the volume is normalised to ``[0, 1]``.

Parameters
----------
scales : sequence of float — Gaussian sigmas, in **voxels**, to bracket the
    vessel *radii* of interest (see the module "scale-dependent" limitation).
alpha, beta : sensitivities of the plate- and blob-suppression terms (Frangi's
    defaults 0.5).
c : half the maximum Hessian norm ``S`` at each scale when ``None`` (Frangi's
    adaptive suggestion); otherwise a fixed structure-strength scale.
black_ridges : ``False`` (default) enhances *bright* tubes on a dark
    background; ``True`` enhances *dark* tubes on a bright background.

Returns a ``(D, H, W)`` float64 volume in ``[0, 1]``. Reference: Frangi et al.,
MICCAI 1998.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [vessel_metrology](../../../../examples_3d/vessel_metrology.py) — `py -3.11 examples_3d/vessel_metrology.py`
- [volume_downsampling](../../../../examples_3d/volume_downsampling.py) — `py -3.11 examples_3d/volume_downsampling.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md)

## 同カテゴリ(`feature`)

[sobel3d](sobel3d.md) · [hessian3d](hessian3d.md) · [curvature_maps](curvature_maps.md) · [edt_jfa](edt_jfa.md) · [vol_sato](vol_sato.md) · [vol_hessian_blobness](vol_hessian_blobness.md) · [vol_gradient_magnitude](vol_gradient_magnitude.md) · [vol_local_maxima](vol_local_maxima.md)

---
*Provenance: volops.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
