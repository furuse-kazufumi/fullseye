---
op: vector_angle_to_rigid
dim: calib
category: fit
in: 
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# vector_angle_to_rigid — CALIB `fit` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.vector_angle_to_rigid(row1, col1, angle1, row2, col2, angle2) -> 'np.ndarray'` (実装を直接呼ぶなら `import fit_transform; fit_transform.vector_angle_to_rigid(row1, col1, angle1, row2, col2, angle2) -> 'np.ndarray'`、台帳から引くなら `opscalib.get("vector_angle_to_rigid")`)

## 使い方

1 組の (点, 角度) から 2D 剛体変換を求める(vector_angle_to_rigid)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`fit`)

[vector_to_rigid](vector_to_rigid.md) · [vector_to_similarity](vector_to_similarity.md) · [hom_vector_to_proj_hom_mat2d](hom_vector_to_proj_hom_mat2d.md)

---
*Provenance: fit_transform.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
