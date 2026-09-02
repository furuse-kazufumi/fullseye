---
op: annotate_outline_layout
dim: annotate
category: paper
in: mask
out: table
examples: [paper_figure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# annotate_outline_layout — ANNOTATE `paper` op

- **データ種**: `mask` → `table`
- **呼び出し**: `import annotate; annotate.annotate_outline_layout(mask)` (または `opsannotate.get("annotate_outline_layout")`)

## 使い方

table(dict)を返す: 2 値マスクの境界ループ(画素の辺に沿う閉多角形)と重心。

輪郭は :func:`contours_xld._trace_mask_boundaries`(外側 + 穴、成分ごと)。
多角形の面積はマスクの画素数と厳密に一致する。

Returns
-------
dict
    ``{"contours": [(K,2) の (x,y)], "centroid": (x,y), "area": int,
    "bbox": (x,y,w,h), "n_loops": int}``。

Raises
------
ValueError
    mask が 2-D でない、真の画素が無い、非有限。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [paper_figure](../../../../examples/paper_figure.py) — `py -3.11 examples/paper_figure.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
