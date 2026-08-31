---
op: vol_fft_lowpass
dim: 3d
category: frequency
in: voxel
out: voxel
examples: [deconv_fft_restore]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_fft_lowpass — 3D `frequency` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volfreq; volfreq.vol_fft_lowpass(vol, cutoff, spacing=None)` (または `ops3d.get("vol_fft_lowpass")`)

## 使い方

Gaussian low-pass: keeps structure coarser than ``1/cutoff`` (voxels, or

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [deconv_fft_restore](../../../../examples_3d/deconv_fft_restore.py) — `py -3.11 examples_3d/deconv_fft_restore.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`frequency`)

[vol_fft_highpass](vol_fft_highpass.md) · [vol_fft_bandpass](vol_fft_bandpass.md)

---
*Provenance: volfreq.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
