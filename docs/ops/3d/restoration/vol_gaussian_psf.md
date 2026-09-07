---
op: vol_gaussian_psf
dim: 3d
category: restoration
in: measurement
out: voxel
examples: [deconv_fft_restore]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_gaussian_psf — 3D `restoration` op

- **データ種**: `measurement` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_gaussian_psf(sigma, truncate=4.0)` (実装を直接呼ぶなら `import volrestore; volrestore.vol_gaussian_psf(sigma, truncate=4.0)`、台帳から引くなら `ops3d.get("vol_gaussian_psf")`)

## 使い方

A normalised (sums to 1) 3-D Gaussian PSF kernel. *sigma* is a scalar or

``(sz, sy, sx)`` in voxels; the kernel spans ``+-truncate*sigma`` per axis
(odd size, centre at the middle voxel). The convenient companion to
:func:`vol_richardson_lucy` when the instrument PSF is well approximated
as Gaussian. Kernels above ``PSF_MAX_ELEMENTS`` (~256^3) raise
``ValueError`` — a PSF that large is an input mistake, not an instrument.

形: 各軸の半径 ``r = ceil(truncate * sigma)``、辺長 ``2r + 1``(奇数)の
``(2rz+1, 2ry+1, 2rx+1)`` float64 配列。軸順は ``(z, y, x)`` で、``sigma`` を
``(sz, sy, sx)`` で渡すとその順に対応する(異方 PSF)。3 本の 1-D Gaussian
``exp(-x^2 / (2 sigma^2))`` の外積を全体和で割るので、合計はちょうど 1、中心
voxel が最大値。単位は voxel(mm の PSF 幅は spacing で割ってから渡す)。

引数と検証(``ValueError``):
- ``sigma``: 正の有限スカラ、または長さ 3 の正の有限値。2 乗が 0 に
  アンダーフローするほど小さい値(~1.5e-154 未満)は 0/0 になるので拒否。
- ``truncate``: 正の有限値(既定 4.0 = 片側 4σ で打ち切り)。
- 要素数 ``prod(2r+1)`` が ``PSF_MAX_ELEMENTS``(``2**24``)を超えると拒否
  (σ≈300 で 64 GB を確保しかけた実測が動機)。

使いどころ: ``vol_richardson_lucy(vol, psf)`` の ``psf``。RL 側でも合計 1 に
再正規化するので、ここで作ったカーネルをそのまま渡してよい。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [deconv_fft_restore](../../../../examples_3d/deconv_fft_restore.py) — `py -3.11 examples_3d/deconv_fft_restore.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`restoration`)

[vol_richardson_lucy](vol_richardson_lucy.md)

---
*Provenance: volrestore.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
