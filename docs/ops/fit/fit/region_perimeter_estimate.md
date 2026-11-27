---
op: region_perimeter_estimate
dim: fit
category: fit
in: mask
out: measurement
gpu: なし
examples: [shape_factors_closed_form]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.2.0  # fullseye lib version this note was generated for
---

# region_perimeter_estimate — FIT `fit` op

- **データ種**: `mask` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.region_perimeter_estimate(region, method: 'str' = 'skimage') -> 'float'` (実装を直接呼ぶなら `import measure; measure.region_perimeter_estimate(region, method: 'str' = 'skimage') -> 'float'`、台帳から引くなら `opsfit.get("region_perimeter_estimate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Estimate a binary region's perimeter with an explicit estimator / 推定量を明示して領域の周囲長を測る。

``method='skimage'`` uses ``skimage.measure.perimeter`` with its four-neighbour
convention, the same estimator used by the existing ``contlength`` and
``compactness`` operators for a single connected component. ``'crofton'`` uses
``skimage.measure.perimeter_crofton(..., directions=4)``. ``'chain'`` counts
exposed four-direction pixel edges (a Freeman 4-chain length); it is available
without scikit-image and is exact for an axis-aligned pixel square, but has a
large positive bias for a circle.

The value is in pixels and includes every foreground component and every hole.
Foreground means ``region > 0.5``. An empty input (``region`` with zero
elements) returns an empty perimeter (reason: without foreground pixels,
no exposed edge exists to measure); its numeric value is ``0.0``.
空の入力(``region`` が 0 要素)は空の周囲長を返す(理由: 前景画素が無く、測る
露出辺も無い)。数値は ``0.0`` となる。これは普遍的に真な周囲長を選ぶのでは
なく、次の *measurement convention* である:
on the fixed closed-form probes (disc ``r=96``, square side ``128``), the
ratios to truth are respectively ``1.0518 / 0.9922`` (``skimage``),
``1.0016 / 0.9459`` (``crofton``), and ``1.2799 / 1.0000`` (``chain``).
Do not substitute its result into an existing feature threshold without
revalidating that threshold.

``region`` must be a finite numeric 2-D array. Invalid dimensionality, values,
or a method other than ``'skimage'``, ``'crofton'`` or ``'chain'`` raises
``ValueError``; the scikit-image methods raise ``ImportError`` when that
optional dependency is unavailable. 既存 op の既定値は変更しない。推定量を
選ぶ必要があるときだけ、この関数を明示して使う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_factors_closed_form](../../../../examples/shape_factors_closed_form.py) — `py -3.11 examples/shape_factors_closed_form.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`fit`)

[fit_circle_geometric](fit_circle_geometric.md) · [fit_curve_principal_axis](fit_curve_principal_axis.md)

---
*Provenance: measure.py — FIT operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
