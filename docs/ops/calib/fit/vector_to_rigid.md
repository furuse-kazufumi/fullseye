---
op: vector_to_rigid
dim: calib
category: fit
in: keypoints
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# vector_to_rigid — CALIB `fit` op

- **データ種**: `keypoints` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.vector_to_rigid(src, dst) -> 'np.ndarray'` (実装を直接呼ぶなら `import fit_transform; fit_transform.vector_to_rigid(src, dst) -> 'np.ndarray'`、台帳から引くなら `opscalib.get("vector_to_rigid")`)

## 使い方

対応点から 2D 剛体変換(回転+並進、Kabsch)を求める(vector_to_rigid)。

fail-closed: 対応が 2 組未満・数が合わない・非有限・src の点が全部 1 点に重なる
(回転が決まらない)ときは ``ValueError``。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[project_hom_point_hom_mat3d](../project/project_hom_point_hom_mat3d.md)

## 同カテゴリ(`fit`)

[vector_to_similarity](vector_to_similarity.md) · [vector_angle_to_rigid](vector_angle_to_rigid.md) · [hom_vector_to_proj_hom_mat2d](hom_vector_to_proj_hom_mat2d.md)

---
*Provenance: fit_transform.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
