---
op: hom_vector_to_proj_hom_mat2d
dim: calib
category: fit
in: points
out: matrix
examples: [poc_panorama_drift, poc_wound_area_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# hom_vector_to_proj_hom_mat2d — CALIB `fit` op

- **データ種**: `points` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.hom_vector_to_proj_hom_mat2d(src, dst) -> 'np.ndarray'` (実装を直接呼ぶなら `import fit_transform; fit_transform.hom_vector_to_proj_hom_mat2d(src, dst) -> 'np.ndarray'`、台帳から引くなら `opscalib.get("hom_vector_to_proj_hom_mat2d")`)

## 使い方

4 点以上の対応から射影変換(homography, DLT)3x3 を求める(hom_vector_to_proj_hom_mat2d)。

本モジュールの契約どおり点は ``(row, col)``: 返る ``H`` は ``(row, col, 1)`` の同次ベクトルに
左から掛けて ``(row', col', w)`` を与える(``transforms.projective_trans_point_2d(H, row, col)``
と整合)。数値安定化のため両点集合を Hartley 正規化してから DLT を解き
``H = T_dst⁻¹ · H_n · T_src`` で戻す。

(旧実装は DLT 行を ``(col, row)`` 順で組んでいたため、``(row, col, 1)`` に適用すると
2 座標を取り違えた行列を返していた — 2026-09-02 実測 max err 27 px。)

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_panorama_drift](../../../../examples/poc_panorama_drift.py) — `py -3.11 examples/poc_panorama_drift.py`
- [poc_wound_area_tracking](../../../../examples/poc_wound_area_tracking.py) — `py -3.11 examples/poc_wound_area_tracking.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

—

## 同カテゴリ(`fit`)

[vector_to_rigid](vector_to_rigid.md) · [vector_to_similarity](vector_to_similarity.md) · [vector_angle_to_rigid](vector_angle_to_rigid.md)

---
*Provenance: fit_transform.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
