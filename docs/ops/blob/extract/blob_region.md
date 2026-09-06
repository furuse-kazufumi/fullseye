---
op: blob_region
dim: blob
category: extract
in: labels2d
out: mask
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_region — BLOB `extract` op

- **データ種**: `labels2d` → `mask`
- **呼び出し**: `import blob2d; blob2d.blob_region(labels: 'Any', index: 'int') -> 'np.ndarray'` (または `opsblob.get("blob_region")`)

## 使い方

物体 1 個を二値領域(bool)として抜く。``index`` は **1 起点**。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`mask` を入力に取れる)

[blob_label](../connect/blob_label.md)

## 同カテゴリ(`extract`)

[blob_boundaries](blob_boundaries.md) · [blob_overlay](blob_overlay.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
