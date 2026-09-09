---
op: vol_richardson_lucy
dim: 3d
category: restoration
in: voxel × voxel
out: voxel
examples: [deconv_fft_restore]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_richardson_lucy — 3D `restoration` op

- **データ種**: `voxel × voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_richardson_lucy(vol, psf, iterations=10, clip_tiny=1e-12)` (実装を直接呼ぶなら `import volrestore; volrestore.vol_richardson_lucy(vol, psf, iterations=10, clip_tiny=1e-12)`、台帳から引くなら `ops3d.get("vol_richardson_lucy")`)

## 使い方

Richardson–Lucy deconvolution of a non-negative volume by a known PSF.

*psf* is a 3-D non-negative kernel (any odd/even size smaller than the
volume; it is normalised to sum 1 internally so overall intensity is
preserved). *iterations* trades sharpness against noise amplification —
5-30 is the practical range (see the module notes on semi-convergence).

Negative voxels are refused (RL is a Poisson model) — except *rounding
dust*: values no lower than ``-NEGATIVE_DUST_TOL * max|vol|`` (1e-9
relative; an FFT-blurred observation typically carries -1e-16) are clipped
to 0 instead of rejected, so the module's own forward model feeds back in.

Returns the deblurred ``(D, H, W)`` float64 volume (non-negative).
Measured on the test scene (binary sphere pair blurred by a sigma-2
Gaussian): the RMSE to ground truth falls to 0.81x the blurred
observation's at 10 iterations and 0.68x at 50 — genuine but *gradual*,
because the residual is dominated by the spheres' hard edges, which RL
recovers slowly. What converges fast is the *forward consistency*:
re-blurring the estimate reproduces the observation almost exactly (that
is the quantity the RL update actually optimises).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [deconv_fft_restore](../../../../examples_3d/deconv_fft_restore.py) — `py -3.11 examples_3d/deconv_fft_restore.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`restoration`)

[vol_gaussian_psf](vol_gaussian_psf.md)

---
*Provenance: volrestore.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
