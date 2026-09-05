---
op: vol_label_slice_rgb
dim: volcolor
category: slice
in: rgbvolume
out: rgbimage
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# vol_label_slice_rgb — VOLCOLOR `slice` op

- **データ種**: `rgbvolume` → `rgbimage`
- **呼び出し**: `import volcolor; volcolor.vol_label_slice_rgb(rgbvol, index: 'int', axis='z')` (または `opsvolcolor.get("vol_label_slice_rgb")`)

## 使い方

色付きボリュームから 1 枚の断面 RGB を取り出す(axial / coronal / sagittal)。

*axis* は ``"z"``/``"axial"``/0(``(H, W, 3)`` が返る)、``"y"``/``"coronal"``/1
(``(D, W, 3)``)、``"x"``/``"sagittal"``/2(``(D, H, 3)``)。**返る 2 軸が
軸ごとに違う**のは ``(D, H, W)`` から 1 軸抜くのだから当然だが、``(H, W)`` を
期待して受けると縦横が入れ替わった絵が例外なしに出る。3 通りの形は
``tests/test_volcolor.py::test_slice_axes_shapes_and_content`` が固定している。

*index* は**非負**でなければならない。``-1`` を「最後の断面」として黙って
受けると、範囲外の指定が最後の断面として通ってしまう(切り出す位置が
1 箇所ずれた図は、機械にも目にも「壊れている」と見えない)。

Returns a contiguous float64 ``(..., 3)`` copy. Raises ``ValueError`` for a bad
volume, an unknown *axis*, or an out-of-range / negative *index*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

—

## 同カテゴリ(`slice`)

[vol_label_mpr_rgb](vol_label_mpr_rgb.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
