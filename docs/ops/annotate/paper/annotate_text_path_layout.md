---
op: annotate_text_path_layout
dim: annotate
category: paper
in: text
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# annotate_text_path_layout — ANNOTATE `paper` op

- **データ種**: `text` → `table`
- **呼び出し**: `import annotate; annotate.annotate_text_path_layout(text, path, font_size=13, font_path=None, spacing=1.0, start=0.0)` (または `opsannotate.get("annotate_text_path_layout")`)

## 使い方

table(dict)を返す: 折れ線に沿って 1 文字ずつ置く位置と傾き(弧長で決める)。

文字 i の中心は弧長 ``s_i = start + Σ_{j<i} w_j*spacing + w_i/2``、傾きは
その位置の線分の接線角(画面座標、度)。経路より長い文字列は ValueError。

Returns
-------
dict
    ``{"chars": [{"char","s","xy","angle_deg","width"}], "length": 経路長,
    "used": 文字が占める弧長}``。

Raises
------
ValueError
    文字が空、経路が 2 点未満か長さゼロ、非有限、文字列が経路より長い。

## 詳しい使い方ガイド

- [figure_annotation ファミリ ガイド](../guides/figure_annotation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`paper`)

[annotate_leader_layout](annotate_leader_layout.md) · [annotate_leader](annotate_leader.md) · [annotate_markers](annotate_markers.md) · [annotate_legend](annotate_legend.md) · [annotate_dimension_layout](annotate_dimension_layout.md) · [annotate_dimension](annotate_dimension.md) · [annotate_angle_layout](annotate_angle_layout.md) · [annotate_angle](annotate_angle.md)

---
*Provenance: annotate.py — ANNOTATE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
