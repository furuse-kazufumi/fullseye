---
op: vol_label_overlay
dim: volcolor
category: colorize
in: voxel × labels
out: rgbvolume
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# vol_label_overlay — VOLCOLOR `colorize` op

- **データ種**: `voxel × labels` → `rgbvolume`
- **呼び出し**: `import volcolor; volcolor.vol_label_overlay(vol, labels, seed: 'int' = 0, alpha: 'float' = 0.5, vmin=None, vmax=None, mode: 'str' = 'fill')` (または `opsvolcolor.get("vol_label_overlay")`)

## 使い方

元のグレーボリュームに色ラベルを重ねた ``(D, H, W, 3)`` を返す。

医用 CT / 産業 CT で実際に使う形 ―― 「セグメンテーションだけの絵」は
どこを切り出したのかが分からず、「元画像だけの絵」は何を測ったのかが分からない。

*vol* は ``(D, H, W)``。表示窓は ``vmin`` / ``vmax`` で**明示**する
(``None`` なら ``vol`` の最小 / 最大)。窓を暗黙に決めないのは、窓が違えば
同じ組織が別の明るさで出るからで、CT の window/level と同じ理由である。

*alpha* は ``0``(元画像のまま)から ``1``(色で塗り潰す)。*mode* は
``"fill"``(成分全体を塗る)か ``"boundary"``(6 近傍で隣が別ラベルの
ボクセルだけを塗る = 輪郭表示、下の構造が完全に見える)。

**``background`` 引数は無い**。この op はラベル 0 のボクセルに一切色を置かず
(そこは元画像そのもの)、パレット行 0 を一度も引かない。受け取っておいて
何もしない引数は「背景色を指定したのに効かない」という形の静かな嘘になる。

実測(``(24, 48, 48)``・16 成分・ノイズ入りグレー体、seed=0、``mode="fill"``):
前景ボクセルにおける元画像との平均絶対差は alpha=0.00 で 0.0000、
0.25 で 0.0679、0.50 で 0.1359、0.75 で 0.2038、1.00 で 0.2718 ――
alpha に対して直線(合成が線形であることの確認)。**背景ボクセルは
alpha に依らず 0.0000**(色は前景にしか乗らない)。

Raises ``ValueError`` when *vol* and *labels* differ in shape, on a non-finite
*vol*, on ``vmin >= vmax``, on an *alpha* outside [0, 1], or on an unknown *mode*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`rgbvolume` を入力に取れる)

[vol_label_slice_rgb](../slice/vol_label_slice_rgb.md) · [vol_label_mpr_rgb](../slice/vol_label_mpr_rgb.md)

## 同カテゴリ(`colorize`)

[vol_colorize_labels](vol_colorize_labels.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
