---
op: ptile_threshold
dim: segmentation
category: threshold
in: image2d
out: scalar
examples: [poc_threshold_transfer_after_normalization]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# ptile_threshold — SEGMENTATION `threshold` op

- **データ種**: `image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.ptile_threshold(image, p: 'float' = 0.01, polarity: 'str' = 'bright') -> 'float'` (実装を直接呼ぶなら `import normalized_threshold; normalized_threshold.ptile_threshold(image, p: 'float' = 0.01, polarity: 'str' = 'bright') -> 'float'`、台帳から引くなら `opssegmentation.get("ptile_threshold")`)

## 使い方

P-tile 法で面積率 *p* を明または暗側に置くグレー値しきい値を返す。

Doyle (1962) の P-tile 法に従い、画素を明るさ順に並べ、指定した側の
``ceil(p * N)`` 画素と残りの境界をしきい値にする。隣接する 2 値の中点を
返すため、値が異なる境界では ``image > threshold`` (``bright``)または
``image < threshold`` (``dark``)が指定個数をそのまま選ぶ。同値画素が境界を
またぐ離散ヒストグラムでは面積率を厳密に分けられないため、その同値を
しきい値として返す。画素を恣意的に間引いて割合だけを合わせることはしない。

Parameters
----------
image : array-like
    有限値だけからなる空でない 2-D 画像。値域は限定しない。
p : float
    前景にしたい面積率。``0 < p < 1``。``p=0`` / ``p=1`` は境界の両側が
    存在せず、有限なしきい値を定義できないため ``ValueError`` で拒否する。
polarity : {'bright', 'dark'}
    ``bright`` は明るい側、``dark`` は暗い側を面積率 *p* にする。

Returns
-------
float
    元画像と同じグレー値単位のしきい値。

**空入力は分布を持たないため拒否し、しきい値を捏造しない。**

References
----------
W. Doyle, "Operations Useful for Similarity-Invariant Pattern Recognition,"
*Journal of the ACM*, 9(2), 1962, pp. 259-267.

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [graph_hierarchy_and_thresholds](../guides/graph_hierarchy_and_thresholds.md) — グラフ・階層・閾値の定理でつくる分割 — 何が厳密で、どこで割れ方が倒れるか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_threshold_transfer_after_normalization](../../../../examples/poc_threshold_transfer_after_normalization.py) — `py -3.11 examples/poc_threshold_transfer_after_normalization.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`threshold`)

[threshold_triangle](threshold_triangle.md) · [threshold_isodata](threshold_isodata.md) · [threshold_kittler](threshold_kittler.md) · [threshold_kapur](threshold_kapur.md) · [image_standardize](image_standardize.md) · [sigma_threshold](sigma_threshold.md)

---
*Provenance: normalized_threshold.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
