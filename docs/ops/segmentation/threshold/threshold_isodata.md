---
op: threshold_isodata
dim: segmentation
category: threshold
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# threshold_isodata — SEGMENTATION `threshold` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.threshold_isodata(image, *, nbins: 'int' = 256, max_iter: 'int' = 1000) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.threshold_isodata(image, *, nbins: 'int' = 256, max_iter: 'int' = 1000) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("threshold_isodata")`)

## 使い方

isodata(Ridler–Calvard 1978): t ← (μ_≤t + μ_>t)/2 を **画素の値の上で** 分割が変わらなくなるまで反復(初期値 = 平均)。

分割が止まれば t は μ を計算し直しても動かない = 不動点 t = (μ_low + μ_high)/2 が厳密に成り立つ(``residual`` = 0)。
ヒストグラムの上の不動点(skimage と同じ「ビンの中心 c で 0 ≤ (μ_≤c + μ_>c)/2 − c < ビン幅」)も ``fixed_points`` で返す。
返す: ``threshold``、``mask`` = image > t、``mu_low`` / ``mu_high``、``residual``、``n_iter``、``fixed_points``。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [graph_hierarchy_and_thresholds](../guides/graph_hierarchy_and_thresholds.md) — グラフ・階層・閾値の定理でつくる分割 — 何が厳密で、どこで割れ方が倒れるか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`threshold`)

[threshold_triangle](threshold_triangle.md) · [threshold_kittler](threshold_kittler.md) · [threshold_kapur](threshold_kapur.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
