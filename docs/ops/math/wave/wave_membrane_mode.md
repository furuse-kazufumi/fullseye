---
op: wave_membrane_mode
dim: math
category: wave
in: 
out: matrix
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# wave_membrane_mode — MATH `wave` op

- **データ種**: `なし` → `matrix`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_membrane_mode(kind='rectangular', m=2, n=3, shape=(256, 256), aspect=1.0, free_edge=True)` (実装を直接呼ぶなら `import mathops; mathops.wave_membrane_mode(kind='rectangular', m=2, n=3, shape=(256, 256), aspect=1.0, free_edge=True)`、台帳から引くなら `opsmath.get("wave_membrane_mode")`)

## 使い方

One eigenmode of a vibrating **membrane** — the shape the sand draws.

★**This is a membrane, not a plate.** The familiar Chladni pattern
``cos(m pi x) cos(n pi y) - cos(n pi x) cos(m pi y)`` solves the Helmholtz
equation with free (Neumann) edges; a real Chladni *plate* obeys the
**biharmonic** equation and has a different frequency ladder. The pictures
look alike, the frequencies do not — so this op says membrane and is checked
against membrane truth only.

``kind="rectangular"`` returns the (possibly combined) cosine mode over a
rectangle of the given *aspect*; ``kind="circular"`` returns
``J_m(k r) cos(m theta)`` with ``k`` from the Bessel zero, zero outside the disc.

★**Why this earns its place**: the nodal lines of a rectangular mode are known
**by count** — a simple ``(m, n)`` mode has ``m-1`` interior vertical and
``n-1`` horizontal nodal lines — and the circular mode's nodal circles are at
the ratios of successive Bessel zeros. The drawing can therefore be graded.

Returns a ``matrix`` (signed displacement, peak scaled to 1). Use
:func:`wave_nodal_lines` for the zero set.

**Raises** ``ValueError``: unknown kind; ``m``/``n`` below the valid range;
a grid over the cap; non-positive aspect; ``free_edge=False`` combined with
``m == n`` for the combined mode (the difference vanishes identically).

HALCON: no operator.

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

- [poc_beats_fringes_and_screens](../../../../examples/poc_beats_fringes_and_screens.py) — `py -3.11 examples/poc_beats_fringes_and_screens.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [mat_svd](../linalg/mat_svd.md) · [mat_eigh](../linalg/mat_eigh.md) · [mat_pinv](../linalg/mat_pinv.md) · [mat_cond](../linalg/mat_cond.md) · [stat_covariance](../stats/stat_covariance.md) · [stat_correlation](../stats/stat_correlation.md)

## 同カテゴリ(`wave`)

[wave_mode_frequencies](wave_mode_frequencies.md) · [wave_nodal_lines](wave_nodal_lines.md) · [wave_two_slit](wave_two_slit.md) · [wave_fringe_period](wave_fringe_period.md) · [wave_grating_orders](wave_grating_orders.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
