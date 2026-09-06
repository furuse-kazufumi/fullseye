---
op: blob_distance
dim: blob
category: split
in: mask
out: image2d
examples: [blob_split_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_distance — BLOB `split` op

- **データ種**: `mask` → `image2d`
- **呼び出し**: `import blob2d; blob2d.blob_distance(region: 'Any', spacing: 'float' = 1.0) -> 'np.ndarray'` (または `opsblob.get("blob_distance")`)

## 使い方

前景の各画素から**いちばん近い背景まで**の距離。単位は ``spacing`` 倍。

``scipy.ndimage.distance_transform_edt`` そのもの。**わざわざ口を作った
理由**は、進化 op の ``distance_transform`` が最大値で正規化して返すため
(``poc_cell_counting`` の実測: 出力の最大が常に 1.0)、**画素単位の距離が
取れない**こと。分水嶺の種を作るには絶対値が要る。

Examples
--------
>>> import numpy as np
>>> m = np.zeros((21, 21), bool); m[5:16, 5:16] = True
>>> float(blob_distance(m).max())      # 11x11 の正方形の中心まで
6.0

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [blob_split_tour](../../../../examples/blob_split_tour.py) — `py -3.11 examples/blob_split_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[blob_seeds](blob_seeds.md) · [blob_split](blob_split.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`split`)

[blob_seeds](blob_seeds.md) · [blob_split](blob_split.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
