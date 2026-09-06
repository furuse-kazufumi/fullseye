---
op: vol_fft_lowpass
dim: 3d
category: frequency
in: voxel
out: voxel
examples: [deconv_fft_restore]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_fft_lowpass — 3D `frequency` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import volfreq; volfreq.vol_fft_lowpass(vol, cutoff, spacing=None)` (または `ops3d.get("vol_fft_lowpass")`)

## 使い方

Gaussian low-pass: keeps structure coarser than ``1/cutoff`` (voxels, or

mm with *spacing*), attenuates finer detail smoothly. Transfer
``exp(-f^2 / (2 cutoff^2))`` — the DC level (mean intensity) passes
unchanged. Typical use: extract the illumination/thickness drift.

手順: ``np.fft.rfftn`` で実 FFT → 各周波数 bin の大きさ ``|f| = sqrt(fz^2 + fy^2 + fx^2)``
に伝達関数 ``exp(-|f|^2 / (2 cutoff^2))`` を掛ける → ``irfftn`` で戻す。入力と同じ
``(D, H, W)`` の float64 を返す(spacing を渡しても shape は変わらない)。

引数:
- ``cutoff``: 正の有限値。``spacing=None`` なら **cycles/voxel**(Nyquist = 0.5)、
  ``spacing=(sz, sy, sx)``(mm、または ``spacing_mm`` を持つ ``volio.VolumeMeta``)を
  渡すと **cycles/mm**。異方 voxel では軸ごとに ``fftfreq(n, d=spacing)`` で物理
  周波数に直すので、同じ物理構造が同じ扱いになる。
- 減衰は Gaussian で、``|f| = cutoff`` で ``exp(-1/2) ≈ 0.61``(brick-wall では
  ない。リンギングは出ない)。

検証(``ValueError``): 3-D でない / NaN・Inf / voxel 数が ``MAX_VOXELS``(``1 << 27``)
超 / ``cutoff`` が非正・非有限・2 乗がアンダーフローするほど小さい / ``spacing`` が
長さ 3 でない・非正。

注意: FFT は volume を周期的とみなす。向かい合う面の輝度差が大きいと wrap を
またいで漏れる(窓掛けは黙ってしない)。``vol_fft_highpass`` は厳密にこの補集合
``1 - lowpass`` で、両者の和は入力に一致する。

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
