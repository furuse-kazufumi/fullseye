---
op: blob_label
dim: blob
category: connect
in: mask
out: labels2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_label — BLOB `connect` op

- **データ種**: `mask` → `labels2d`
- **呼び出し**: `import blob2d; blob2d.blob_label(region: 'Any', connectivity: 'int' = 8) -> 'np.ndarray'` (または `opsblob.get("blob_label")`)

## 使い方

二値領域を連結成分に分け、``int32`` のラベル画像(背景 0、物体 1..n)を返す。

Parameters
----------
region : array_like
    2-D。``> 0`` が前景(bool でも実数でもよい。NaN は背景)。
connectivity : {4, 8}
    斜めに触れる 2 画素をつなぐか。既定 8 は ``ndimage.label`` と
    HALCON ``connection`` の既定に一致する。**4 にすると斜めに接した塊が
    別々に数えられる**。

Returns
-------
numpy.ndarray
    ``(H, W)`` の ``int32``。番号は 1 から連番で歯抜けが無い。

Examples
--------
>>> import numpy as np
>>> m = np.zeros((6, 9), bool); m[1:4, 1:4] = True; m[1:4, 5:8] = True
>>> int(blob_label(m).max())
2

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`labels2d` を入力に取れる)

[blob_features](../measure/blob_features.md) · [blob_select](../select/blob_select.md) · [blob_select_largest](../select/blob_select_largest.md) · [blob_region](../extract/blob_region.md) · [blob_boundaries](../extract/blob_boundaries.md) · [blob_overlay](../extract/blob_overlay.md)

## 同カテゴリ(`connect`)

—

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
