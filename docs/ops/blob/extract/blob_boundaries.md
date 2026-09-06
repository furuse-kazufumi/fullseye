---
op: blob_boundaries
dim: blob
category: extract
in: labels2d
out: mask
examples: [poc_gear_tooth_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# blob_boundaries — BLOB `extract` op

- **データ種**: `labels2d` → `mask`
- **呼び出し**: `import blob2d; blob2d.blob_boundaries(labels: 'Any') -> 'np.ndarray'` (または `opsblob.get("blob_boundaries")`)

## 使い方

物体の輪郭(1 画素幅、bool)。**隣り合う物体の境目も残る**。

内側の縁を取る(自分と違うラベルに隣接する前景画素)ので、輪郭は必ず
物体の内部にある —— 外側を取ると隣の物体の画素を輪郭だと言うことになる。

## 詳しい使い方ガイド

- [blob_analysis ファミリ ガイド](../guides/blob_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_gear_tooth_metrology](../../../../examples/poc_gear_tooth_metrology.py) — `py -3.11 examples/poc_gear_tooth_metrology.py`

## 型が繋がる次の op(`mask` を入力に取れる)

[blob_label](../connect/blob_label.md) · [blob_distance](../split/blob_distance.md)

## 同カテゴリ(`extract`)

[blob_region](blob_region.md) · [blob_overlay](blob_overlay.md)

---
*Provenance: blob2d.py — BLOB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
