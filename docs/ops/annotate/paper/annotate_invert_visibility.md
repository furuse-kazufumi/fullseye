---
op: annotate_invert_visibility
dim: annotate
category: paper
in: image2d × mask
out: table
examples: [annotate_paper_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# annotate_invert_visibility — ANNOTATE `paper` op

- **データ種**: `image2d × mask` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.annotate_invert_visibility(img, mask, mode='complement', alpha=1.0)` (実装を直接呼ぶなら `import annotate; annotate.annotate_invert_visibility(img, mask, mode='complement', alpha=1.0)`、台帳から引くなら `opsannotate.get("annotate_invert_visibility")`)

## 使い方

反転色が**その地の上で本当に見えるか**を、描く前に測る。

反転色の利点は「地の色を知らなくてよい」ことだが、弱点はたった 1 つで、
しかも致命的 —— **中間調では反転しても同じ色になる**。8bit グレーの
v=128 に対する補色は v=127 で、WCAG のコントラスト比は **1.014**
(比 1.0 が「同じ色」。実測 2026-09-08)。比 1.5 を下回る帯は
v ∈ [113, 142] の 30/256 階調 = 全階調の 12 % に及ぶ。

:func:`annotate_invert` と :func:`annotate_invert_path` は内部でこれを
呼んで警告するが、**自分で fail-closed にしたいとき**はこの op で測って
から描く(``min_contrast`` を見て、低ければ ``mode="contrast"`` に倒す)。

Parameters
----------
img : (H,W) または (H,W,C)
    地。値域 [0,1]。
mask : (H,W)
    反転を乗せるところ。真偽か [0,1] の重み。**形が違えば例外**。
mode : str
    :data:`INVERT_MODES` のいずれか。
alpha : float
    反転の効き。描くときと同じ値を渡すこと —— 見え方は「反転色」ではなく
    **実際に置かれる色**で決まるので、``alpha`` を落とすと答えが変わる。

Returns
-------
dict
    ``pixels``(重み >= 0.5 の画素数) / ``min_contrast`` /
    ``median_contrast`` / ``invisible_fraction``(比が
    :data:`INVERT_MIN_CONTRAST` 未満の割合) / ``worst_xy``(最悪の画素、
    無ければ ``None``)。

Examples
--------
>>> import numpy as np, annotate
>>> flat = np.full((8, 8), 128 / 255.0)          # 中間調 —— 反転が消える地
>>> rep = annotate.annotate_invert_visibility(flat, np.ones((8, 8), bool))
>>> round(rep["min_contrast"], 3)
1.014
>>> rep["invisible_fraction"]
1.0
>>> annotate.annotate_invert_visibility(flat, np.ones((8, 8), bool),
...                                     mode="contrast")["min_contrast"] > 4.5
True

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [dataset_conventions](../guides/dataset_conventions.md) — 学習データセット規約の知識 — COCO / YOLO / VOC と外観検査での落とし穴

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [annotate_paper_tour](../../../../examples/annotate_paper_tour.py) — `py -3.11 examples/annotate_paper_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
