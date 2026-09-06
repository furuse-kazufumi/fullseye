---
op: blob_split
dim: blob
category: split
in: labels2d × labels2d × image2d
out: labels2d
examples: [blob_split_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_split — BLOB `split` op

- **データ種**: `labels2d × labels2d × image2d` → `labels2d`
- **呼び出し**: `import blob2d; blob2d.blob_split(labels: 'Any', seeds: 'Any', distance: 'Any') -> 'np.ndarray'` (または `opsblob.get("blob_split")`)

## 使い方

種から**高いところ順に**領域を広げて、融合した塊を割る(分水嶺)。

``distance`` の高い画素から順に、隣接する既知のラベルを取り込んでいく
(immersion 型の分水嶺を、距離の降順で回す形)。**種を持たない塊はその
まま残す** —— 割る材料が無いのに消すのは嘘になるため。

``segmentation.watersheds_marker`` を使わないのは、**skimage が無い環境で
黙って別の算法(マーカーからの最近傍)に落ちる**から。落ちた先は画像を
一切見ないので、同じ関数名で違うものが返る。ここは numpy と scipy だけで
閉じる。

Parameters
----------
labels : array_like
    割る対象。:func:`blob_label` の出力(``> 0`` の画素だけが割られる)。
seeds : array_like
    :func:`blob_seeds` の出力。``labels`` の外にある種は無視する。
distance : array_like
    優先度。ふつうは :func:`blob_distance` の出力。

Returns
-------
numpy.ndarray
    ``int32`` のラベル画像。番号は 1 から振り直す。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [blob_split_tour](../../../../examples/blob_split_tour.py) — `py -3.11 examples/blob_split_tour.py`

## 型が繋がる次の op(`labels2d` を入力に取れる)

[blob_features](../measure/blob_features.md) · [blob_select](../select/blob_select.md) · [blob_select_largest](../select/blob_select_largest.md) · [blob_region](../extract/blob_region.md) · [blob_boundaries](../extract/blob_boundaries.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`split`)

[blob_distance](blob_distance.md) · [blob_seeds](blob_seeds.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
