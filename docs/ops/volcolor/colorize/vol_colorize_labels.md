---
op: vol_colorize_labels
dim: volcolor
category: colorize
in: labels
out: rgbvolume
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# vol_colorize_labels — VOLCOLOR `colorize` op

- **データ種**: `labels` → `rgbvolume`
- **呼び出し**: `import volcolor; volcolor.vol_colorize_labels(labels, seed: 'int' = 0, background=(0.0, 0.0, 0.0))` (または `opsvolcolor.get("vol_colorize_labels")`)

## 使い方

3-D ラベルボリューム -> ``(D, H, W, 3)`` float64 の RGB ボリューム。

「切ってから色を付ける」のではなく「**色を付けてから切る**」ための入口。
ラベル ``k`` の色は :func:`vol_label_palette` の行 ``k`` そのもので、
``imgio.colorize_labels(labels, seed)`` を同じ配列に対して呼んだ結果と
**バイト単位で一致する**(``tests/test_volcolor.py`` が固定)。

切る順序が効くこと自体は :func:`vol_label_color_flicker` が数える。実測
(16 球・``(24, 48, 48)`` の参照ファントム、``connectivity=26``、seed=0):
スライスごとに色を付け直すと **24 スライス中 20 スライス**で少なくとも
1 成分の色が変わり、(成分, スライス) の変化は 108 組中 **62 件**、
**16 成分すべて**が一度は色を変える。ボリュームで色を付けてから切ると
3 つとも 0。

Raises ``ValueError`` on a non-3-D, float, or negative label volume, on a label
over :data:`MAX_LABELS`, or on more than :data:`MAX_COLOR_VOXELS` voxels.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`rgbvolume` を入力に取れる)

[vol_label_slice_rgb](../slice/vol_label_slice_rgb.md) · [vol_label_mpr_rgb](../slice/vol_label_mpr_rgb.md)

## 同カテゴリ(`colorize`)

[vol_label_overlay](vol_label_overlay.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
