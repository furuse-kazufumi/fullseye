---
op: vol_fft_highpass
dim: 3d
category: frequency
in: voxel
out: voxel
examples: [deconv_fft_restore]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# vol_fft_highpass — 3D `frequency` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_fft_highpass(vol, cutoff, spacing=None)` (実装を直接呼ぶなら `import volfreq; volfreq.vol_fft_highpass(vol, cutoff, spacing=None)`、台帳から引くなら `ops3d.get("vol_fft_highpass")`)

## 使い方

Gaussian high-pass — the exact complement ``1 - lowpass`` (the two sum

to the input to float precision, proven in tests). Removes the DC level and
slow drift, keeps edges/texture. Output is signed (mean ~ 0).

伝達関数は ``1 - exp(-|f|^2 / (2 cutoff^2))``。DC(``f = 0``)は係数 0 なので平均
輝度は完全に落ち、``|f| = cutoff`` で ``1 - 0.61 ≈ 0.39``、高周波ほど 1 に近づく。
返り値は入力と同じ ``(D, H, W)`` の float64 で **符号付き**(負の値を含む)。
``[0, 1]`` 前提の後段(表示・``vol_window_level`` 等)に渡すなら ``vol_stretch`` で
正規化するか、``vol + highpass`` の形で使う。

引数: ``cutoff`` は正の有限値。``spacing=None`` で cycles/voxel、``spacing``
(``(sz, sy, sx)`` または ``volio.VolumeMeta``)を渡すと cycles/mm。

検証(``ValueError``): ``vol_fft_lowpass`` と同じ(3-D でない / NaN・Inf /
``MAX_VOXELS`` 超 / cutoff・spacing 不正)。

使いどころ: 照明むら・厚みドリフト・背景勾配の除去(``vol_fft_lowpass`` の結果を
引くのと同値)。周期的とみなす FFT の性質上、面どうしの輝度差は wrap で漏れる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [deconv_fft_restore](../../../../examples_3d/deconv_fft_restore.py) — `py -3.11 examples_3d/deconv_fft_restore.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`frequency`)

[vol_fft_lowpass](vol_fft_lowpass.md) · [vol_fft_bandpass](vol_fft_bandpass.md)

---
*Provenance: volfreq.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
