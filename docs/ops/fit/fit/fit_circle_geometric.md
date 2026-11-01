---
op: fit_circle_geometric
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

# fit_circle_geometric — FIT `fit` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_circle_geometric(points, *, max_iterations: 'int' = 100, radius_limit_factor: 'float' = 1000000.0) -> 'dict'` (実装を直接呼ぶなら `import measure; measure.fit_circle_geometric(points, *, max_iterations: 'int' = 100, radius_limit_factor: 'float' = 1000000.0) -> 'dict'`、台帳から引くなら `opsfit.get("fit_circle_geometric")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

短い円弧を含む ``(row, col)`` 点に幾何距離の最小二乗で円と半径を当てはめる。

Kåsa's algebraic fit supplies the initial centre and radius, then a
Levenberg--Marquardt solve minimises ``hypot(x-cx, y-cy) - r`` (Chernov &
Lesort 2005).  Returns ``cy``, ``cx``, ``r``, geometric ``rms``,
``iterations`` and ``converged``. ``max_iterations`` is the maximum number
of function evaluations. ``radius_limit_factor`` bounds the fitted radius
relative to the point-cloud span; an exceeded bound is reported as
``ValueError`` instead of returning a line-like, effectively infinite
circle. Non-finite, collinear, or fewer than three points are also rejected.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fit_ops_from_knowhow](../../../../examples/fit_ops_from_knowhow.py) — `py -3.11 examples/fit_ops_from_knowhow.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`fit`)

[fit_curve_principal_axis](fit_curve_principal_axis.md)

---
*Provenance: measure.py — FIT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
