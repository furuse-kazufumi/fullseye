---
op: vol_label_volume_render
dim: volcolor
category: render
in: labels
out: rgbimage
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# vol_label_volume_render — VOLCOLOR `render` op

- **データ種**: `labels` → `rgbimage`
- **呼び出し**: `import volcolor; volcolor.vol_label_volume_render(labels, axis='z', mode: 'str' = 'front', seed: 'int' = 0, alpha: 'float' = 0.35, background=(0.0, 0.0, 0.0))` (または `opsvolcolor.get("vol_label_volume_render")`)

## 使い方

色付きラベルの**合成投影** ``(H, W, 3)`` を numpy だけで作る。

*mode*:

  * ``"front"`` ―― 視線方向で最初に当たる非背景ボクセルの色(不透明表示)。
  * ``"back"``  ―― 最後に当たるもの(裏側から見た形)。
  * ``"alpha"`` ―― front-to-back の ``over`` 合成(Porter & Duff 1984)。
    非背景ボクセルが不透明度 *alpha* を持つとして手前から積む。
    奥行きの重なりが出る一方、手前の色は必ず後ろより濃く出る。

**``mode="max"`` は拒否する**(``ValueError``)。RGB をチャネルごとに max
すると、赤成分が部品 A・緑成分が部品 B から来た**どの部品の色でもない色**が
出るからである。実測(z 方向にずれて重なる 3 枚の板・``(16, 16, 16)``、
seed=0、axis="z"):チャネル別 max の投影 ``(16, 16)`` は、前景 168 画素の
うち **90 画素**でパレットのどの行とも一致しない色を作った。同じ入力に対し
``"front"`` は 256 画素すべてがパレットの色である
(``tests/test_volcolor.py::test_channelwise_max_would_invent_colours``)。

*axis* は ``"z"``/0(``(H, W, 3)`` が返る)、``"y"``/1(``(D, W, 3)``)、
``"x"``/2(``(D, H, 3)``)。

Raises ``ValueError`` for an unknown *mode* / *axis*, an *alpha* outside
[0, 1], or a bad label volume.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

—

## 同カテゴリ(`render`)

[vol_labels_to_meshes](vol_labels_to_meshes.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
