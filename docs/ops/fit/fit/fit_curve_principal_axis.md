---
op: fit_curve_principal_axis
dim: fit
category: fit
in: keypoints
out: table
gpu: なし
examples: [fit_ops_from_knowhow]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fit_curve_principal_axis — FIT `fit` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_curve_principal_axis(points, degree: 'int' = 2, *, isotropy_ratio: 'float' = 0.95) -> 'dict'` (実装を直接呼ぶなら `import measure; measure.fit_curve_principal_axis(points, degree: 'int' = 2, *, isotropy_ratio: 'float' = 0.95) -> 'dict'`、台帳から引くなら `opsfit.get("fit_curve_principal_axis")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

斜めの曲がった縁を主軸へ回してから多項式 ``y'=f(x')`` を当てはめる。

Returns the image-plane ``angle_deg``, ``centroid`` (row, col), polynomial
``coefficients`` in NumPy's descending-power convention, orthonormal
``axes`` (rows are local x/y axes in col,row order), local coordinates,
``fitted_points`` in the original row/col frame, and a gradient-normalised
geometric ``rms``. ``degree`` must be at least one and leave more samples
than coefficients. A nearly round cloud (minor/major variance ratio at or
above ``isotropy_ratio``) is rejected because its principal direction is
undefined.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_ops_from_knowhow](../../../../examples/fit_ops_from_knowhow.py) — `py -3.11 examples/fit_ops_from_knowhow.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`fit`)

[fit_circle_geometric](fit_circle_geometric.md)

---
*Provenance: measure.py — FIT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
