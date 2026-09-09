---
op: vol_fft_bandpass
dim: 3d
category: frequency
in: voxel
out: voxel
examples: [deconv_fft_restore]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# vol_fft_bandpass — 3D `frequency` op

- **データ種**: `voxel` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_fft_bandpass(vol, low, high, spacing=None)` (実装を直接呼ぶなら `import volfreq; volfreq.vol_fft_bandpass(vol, low, high, spacing=None)`、台帳から引くなら `ops3d.get("vol_fft_bandpass")`)

## 使い方

Gaussian band-pass ``lowpass(high) - lowpass(low)``: keeps structure

between the two scales (``low < high`` required, both in cycles/voxel or
cycles/mm with *spacing*). Typical use: isolate one texture scale, or a
periodic artefact band before subtracting it.

伝達関数は ``exp(-|f|^2 / (2 high^2)) - exp(-|f|^2 / (2 low^2))``。DC では
``1 - 1 = 0`` なので平均輝度は落ち、``low`` と ``high`` の間に山を持つ Gaussian 差分
(DoG 型)の帯域だけが残る。山の高さは 1 に届かない(2 つの Gaussian の差なので、
``low`` と ``high`` が近いほど通過量は小さい)。返り値は入力と同じ ``(D, H, W)`` の
float64、符号付き。

引数: ``low < high`` が必須(両方とも正の有限値)。単位は ``spacing=None`` で
cycles/voxel、``spacing`` 指定で cycles/mm。周期(voxel または mm)で考えるなら
``1/high`` が最小構造サイズ、``1/low`` が最大構造サイズ。

検証(``ValueError``): 3-D でない / NaN・Inf / ``MAX_VOXELS`` 超 / ``low``・``high``
が非正・非有限・2 乗がアンダーフロー / ``low >= high`` / ``spacing`` 不正。

使いどころ: 1 つのテクスチャスケールの抽出、周期的な縞・リングアーティファクト帯
を取り出して入力から引く。``vol_fft_lowpass(vol, high) - vol_fft_lowpass(vol, low)``
と同値。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [deconv_fft_restore](../../../../examples_3d/deconv_fft_restore.py) — `py -3.11 examples_3d/deconv_fft_restore.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[voxel_to_mips](../transform/voxel_to_mips.md) · [voxel_to_mesh](../transform/voxel_to_mesh.md) · [signed_distance_field](../transform/signed_distance_field.md) · [to_points](../transform/to_points.md) · [sobel3d](../feature/sobel3d.md) · [hessian3d](../feature/hessian3d.md) · [curvature_maps](../feature/curvature_maps.md) · [edt_jfa](../feature/edt_jfa.md)

## 同カテゴリ(`frequency`)

[vol_fft_lowpass](vol_fft_lowpass.md) · [vol_fft_highpass](vol_fft_highpass.md)

---
*Provenance: volfreq.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
