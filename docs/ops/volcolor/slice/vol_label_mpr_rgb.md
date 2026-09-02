---
op: vol_label_mpr_rgb
dim: volcolor
category: slice
in: rgbvolume
out: rgbimage
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_label_mpr_rgb — VOLCOLOR `slice` op

- **データ種**: `rgbvolume` → `rgbimage`
- **呼び出し**: `import volcolor; volcolor.vol_label_mpr_rgb(rgbvol, center=None, gap: 'int' = 4, background=(0.05, 0.05, 0.07))` (または `opsvolcolor.get("vol_label_mpr_rgb")`)

## 使い方

色付きボリュームの直交 3 断面を **1 枚の RGB** に並べた図を返す。

左から axial ``(H, W)`` / coronal ``(D, W)`` / sagittal ``(D, H)``。*center* は
``(z, y, x)`` の交点(既定は各軸の中央)。パネルの高さは最大値へ *background*
で下詰めパディングし、間に *gap* 画素の隙間を空ける。

ラベル色が**ボリューム由来**であることがこの図の意味である ―― 3 面で同じ部品が
同じ色に見えることが、3 断面が同じラベリングから来ている証拠になる
(断面ごとに色を付け直した図では 3 面の色は一致しない)。

Returns float64 ``(H_out, W_out, 3)``. Raises ``ValueError`` for a bad volume,
a *center* outside the volume, or a negative *gap*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

—

## 同カテゴリ(`slice`)

[vol_label_slice_rgb](vol_label_slice_rgb.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
