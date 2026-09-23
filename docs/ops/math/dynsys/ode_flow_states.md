---
op: ode_flow_states
dim: math
category: dynsys
in: 
out: table
examples: [poc_what_a_picture_cannot_check]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ode_flow_states — MATH `dynsys` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.ode_flow_states(system='lorenz', params=None, x0=None, t_end=40.0, dt=0.005, method='rk4')` (実装を直接呼ぶなら `import mathops; mathops.ode_flow_states(system='lorenz', params=None, x0=None, t_end=40.0, dt=0.005, method='rk4')`、台帳から引くなら `opsmath.get("ode_flow_states")`)

## 使い方

Integrate a named vector field — the trajectory, with the order you paid for.

Explicit Runge-Kutta on one of the named systems (``lorenz``, ``rossler``,
``harmonic``, ``linear``). ``method="rk4"`` is the classical 4th-order step;
``method="euler"`` is there as a **control group** — the same picture comes out
of both, and only the error tells them apart.

★**Why the field is a name, not a function**: the typed ledger registers inputs
by sort and the chain fuzzer builds arguments from data, so a callable can
never be reached from there. A name (or, for ``linear``, the matrix itself in
``params``) keeps every op in this family reachable from the ledger.

★**Why this earns its place**: for ``system="linear"`` the exact solution is
``expm(A t) x0``, so the error is known in closed form — and halving ``dt``
divides it by **16**, which is what "4th order" means. A drawing of an
attractor cannot be checked; this can.

Parameters
----------
system : str
    One of ``DYNSYS_SYSTEMS``.
params : floats or None
    System parameters (defaults in ``DYNSYS_SYSTEMS``). For ``linear`` this is
    the matrix ``A`` in row-major order (``n*n`` numbers).
x0 : floats or None
    Initial state (default: a point on the attractor / unit first coordinate).
t_end, dt : float
    Integration window and step. ``t_end / dt`` must stay under 4,000,000.
method : "rk4" | "euler"

Returns a ``states`` table: ``t`` (S,) and ``x`` (S, n).

**Raises** ``ValueError``: unknown system or method; wrong parameter count;
non-finite input; ``dt`` not positive; a step count over the cap; a trajectory
that left float range (the field diverged — reported, never silently clipped).

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

- [poc_what_a_picture_cannot_check](../../../../examples/poc_what_a_picture_cannot_check.py) — `py -3.11 examples/poc_what_a_picture_cannot_check.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](dynsys_poincare_section.md)

## 同カテゴリ(`dynsys`)

[ode_vector_field_grid](ode_vector_field_grid.md) · [dynsys_poincare_section](dynsys_poincare_section.md) · [dynsys_lyapunov_spectrum](dynsys_lyapunov_spectrum.md) · [dynsys_bifurcation_map](dynsys_bifurcation_map.md) · [dynsys_correlation_dimension](dynsys_correlation_dimension.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
