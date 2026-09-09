---
op: interp_scattered
dim: math
category: interp_poly
in: points × signal × points
out: table
examples: [poc_datacenter_thermal_field, poc_multibeam_bathymetry, poc_stockpile_volume]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# interp_scattered — MATH `interp_poly` op

- **データ種**: `points × signal × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.interp_scattered(points, values, query, method='linear', fill_value=nan, rescale=False, neighbors=None)` (実装を直接呼ぶなら `import mathops; mathops.interp_scattered(points, values, query, method='linear', fill_value=nan, rescale=False, neighbors=None)`、台帳から引くなら `opsmath.get("interp_scattered")`)

## 使い方

Values at *query* from **scattered** samples — sensor nets, boreholes, weather.

:func:`interp_linear` and :func:`interp_cubic` need samples on a sorted 1-D
axis. A great deal of measurement does not arrive that way: temperature
sensors bolted wherever a rack allowed, boreholes drilled where access
permitted, weather stations placed by history. This is the N-D scattered
entry point (``scipy.interpolate``), and it returns **how much of the answer
was not interpolation at all**.

*method*:

``"nearest"``
    the value of the closest sample. Defined everywhere, and never
    overshoots, but it is a staircase: on a smooth field the step itself
    becomes a false feature. Measured on a smooth 3-D field sampled at 0.60,
    the nearest-neighbour reconstruction leaves a residual of 0.975 units
    where the sensor noise is only 0.15 — 6.5 times the noise, and none of
    it is noise.
``"linear"``
    barycentric interpolation on a Delaunay triangulation. Never exceeds the
    surrounding samples, and is **undefined outside their convex hull**.
``"rbf"``
    a thin-plate radial basis function through every sample. Smooth and
    defined everywhere, but it **overshoots its own nodes**: measured on the
    same field it returns peaks 1.372 times the sampled height, which is a
    37 % over-statement of a hot spot that no interpolation of the data can
    justify.

**The point of the ``outside`` return value.** Sensors sit inside a room, a
site, a country; the corners are always outside their hull. Ask a linear
interpolator there and it returns ``fill_value``, or, if a caller quietly
falls back to nearest, it returns a different method's answer under the
first method's name. Measured on a 12 x 8.4 x 3.0 m room sampled at 1.20 m
spacing, **71.2 %** of the evaluation grid lay outside the hull. A number
that large has to be visible, so it is returned rather than logged.

Parameters
----------
points : (n, d) array_like
    Sample coordinates. 1-D input is accepted and treated as ``(n, 1)``.
values : (n,) array_like
query : (m, d) or (..., d) array_like
    Where to evaluate. The leading shape is preserved in the result.
method : {"linear", "nearest", "rbf"}
fill_value : float
    Returned outside the convex hull for ``"linear"``. ``"nearest"`` and
    ``"rbf"`` are defined everywhere and ignore it.
rescale : bool
    Normalise each axis before triangulating. Needed when the axes have very
    different units (metres against millimetres); ignored by ``"rbf"``.
neighbors : int or None
    ``"rbf"`` only: solve against the *k* nearest samples instead of all of
    them. The global solve is O(n^3); measured on 5000 query points in 3-D,
    it costs 0.55 / 1.76 / 7.53 s at 1400 / 4000 / 8000 samples, while
    ``neighbors=48`` costs 0.38 / 0.55 / 0.81 s. Below a few thousand
    samples the global solve is fine and exact — the knob earns its place
    above that. ``None`` keeps the exact global solution.

Returns
-------
dict
    ``value`` (query shape), ``outside`` (bool mask, query shape, of query
    points beyond the convex hull of the samples), ``outside_fraction``,
    ``method``, ``n_points``.

Fail-closed: fewer samples than ``d + 1`` cannot define a simplex, and
raises ``ValueError`` rather than returning a field made of ``fill_value``.

See also
--------
interp_linear : the sorted 1-D case, which is cheaper and needs no hull.

## ファミリ共通の入力契約(fail-closed)

mathops の全 op は入力を検証してから計算する(黙って通さない):

- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。
- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。
- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。
- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。
- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は `mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。

## 詳しい使い方ガイド

- [math_metrology ファミリ ガイド](../guides/math_metrology.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_datacenter_thermal_field](../../../../examples/poc_datacenter_thermal_field.py) — `py -3.11 examples/poc_datacenter_thermal_field.py`
- [poc_multibeam_bathymetry](../../../../examples/poc_multibeam_bathymetry.py) — `py -3.11 examples/poc_multibeam_bathymetry.py`
- [poc_stockpile_volume](../../../../examples/poc_stockpile_volume.py) — `py -3.11 examples/poc_stockpile_volume.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`interp_poly`)

[interp_linear](interp_linear.md) · [interp_cubic](interp_cubic.md) · [poly_fit](poly_fit.md) · [poly_eval](poly_eval.md) · [poly_roots](poly_roots.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
