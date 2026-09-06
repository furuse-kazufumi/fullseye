---
op: shape_explained_variance
dim: shapestat
category: model
in: shapemodel
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# shape_explained_variance — SHAPESTAT `model` op

- **データ種**: `shapemodel` → `signal`
- **呼び出し**: `import shapestats; shapestats.shape_explained_variance(model)` (または `opsshapestat.get("shape_explained_variance")`)

## 使い方

各主成分の寄与率(合計 1)。→ ``(k,)``。

## 詳しい使い方ガイド

- [shape_statistics ファミリ ガイド](../guides/shape_statistics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

[shape_reconstruct](shape_reconstruct.md)

## 同カテゴリ(`model`)

[shape_pca](shape_pca.md) · [shape_project](shape_project.md) · [shape_reconstruct](shape_reconstruct.md) · [shape_mahalanobis](shape_mahalanobis.md) · [shape_synthesize](shape_synthesize.md)

---
*Provenance: shapestats.py — SHAPESTAT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
