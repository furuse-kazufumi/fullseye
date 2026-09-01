---
op: vol_label_legend
dim: volcolor
category: measure
in: labels
out: table
examples: [voxel_labels_color]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# vol_label_legend — VOLCOLOR `measure` op

- **データ種**: `labels` → `table`
- **呼び出し**: `import volcolor; volcolor.vol_label_legend(labels, props=None, seed: 'int' = 0, spacing=None, measure: 'str' = 'volume', top=None)` (または `opsvolcolor.get("vol_label_legend")`)

## 使い方

「どの色がどの成分で、その計測値は幾つか」の凡例表を返す。

色だけを出して意味の読めない図を作らないための op。返りは ``list[dict]``:

  ``label`` · ``rgb`` ``(r, g, b)`` float ``[0, 1]`` · ``hex`` ``"#rrggbb"`` ·
  ``voxel_count`` · ``volume`` · ``measure`` 並べ替えに使った量の名前 ·
  ``value`` その値 · ``rank`` 1 始まりの順位 · ``share`` 全成分の
  *measure* 合計に対する割合。

*measure* は props に載っている数値キーなら何でもよい(``"volume"``
``"voxel_count"`` ``"equivalent_diameter"``、``volops.vol_region_props`` を
渡したなら ``"sphericity"`` も)。降順に並べ、同点はラベル番号の昇順で割る
(**決定的**)。*top* を与えると上位 N 件だけ返す。

実在するラベルは ``np.bincount`` の非ゼロから取る。``labels.max()`` を成分数と
見なさないので、番号に欠番があっても件数も順位も狂わない
(``tests/test_volcolor.py::test_stats_do_not_invent_the_component_count_from_max``)。

Raises ``ValueError`` when *measure* is not a numeric key of *props*, when
*props* does not cover the labels present, or on a bad *top*.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [voxel_labels_color](../../../../examples/voxel_labels_color.py) — `py -3.11 examples/voxel_labels_color.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`measure`)

[vol_label_shape_stats](vol_label_shape_stats.md)

---
*Provenance: volcolor.py — VOLCOLOR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
