---
op: wave_mode_frequencies
dim: math
category: wave
in: 
out: signal
examples: [poc_beats_fringes_and_screens]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# wave_mode_frequencies — MATH `wave` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.wave_mode_frequencies(kind='rectangular', count=10, aspect=1.0)` (実装を直接呼ぶなら `import mathops; mathops.wave_mode_frequencies(kind='rectangular', count=10, aspect=1.0)`、台帳から引くなら `opsmath.get("wave_mode_frequencies")`)

## 使い方

The eigenvalue ladder of a membrane — a closed form you can check against.

``kind="rectangular"``: the Dirichlet eigenvalues of a rectangle are
``pi**2 * (m**2 + n**2 / aspect**2)`` for ``m, n >= 1`` — **not** ``m n pi``,
which is the usual slip. ``kind="circular"``: the free-edge (Neumann) circular
membrane's eigenvalues are the squares of the zeros of ``J'_m``.

★**Why this earns its place**: this ladder is what separates a membrane from a
plate, and it is exactly computable. The square drum's ratios start
2, 5, 5, 8, 10, 10, 13 (in units of ``pi**2``) — the repeated 5 and 10 are the
famous degeneracies that make the square drum's modes ambiguous, and a wrong
implementation loses them.

Returns a ``signal``: the eigenvalues, ascending.

**Raises** ``ValueError``: unknown kind; non-positive count or aspect; a
circular request without scipy.

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

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [interp_scattered](../interp_poly/interp_scattered.md)

## 同カテゴリ(`wave`)

[wave_membrane_mode](wave_membrane_mode.md) · [wave_nodal_lines](wave_nodal_lines.md) · [wave_two_slit](wave_two_slit.md) · [wave_fringe_period](wave_fringe_period.md) · [wave_grating_orders](wave_grating_orders.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
