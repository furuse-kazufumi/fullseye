---
op: threshold_kittler
dim: segmentation
category: threshold
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# threshold_kittler — SEGMENTATION `threshold` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.threshold_kittler(image, *, nbins: 'int' = 256) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.threshold_kittler(image, *, nbins: 'int' = 256) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("threshold_kittler")`)

## 使い方

最小誤差閾値(Kittler–Illingworth 1986): 各ビン t で低い側(ビン ≤ t)と高い側に分け、
J(t) = 1 + 2(P1 ln σ1 + P2 ln σ2) − 2(P1 ln P1 + P2 ln P2) を最小にする(σ は各側のビンの中心の標準偏差。どちらかの側の
σ が 0 のビンは除く)。返す: ``threshold`` = そのビンの上端(mask はビンの番号 > t で決める = 端の値も矛盾なし)、
``mask``、``bin``、``criterion``(J、除いたビンは nan)。

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

[threshold_triangle](threshold_triangle.md) · [threshold_isodata](threshold_isodata.md) · [threshold_kapur](threshold_kapur.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
