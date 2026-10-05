---
op: integrate_hamiltonian
dim: math
category: numerics
in: signal × signal
out: table
examples: [numerics_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# integrate_hamiltonian — MATH `numerics` op

- **データ種**: `signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.integrate_hamiltonian(q0, p0, dt: 'float' = 0.05, n_steps: 'int' = 1000, *, system: 'str' = 'harmonic', method: 'str' = 'verlet', **params) -> 'dict'` (実装を直接呼ぶなら `import mathnumerics; mathnumerics.integrate_hamiltonian(q0, p0, dt: 'float' = 0.05, n_steps: 'int' = 1000, *, system: 'str' = 'harmonic', method: 'str' = 'verlet', **params) -> 'dict'`、台帳から引くなら `opsmath.get("integrate_hamiltonian")`)

## 使い方

名前つきのハミルトン系(質量 1)を時間積分する。返り値 ``{"t","q","p","energy","energy_drift"}``。

``method``:
  * ``"verlet"`` —— 速度 Verlet(シンプレクティック・時間反転対称)。エネルギー誤差は O(dt²) で**有界**のまま
    振動し、長時間でも増えない。dt を負にして回すと元の状態に(丸め誤差まで)戻る。
  * ``"euler"`` —— 陽的 Euler(比較用の失敗例)。調和振動子ではエネルギーが毎ステップ (1 + ω²dt²) 倍に増え、
    位相空間で外向きの渦巻きになる。
  * ``"rk4"`` —— 古典的 4 次 Runge–Kutta。短時間はとても正確だが、シンプレクティックではないので
    エネルギーは長時間でゆっくり減り続ける(有界ではない)。

``system``: ``"harmonic"``(omega)/ ``"pendulum"``(omega)/ ``"kepler"``(mu、2-D)。
門: Verlet のエネルギー誤差が有界 / 時間反転で戻る / Euler の増幅率が (1 + ω²dt²)^n。

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

- [numerics_tour](../../../../examples/numerics_tour.py) — `py -3.11 examples/numerics_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[dynsys_poincare_section](../dynsys/dynsys_poincare_section.md) · [dwt_inverse](../transform/dwt_inverse.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md)

## 同カテゴリ(`numerics`)

[erf](erf.md) · [erfc](erfc.md) · [bessel](bessel.md) · [gauss_quadrature](gauss_quadrature.md) · [gauss_cubature](gauss_cubature.md) · [chebyshev_coeffs_nd](chebyshev_coeffs_nd.md) · [chebyshev_eval_nd](chebyshev_eval_nd.md) · [low_discrepancy](low_discrepancy.md)

---
*Provenance: mathnumerics.py — MATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
