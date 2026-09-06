---
op: blob_overlay
dim: blob
category: extract
in: image2d × labels2d
out: rgb
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_overlay — BLOB `extract` op

- **データ種**: `image2d × labels2d` → `rgb`
- **呼び出し**: `import blob2d; blob2d.blob_overlay(image: 'Any', labels: 'Any', alpha: 'float' = 0.5, seed: 'int' = 0) -> 'np.ndarray'` (または `opsblob.get("blob_overlay")`)

## 使い方

元画像の上に物体を色分けして重ね、``(H, W, 3)`` の float RGB を返す。

この族の**出口**。作れて測れるが見られない型にしないために置く。
色は :func:`fullseye.colorize_labels` と同じ規則で、背景は元画像のまま。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`extract`)

[blob_region](blob_region.md) · [blob_boundaries](blob_boundaries.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
