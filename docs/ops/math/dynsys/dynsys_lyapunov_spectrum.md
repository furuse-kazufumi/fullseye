---
op: dynsys_lyapunov_spectrum
dim: math
category: dynsys
in: 
out: signal
examples: [poc_what_a_picture_cannot_check]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# dynsys_lyapunov_spectrum — MATH `dynsys` op

- **データ種**: `なし` → `signal`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dynsys_lyapunov_spectrum(system='lorenz', params=None, x0=None, t_end=200.0, dt=0.005, burn_in=20.0)` (実装を直接呼ぶなら `import mathops; mathops.dynsys_lyapunov_spectrum(system='lorenz', params=None, x0=None, t_end=200.0, dt=0.005, burn_in=20.0)`、台帳から引くなら `opsmath.get("dynsys_lyapunov_spectrum")`)

## 使い方

The Lyapunov spectrum by tangent flow + QR — and the sum you can check.

Integrates the state together with an orthonormal frame of tangent vectors
(the variational equation ``dY/dt = J(x) Y``), re-orthonormalising by QR at
every step and accumulating ``log`` of the diagonal. The exponents come out
**ordered**, largest first.

★★**Why this earns its place — the trace identity.** The sum of the exponents
equals the time-average of the divergence of the field:

    sum(lambda_i) == <div f>

For Lorenz the divergence is the **constant** ``-(sigma + 1 + beta)``, so the
sum is known in closed form: ``-13.6667`` for the classical parameters. That
is an exact target the attractor picture cannot provide. The published largest
exponent (≈ 0.906 for sigma=10, beta=8/3, rho=28) is a second, independent
check.

Returns a ``signal``: the exponents, descending.

**Raises** ``ValueError``: unknown system; non-finite input; ``burn_in`` not
shorter than ``t_end``; a trajectory that left float range.

Limits: the exponents converge like ``1/sqrt(T)`` — a short window gives a
plausible but wrong spectrum. The trace identity converges much faster and is
the honest gate; the individual exponents need long windows.

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

## 型が繋がる次の op(`signal` を入力に取れる)

[mat_solve](../linalg/mat_solve.md) · [mat_lstsq](../linalg/mat_lstsq.md) · [stat_describe](../stats/stat_describe.md) · [stat_histogram](../stats/stat_histogram.md) · [stat_zscore](../stats/stat_zscore.md) · [interp_linear](../interp_poly/interp_linear.md) · [interp_cubic](../interp_poly/interp_cubic.md) · [interp_scattered](../interp_poly/interp_scattered.md)

## 同カテゴリ(`dynsys`)

[ode_flow_states](ode_flow_states.md) · [ode_vector_field_grid](ode_vector_field_grid.md) · [dynsys_poincare_section](dynsys_poincare_section.md) · [dynsys_bifurcation_map](dynsys_bifurcation_map.md) · [dynsys_correlation_dimension](dynsys_correlation_dimension.md)

---
*Provenance: mathops.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
